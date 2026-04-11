"""
FlowMind AI — Firebase Client (Real + Mock Fallback)
Provides a unified DB interface backed by Firebase Realtime Database
when FIREBASE_DATABASE_URL is set, falling back to a thread-safe
in-memory mock when it is not.
Uses Application Default Credentials — no JSON key file needed.
"""

import os
import logging
import threading
from typing import Any, Dict, Optional
from copy import deepcopy

import firebase_admin
from firebase_admin import db as firebase_db

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
#  Firebase App Initializer (lazy, singleton)
# ═══════════════════════════════════════════════════════════════════════════════

_firebase_app = None


def get_firebase_app():
    """
    Lazily initialise the Firebase Admin SDK using Application Default
    Credentials.  Returns the app instance on success, None on failure.
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
    """

    def __init__(self):
        self._data: Dict[str, Any] = {}
        self._lock = threading.Lock()

    def _navigate(self, path: str, create: bool = False) -> tuple:
        """Navigate to a nested location. Returns (parent_dict, final_key)."""
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
        """Get data at the given path."""
        with self._lock:
            if path == "/":
                return deepcopy(self._data)
            parent, key = self._navigate(path)
            if parent is None or key is None:
                return None
            return deepcopy(parent.get(key))

    def set(self, path: str, value: Any) -> None:
        """Set data at the given path (overwrites)."""
        with self._lock:
            if path == "/":
                self._data = deepcopy(value) if isinstance(value, dict) else value
                return
            parent, key = self._navigate(path, create=True)
            if parent is not None and key is not None:
                parent[key] = deepcopy(value)

    def update(self, path: str, value: Dict) -> None:
        """Merge data at the given path (partial update)."""
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
        """Delete data at the given path."""
        with self._lock:
            parent, key = self._navigate(path)
            if parent is not None and key is not None and key in parent:
                del parent[key]

    def exists(self, path: str) -> bool:
        """Check if a path exists."""
        return self.get(path) is not None


# ═══════════════════════════════════════════════════════════════════════════════
#  Firebase Realtime Database Wrapper
# ═══════════════════════════════════════════════════════════════════════════════


class FirebaseRealtimeDB:
    """
    Wraps firebase_admin.db.reference to expose the same
    get / set / update / delete / exists interface as MockFirebaseDB,
    with automatic per-call fallback to the in-memory mock on error.
    """

    def __init__(self, fallback: MockFirebaseDB):
        self._fallback = fallback

    def _ref(self, path: str):
        clean = path.strip("/") or "/"
        return firebase_db.reference(clean)

    def get(self, path: str = "/") -> Optional[Any]:
        try:
            return self._ref(path).get()
        except Exception as exc:
            logger.warning(f"[FIREBASE] get('{path}') failed: {exc} — using in-memory fallback.")
            return self._fallback.get(path)

    def set(self, path: str, value: Any) -> None:
        try:
            self._ref(path).set(value)
            self._fallback.set(path, value)   # keep mirror in sync
        except Exception as exc:
            logger.warning(f"[FIREBASE] set('{path}') failed: {exc} — writing to in-memory only.")
            self._fallback.set(path, value)

    def update(self, path: str, value: Dict) -> None:
        try:
            self._ref(path).update(value)
            self._fallback.update(path, value)
        except Exception as exc:
            logger.warning(f"[FIREBASE] update('{path}') failed: {exc} — updating in-memory only.")
            self._fallback.update(path, value)

    def delete(self, path: str) -> None:
        try:
            self._ref(path).delete()
            self._fallback.delete(path)
        except Exception as exc:
            logger.warning(f"[FIREBASE] delete('{path}') failed: {exc} — deleting from in-memory only.")
            self._fallback.delete(path)

    def exists(self, path: str) -> bool:
        try:
            return self._ref(path).get() is not None
        except Exception:
            return self._fallback.exists(path)


# ═══════════════════════════════════════════════════════════════════════════════
#  Factory — pick real Firebase or in-memory mock
# ═══════════════════════════════════════════════════════════════════════════════

def _create_db():
    """
    Attempt to connect to Firebase RTDB.  If FIREBASE_DATABASE_URL is not
    set, or if the SDK fails to initialise, silently return the in-memory mock.
    """
    _mock = MockFirebaseDB()

    app = get_firebase_app()
    if app is None:
        db_url = os.getenv("FIREBASE_DATABASE_URL", "")
        if db_url:
            print("[DB] Firebase init failed → using in-memory mock DB.")
        else:
            print("[DB] FIREBASE_DATABASE_URL not set → using in-memory mock DB.")
        return _mock

    print(f"[DB] Connected to Firebase RTDB: {os.getenv('FIREBASE_DATABASE_URL')}")
    return FirebaseRealtimeDB(fallback=_mock)


# ── Singleton Instance ───────────────────────────────────────────────────────

db = _create_db()
