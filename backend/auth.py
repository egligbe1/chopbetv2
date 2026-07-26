"""
Authentication utilities for the admin panel.

- Passwords are hashed with bcrypt.
- Sessions are stateless JWTs signed with JWT_SECRET_KEY.
- An initial admin is seeded from ADMIN_USERNAME / ADMIN_PASSWORD env vars.
"""

import os
import hmac
import logging
from datetime import datetime, timedelta, UTC

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from dotenv import load_dotenv

from database import SessionLocal
from models import AdminUser

load_dotenv()
logger = logging.getLogger(__name__)

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = int(os.getenv("ACCESS_TOKEN_EXPIRE_HOURS", "12"))

# Break-glass password reset. When unset, the reset endpoint is disabled entirely.
ADMIN_RESET_KEY = os.getenv("ADMIN_RESET_KEY", "")
MIN_PASSWORD_LENGTH = 8

if not JWT_SECRET_KEY:
    logger.warning(
        "JWT_SECRET_KEY is not set. Falling back to an insecure default — "
        "set JWT_SECRET_KEY in your environment before deploying."
    )
    JWT_SECRET_KEY = "change-me-insecure-dev-secret"

# tokenUrl is informational (used by OpenAPI docs); login lives at /admin/login.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="admin/login")


# ── Password hashing ────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


# ── JWT ───────────────────────────────────────────────────────────────────

def create_access_token(username: str) -> str:
    expire = datetime.now(UTC) + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    payload = {"sub": username, "exp": expire}
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def get_current_admin(token: str = Depends(oauth2_scheme)) -> str:
    """FastAPI dependency: validate the Bearer JWT and return the admin username."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        username = payload.get("sub")
        if not username:
            raise credentials_exception
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.PyJWTError:
        raise credentials_exception

    # Confirm the user still exists
    db = SessionLocal()
    try:
        user = db.query(AdminUser).filter(AdminUser.username == username).first()
        if not user:
            raise credentials_exception
        return user.username
    finally:
        db.close()


class ResetError(Exception):
    """Raised when a break-glass password reset is rejected. `status` is the HTTP code to return."""

    def __init__(self, message: str, status: int):
        super().__init__(message)
        self.message = message
        self.status = status


def reset_password_with_key(username: str, reset_key: str, new_password: str) -> None:
    """
    Break-glass reset: verify the shared ADMIN_RESET_KEY and set a new password.
    Raises ResetError (with an HTTP status) on any failure.
    """
    if not ADMIN_RESET_KEY:
        raise ResetError("Password reset is not enabled on this server.", 403)

    # Constant-time comparison so the key can't be guessed via timing.
    if not hmac.compare_digest(reset_key or "", ADMIN_RESET_KEY):
        raise ResetError("Invalid reset key.", 401)

    if len(new_password or "") < MIN_PASSWORD_LENGTH:
        raise ResetError(f"New password must be at least {MIN_PASSWORD_LENGTH} characters.", 400)

    db = SessionLocal()
    try:
        user = db.query(AdminUser).filter(AdminUser.username == username).first()
        if not user:
            raise ResetError("No admin account found with that username.", 404)
        user.password_hash = hash_password(new_password)
        db.commit()
        logger.info(f"Password reset via break-glass key for admin '{username}'.")
    except ResetError:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Password reset failed for '{username}': {e}")
        raise ResetError("Password reset failed. Please try again.", 500)
    finally:
        db.close()


def authenticate_admin(username: str, password: str) -> AdminUser | None:
    db = SessionLocal()
    try:
        user = db.query(AdminUser).filter(AdminUser.username == username).first()
        if user and verify_password(password, user.password_hash):
            return user
        return None
    finally:
        db.close()


# ── Seeding ─────────────────────────────────────────────────────────────────

def seed_admin_user() -> None:
    """Create the initial admin from ADMIN_USERNAME / ADMIN_PASSWORD if it doesn't exist."""
    username = os.getenv("ADMIN_USERNAME")
    password = os.getenv("ADMIN_PASSWORD")

    if not username or not password:
        logger.warning(
            "ADMIN_USERNAME / ADMIN_PASSWORD not set — skipping admin seed. "
            "No admin account will be available until these are configured."
        )
        return

    db = SessionLocal()
    try:
        existing = db.query(AdminUser).filter(AdminUser.username == username).first()
        if existing:
            logger.info(f"Admin user '{username}' already exists — skipping seed.")
            return
        admin = AdminUser(username=username, password_hash=hash_password(password))
        db.add(admin)
        db.commit()
        logger.info(f"Seeded initial admin user '{username}'.")
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to seed admin user: {e}")
    finally:
        db.close()
