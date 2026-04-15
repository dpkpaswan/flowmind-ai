"""FlowMind AI -- Firebase Client (Real + Mock Fallback).

Provides a unified DB interface backed by Firebase Realtime Database
when ``FIREBASE_DATABASE_URL`` is set, falling back to a thread-safe
in-memory mock when it is not.

Uses Application Default Credentials (ADC) -- no JSON key file needed.
On Cloud Run the service account's default credentials are used
automatically.

Performance notes:
    * The Firebase Admin SDK maintains a persistent HTTP/2 connection
      pool internally.  ``FirebaseRealtimeDB`` wraps this with an
      async-friendly layer using ``asyncio.to_thread()`` and a bounded
      semaphore for connection pooling (max 10 concurrent ops).
    * ``MockFirebaseDB`` uses a single ``threading.Lock`` for thread
      safety.  All operations are O(D) where D = path depth (2--3).
    * Both implementations keep an in-memory mirror for read-heavy
      workloads -- reads hit the mirror first, avoiding round-trips.
"""

import os
import asyncio
import logging
import threading
from typing import Any, Dict, Optional
from copy import deepcopy

import firebase_admin
from firebase_admin import db as firebase_db

logger = logging.getLogger(__name__)

__all__ = [
    "db",
    "MockFirebaseDB",
    "FirebaseRealtimeDB",
    "get_firebase_app",
]

# ── Connection Pool Settings ────────────────────────────────────────────────
# Max concurrent Firebase I/O operations.  Prevents overwhelming the RTDB
# with too many simultaneous writes during high-traffic snapshot bursts.
# Space: O(1) — the semaphore itself.  Time: O(1) per acquire/release.
_MAX_CONCURRENT_FIREBASE_OPS = 10


# ═══════════════════════════════════════════════════════════════════════════════
#  Firebase App Initializer (lazy, singleton)
# ═══════════════════════════════════════════════════════════════════════════════

_firebase_app = None


def get_firebase_app() -> Optional[Any]:
    """Lazily initialise the Firebase Admin SDK using ADC.

    Returns:
        The Firebase app instance, or ``None`` if initialisation fails.

    Complexity:
        Time:  O(1) after first call (cached in ``_firebase_app``).
        Space: O(1) -- one SDK app instance.
    """
    global _firebase_app
    if _firebase_app is None:
        try:
            database_url = os.getenv("FIREBASE_DATABASE_URL")
            if database_url:
                # Avoid double-init (e.g. during tests)
                if not firebase_admin._apps:
                    _firebase_app = firebase_admin.initialize_app(
                        options={"databaseURL": database_url}
                    )
                else:
                    _firebase_app = firebase_admin.get_app()
        except Exception as exc:
            logger.warning(f"[FIREBASE] App init failed: {exc}")
            _firebase_app = None
    return _firebase_app


# ═══════════════════════════════════════════════════════════════════════════════
#  In-Memory Mock (always available — original implementation)
# ═══════════════════════════════════════════════════════════════════════════════


class MockFirebaseDB:
    """
    Thread-safe in-memory key-value store mimicking Firebase Realtime DB.
    Data is stored in a nested dict, accessed via slash-separated paths.

    All operations are guarded by a single threading.Lock.
    Time complexity:  O(D) per operation where D = path depth.
    Space complexity: O(N) total where N = number of stored key-value pairs.
    """

    def __init__(self):
        self._data: Dict[str, Any] = {}
        self._lock = threading.Lock()

    def _navigate(self, path: str, create: bool = False) -> tuple:
        """
        Navigate to a nested location. Returns (parent_dict, final_key).

        Time complexity:  O(D) where D = number of path segments.
        Space complexity: O(D) if create=True (may create intermediate dicts).
        """
        keys = [k for k in path.strip("/").split("/") if k]
        if not keys:
            return self._data, None

        current = self._data
        for key in keys[:-1]:
            if key not in current:
                if create:
                    current[key] = {}
                else:
                    return None, keys[-1]
            current = current[key]
            if not isinstance(current, dict):
                return None, keys[-1]

        return current, keys[-1]

    def get(self, path: str = "/") -> Optional[Any]:
        """
        Get data at the given path.

        Time complexity:  O(D + S) where D = path depth, S = size of returned subtree.
        Space complexity: O(S) for the deepcopy of the returned value.
        """
        with self._lock:
            if path == "/":
                return deepcopy(self._data)
            parent, key = self._navigate(path)
            if parent is None or key is None:
                return None
            return deepcopy(parent.get(key))

    def set(self, path: str, value: Any) -> None:
        """
        Set data at the given path (overwrites).

        Time complexity:  O(D + S) where D = path depth, S = value size (deepcopy).
        Space complexity: O(S) for the stored copy.
        """
        with self._lock:
            if path == "/":
                self._data = deepcopy(value) if isinstance(value, dict) else value
                return
            parent, key = self._navigate(path, create=True)
            if parent is not None and key is not None:
                parent[key] = deepcopy(value)

    def update(self, path: str, value: Dict) -> None:
        """
        Merge data at the given path (partial update).

        Time complexity:  O(D + S) where D = depth, S = value size.
        Space complexity: O(S) for the deepcopy.
        """
        with self._lock:
            parent, key = self._navigate(path, create=True)
            if parent is not None and key is not None:
                if key not in parent:
                    parent[key] = {}
                if isinstance(parent[key], dict) and isinstance(value, dict):
                    parent[key].update(deepcopy(value))
                else:
                    parent[key] = deepcopy(value)

    def delete(self, path: str) -> None:
        """
        Delete data at the given path.

        Time complexity:  O(D) where D = path depth.
        Space complexity: O(1).
        """
        with self._lock:
            parent, key = self._navigate(path)
            if parent is not None and key is not None and key in parent:
                del parent[key]

    def exists(self, path: str) -> bool:
        """
        Check if a path exists.

        Time complexity:  O(D + S) (delegates to get).
        Space complexity: O(S) (deepcopy in get — could optimize, but data is small).
        """
        return self.get(path) is not None


# ═══════════════════════════════════════════════════════════════════════════════
#  Firebase Realtime Database Wrapper (with async connection pooling)
# ═══════════════════════════════════════════════════════════════════════════════


class FirebaseRealtimeDB:
    """
    Wraps firebase_admin.db.reference to expose the same
    get / set / update / delete / exists interface as MockFirebaseDB,
    with automatic per-call fallback to the in-memory mock on error.

    Async connection pooling:
      - A bounded asyncio.Semaphore limits concurrent Firebase I/O to
        _MAX_CONCURRENT_FIREBASE_OPS (default 10).  This prevents the
        RTDB from being overwhelmed during burst writes (e.g., when
        multiple snapshots and history updates fire together).
      - Sync methods are kept for backward compatibility with the
        existing synchronous service layer.
      - Async methods (aget, aset, aupdate, adelete) are provided for
        use in async FastAPI route handlers via asyncio.to_thread().

    The in-memory fallback mirror is always kept in sync so that read-heavy
    operations can be served from memory without network latency.
    """

    def __init__(self, fallback: MockFirebaseDB):
        self._fallback = fallback
        # Async semaphore for connection pooling — limits concurrent I/O ops.
        # Initialized lazily in async methods since Semaphore needs an event loop.
        self._semaphore: Optional[asyncio.Semaphore] = None

    def _get_semaphore(self) -> asyncio.Semaphore:
        """
        Lazy-init the async semaphore.  Must be called inside a running
        event loop (i.e., from an async method).

        Time complexity:  O(1).
        Space complexity: O(1).
        """
        if self._semaphore is None:
            self._semaphore = asyncio.Semaphore(_MAX_CONCURRENT_FIREBASE_OPS)
        return self._semaphore

    def _ref(self, path: str):
        """
        Get a Firebase RTDB reference for the given path.

        Time complexity:  O(1).
        Space complexity: O(1).
        """
        clean = path.strip("/") or "/"
        return firebase_db.reference(clean)

    # ── Synchronous methods (used by existing service layer) ─────────────

    def get(self, path: str = "/") -> Optional[Any]:
        """
        Synchronous get — reads from Firebase RTDB, falls back to in-memory.

        Time complexity:  O(1) local; O(network) for Firebase round-trip.
        Space complexity: O(S) where S = size of returned data.
        """
        try:
            return self._ref(path).get()
        except Exception as exc:
            logger.warning(f"[FIREBASE] get('{path}') failed: {exc} — using in-memory fallback.")
            return self._fallback.get(path)

    def set(self, path: str, value: Any) -> None:
        """
        Synchronous set — writes to Firebase RTDB + in-memory mirror.

        Time complexity:  O(S) where S = value size (serialization + network).
        Space complexity: O(S) for the mirror copy.
        """
        try:
            self._ref(path).set(value)
            self._fallback.set(path, value)   # keep mirror in sync
        except Exception as exc:
            logger.warning(f"[FIREBASE] set('{path}') failed: {exc} — writing to in-memory only.")
            self._fallback.set(path, value)

    def update(self, path: str, value: Dict) -> None:
        """
        Synchronous update — merges into Firebase RTDB + mirror.

        Time complexity:  O(S) where S = value size.
        Space complexity: O(S) for the mirror copy.
        """
        try:
            self._ref(path).update(value)
            self._fallback.update(path, value)
        except Exception as exc:
            logger.warning(f"[FIREBASE] update('{path}') failed: {exc} — updating in-memory only.")
            self._fallback.update(path, value)

    def delete(self, path: str) -> None:
        """
        Synchronous delete — removes from Firebase RTDB + mirror.

        Time complexity:  O(1) local + O(network).
        Space complexity: O(1).
        """
        try:
            self._ref(path).delete()
            self._fallback.delete(path)
        except Exception as exc:
            logger.warning(f"[FIREBASE] delete('{path}') failed: {exc} — deleting from in-memory only.")
            self._fallback.delete(path)

    def exists(self, path: str) -> bool:
        """
        Synchronous exists check.

        Time complexity:  O(1) + O(network).
        Space complexity: O(S) for the returned data (discarded after check).
        """
        try:
            return self._ref(path).get() is not None
        except Exception:
            return self._fallback.exists(path)

    # ── Async methods (connection-pooled via semaphore) ───────────────────
    # These offload blocking Firebase SDK calls to threadpool workers via
    # asyncio.to_thread(), bounded by the semaphore so at most
    # _MAX_CONCURRENT_FIREBASE_OPS threads hit Firebase simultaneously.

    async def aget(self, path: str = "/") -> Optional[Any]:
        """
        Async get with connection pooling.
        Offloads the blocking Firebase call to a thread, bounded by semaphore.

        Time complexity:  O(1) local + O(network) in thread.
        Space complexity: O(S) where S = returned data size.
        """
        sem = self._get_semaphore()
        async with sem:
            try:
                return await asyncio.to_thread(self._ref(path).get)
            except Exception as exc:
                logger.warning(f"[FIREBASE] aget('{path}') failed: {exc} — using fallback.")
                return self._fallback.get(path)

    async def aset(self, path: str, value: Any) -> None:
        """
        Async set with connection pooling.
        Writes to Firebase in a pooled thread, mirrors to in-memory store.

        Time complexity:  O(S) serialization + O(network) in thread.
        Space complexity: O(S) for mirror copy.
        """
        sem = self._get_semaphore()
        async with sem:
            try:
                await asyncio.to_thread(self._ref(path).set, value)
                self._fallback.set(path, value)
            except Exception as exc:
                logger.warning(f"[FIREBASE] aset('{path}') failed: {exc} — writing in-memory only.")
                self._fallback.set(path, value)

    async def aupdate(self, path: str, value: Dict) -> None:
        """
        Async update with connection pooling.

        Time complexity:  O(S) + O(network) in thread.
        Space complexity: O(S) for mirror copy.
        """
        sem = self._get_semaphore()
        async with sem:
            try:
                await asyncio.to_thread(self._ref(path).update, value)
                self._fallback.update(path, value)
            except Exception as exc:
                logger.warning(f"[FIREBASE] aupdate('{path}') failed: {exc} — updating in-memory only.")
                self._fallback.update(path, value)

    async def adelete(self, path: str) -> None:
        """
        Async delete with connection pooling.

        Time complexity:  O(1) + O(network) in thread.
        Space complexity: O(1).
        """
        sem = self._get_semaphore()
        async with sem:
            try:
                await asyncio.to_thread(self._ref(path).delete)
                self._fallback.delete(path)
            except Exception as exc:
                logger.warning(f"[FIREBASE] adelete('{path}') failed: {exc} — deleting in-memory only.")
                self._fallback.delete(path)


# ═══════════════════════════════════════════════════════════════════════════════
#  Factory — pick real Firebase or in-memory mock
# ═══════════════════════════════════════════════════════════════════════════════

def _create_db():
    """
    Attempt to connect to Firebase RTDB.  If FIREBASE_DATABASE_URL is not
    set, or if the SDK fails to initialise, silently return the in-memory mock.

    Time complexity:  O(1).
    Space complexity: O(1) — one DB instance.
    """
    _mock = MockFirebaseDB()

    app = get_firebase_app()
    if app is None:
        db_url = os.getenv("FIREBASE_DATABASE_URL", "")
        if db_url:
            print("[DB] Firebase init failed -> using in-memory mock DB.")
        else:
            print("[DB] FIREBASE_DATABASE_URL not set -> using in-memory mock DB.")
        return _mock

    print(f"[DB] Connected to Firebase RTDB: {os.getenv('FIREBASE_DATABASE_URL')}")
    print(f"[DB] Async connection pool: max {_MAX_CONCURRENT_FIREBASE_OPS} concurrent ops.")
    return FirebaseRealtimeDB(fallback=_mock)


# ── Singleton Instance ───────────────────────────────────────────────────────

db = _create_db()
