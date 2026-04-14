"""웹 설정 route 다운로드 종속 옵션 테스트."""

import pytest
from backend.api.routes import settings as settings_route
from backend.api.state import app_state

from src.config import Config
from src.event_log import list_events


class _FakeScraper:
    pass


def _make_db(tmp_path, monkeypatch):
    import src.db as db_module

    monkeypatch.setattr(db_module, "_db_path", lambda: tmp_path / "app.db")


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


@pytest.mark.asyncio
async def test_update_settings_ignores_download_dir(monkeypatch):
    saved = {}

    monkeypatch.setattr(settings_route.db, "set_many", lambda values: saved.update(values))
    monkeypatch.setattr(Config, "load", lambda: None)

    await settings_route.update_settings(
        settings_route.SettingsUpdate.model_validate(
            {
                "DOWNLOAD_ENABLED": "true",
                "DOWNLOAD_DIR": "/tmp/custom",
                "DOWNLOAD_RULE": "mp3",
            }
        )
    )

    assert saved["DOWNLOAD_ENABLED"] == "true"
    assert saved["DOWNLOAD_RULE"] == "mp3"
    assert "DOWNLOAD_DIR" not in saved


@pytest.mark.asyncio
async def test_update_settings_writes_masked_event_log(monkeypatch, tmp_path):
    _make_db(tmp_path, monkeypatch)
    app_state.user_id = "student"

    await settings_route.update_settings(
        settings_route.SettingsUpdate(
            DOWNLOAD_RULE="mp3",
            GOOGLE_API_KEY="real-secret-key",
        )
    )

    events = list_events(event_type="settings", limit=1)

    assert events[0]["action"] == "update"
    assert events[0]["status"] == "success"
    assert events[0]["actor_user_id"] == "student"
    assert events[0]["metadata"]["after"]["GOOGLE_API_KEY"] == "[redacted]"
    assert "real-secret-key" not in str(events[0]["metadata"])
