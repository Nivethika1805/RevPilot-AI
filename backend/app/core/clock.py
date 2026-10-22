from datetime import datetime, timezone
from app.core.config import settings

class Clock:
    """Injectable Clock for deterministic, reproducible time in rules and tests."""
    def __init__(self, fixed_now: datetime | None = None):
        self._fixed_now = fixed_now

    def now(self) -> datetime:
        if self._fixed_now is not None:
            return self._fixed_now
        # If AS_OF_DATE is configured, use it for consistent scoring/overdue dates
        if settings.AS_OF_DATE:
            return settings.as_of_datetime
        return datetime.now(timezone.utc)

    def set_now(self, now: datetime | None) -> None:
        self._fixed_now = now

_global_clock = Clock()

def get_clock() -> Clock:
    return _global_clock
