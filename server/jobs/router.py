"""/jobs - list the sample jobs and trigger the alert run by hand."""
from fastapi import APIRouter

from .alerts import run_alerts
from .scheduler import lifespan
from .store import load_jobs

router = APIRouter(prefix="/jobs", tags=["jobs"], lifespan=lifespan)


@router.get("")
async def list_jobs(q: str = "", limit: int = 10):
    from .store import matches

    jobs = [j for j in load_jobs() if matches(j, q)]
    return {"jobs": jobs[: max(1, min(limit, 50))]}


@router.post("/run-alerts")
async def run_alerts_now():
    """Demo trigger: do now what the scheduler does every few minutes."""
    return await run_alerts()
