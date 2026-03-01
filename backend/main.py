import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from database import engine, Base
from scheduler import start_scheduler, shutdown_scheduler
from routes.admin import router as admin_router
from routes.predictions import router as predictions_router
from routes.stats import router as stats_router
from dotenv import load_dotenv

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Rate limiter: 60 requests per minute per IP
limiter = Limiter(key_func=get_remote_address)

# Allowed frontend origins
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup & shutdown lifecycle events."""
    logger.info("ChopBet API starting up...")
    start_scheduler()
    yield
    logger.info("ChopBet API shutting down...")
    shutdown_scheduler()


app = FastAPI(
    title="ChopBet API",
    description="AI-powered football prediction platform",
    version="1.0.0",
    lifespan=lifespan
)

# Attach rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Configure CORS — restricted to frontend domain
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001", "http://localhost:3003", FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Security headers middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response: Response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    return response


# Register routers
app.include_router(predictions_router)
app.include_router(stats_router)
app.include_router(admin_router)


@app.get("/")
@limiter.limit("60/minute")
async def root(request: Request):
    return {"message": "Welcome to ChopBet API", "status": "healthy"}


@app.get("/health")
@limiter.limit("60/minute")
async def health_check(request: Request):
    return {"status": "ok"}
