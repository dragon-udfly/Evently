import os
from datetime import datetime
from zoneinfo import ZoneInfo


class Settings:
    database_url = os.getenv("DATABASE_URL", "sqlite:///./eventsphere.db")
    secret_key = os.getenv("SECRET_KEY", "dev-only-change-me")
    