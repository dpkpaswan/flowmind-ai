"""
FlowMind AI — Mock Firebase Client
In-memory mock that mirrors Firebase Realtime DB interface.
Can be swapped for real Firebase with a config change.
"""

import threading
from typing import Any, Dict, Optional
from copy import deepcopy


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
                return deepcopy(self._data) if path == "/" else None
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


# ── Singleton Instance ───────────────────────────────────────────────────────

db = MockFirebaseDB()
