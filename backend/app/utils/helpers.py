"""
FlowMind AI — Utility Helpers
Common utility functions used across the application.
"""

from datetime import datetime, timezone


def now_iso() -> str:
    """Return current UTC time as ISO 8601 string."""
    return datetime.now(timezone.utc).isoformat()


def clamp(value: float, min_val: float = 0.0, max_val: float = 1.0) -> float:
    """Clamp a value between min and max."""
    return max(min_val, min(max_val, value))


def density_to_status(density: float) -> str:
    """Convert a density float (0–1) to a human-readable status."""
    if density >= 0.90:
        return "critical"
    elif density >= 0.75:
        return "high"
    elif density >= 0.40:
        return "moderate"
    return "low"


def minutes_to_human(minutes: float) -> str:
    """Convert minutes to a human-readable string."""
    if minutes < 1:
        return "less than a minute"
    elif minutes < 60:
        m = int(minutes)
        return f"{m} minute{'s' if m != 1 else ''}"
    else:
        h = int(minutes // 60)
        m = int(minutes % 60)
        parts = [f"{h} hour{'s' if h != 1 else ''}"]
        if m > 0:
            parts.append(f"{m} minute{'s' if m != 1 else ''}")
        return " ".join(parts)
