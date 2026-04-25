"""Application configuration from environment variables."""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment."""
    
    # App
    app_name: str = "ScheduleLink"
    app_url: str = "http://localhost:8080"
    secret_key: str = "change-me-in-production"
    
    # Database
    database_url: str = "sqlite:///./schedulelink.db"
    
    # JWT
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 10080  # 7 days
    
    # Stripe
    stripe_secret_key: str = ""
    stripe_publishable_key: str = ""
    stripe_price_id: str = ""
    stripe_webhook_secret: str = ""
    
    # Google OAuth
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8080/api/google/callback"
    
    # Email
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    email_from: str = "i.samson.pots@gmail.com"
    
    # Free tier limits
    free_bookings_per_month: int = 5
    
    # Stripe price IDs for each tier
    stripe_price_id_pro: str = ""  # $5/mo Pro tier
    stripe_price_id_pro_plus: str = ""  # $7/mo Pro+ tier with reminders
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
