import os
from fastapi import APIRouter, Header, HTTPException, BackgroundTasks
from gemini_engine import generate_predictions
from results_checker import check_results
from dotenv import load_dotenv

load_dotenv()

router = APIRouter(prefix="/admin", tags=["admin"])

ADMIN_API_KEY = os.getenv("ADMIN_API_KEY")

def verify_admin_key(x_admin_key: str = Header(...)):
    if x_admin_key != ADMIN_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid Admin Key")

@router.post("/trigger-predictions")
async def trigger_predictions(background_tasks: BackgroundTasks, x_admin_key: str = Header(...)):
    """Manually trigger the daily prediction generation job for football."""
    verify_admin_key(x_admin_key)
    background_tasks.add_task(generate_predictions)
    return {"message": "Football prediction generation triggered in background."}


@router.post("/trigger-results")
async def trigger_results(background_tasks: BackgroundTasks, x_admin_key: str = Header(...)):
    """Manually trigger the daily results checking job for football."""
    verify_admin_key(x_admin_key)
    background_tasks.add_task(check_results)
    return {"message": "Results check triggered for football in background."}
