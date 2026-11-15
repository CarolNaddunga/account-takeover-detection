from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from .schemas import LoginEvent

WINDOW = timedelta(minutes=10)
MAX_SEEN_EVENT_IDS = 100_000
MAX_LATE_AUDIT_RECORDS = 1_000


@dataclass(frozen=True)
class StoredLogin:
    event_time: datetime
    result: str
    device_id: str
    ip_address: str


class InMemoryFeatureStore:
    """Demo state; production state must be durable and access-controlled."""

    def __init__(self) -> None:
        self._events: dict[str, list[StoredLogin]] = {}
        self._seen_ids: set[str] = set()
        self._seen_order: deque[str] = deque()
        self.late_review: deque[dict[str, object]] = deque(maxlen=MAX_LATE_AUDIT_RECORDS)

    def mark_seen(self, event_id: str) -> bool:
        if event_id in self._seen_ids:
            return False
        self._seen_ids.add(event_id)
        self._seen_order.append(event_id)
        while len(self._seen_order) > MAX_SEEN_EVENT_IDS:
            expired = self._seen_order.popleft()
            self._seen_ids.discard(expired)
        return True

    def record(self, event: LoginEvent) -> None:
        history = self._events.setdefault(event.account_id, [])
        history.append(
            StoredLogin(
                event_time=event.event_time,
                result=event.result,
                device_id=event.device_id,
                ip_address=event.ip_address,
            )
        )
        newest = max(item.event_time for item in history)
        cutoff = newest - WINDOW
        self._events[event.account_id] = [item for item in history if item.event_time >= cutoff]

    def recent(self, account_id: str, at: datetime) -> list[StoredLogin]:
        cutoff = at - WINDOW
        return [
            event
            for event in self._events.get(account_id, [])
            if cutoff <= event.event_time <= at
        ]

    def note_late_event(self, event: LoginEvent, delay_seconds: float) -> None:
        # Keep identifiers and timing only in the review summary, not raw IP/device values.
        self.late_review.append(
            {
                "event_id": event.event_id,
                "account_id": event.account_id,
                "event_time": event.event_time.isoformat(),
                "received_at": event.received_at.isoformat(),
                "delay_seconds": round(delay_seconds, 3),
                "recorded_at": datetime.now(timezone.utc).isoformat(),
            }
        )


feature_store = InMemoryFeatureStore()
