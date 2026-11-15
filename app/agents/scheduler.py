import asyncio
import logging

from ..config import settings
from ..database import SessionLocal
from .messages import Message
from .registry import bus

log = logging.getLogger("eventsphere.scheduler")


def run_sweep():
    with SessionLocal() as db:
        bus.send(db, Message.make("Scheduler", "WaitlistAgent", "INFORM", None, topic="sweep"))
        db.commit()


async def sweep_loop():
    while True:
        await asyncio.sleep(settings.sweep_seconds)
        try:
            await asyncio.to_thread(run_sweep)
        except Exception:  # keep the loop alive
            log.exception("sweep failed")
