import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.sessions import SessionMiddleware

from .agents.scheduler import sweep_loop
from .config import settings
from .database import Base, engine
from .routers import admin, api, auth, hire, public, staff
from .seed import seed
from .web import BASE, peek_user, render


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)
    if settings.seed_demo:
        seed()
    task = asyncio.create_task(sweep_loop()) if settings.enable_scheduler else None
    yield
    if task:
        task.cancel()


app = FastAPI(title="EventSphere", lifespan=lifespan)
app.add_middleware(SessionMiddleware, secret_key=settings.secret_key, https_only=settings.https_only,
                   same_site="lax", max_age=60 * 60 * 24)
app.mount("/static", StaticFiles(directory=str(BASE / "static")), name="static")
for r in (auth.router, public.router, hire.router, staff.router, admin.router, api.router):
    app.include_router(r)


@app.exception_handler(StarletteHTTPException)
async def http_error(request: Request, exc: StarletteHTTPException):
    wants_json = request.url.path.startswith(("/api/", "/staff/scan"))
    if exc.status_code == 401 and not wants_json:
        return RedirectResponse("/login", status_code=303)
    if wants_json:
        return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)
    return render(request, "error.html", peek_user(request), status_code=exc.status_code,
                  code=exc.status_code, detail=exc.detail)
