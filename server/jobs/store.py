"""Sample jobs from data/jobs.json (read fresh each time, so edits show up without a restart)."""
import datetime
import json

from server.channels.config import JOBS_FILE
from server.channels.strings import t


def load_jobs(include_expired: bool = False) -> list:
    """All jobs, newest first."""
    try:
        jobs = json.loads(JOBS_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    today = datetime.date.today().isoformat()
    if not include_expired:
        jobs = [j for j in jobs if (j.get("deadline") or "9999") >= today]
    return sorted(jobs, key=lambda j: j.get("posted") or "", reverse=True)


def get_job(job_id: str):
    return next((j for j in load_jobs(include_expired=True) if j["id"] == job_id), None)


def matches(job: dict, keyword: str) -> bool:
    keyword = (keyword or "").strip().lower()
    if keyword in ("", "*", "all"):
        return True
    desc = job.get("description") or {}
    haystack = " ".join(
        [job.get("title", ""), job.get("company", ""), job.get("location", ""),
         " ".join(job.get("skills") or []), desc.get("en", ""), desc.get("am", "")]
    ).lower()
    return keyword in haystack


def format_job(job: dict, lang: str) -> str:
    """Multi-line text for Telegram."""
    desc = job.get("description") or {}
    lines = [
        "{} - {}".format(job["title"], job["company"]),
        job["location"] + (" ({})".format(t(lang, "job_remote")) if job.get("remote") else ""),
        desc.get(lang) or desc.get("en", ""),
        "{}: {}".format(t(lang, "job_skills"), ", ".join(job.get("skills") or [])),
        "{}: {}".format(t(lang, "job_deadline"), job["deadline"]),
        job["link"],
    ]
    return "\n".join(line for line in lines if line)


def format_job_sms(job: dict, lang: str) -> str:
    """One compact line for SMS."""
    return "{}, {}. {} {}. {}".format(
        job["title"], job["company"], t(lang, "job_deadline"), job["deadline"], job["link"]
    )


def jobs_list_sms(lang: str, limit: int = 3) -> str:
    jobs = load_jobs()[:limit]
    if not jobs:
        return t(lang, "jobs_none")
    items = ["{}. {} ({}, {})".format(i, j["title"], j["company"], j["deadline"][5:]) for i, j in enumerate(jobs, 1)]
    return t(lang, "jobs_header") + " " + " ".join(items)
