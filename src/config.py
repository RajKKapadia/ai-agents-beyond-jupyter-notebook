import os
from urllib.parse import urlparse

from arq.connections import RedisSettings
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_X_SECRET_KEY = os.getenv("TELEGRAM_X_SECRET_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENWEATHERMAP_API_KEY = os.getenv("OPENWEATHERMAP_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")
REDIS_URL = os.getenv("REDIS_URL")

if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN is not set in environment variables")

if not TELEGRAM_X_SECRET_KEY:
    raise ValueError("TELEGRAM_X_SECRET_KEY is not set in environment variables")

if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY is not set in environment variables")

if not OPENWEATHERMAP_API_KEY:
    raise ValueError("OPENWEATHERMAP_API_KEY is not set in environment variables")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL is not set in environment variables")

if not REDIS_URL:
    raise ValueError("REDIS_URL is not set in environment variables")

OPENAI_MODEL = "gpt-4.1-mini"


def get_arq_redis_settings() -> RedisSettings:
    """Parse REDIS_URL into ARQ RedisSettings."""
    parsed = urlparse(REDIS_URL)
    return RedisSettings(
        host=parsed.hostname or "localhost",
        port=parsed.port or 6379,
        database=int(parsed.path.lstrip("/") or 0),
        password=parsed.password,
    )
