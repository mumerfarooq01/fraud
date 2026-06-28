from pydantic_settings import BaseSettings
from typing import List, Optional
import os

class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # API Configuration
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Document Fraud Detection API"
    VERSION: str = "1.0.0"
    DESCRIPTION: str = "API for detecting fraudulent tax documents using forensic analysis"
    
    # Server
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_RELOAD: bool = True
    
    # CORS
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:8501"
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Convert comma-separated CORS origins to list"""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]
    
    # Database
    DATABASE_URL: str = "sqlite:///./forensic_records.db"
    FORENSIC_DB_PATH: str = "./forensic_records.db"
    
    # Gemini API
    GEMINI_API_KEY: Optional[str] = None
    
    # Security
    SECRET_KEY: str = "change-this-in-production"
    API_KEY: Optional[str] = None
    
    # File Upload
    MAX_FILE_SIZE_MB: int = 50
    ALLOWED_EXTENSIONS: List[str] = ["pdf", "jpg", "jpeg", "png"]
    
    @property
    def max_file_size_bytes(self) -> int:
        """Convert MB to bytes"""
        return self.MAX_FILE_SIZE_MB * 1024 * 1024
    
    # Path to existing fraud detection code
    # FRAUD_DETECTION_CODE_PATH: str = "../fraud-detection-poc"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

# Create global settings instance
settings = Settings()

# Validate critical settings
if not settings.GEMINI_API_KEY:
    print("WARNING: GEMINI_API_KEY not set. Document comparison features will not work.")




