import logging
import sys
import os

# Add current directory to path so we can import local modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from gemini_engine import generate_predictions
from results_checker import check_results
from database import SessionLocal
from models import Prediction

# Configure logging for the test
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_engines")

def run_test():
    logger.info("="*50)
    logger.info("STARTING ENGINE VERIFICATION")
    logger.info("="*50)
    
    db = SessionLocal()
    initial_count = db.query(Prediction).count()
    logger.info(f"Initial prediction count: {initial_count}")
    
    # 1. Test Prediction Engine
    logger.info("\n--- Step 1: Running Prediction Engine ---")
    try:
        generate_predictions()
        after_run1_count = db.query(Prediction).count()
        logger.info(f"Predictions after run 1: {after_run1_count}")
    except Exception as e:
        logger.error(f"Prediction engine failed: {e}")
        return

    # 2. Test Deduplication (Run again)
    logger.info("\n--- Step 2: Testing Deduplication (Running again) ---")
    try:
        generate_predictions()
        after_run2_count = db.query(Prediction).count()
        logger.info(f"Predictions after run 2 (should be same/similar if fixtures haven't changed): {after_run2_count}")
        if after_run2_count > after_run1_count + 5: # Small buffer for newly discovered fixtures
             logger.warning("Large increase in predictions detected - deduplication might be ineffective if fixtures are identical.")
        else:
             logger.info("Deduplication seems to be working (no massive surge in counts).")
    except Exception as e:
        logger.error(f"Deduplication test failed: {e}")

    # 3. Test Results Checker
    logger.info("\n--- Step 3: Running Results Checker ---")
    try:
        check_results()
        logger.info("Results checker executed successfully.")
    except Exception as e:
        logger.error(f"Results checker failed: {e}")

    db.close()
    logger.info("\n" + "="*50)
    logger.info("VERIFICATION COMPLETE")
    logger.info("="*50)

if __name__ == "__main__":
    run_test()
