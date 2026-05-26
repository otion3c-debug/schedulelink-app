from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
from cryptography.fernet import Fernet
import base64
import hashlib


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str = "sqlite:///./schedulelink.db"
    JWT_SECRET_KEY: str = "change-me"
    ENCRYPTION_KEY: str = ""
    ENVIRONMENT: str = "development"

    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "https://api.schedulelink.tech/auth/google/callback"

    @field_validator("GOOGLE_REDIRECT_URI")
    @classmethod
    def strip_trailing_whitespace(cls, v: str) -> str:
        return v.strip()

    MICROSOFT_CLIENT_ID: str = ""
    MICROSOFT_CLIENT_SECRET: str = ""
    MICROSOFT_TENANT_ID: str = "consumers"
    MICROSOFT_REDIRECT_URI: str = "https://api.schedulelink.tech/auth/microsoft/callback"

    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    STRIPE_PRO_PRICE_ID: str = ""
    STRIPE_PRO_PLUS_PRICE_ID: str = ""

    SMTP_HOST: str = "smtp.zoho.com"
    SMTP_PORT: int = 465
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_USE_SSL: bool = True
    EMAIL_FROM: str = "ScheduleLink <support@schedulelink.tech>"

    FRONTEND_URL: str = "https://www.schedulelink.tech"
    BACKEND_URL: str = "https://schedulelink-app.onrender.com"

    VAPI_WEBHOOK_SECRET: str = ""
    VAPI_BOOKING_SLUG: str = "eric-hunt"

    @property
    def CORS_ORIGINS(self) -> list[str]:
        return [
            self.FRONTEND_URL.rstrip("/"),
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:8000",
            "https://schedulelink.tech",
            "https://www.schedulelink.tech",
        ]

    @property
    def fernet(self) -> Fernet:
        key = self.ENCRYPTION_KEY
        if not key:
            # Derive a deterministic Fernet key from JWT_SECRET_KEY for local dev
            digest = hashlib.sha256(self.JWT_SECRET_KEY.encode()).digest()
            key = base64.urlsafe_b64encode(digest).decode()
        return Fernet(key.encode() if isinstance(key, str) else key)


settings = Settings()
