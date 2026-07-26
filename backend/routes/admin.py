import os
import hmac
import asyncio
from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel

from gemini_engine import generate_predictions
from results_checker import check_results
from database import SessionLocal
from models import Prediction
from cache import invalidate_cache
from rate_limit import limiter
from auth import (
    authenticate_admin,
    create_access_token,
    get_current_admin,
    reset_password_with_key,
    ResetError,
)

router = APIRouter(prefix="/admin", tags=["admin"])

# Shared secret for external cron callers (QStash). When unset, cron endpoints
# are disabled. This lets an external scheduler wake the backend and run jobs
# so the service can sleep between them (Render free-tier hour budget).
CRON_SECRET = os.getenv("CRON_SECRET", "")


def verify_cron_secret(x_cron_secret: str = Header(default="")):
    if not CRON_SECRET:
        raise HTTPException(status_code=503, detail="Cron endpoints are disabled (CRON_SECRET not set).")
    if not hmac.compare_digest(x_cron_secret, CRON_SECRET):
        raise HTTPException(status_code=401, detail="Invalid cron secret.")


class LoginRequest(BaseModel):
    username: str
    password: str


class ResetPasswordRequest(BaseModel):
    username: str
    reset_key: str
    new_password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str


@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")
async def login(request: Request, payload: LoginRequest):
    """Authenticate an admin with username/password and return a JWT."""
    user = authenticate_admin(payload.username, payload.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
        )
    token = create_access_token(user.username)
    return TokenResponse(access_token=token, username=user.username)


@router.post("/reset-password")
@limiter.limit("5/hour")
async def reset_password(request: Request, payload: ResetPasswordRequest):
    """Break-glass password reset gated by the shared ADMIN_RESET_KEY (no login required)."""
    try:
        reset_password_with_key(payload.username, payload.reset_key, payload.new_password)
    except ResetError as e:
        raise HTTPException(status_code=e.status, detail=e.message)
    return {"message": "Password reset successfully. You can now log in with your new password."}


@router.get("/me")
async def me(admin: str = Depends(get_current_admin)):
    """Return the current authenticated admin — used by the frontend to validate a stored token."""
    return {"username": admin}


@router.post("/trigger-predictions")
async def trigger_predictions(admin: str = Depends(get_current_admin)):
    """Trigger prediction engine in a thread pool so the event loop stays unblocked."""
    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, generate_predictions)
        return {"message": "Football prediction generation completed successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/trigger-results")
async def trigger_results(admin: str = Depends(get_current_admin)):
    """Trigger results checker in a thread pool so the event loop stays unblocked."""
    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, check_results)
        return {"message": "Results check completed successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cron/predictions", status_code=202)
async def cron_predictions(background: BackgroundTasks, _=Depends(verify_cron_secret)):
    """External-cron (QStash) entrypoint to generate predictions. Returns 202
    immediately and runs the job in a background thread so the caller doesn't
    time out; the service stays awake until the job finishes, then idles."""
    background.add_task(generate_predictions)
    return {"message": "Prediction generation started."}


@router.post("/cron/results", status_code=202)
async def cron_results(background: BackgroundTasks, _=Depends(verify_cron_secret)):
    """External-cron (QStash) entrypoint to check results. Returns 202 immediately
    and runs the job in a background thread."""
    background.add_task(check_results)
    return {"message": "Results check started."}


@router.post("/clear-pending")
async def clear_pending_predictions(admin: str = Depends(get_current_admin)):
    """Deletes all unmatched 'pending' predictions."""
    db = SessionLocal()
    try:
        deleted_count = db.query(Prediction).filter(Prediction.status == "pending").delete()
        db.commit()
        invalidate_cache()
        return {"message": f"Successfully deleted {deleted_count} pending predictions."}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()
