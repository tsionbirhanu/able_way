"""A plain asyncio loop that runs the job alerts every few minutes (ALERTS_INTERVAL_MINUTES)."""
import asyncio
from contextlib import asynccontextmanager

from server.channels.config import alerts_interval_minutes, log

from .alerts import run_alerts


async def _loop(minutes: float) -> None:
    while True:
        await asyncio.sleep(minutes * 60)
        try:
            summary = await run_alerts()
            if summary["sent"] or summary["failed"]:
                log.info("job alerts: %s sent, %s failed", summary["sent"], summary["failed"])
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            log.error("job alerts run failed: %s", type(exc).__name__)


@asynccontextmanager
async def lifespan(app):
    minutes = alerts_interval_minutes()
    task = asyncio.create_task(_loop(minutes)) if minutes > 0 else None
    if task:
        log.info("Job alert scheduler runs every %g minutes.", minutes)
    try:
        yield
    finally:
        if task:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
