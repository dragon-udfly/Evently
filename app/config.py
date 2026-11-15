import os
from datetime import datetime
from zoneinfo import ZoneInfo


class Settings:
    database_url = os.getenv("DATABASE_URL", "sqlite:///./evently.db")
    secret_key = os.getenv("SECRET_KEY", "dev-only-change-me")
    timezone = os.getenv("APP_TIMEZONE", "Asia/Colombo")
    https_only = os.getenv("HTTPS_ONLY", "0") == "1"
    agent_api_key = os.getenv("AGENT_API_KEY", "")
    seed_demo = os.getenv("SEED_DEMO", "1") == "1"
    enable_scheduler = os.getenv("ENABLE_SCHEDULER", "1") == "1"

    max_tickets_per_request = 6
    max_tickets_per_user_event = 10
    hold_minutes = int(os.getenv("HOLD_MINUTES", "10"))
    sweep_seconds = 30
    venue_buffer_minutes = 30
    checkin_opens_minutes = 120
    suspicious_scan_threshold = 3
    hire_max_hours = 12
    hire_auto_max_hours = 4
    hire_auto_max_fill = 0.8
    weekend_multiplier = 1.25
    peak_multiplier = 1.15
    peak_from_hour = 17
    peak_to_hour = 22


settings = Settings()

def now() -> datetime:
    return datetime.now(ZoneInfo(settings.timezone)).replace(tzinfo=None, microsecond=0)
