import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_X_SECRET_KEY = os.getenv("TELEGRAM_X_SECRET_KEY")

if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN is not set in environment variables")

if not TELEGRAM_X_SECRET_KEY:
    raise ValueError("TELEGRAM_X_SECRET_KEY is not set in environment variables")
