import os
import asyncio
from fastapi import APIRouter, Header, HTTPException
from gemini_engine import generate_predictions
from results_checker import check_results
from database import SessionLocal
from models import Prediction
from dotenv import load_dotenv

load_dotenv()

router = APIRouter(prefix="/admin", tags=["admin"])

ADMIN_API_KEY = os.getenv("ADMIN_API_KEY")

def verify_admin_key(x_admin_key: str = Header(...)):
    if x_admin_key != ADMIN_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid Admin Key")

@router.post("/trigger-predictions")
async def trigger_predictions(x_admin_key: str = Header(...)):
    """Trigger prediction engine in a thread pool so the event loop stays unblocked."""
    verify_admin_key(x_admin_key)
    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, generate_predictions)
        return {"message": "Football prediction generation completed successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/trigger-results")
async def trigger_results(x_admin_key: str = Header(...)):
    """Trigger results checker in a thread pool so the event loop stays unblocked."""
    verify_admin_key(x_admin_key)
    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, check_results)
        return {"message": "Results check completed successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/clear-pending")
async def clear_pending_predictions(x_admin_key: str = Header(...)):
    """Deletes all unmatched 'pending' predictions."""
    verify_admin_key(x_admin_key)
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
