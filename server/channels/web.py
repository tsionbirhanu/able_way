"""Shared Jinja setup for the server-rendered pages of the channels / handoff work."""
from fastapi.templating import Jinja2Templates

from .config import TEMPLATES_DIR
from .strings import LANGS, norm_lang, t

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
templates.env.globals.update(t=t, LANGS=LANGS)


def render(request, name: str, lang: str, status_code: int = 200, **context):
    lang = norm_lang(lang)
    context.update(lang=lang)
    resp = templates.TemplateResponse(request, name, context, status_code=status_code)
    resp.headers["Cache-Control"] = "no-store"
    return resp
