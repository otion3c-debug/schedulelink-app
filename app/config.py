from pydantic_settings import BaseSettings, SettingsConfigDict
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
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/auth/google/callback"

    MICROSOFT_CLIENT_ID: str = ""
    MICROSOFT_CLIENT_SECRET: str = ""
    MICROSOFT_TENANT_ID: str = "common"
    MICROSOFT_REDIRECT_URI: str = "http://localhost:8000/auth/microsoft/callback"

    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    STRIPE_PRO_PRICE_ID: str = ""
    STRIPE_PRO_PLUS_PRICE_ID: str = ""

    SMTP_HOST: str = "smtp.zoho.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    EMAIL_FROM: str = "ScheduleLink <support@schedulelink.tech>"

    FRONTEND_URL: str = "http://localhost:3000"
    BACKEND_URL: str = "http://localhost:8000"

    @property
    def fernet(self) -> Fernet:
        key = self.ENCRYPTION_KEY
        if not key:
            # Derive a deterministic Fernet key from JWT_SECRET_KEY for local dev
            digest = hashlib.sha256(self.JWT_SECRET_KEY.encode()).digest()
            key = base64.urlsafe_b64encode(digest).decode()
        return Fernet(key.encode() if isinstance(key, str) else key)


settings = Settings()
