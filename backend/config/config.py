from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve absolute path to backend/.env relative to this file's location
ENV_FILE_PATH = str(Path(__file__).resolve().parent.parent / ".env")

class Settings(BaseSettings):
    # Google Sheets Configuration
    GOOGLE_SHEET_URL: Optional[str] = None
    GOOGLE_CREDENTIALS_FILE: Optional[str] = "credentials.json"
    GOOGLE_API_KEY: Optional[str] = None
    
    DATABASE_URL: Optional[str] = "sqlite:///./nhai_dashboard.db" # Default for local testing if not set
    
    # App Settings
    CACHE_EXPIRY_SECONDS: int = 300  # 5 minutes cache
    
    # Environment config
    model_config = SettingsConfigDict(
        env_file=ENV_FILE_PATH,
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def spreadsheet_id(self) -> Optional[str]:
        if not self.GOOGLE_SHEET_URL:
            return None
        import re
        match = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", self.GOOGLE_SHEET_URL)
        if match:
            return match.group(1)
        return self.GOOGLE_SHEET_URL

settings = Settings()
