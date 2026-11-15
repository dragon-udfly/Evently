from .config import now
from .models import Event

REFUND_POLICY = "Refund: 100% if 72h or more before start, 50% from 24h to 72h, 0% under 24h. Cancelled events: 100%."


def refund_pct(event: Event) -> int:
    hours = (event.start - now()).total_seconds() / 3600
    return 100 if hours >= 72 else 50 if hours >= 24 else 0
