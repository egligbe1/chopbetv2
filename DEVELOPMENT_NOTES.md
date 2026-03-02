# ChopBet - Development Notes

## 🎯 Key Changes Made (March 1, 2026)

### 1. Basketball (NBA) Support Pipeline ✅
**Files Modified:**
- `backend/scheduler.py` - Added NBA predictions at 7:05 AM UTC
- `backend/routes/admin.py` - Added `/admin/trigger-nba-predictions` endpoint
- `backend/gemini_engine.py` - Already had `generate_nba_predictions()` function
- `frontend/lib/api.ts` - Added `triggerNBAPredictions()` method
- `frontend/app/admin/page.tsx` - Updated admin dashboard with 3-column layout

**How it works:**
```
User clicks "Run Engine" on NBA card
  → triggerNBAPredictions(adminKey)
  → POST /admin/trigger-nba-predictions
  → Background task: generate_nba_predictions()
  → Searches NBA fixtures
  → Analyzes injury reports, lineups
  → Saves to DB with sport="basketball"
```

### 2. Dependencies Updated ✅
**File:** `backend/requirements.txt`

Added:
- `google-genai==1.2.0` - Latest Gemini API SDK
- `tavily==1.1.0` - Premium search API
- `duckduckgo-search==8.1.1` - Fallback search

These packages were already installed but missing from requirements.txt

### 3. Frontend Admin Dashboard Improved ✅
**File:** `frontend/app/admin/page.tsx`

Changes:
- Grid layout: 2 columns → 3 columns
- Added NBA predictions card with orange branding (#F58426)
- Separate trigger buttons for Football and NBA
- Better visual hierarchy

**Admin Page Flow:**
```
Login with ADMIN_API_KEY
  ↓
Three cards visible:
  [Football Predictions] [NBA Predictions] [Check Results]
  ↓
Click any "Run Engine" button
  → Backend processes in background
  → Admin page shows success/error message
```

---

## 🔧 File-by-File Changes

### `backend/scheduler.py`
```python
# BEFORE
from gemini_engine import generate_predictions

scheduler.add_job(generate_predictions, trigger=CronTrigger(hour=7, minute=0, ...))

# AFTER
from gemini_engine import generate_predictions, generate_nba_predictions

scheduler.add_job(generate_predictions, trigger=CronTrigger(hour=7, minute=0, ...))
scheduler.add_job(generate_nba_predictions, trigger=CronTrigger(hour=7, minute=5, ...))
```

### `backend/routes/admin.py`
```python
# ADDED
@router.post("/trigger-nba-predictions")
async def trigger_nba_predictions(background_tasks: BackgroundTasks, x_admin_key: str = Header(...)):
    """Manually trigger the daily NBA prediction generation job."""
    verify_admin_key(x_admin_key)
    background_tasks.add_task(generate_nba_predictions)
    return {"message": "NBA prediction generation triggered in background."}
```

### `frontend/lib/api.ts`
```typescript
// ADDED
async triggerNBAPredictions(adminKey: string): Promise<{ message: string }> {
    return this.request('/admin/trigger-nba-predictions', {
      method: 'POST',
      headers: { 'X-Admin-Key': adminKey },
    });
}
```

### `frontend/app/admin/page.tsx`
```typescript
// Changed trigger function
triggerJob = async (type: 'predictions' | 'nba-predictions' | 'results') => {
    // ... handles three types now

// Changed grid layout
<div className="grid md:grid-cols-3 gap-6"> {/* was md:grid-cols-2 */}

// Added NBA card
<div className="glass-card p-6 space-y-4">
    <h3 className="text-xl font-bold">NBA Predictions</h3>
    ...
```

---

## 📋 Testing Checklist

- [x] Scheduler calls both generate_predictions() and generate_nba_predictions()
- [x] Admin endpoints for both sports exist
- [x] Frontend toggles between football and basketball
- [x] API client has methods for both triggers
- [x] Database differentiates by sport="football" vs sport="basketball"
- [x] Results checker handles both sports
- [x] All imports work without errors
- [x] Backend loads with 17 routes
- [x] 20 sample predictions in database

### Manual Testing Commands

```bash
# Check backend loads
cd backend && python -c "from main import app; print(len(app.routes))" 
# Expected output: 17

# Test API endpoints
curl http://localhost:8000/health
curl http://localhost:8000/predictions/today?sport=football
curl http://localhost:8000/predictions/today?sport=basketball

# Test admin triggers
curl -X POST http://localhost:8000/admin/trigger-predictions \
  -H "X-Admin-Key: your_secret_admin_key_here"

curl -X POST http://localhost:8000/admin/trigger-nba-predictions \
  -H "X-Admin-Key: your_secret_admin_key_here"
```

---

## ⚠️ Important Considerations

### 1. Admin Key Security
- **Current:** Set to `"your_secret_admin_key_here"` in `.env`
- **TODO for Production:** Change this to a secure random string
- **Where used:** Admin panel authentication, triggers predictions/results checks

### 2. Search Rate Limiting
- **Football:** Max 10 matches researched per run (safety limit)
- **NBA:** Max 8 matches researched per run (API tier limit)
- **Fallback:** If Tavily API key missing, uses DuckDuckGo (slower)

### 3. Scheduler Timezone
- **Current:** All times are UTC
- **Adjust in:** `backend/scheduler.py` trigger CronTrigger settings
- Example change to GMT+1:
  ```python
  CronTrigger(hour=8, minute=0, timezone="Europe/London")
  ```

### 4. Database Predictions Schema
The `Prediction` model includes `sport` column:
```sql
sport VARCHAR DEFAULT 'football'
```
This is indexed for fast sport-based queries. Existing data might not have sport set; backend code handles this.

### 5. Frontend Environment
- **API_BASE_URL:** Defaults to `http://localhost:8000`
- **Override in:** `frontend/.env.local` as `NEXT_PUBLIC_API_URL`
- **CORS:** Configured for localhost:3000-3004 in backend

---

## 🚀 Deployment Checklist

Before deploying to production:

- [ ] Change `ADMIN_API_KEY` to secure value
- [ ] Update CORS allowed_origins in `backend/main.py`
- [ ] Configure DATABASE_URL for production database
- [ ] Set `FRONTEND_URL` to actual frontend domain
- [ ] Ensure Gemini API key is valid
- [ ] Test Tavily API key or ensure DuckDuckGo fallback works
- [ ] Set `ENV=production` in `.env`
- [ ] Run `alembic upgrade head` on production database
- [ ] Configure scheduled jobs timezone if needed
- [ ] Enable HTTPS/TLS for production
- [ ] Set up monitoring/alerting for scheduled jobs
- [ ] Review rate limiting (currently 60/minute)

---

## 🐛 Common Issues & Fixes

### Issue: "Scheduler not calling NBA predictions"
**Fix:** Already solved! See `backend/scheduler.py` - Now imports and calls both functions

### Issue: "Admin panel sports toggle doesn't work"
**Fix:** Ensure API client has `triggerNBAPredictions()` method (already added to `frontend/lib/api.ts`)

### Issue: "Predictions still show as 'pending' after results check"
**Check:** 
1. Run `POST /admin/trigger-results` to manually check
2. Verify Gemini can parse scores (check backend logs)
3. Ensure prediction statuses are in ["won", "lost", "void"]

### Issue: "DuckDuckGo warning about package rename"
**Status:** This is just a deprecation warning. Code uses correct `ddgs` package. No breaking issue.

### Issue: "Football and NBA predictions mixed up"
**Check:** Verify sport column is set correctly in database:
```sql
SELECT COUNT(*) as total, sport FROM predictions GROUP BY sport;
```

---

## 📊 Current Status Summary

| Component | Status | Notes |
|-----------|--------|-------|
| Football Predictions | ✅ Working | 7:00 AM UTC schedule |
| NBA Predictions | ✅ Working | 7:05 AM UTC schedule |
| Results Checking | ✅ Working | 11:00 PM UTC schedule |
| Admin Dashboard | ✅ Enhanced | 3 separate trigger buttons |
| Frontend Toggle | ✅ Working | Football ↔ Basketball |
| Database | ✅ Connected | 20 sample predictions |
| Gemini API | ✅ Responding | Flash model active |
| Search APIs | ✅ Working | Tavily + DuckDuckGo fallback |

---

## 🔗 Related Files

- Main prediction flow: `backend/gemini_engine.py`
- Results checking: `backend/results_checker.py`  
- Search utilities: `backend/search_utils.py`
- Database models: `backend/models.py`
- API routes: `backend/routes/{predictions,stats,admin}.py`
- Frontend pages: `frontend/app/{page,admin,stats}.tsx`
- Full analysis: `TESTING_AND_FIXES_REPORT.md`

---

Last Updated: March 1, 2026
