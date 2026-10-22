import os
from typing import List
from pydantic_settings import BaseSettings
from datetime import datetime, timezone
from dateutil import parser

class Settings(BaseSettings):
    PROJECT_NAME: str = "RevPilot AI"
    VERSION: str = "1.0.0"
    SCHEMA_VERSION: str = "1.0.0"
    API_V1_STR: str = "/api"
    
    DATABASE_URL: str = "sqlite:///./revpilot.db"
    SECRET_KEY: str = "dev-secret-key-for-local-revpilot-testing-98234710923847"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    
    AS_OF_DATE: str = "2026-10-20T00:00:00Z"
    DEMO_MODE: bool = True
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000"
    EXPORTS_DIR: str = "./exports/runtime"
    
    LLM_API_KEY: str = ""
    LLM_PROVIDER: str = "none"

    @property
    def cors_origin_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def as_of_datetime(self) -> datetime:
        if self.AS_OF_DATE:
            try:
                dt = parser.isoparse(self.AS_OF_DATE)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            except Exception:
                pass
        return datetime.now(timezone.utc)

    class Config:
        env_file = ".env"
        extra = "allow"

settings = Settings()
