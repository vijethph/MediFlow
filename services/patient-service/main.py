"""FastAPI application main entry point."""
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import make_asgi_app
from contextlib import asynccontextmanager
import time
import logging

from config import settings
from database import init_db, close_db
from patients import router as patients_router
from cache import init_redis, close_redis

# Optional FHIR support
try:
    from fhir_patients import router as fhir_patients_router
    FHIR_ENABLED = True
except ImportError as e:
    FHIR_ENABLED = False
    import logging
    logger = logging.getLogger(__name__)
    logger.warning(f"FHIR support disabled: {e}")
from middleware.security import SecurityHeadersMiddleware
from middleware.correlation import CorrelationIDMiddleware
from middleware.rate_limit import limiter, rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    # Startup
    logger.info("Starting Patient Management Service...")
    try:
        await init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
    
    # Initialize Redis if enabled
    if settings.redis_enabled:
        try:
            await init_redis()
        except Exception as e:
            logger.warning(f"Redis initialization failed: {e}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Patient Management Service...")
    await close_db()
    logger.info("Database connections closed")
    
    # Close Redis connection
    if settings.redis_enabled:
        await close_redis()


# Create FastAPI application
app = FastAPI(
    title=settings.service_name,
    version="1.0.0",
    description="Patient Management Service - Microservice #1 for Healthcare Patient Management System",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security headers middleware
app.add_middleware(SecurityHeadersMiddleware)

# Correlation ID middleware
app.add_middleware(CorrelationIDMiddleware)

# Rate limiting
if True:
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests."""
    start_time = time.time()
    
    # Log request
    logger.info(f"{request.method} {request.url.path}")
    
    # Process request
    response = await call_next(request)
    
    # Calculate duration
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    
    # Log response
    logger.info(
        f"{request.method} {request.url.path} - "
        f"Status: {response.status_code} - "
        f"Time: {process_time:.4f}s"
    )
    
    return response


# Exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"}
    )


# Include routers
app.include_router(patients_router)

# Include FHIR router if available
if FHIR_ENABLED:
    app.include_router(fhir_patients_router)

# Include advanced search router
from advanced_search import router as advanced_search_router
app.include_router(advanced_search_router)

# Health check endpoint (simple, no auth required)
@app.get("/health", tags=["health"])
async def health():
    """Simple health check endpoint."""
    return {"status": "healthy", "service": settings.service_name}


# Metrics endpoint
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)


# Root endpoint
@app.get("/", tags=["root"])
async def root():
    """Root endpoint."""
    return {
        "service": settings.service_name,
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
        "health": "/health"
    }

