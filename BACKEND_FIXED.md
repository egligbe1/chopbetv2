# Backend Configuration Fixed - Port 8001

## Issue Found & Resolved
**Problem:** NBA endpoint (`/admin/nba`) was returning 404 error while football endpoint (`/admin/trigger-predictions`) was working fine.

**Root Cause:** Zombie processes on port 8000 from previous failed uvicorn startups were listening but not serving the actual application code.

**Solution:** Backend server now runs on **port 8001** instead of 8000.

## Current Status

### ✅ Working Endpoints (on port 8001)
- `POST /admin/trigger-predictions` - Triggers football prediction generation
- `POST /admin/nba` - **NOW WORKING** - Triggers NBA prediction generation  
- `POST /admin/trigger-results` - Triggers results checking
- `GET /health` - Health check endpoint
- All prediction, stats, and prediction retrieval routes

### ✅ Backend Features
- FastAPI server with proper routing
- APScheduler with 3 daily jobs:
  - Football predictions at 07:00 UTC
  - NBA predictions at 07:05 UTC
  - Results check at 23:00 UTC
- Gemini AI integration for both sports
- PostgreSQL database connection
- CORS configured for frontend
- Rate limiting enabled

## Frontend Configuration
- Updated `frontend/lib/api.ts` to use `http://localhost:8001`
- Frontend running on port 3001 (due to port 3000 in use)
- Admin panel at `http://localhost:3001/admin` with three trigger buttons:
  - Football predictions
  - NBA predictions (NOW FUNCTIONAL)
  - Results check

## How to Run
```bash
# Terminal 1 - Backend (port 8001)
cd backend
python -m uvicorn main:app --host 127.0.0.1 --port 8001

# Terminal 2 - Frontend (port 3001)
cd frontend
npm run dev
```

## Testing
```bash
# Test football predictions
curl -X POST http://localhost:8001/admin/trigger-predictions \
  -H "X-Admin-Key: your_secret_admin_key_here"

# Test NBA predictions (NOW WORKS)
curl -X POST http://localhost:8001/admin/nba \
  -H "X-Admin-Key: your_secret_admin_key_here"

# Test results check
curl -X POST http://localhost:8001/admin/trigger-results \
  -H "X-Admin-Key: your_secret_admin_key_here"
```

## What Was Fixed
1. Identified and cleaned zombie processes on port 8000
2. Started backend on port 8001 (clean port)
3. Updated frontend API client and admin panel to use new port
4. Verified both football and NBA endpoints respond with 200 OK
5. Both endpoints have proper async task scheduling in background

## Next Steps
- Verify NBA predictions are being generated and stored in database
- Test through UI by clicking NBA trigger button
- Monitor logs to ensure generate_nba_predictions() executes properly
- Check database for new NBA prediction records
