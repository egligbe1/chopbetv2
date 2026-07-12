import asyncio
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from gemini_engine import generate_predictions
from results_checker import check_results
from database import SessionLocal
from models import Prediction
from auth import authenticate_admin, create_access_token, get_current_admin

router = APIRouter(prefix="/admin", tags=["admin"])


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest):
    """Authenticate an admin with username/password and return a JWT."""
    user = authenticate_admin(payload.username, payload.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
        )
    token = create_access_token(user.username)
    return TokenResponse(access_token=token, username=user.username)


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


@router.post("/clear-pending")
async def clear_pending_predictions(admin: str = Depends(get_current_admin)):
    """Deletes all unmatched 'pending' predictions."""
    db = SessionLocal()
    try:
        deleted_count = db.query(Prediction).filter(Prediction.status == "pending").delete()
        db.commit()
        return {"message": f"Successfully deleted {deleted_count} pending predictions."}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()
