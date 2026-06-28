"""
FastAPI Application Runner
Run with: python run.py
"""

import uvicorn
from app.config import settings

if __name__ == "__main__":
    print(f"Starting {settings.PROJECT_NAME}")
    # Display localhost for browser access (0.0.0.0 is just the bind address)
    display_host = "localhost" if settings.API_HOST == "0.0.0.0" else settings.API_HOST
    print(f"Server: http://{display_host}:{settings.API_PORT}")
    print(f"Docs: http://{display_host}:{settings.API_PORT}/api/docs")
    print(f"Health: http://{display_host}:{settings.API_PORT}/health")
    print()
    
    uvicorn.run(
        "app.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.API_RELOAD,
        log_level="info"
    )




