import os
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

# --- DYNAMIC PATH RESOLUTION ---
# Path logic to find the .env in the root Raakin_Atlas_AI folder
BASE_DIR = Path(__file__).resolve().parents[2] # Adjusting for backend/app/core/
ENV_PATH = BASE_DIR.parents[0] / ".env"

# Force load the .env file
if ENV_PATH.exists():
    load_dotenv(str(ENV_PATH))
    print(f"✅ FOUND .env at: {ENV_PATH}")
else:
    # Try local folder if root fails
    load_dotenv()

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Core App Settings (Restored)
    app_name: str = "Atlas AI Command Center"
    debug: bool = False  # Fixed the missing attribute
    secret_key: str = "change-me-in-production"
    
    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./academic.db"
    
    # AI Keys (Resolved from ENV)
    GROQ_API_KEY: str = Field(default_factory=lambda: os.getenv("GROQ_API_KEY", ""))
    gemini_api_key: str = Field(default_factory=lambda: os.getenv("GEMINI_API_KEY", ""))
    
    # SMTP Credentials (THE LIVE ONES)
    smtp_user: str = Field(default_factory=lambda: os.getenv("SMTP_USER", ""))
    smtp_pass: str = Field(default_factory=lambda: os.getenv("SMTP_PASS", ""))
    
    # Approved Domains (Added gmail.com and your university domain)
    approved_email_domains: str = "gmail.com,atlasuniversity.edu.in,atlasskilltech.university,example.com"
    
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

settings = Settings()

# --- FINAL DEBUG PRINT ---
print("--- 🚀 ATLAS AI MAILMAN STATUS ---")
if settings.smtp_user and settings.smtp_pass:
    print(f"STATUS: LIVE 🟢")
    print(f"SENDER: {settings.smtp_user}")
else:
    print("STATUS: SIMULATING 🟡 (Credentials Missing)")
print(f"APPROVED DOMAINS: {settings.approved_email_domains}")
print("----------------------------------")