import os

OKX_API_KEY = os.getenv("OKX_API_KEY")
OKX_SECRET_KEY = os.getenv("OKX_SECRET_KEY")
OKX_PASSPHRASE = os.getenv("OKX_PASSPHRASE")
OKX_PROJECT_ID = os.getenv("OKX_PROJECT_ID")

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

MORALIS_API_KEY = os.getenv("MORALIS_KEY")

DATABASE_URL = os.getenv("DATABASE_URL")

REDIS_URL = os.getenv("REDIS_URL")

FERNET_KEY = os.getenv("FERNET_KEY").encode("utf-8")