import hashlib
import hmac
import secrets

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from .database import get_db
from .models import User

ITER = 200_000


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, ITER)
    return f"pbkdf2_sha256${ITER}${salt.hex()}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, iters, salt, digest = stored.split("$")
        dk = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), int(iters))
        return hmac.compare_digest(dk.hex(), digest)
    except Exception:
        return False


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User | None:
    uid = request.session.get("user_id")
    return db.get(User, uid) if uid else None


def login_required(user: User | None = Depends(get_current_user)) -> User:
    if user is None:
        raise HTTPException(401, "Please sign in")
    return user


def require_role(*roles: str):
    """Dependency factory: every admin/staff route uses it, so role checks cannot be forgotten."""
    def dep(user: User = Depends(login_required)) -> User:
        if user.role not in roles:
            raise HTTPException(403, "You do not have permission to open this page")
        return user
    return dep


def csrf_token(request: Request) -> str:
    tok = request.session.get("csrf")
    if not tok:
        tok = secrets.token_urlsafe(24)
        request.session["csrf"] = tok
    return tok


async def csrf_protect(request: Request):
    """Reject any POST that lacks the session's CSRF token (form field or X-CSRF-Token header)."""
    sent = request.headers.get("x-csrf-token")
    if not sent:
        form = await request.form()
        sent = form.get("csrf_token")
    expected = request.session.get("csrf", "")
    if not sent or not expected or not hmac.compare_digest(str(sent), expected):
        raise HTTPException(403, "Invalid or missing CSRF token")


def flash(request: Request, message: str, kind: str = "info"):
    request.session.setdefault("flashes", [])
    request.session["flashes"] = request.session["flashes"] + [[kind, message]]


def pop_flashes(request: Request) -> list:
    return request.session.pop("flashes", [])
