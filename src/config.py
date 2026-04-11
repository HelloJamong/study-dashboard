import sys
from datetime import timedelta, timezone
from pathlib import Path

from src import db
from src.crypto import decrypt, encrypt, is_encrypted

# ── 공용 상수 ─────────────────────────────────────────────────
KST = timezone(timedelta(hours=9))


def _load_credential(key: str) -> str:
    """DB에서 읽어 복호화한다. 복호화 실패 시 빈 문자열 반환."""
    raw = db.get(key)
    if not raw:
        return ""
    if is_encrypted(raw):
        return decrypt(raw)
    return raw


def _default_download_dir() -> str:
    """OS별 기본 다운로드 경로를 반환한다."""
    if sys.platform == "win32":
        return str(Path.home() / "Downloads")
    # Docker 컨테이너 환경: /data 볼륨이 마운트된 경우 사용
    if Path("/data").exists() and str(Path.home()) == "/root":
        return "/data/downloads"
    # macOS / 일반 Linux
    return str(Path.home() / "Downloads")


def _read_version() -> str:
    """CHANGELOG.md의 첫 번째 ## [vX.Y.Z] 항목에서 버전을 읽어온다."""
    import re

    changelog = Path(__file__).parent.parent / "CHANGELOG.md"
    try:
        for line in changelog.read_text(encoding="utf-8").splitlines():
            m = re.match(r"^## \[v(.+?)\]", line)
            if m:
                return m.group(1)
    except Exception:
        pass
    return "unknown"


APP_VERSION = _read_version()


def get_data_path(filename: str) -> Path:
    """데이터 파일 경로를 반환한다. Docker(/data) 또는 로컬(data/)."""
    base = Path("/data") if Path("/data").exists() else Path("data")
    return base / filename


class Config:
    # 클래스 정의 시점에는 기본값으로 초기화.
    # 앱 시작 시 Config.load()를 호출해 DB에서 실제 값을 로드한다.
    LMS_USER_ID: str = ""
    LMS_PASSWORD: str = ""
    GOOGLE_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    WHISPER_MODEL: str = "base"
    STT_LANGUAGE: str = "ko"
    DOWNLOAD_DIR: str = ""
    DOWNLOAD_RULE: str = ""
    STT_ENABLED: str = ""
    AI_ENABLED: str = ""
    AI_AGENT: str = ""
    GEMINI_MODEL: str = ""
    SUMMARY_PROMPT_EXTRA: str = ""
    TELEGRAM_ENABLED: str = ""
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""
    TELEGRAM_AUTO_DELETE: str = ""

    @classmethod
    def load(cls) -> None:
        """DB에서 모든 설정을 로드한다. 앱 시작 시 반드시 1회 호출."""
        cls.LMS_USER_ID = _load_credential("LMS_USER_ID")
        cls.LMS_PASSWORD = _load_credential("LMS_PASSWORD")
        cls.GOOGLE_API_KEY = _load_credential("GOOGLE_API_KEY")
        cls.OPENAI_API_KEY = _load_credential("OPENAI_API_KEY")
        cls.TELEGRAM_BOT_TOKEN = _load_credential("TELEGRAM_BOT_TOKEN")
        cls.WHISPER_MODEL = db.get("WHISPER_MODEL", "base")
        cls.STT_LANGUAGE = db.get("STT_LANGUAGE", "ko")
        cls.DOWNLOAD_DIR = db.get("DOWNLOAD_DIR", "")
        cls.DOWNLOAD_RULE = db.get("DOWNLOAD_RULE", "")
        cls.STT_ENABLED = db.get("STT_ENABLED", "")
        cls.AI_ENABLED = db.get("AI_ENABLED", "")
        cls.AI_AGENT = db.get("AI_AGENT", "")
        cls.GEMINI_MODEL = db.get("GEMINI_MODEL", "")
        cls.SUMMARY_PROMPT_EXTRA = db.get("SUMMARY_PROMPT_EXTRA", "")
        cls.TELEGRAM_ENABLED = db.get("TELEGRAM_ENABLED", "")
        cls.TELEGRAM_CHAT_ID = db.get("TELEGRAM_CHAT_ID", "")
        cls.TELEGRAM_AUTO_DELETE = db.get("TELEGRAM_AUTO_DELETE", "")

    @classmethod
    def get_telegram_credentials(cls) -> tuple[str, str] | None:
        """텔레그램이 활성화되고 credential이 유효하면 (token, chat_id) 반환."""
        if cls.TELEGRAM_ENABLED != "true":
            return None
        if not cls.TELEGRAM_BOT_TOKEN or not cls.TELEGRAM_CHAT_ID:
            return None
        return cls.TELEGRAM_BOT_TOKEN, cls.TELEGRAM_CHAT_ID

    @classmethod
    def has_credentials(cls) -> bool:
        return bool(cls.LMS_USER_ID and cls.LMS_PASSWORD)

    @classmethod
    def has_settings(cls) -> bool:
        """최초 설정이 완료됐는지 확인 (다운로드 규칙 기준)."""
        return bool(cls.DOWNLOAD_RULE)

    @classmethod
    def get_download_dir(cls) -> str:
        """저장된 경로가 없으면 OS 기본 다운로드 폴더를 반환한다."""
        return cls.DOWNLOAD_DIR or _default_download_dir()

    @classmethod
    def save_settings(
        cls,
        download_dir: str,
        download_rule: str,
        stt_enabled: bool,
        ai_enabled: bool,
        ai_agent: str,
        api_key: str,
        gemini_model: str = "",
        summary_prompt_extra: str = "",
    ) -> None:
        """설정 항목을 DB에 저장한다."""
        cls.DOWNLOAD_DIR = download_dir
        cls.DOWNLOAD_RULE = download_rule
        cls.STT_ENABLED = "true" if stt_enabled else "false"
        cls.AI_ENABLED = "true" if ai_enabled else "false"
        cls.AI_AGENT = ai_agent
        cls.SUMMARY_PROMPT_EXTRA = summary_prompt_extra
        if gemini_model:
            cls.GEMINI_MODEL = gemini_model

        to_save: dict = {
            "DOWNLOAD_DIR": download_dir,
            "DOWNLOAD_RULE": download_rule,
            "STT_ENABLED": cls.STT_ENABLED,
            "AI_ENABLED": cls.AI_ENABLED,
            "AI_AGENT": ai_agent,
            "SUMMARY_PROMPT_EXTRA": summary_prompt_extra,
        }
        if gemini_model:
            to_save["GEMINI_MODEL"] = gemini_model
        if ai_enabled and ai_agent == "gemini":
            cls.GOOGLE_API_KEY = api_key
            to_save["GOOGLE_API_KEY"] = encrypt(api_key) if api_key else ""
        elif ai_enabled and ai_agent == "openai":
            cls.OPENAI_API_KEY = api_key
            to_save["OPENAI_API_KEY"] = encrypt(api_key) if api_key else ""

        db.set_many(to_save)

    @classmethod
    def save_telegram(cls, enabled: bool, bot_token: str, chat_id: str, auto_delete: bool) -> None:
        """텔레그램 설정을 DB에 저장한다."""
        cls.TELEGRAM_ENABLED = "true" if enabled else "false"
        cls.TELEGRAM_BOT_TOKEN = bot_token
        cls.TELEGRAM_CHAT_ID = chat_id
        cls.TELEGRAM_AUTO_DELETE = "true" if auto_delete else "false"
        db.set_many(
            {
                "TELEGRAM_ENABLED": cls.TELEGRAM_ENABLED,
                "TELEGRAM_BOT_TOKEN": encrypt(bot_token) if bot_token else "",
                "TELEGRAM_CHAT_ID": chat_id,
                "TELEGRAM_AUTO_DELETE": cls.TELEGRAM_AUTO_DELETE,
            }
        )

    @classmethod
    def save_credentials(cls, user_id: str, password: str) -> None:
        """계정 정보를 암호화해서 DB에 저장."""
        cls.LMS_USER_ID = user_id
        cls.LMS_PASSWORD = password
        db.set_many(
            {
                "LMS_USER_ID": encrypt(user_id),
                "LMS_PASSWORD": encrypt(password),
            }
        )

    @classmethod
    def _save_env(cls, keys_to_update: dict) -> None:
        """지정한 키/값을 DB에 저장한다.

        settings.py 등에서 직접 호출하는 경우를 위해 유지.
        """
        db.set_many(keys_to_update)
