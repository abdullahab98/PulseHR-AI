from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

_BASE_DIR = Path(__file__).resolve().parent.parent
_ENV_FILE = _BASE_DIR / ".env"

class Settings(BaseSettings):
    PROJECT_NAME: str = "AI-Driven Office Management System API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days token
    
    # Database
    DATABASE_URL: str = "sqlite:///./office_management.db"
    
    # MongoDB Database
    MONGODB_URL: str
    MONGODB_DB_NAME: str = "office_management"
    
    # AI Engine Integration
    GEMINI_API_KEY: str
    
    # Timezone Configuration (Bangladesh Standard Time: UTC+6)
    TIMEZONE: str = "Asia/Dhaka"
    
    model_config = SettingsConfigDict(
        env_file=[str(_ENV_FILE), ".env"],
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
