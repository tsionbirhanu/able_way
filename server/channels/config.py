"""Settings for the channels / handoff work. Everything comes from environment variables."""
import logging
import os
import secrets
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SERVER_DIR = REPO_ROOT / "server"
TEMPLATES_DIR = SERVER_DIR / "templates"
STATIC_DIR = SERVER_DIR / "static"
JOBS_FILE = REPO_ROOT / "data" / "jobs.json"

try:  # .env is optional; load the project's server config regardless of launch directory
    from dotenv import load_dotenv

    # The one settings file is .env at the project root (as for the tutor server, server/app.py);
    # server/.env is the older location, still read. Neither overrides a real environment variable.
    load_dotenv(dotenv_path=REPO_ROOT / ".env")
    load_dotenv(dotenv_path=SERVER_DIR / ".env")
    # Or one folder up, outside the project and outside git (as the tutor server reads it too).
    load_dotenv(dotenv_path=REPO_ROOT.parent / ".env")
except Exception:  # pragma: no cover
    pass

log = logging.getLogger("channels")

def _path(env: str, default: str) -> Path:
    p = Path(os.environ.get(env) or default)
    return p if p.is_absolute() else REPO_ROOT / p


def channels_db_path() -> Path:
    return _path("CHANNELS_DB_PATH", "data/channels.db")


def accommodations_db_path() -> Path:
    return _path("ACCOMMODATIONS_DB_PATH", "data/accommodations.db")


def telegram_token() -> str:
    return (os.environ.get("TELEGRAM_BOT_TOKEN") or "").strip()


def public_base_url() -> str:
    return (os.environ.get("PUBLIC_BASE_URL") or "http://localhost:8000").rstrip("/")


def alerts_interval_minutes() -> float:
    try:
        return float(os.environ.get("ALERTS_INTERVAL_MINUTES") or 3)
    except ValueError:
        return 3.0


_generated_password = None


def tutor_password() -> str:
    """The one shared tutor password. Generated and logged once if not configured."""
    global _generated_password
    pw = (os.environ.get("TUTOR_PASSWORD") or "").strip()
    if pw:
        return pw
    if _generated_password is None:
        _generated_password = secrets.token_urlsafe(9)
        log.warning("TUTOR_PASSWORD is not set. Temporary tutor password: %s", _generated_password)
    return _generated_password

if not log.handlers:  # make our own INFO lines visible under uvicorn without touching its config
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter("%(levelname)s:     [%(name)s] %(message)s"))
    log.addHandler(_h)
    log.setLevel(logging.INFO)
    log.propagate = False
