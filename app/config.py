import os
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env", override=True)

REQUIRED_VARS = (
    "SUPABASE_URL",
    "SUPABASE_SERVICE_KEY",
    "SESSION_SECRET",
    "APP_PIN",
    "TIMEZONE",
)

missing = [name for name in REQUIRED_VARS if not os.environ.get(name)]
if missing:
    raise RuntimeError(
        "Faltan variables de entorno requeridas: "
        + ", ".join(missing)
        + ". Copia .env.example a .env y completalas antes de arrancar."
    )

SUPABASE_URL = os.environ["SUPABASE_URL"].rstrip("/")
SUPABASE_SERVICE_KEY = os.environ["SUPABASE_SERVICE_KEY"]
SESSION_SECRET = os.environ["SESSION_SECRET"]
APP_PIN = os.environ["APP_PIN"]
TIMEZONE = os.environ["TIMEZONE"]

ENV = os.environ.get("ENV", "development").strip().lower()
SESSION_COOKIE_SECURE = ENV == "production"

if len(SESSION_SECRET) < 32:
    raise RuntimeError(
        "SESSION_SECRET debe tener al menos 32 caracteres. Genera uno con: "
        "python -c \"import secrets; print(secrets.token_hex(32))\""
    )

try:
    TZ = ZoneInfo(TIMEZONE)
except ZoneInfoNotFoundError:
    raise RuntimeError(
        f"TIMEZONE invalida: '{TIMEZONE}'. Usa un nombre IANA valido "
        "como 'America/Managua'."
    ) from None

SESSION_COOKIE = "session"
SESSION_MAX_AGE = 7 * 24 * 60 * 60
LOGIN_MAX_ATTEMPTS = 5
LOGIN_BLOCK_SECONDS = 300
