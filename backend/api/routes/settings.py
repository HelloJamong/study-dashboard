from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from src import db
from src.config import Config
from src.crypto import encrypt

router = APIRouter()

_SENSITIVE = {"LMS_USER_ID", "LMS_PASSWORD", "GOOGLE_API_KEY", "OPENAI_API_KEY", "TELEGRAM_BOT_TOKEN"}


@router.get("")
async def get_settings():
    return {
        "DOWNLOAD_DIR": Config.DOWNLOAD_DIR,
        "DOWNLOAD_RULE": Config.DOWNLOAD_RULE,
        "STT_ENABLED": Config.STT_ENABLED,
        "STT_LANGUAGE": Config.STT_LANGUAGE,
        "WHISPER_MODEL": Config.WHISPER_MODEL,
        "AI_ENABLED": Config.AI_ENABLED,
        "AI_AGENT": Config.AI_AGENT,
        "GEMINI_MODEL": Config.GEMINI_MODEL,
        "SUMMARY_PROMPT_EXTRA": Config.SUMMARY_PROMPT_EXTRA,
        "TELEGRAM_ENABLED": Config.TELEGRAM_ENABLED,
        "TELEGRAM_CHAT_ID": Config.TELEGRAM_CHAT_ID,
        "TELEGRAM_AUTO_DELETE": Config.TELEGRAM_AUTO_DELETE,
    }


class SettingsUpdate(BaseModel):
    DOWNLOAD_RULE: Optional[str] = None
    DOWNLOAD_DIR: Optional[str] = None
    STT_ENABLED: Optional[str] = None
    STT_LANGUAGE: Optional[str] = None
    WHISPER_MODEL: Optional[str] = None
    AI_ENABLED: Optional[str] = None
    AI_AGENT: Optional[str] = None
    GEMINI_MODEL: Optional[str] = None
    GOOGLE_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    SUMMARY_PROMPT_EXTRA: Optional[str] = None
    TELEGRAM_ENABLED: Optional[str] = None
    TELEGRAM_BOT_TOKEN: Optional[str] = None
    TELEGRAM_CHAT_ID: Optional[str] = None
    TELEGRAM_AUTO_DELETE: Optional[str] = None


@router.put("")
async def update_settings(body: SettingsUpdate):
    to_save = {}
    for key, val in body.model_dump(exclude_none=True).items():
        to_save[key] = encrypt(val) if key in _SENSITIVE and val else val

    if to_save:
        db.set_many(to_save)
        Config.load()

    return {"success": True}
