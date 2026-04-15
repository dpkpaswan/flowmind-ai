"""FlowMind AI — Utility Helpers.

Pure-function utilities used across the application.  All functions are
O(1) time and space — no I/O, no side effects.
"""

from datetime import datetime, timezone

__all__ = [
    "now_iso",
    "clamp",
    "density_to_status",
    "minutes_to_human",
]


def now_iso() -> str:
    """Return the current UTC time as an ISO 8601 string.

    Returns:
        An ISO 8601 timestamp, e.g. ``"2026-04-14T10:35:22+00:00"``.

    Complexity:
        O(1) time and space.
    """
    return datetime.now(timezone.utc).isoformat()


def clamp(value: float, min_val: float = 0.0, max_val: float = 1.0) -> float:
    """Clamp a numeric value to a closed interval ``[min_val, max_val]``.

    Args:
        value: The value to clamp.
        min_val: Lower bound (inclusive, default 0.0).
        max_val: Upper bound (inclusive, default 1.0).

    Returns:
        ``value`` bounded to ``[min_val, max_val]``.

    Complexity:
        O(1) time and space.
    """
    return max(min_val, min(max_val, value))


def density_to_status(density: float) -> str:
    """Convert a density float (0–1) to a human-readable status label.

    Thresholds match the ``app.config.Settings`` alert thresholds:
        * ``≥ 0.90`` → ``"critical"``
        * ``≥ 0.75`` → ``"high"``
        * ``≥ 0.40`` → ``"moderate"``
        * ``< 0.40`` → ``"low"``

    Args:
        density: Zone density as a float in [0, 1].

    Returns:
        One of ``"critical"``, ``"high"``, ``"moderate"``, ``"low"``.

    Complexity:
        O(1) time and space.
    """
    if density >= 0.90:
        return "critical"
    elif density >= 0.75:
        return "high"
    elif density >= 0.40:
        return "moderate"
    return "low"


def minutes_to_human(minutes: float) -> str:
    """Convert a duration in minutes to a human-readable string.

    Examples::

        minutes_to_human(0.5)  → "less than a minute"
        minutes_to_human(7)    → "7 minutes"
        minutes_to_human(90)   → "1 hour 30 minutes"

    Args:
        minutes: Duration in minutes (may be fractional).

    Returns:
        A human-readable duration string.

    Complexity:
        O(1) time and space.
    """
    if minutes < 1:
        return "less than a minute"
    elif minutes < 60:
        m: int = int(minutes)
        return f"{m} minute{'s' if m != 1 else ''}"
    else:
        h: int = int(minutes // 60)
        m = int(minutes % 60)
        parts = [f"{h} hour{'s' if h != 1 else ''}"]
        if m > 0:
            parts.append(f"{m} minute{'s' if m != 1 else ''}")
        return " ".join(parts)
