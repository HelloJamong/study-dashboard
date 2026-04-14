from backend.api.state import app_state
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src import db, event_log
from src.config import Config, normalize_download_rule
from src.crypto import encrypt

router = APIRouter()

_SENSITIVE = {"GOOGLE_API_KEY", "TELEGRAM_BOT_TOKEN"}


def _require_auth() -> None:
    if not app_state.scraper:
        raise HTTPException(status_code=401, detail="로그인이 필요합니다.")


@router.get("")
async def get_settings():
    _require_auth()
    return {
        "DOWNLOAD_ENABLED": Config.DOWNLOAD_ENABLED,
        "DOWNLOAD_DIR": Config.get_download_dir(),
        "DOWNLOAD_RULE": Config.get_download_rule(),
        "AUTO_DOWNLOAD_AFTER_PLAY": Config.AUTO_DOWNLOAD_AFTER_PLAY,
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
    DOWNLOAD_ENABLED: str | None = None
    DOWNLOAD_RULE: str | None = None
    AUTO_DOWNLOAD_AFTER_PLAY: str | None = None
    STT_ENABLED: str | None = None
    STT_LANGUAGE: str | None = None
    WHISPER_MODEL: str | None = None
    AI_ENABLED: str | None = None
    AI_AGENT: str | None = None
    GEMINI_MODEL: str | None = None
    GOOGLE_API_KEY: str | None = None
    SUMMARY_PROMPT_EXTRA: str | None = None
    TELEGRAM_ENABLED: str | None = None
    TELEGRAM_BOT_TOKEN: str | None = None
    TELEGRAM_CHAT_ID: str | None = None
    TELEGRAM_AUTO_DELETE: str | None = None


@router.put("")
async def update_settings(body: SettingsUpdate):
    _require_auth()
    to_save = {}
    for key, val in body.model_dump(exclude_none=True).items():
        if key == "DOWNLOAD_RULE":
            val = normalize_download_rule(val)
        to_save[key] = encrypt(val) if key in _SENSITIVE and val else val

    download_enabled = to_save.get("DOWNLOAD_ENABLED", Config.DOWNLOAD_ENABLED) == "true"
    auto_download_after_play = to_save.get("AUTO_DOWNLOAD_AFTER_PLAY", Config.AUTO_DOWNLOAD_AFTER_PLAY) == "true"
    if not download_enabled:
        to_save["AUTO_DOWNLOAD_AFTER_PLAY"] = "false"
        to_save["STT_ENABLED"] = "false"
        to_save["AI_ENABLED"] = "false"
    elif not auto_download_after_play:
        to_save["STT_ENABLED"] = "false"
        to_save["AI_ENABLED"] = "false"

    if to_save:
        keys = sorted(to_save)
        before = event_log.setting_snapshot(keys)
        try:
            db.set_many(to_save)
            Config.load()
        except Exception as e:
            event_log.record_event(
                event_type="settings",
                action="update",
                status="failed",
                actor_user_id=app_state.user_id or None,
                error_code=type(e).__name__,
                error_message=str(e),
                metadata={"changed_keys": keys, "before": before, "attempted": to_save},
            )
            raise

        after = event_log.setting_snapshot(keys)
        event_log.record_event(
            event_type="settings",
            action="update",
            status="success",
            actor_user_id=app_state.user_id or None,
            message="설정이 저장되었습니다.",
            metadata={"changed_keys": event_log.changed_keys(before, after), "before": before, "after": after},
        )

    return {"success": True}
