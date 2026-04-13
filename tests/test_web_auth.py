"""웹 auth route 실패/타임아웃 처리 테스트."""

import asyncio

import pytest
from backend.api.routes import auth as auth_route
from backend.api.state import PlaybackProgress, app_state
from fastapi import HTTPException


def _reset_app_state() -> None:
    app_state.scraper = None
    app_state.user_id = ""
    app_state.courses = []
    app_state.details = []
    app_state.is_playing = False
    app_state.current_lecture_title = ""
    app_state.current_lecture_url = ""
    app_state.current_week_label = ""
    app_state.current_course_name = ""
    app_state.playback = PlaybackProgress()
    app_state.play_task = None


@pytest.fixture(autouse=True)
def reset_state():
    _reset_app_state()
    yield
    _reset_app_state()


@pytest.mark.asyncio
async def test_login_invalid_credentials_returns_401(monkeypatch):
    closed = False

    class FakeScraper:
        def __init__(self, username: str, password: str):
            self.username = username
            self.password = password

        async def start(self):
            raise RuntimeError("invalid")

        async def close(self):
            nonlocal closed
            closed = True

    monkeypatch.setattr("src.scraper.course_scraper.CourseScraper", FakeScraper)

    with pytest.raises(HTTPException) as exc:
        await auth_route.login(auth_route.LoginRequest(user_id="bad", password="bad"))

    assert exc.value.status_code == 401
    assert "로그인 실패" in exc.value.detail
    assert closed is True
    assert app_state.scraper is None


@pytest.mark.asyncio
async def test_login_timeout_returns_504_and_closes_scraper(monkeypatch):
    closed = False

    class FakeScraper:
        def __init__(self, username: str, password: str):
            self.username = username
            self.password = password

        async def start(self):
            await asyncio.sleep(1)

        async def close(self):
            nonlocal closed
            closed = True

    monkeypatch.setattr("src.scraper.course_scraper.CourseScraper", FakeScraper)
    monkeypatch.setattr(auth_route, "_LOGIN_TIMEOUT_SECONDS", 0.01)

    with pytest.raises(HTTPException) as exc:
        await auth_route.login(auth_route.LoginRequest(user_id="slow", password="slow"))

    assert exc.value.status_code == 504
    assert "로그인 시간이 초과" in exc.value.detail
    assert closed is True
    assert app_state.scraper is None


@pytest.mark.asyncio
async def test_login_timeout_does_not_wait_for_noncooperative_start(monkeypatch):
    closed = False
    should_stop = False

    class FakeScraper:
        def __init__(self, username: str, password: str):
            self.username = username
            self.password = password

        async def start(self):
            while True:
                if should_stop:
                    return
                try:
                    await asyncio.sleep(1)
                except asyncio.CancelledError:
                    # Playwright 내부 작업이 cancellation에 즉시 응답하지 않는 경우를 재현한다.
                    continue

        async def close(self):
            nonlocal closed, should_stop
            closed = True
            should_stop = True

    monkeypatch.setattr("src.scraper.course_scraper.CourseScraper", FakeScraper)
    monkeypatch.setattr(auth_route, "_LOGIN_TIMEOUT_SECONDS", 0.01)

    with pytest.raises(HTTPException) as exc:
        await asyncio.wait_for(
            auth_route.login(auth_route.LoginRequest(user_id="stuck", password="stuck")),
            timeout=0.2,
        )

    assert exc.value.status_code == 504
    assert app_state.scraper is None
    await asyncio.sleep(0.05)
    assert closed is True
