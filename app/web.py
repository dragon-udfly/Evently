from pathlib import Path
from fastapi import Request
from fastapi.templating import Jinja2Templates
from .database import SessionLocal
from .models import User
from .security import csrf_token, pop_flashes

BASE = Path(__file__).parent
templates = Jinja2Templates(directory=str(BASE / "templates"))
templates.env.filters["money"] = lambda v: f"{float(v or 0):,.2f}"
templates.env.filters["dt"] = lambda v: v.strftime("%a %d %b %Y, %H:%M") if v else ""
templates.env.filters["dtlocal"] = lambda v: v.strftime("%Y-%m-%dT%H:%M") if v else ""


def render(request: Request, name: str, user: User | None = None, status_code: int = 200, **ctx):
    ctx.update(user=user, flashes=pop_flashes(request), csrf=csrf_token(request))
    return templates.TemplateResponse(request, name, ctx, status_code=status_code)


