from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

@dataclass(slots=True)
class AppConfig:
    app_name: str
    city: str
    secret_key: str
    db_host: str
    db_port: int
    db_user: str
    db_password: str
    db_name: str
    sms_username: str
    sms_password: str
    sms_api_url: str
    huggingface_api_token: str
    openai_api_key: str
    demo_mode: bool

def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}

CONFIG = AppConfig(
    app_name=os.getenv("APP_NAME", "AI-Powered Tin Pet Grooming Online Booking System"),
    city=os.getenv("APP_CITY", "Calumpang, General Santos City"),
    secret_key=os.getenv("SECRET_KEY", "tin-pet-grooming-dev-secret"),
    db_host=os.getenv("MYSQL_HOST", "127.0.0.1"),
    db_port=int(os.getenv("MYSQL_PORT", "3306")),
    db_user=os.getenv("MYSQL_USER", "root"),
    db_password=os.getenv("MYSQL_PASSWORD", ""),
    db_name=os.getenv("MYSQL_DATABASE", "tin_pet_grooming"),
    sms_username=os.getenv("SMS_USERNAME", ""),
    sms_password=os.getenv("SMS_PASSWORD", ""),
    sms_api_url=os.getenv("SMS_API_URL", "https://sms.capcom.me/api/3rdparty/v1"),
    huggingface_api_token=os.getenv("HUGGINGFACE_API_TOKEN", ""),
    openai_api_key=os.getenv("OPENAI_API_KEY", ""),
    demo_mode=_as_bool(os.getenv("DEMO_MODE"), default=True),
)
