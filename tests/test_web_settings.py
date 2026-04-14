"""웹 설정 route 다운로드 종속 옵션 테스트."""

import pytest
from backend.api.routes import settings as settings_route
from backend.api.state import app_state

from src.config import Config


class _FakeScraper:
    pass


@pytest.fixture(autouse=True)
def reset_state():
    app_state.scraper = _FakeScraper()
    Config.DOWNLOAD_ENABLED = "true"
    Config.AUTO_DOWNLOAD_AFTER_PLAY = "true"
    yield
    app_state.scraper = None


@pytest.mark.asyncio
async def test_update_settings_disables_dependent_options_when_download_off(monkeypatch):
    saved = {}

    monkeypatch.setattr(settings_route.db, "set_many", lambda values: saved.update(values))
    monkeypatch.setattr(Config, "load", lambda: None)

    await settings_route.update_settings(
        settings_route.SettingsUpdate(
            DOWNLOAD_ENABLED="false",
            AUTO_DOWNLOAD_AFTER_PLAY="true",
            STT_ENABLED="true",
            AI_ENABLED="true",
        )
    )

    assert saved["DOWNLOAD_ENABLED"] == "false"
    assert saved["AUTO_DOWNLOAD_AFTER_PLAY"] == "false"
    assert saved["STT_ENABLED"] == "false"
    assert saved["AI_ENABLED"] == "false"


@pytest.mark.asyncio
async def test_update_settings_disables_stt_ai_when_auto_download_off(monkeypatch):
    saved = {}

    monkeypatch.setattr(settings_route.db, "set_many", lambda values: saved.update(values))
    monkeypatch.setattr(Config, "load", lambda: None)

    await settings_route.update_settings(
        settings_route.SettingsUpdate(
            DOWNLOAD_ENABLED="true",
            AUTO_DOWNLOAD_AFTER_PLAY="false",
            STT_ENABLED="true",
            AI_ENABLED="true",
        )
    )

    assert saved["DOWNLOAD_ENABLED"] == "true"
    assert saved["AUTO_DOWNLOAD_AFTER_PLAY"] == "false"
    assert saved["STT_ENABLED"] == "false"
    assert saved["AI_ENABLED"] == "false"
