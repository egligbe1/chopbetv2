#!/usr/bin/env python3
"""
Quick integration test to verify the app setup is correct.
Tests database connection, Gemini API, and basic flow.
"""
import os
import sys
from datetime import datetime, UTC
from dotenv import load_dotenv

# Load environment
load_dotenv()

print("=" * 60)
print("CHOPBET INTEGRATION TEST")
print("=" * 60)

# Test 1: Check environment variables
print("\n[1/6] Checking environment variables...")
required_vars = ['DATABASE_URL', 'GEMINI_API_KEY', 'TAVILY_API_KEY', 'ADMIN_API_KEY']
missing = []
for var in required_vars:
    if os.getenv(var):
        print(f"  ✓ {var} found")
    else:
        print(f"  ✗ {var} missing")
        missing.append(var)

if missing:
    print(f"\n⚠️  Missing variables: {', '.join(missing)}")
    print("   These are required for full functionality")
else:
    print("  ✓ All required variables set!")

# Test 2: Database Connection
print("\n[2/6] Testing database connection...")
try:
    from database import engine, Base
    connection = engine.connect()
    connection.close()
    print("  ✓ Database connection successful")
except Exception as e:
    print(f"  ✗ Database connection failed: {e}")
    sys.exit(1)

# Test 3: Gemini API
print("\n[3/6] Testing Gemini API...")
try:
    from google import genai
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    response = client.models.generate_content(
        model="gemini-flash-latest",
        contents="Say 'Hello' in one word only.",
    )
    print(f"  ✓ Gemini API working: {response.text[:20].strip()}...")
except Exception as e:
    print(f"  ✗ Gemini API failed: {e}")

# Test 4: Search Utils
print("\n[4/6] Testing Search Utilities...")
try:
    from search_utils import search_utils
    results = search_utils.search_ddg("test query", max_results=1)
    print(f"  ✓ Search utils working: Found {len(results)} result(s)")
except Exception as e:
    print(f"  ✗ Search utils failed: {e}")

# Test 5: Models and ORM
print("\n[5/6] Testing ORM Models...")
try:
    from models import Prediction, Result, AccuracyStats
    from database import SessionLocal
    db = SessionLocal()
    
    # Query count
    count = db.query(Prediction).count()
    print(f"  ✓ Models working: {count} predictions in database")
    
    db.close()
except Exception as e:
    print(f"  ✗ Models failed: {e}")

# Test 6: Import all routes
print("\n[6/6] Testing route imports...")
try:
    from routes.predictions import router as pred_router
    from routes.stats import router as stats_router
    from routes.admin import router as admin_router
    print(f"  ✓ All route modules imported successfully")
except Exception as e:
    print(f"  ✗ Route imports failed: {e}")

print("\n" + "=" * 60)
print("✓ INTEGRATION TEST COMPLETE")
print("=" * 60)

print("\nNext steps:")
print("1. Start backend: uvicorn main:app --reload")
print("2. Start frontend: npm run dev (from frontend/)")
print("3. Visit: http://localhost:3000")
print("4. Admin panel: http://localhost:3000/admin")
