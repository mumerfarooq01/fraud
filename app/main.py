from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.config import settings
import time
# import sys
# import os

# Add path to existing fraud detection code (MUST be before importing routes!)
# sys.path.insert(0, os.path.abspath(settings.FRAUD_DETECTION_CODE_PATH))

# Import routes AFTER adding fraud-detection-poc to sys.path
from app.api.v1.routes import forensics, comparison, database

# Create FastAPI application
app = FastAPI(
    title=settings.PROJECT_NAME,
    description=settings.DESCRIPTION,
    version=settings.VERSION,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add processing time to response headers"""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = f"{process_time:.4f}"
    return response

# Include API routers
app.include_router(
    forensics.router,
    prefix=settings.API_V1_STR,
    tags=["forensics"]
)

app.include_router(
    comparison.router,
    prefix=settings.API_V1_STR,
    tags=["comparison"]
)

app.include_router(
    database.router,
    prefix=settings.API_V1_STR,
    tags=["database"]
)

# Root endpoint
@app.get("/", tags=["system"])
async def root():
    """API root endpoint"""
    return {
        "message": "Document Fraud Detection API",
        "version": settings.VERSION,
        "docs": "/api/docs",
        "health": "/health",
        "status": "operational"
    }

# Health check endpoint
@app.get("/health", tags=["system"])
async def health_check():
    """
    Health check endpoint
    Returns API status and configuration
    """
    return {
        "status": "healthy",
        "version": settings.VERSION,
        "service": settings.PROJECT_NAME,
        "timestamp": time.time(),
        "features": {
            "forensics": True,
            "comparison": True,
            "database": True
        },
        "config": {
            "max_file_size_mb": settings.MAX_FILE_SIZE_MB,
            "allowed_extensions": settings.ALLOWED_EXTENSIONS,
            "gemini_configured": bool(settings.GEMINI_API_KEY)
        }
    }

# Startup event
@app.on_event("startup")
async def startup_event():
    """Run on application startup"""
    print(f"Starting {settings.PROJECT_NAME} v{settings.VERSION}")
    # Display localhost for browser access (0.0.0.0 is just the bind address)
    display_host = "localhost" if settings.API_HOST == "0.0.0.0" else settings.API_HOST
    print(f"API Documentation: http://{display_host}:{settings.API_PORT}/api/docs")
    print(f"Health Check: http://{display_host}:{settings.API_PORT}/health")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Run on application shutdown"""
    print(f"Shutting down {settings.PROJECT_NAME}")

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle all unhandled exceptions"""
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc),
            "type": type(exc).__name__
        }
    )




