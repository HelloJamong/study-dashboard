"""웹 행위 로그 조회 API 테스트."""

import pytest
from backend.api.routes import logs as logs_route
from backend.api.state import app_state
from fastapi import HTTPException

from src import event_log


class _FakeScraper:
    pass


@pytest.fixture(autouse=True)
def reset_state(monkeypatch, tmp_path):
    import src.db as db_module

    monkeypatch.setattr(db_module, "_db_path", lambda: tmp_path / "app.db")
    app_state.scraper = None
    app_state.user_id = ""
    yield
    app_state.scraper = None
    app_state.user_id = ""


@pytest.mark.asyncio
async def test_get_logs_requires_auth():
    with pytest.raises(HTTPException) as exc:
        await logs_route.get_logs()

    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_get_logs_filters_events():
    app_state.scraper = _FakeScraper()
    event_log.record_event(event_type="auth", action="login", status="success")
    event_log.record_event(event_type="download", action="download_failed", status="failed")

    payload = await logs_route.get_logs(event_type="download", status="failed", limit=10)

    assert len(payload["events"]) == 1
    assert payload["events"][0]["event_type"] == "download"
    assert payload["events"][0]["status"] == "failed"
    assert event_log.is_timestamp_format(payload["events"][0]["created_at"])
