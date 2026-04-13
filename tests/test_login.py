"""SSO 로그인 실패/성공 판정 테스트."""

import time

import pytest

from src.auth import login as login_module


class _VisibleElement:
    async def click(self):
        return None

    async def is_visible(self):
        return True


class _FakePage:
    def __init__(self, url: str = "https://canvas.ssu.ac.kr/login"):
        self.url = url
        self.filled: dict[str, str] = {}
        self.events: dict[str, object] = {}

    def on(self, event: str, handler):
        self.events[event] = handler

    def remove_listener(self, event: str, handler):
        if self.events.get(event) is handler:
            self.events.pop(event, None)

    async def query_selector(self, selector: str):
        if selector == "input#userid":
            return _VisibleElement()
        return None

    async def wait_for_selector(self, selector: str, timeout: int = 0):
        return _VisibleElement()

    async def wait_for_load_state(self, state: str, timeout: int = 0):
        return None

    async def fill(self, selector: str, value: str, timeout: int = 0):
        self.filled[selector] = value

    async def click(self, selector: str, timeout: int = 0):
        return None

    async def evaluate(self, script: str, keywords):
        return False


@pytest.fixture(autouse=True)
def fast_login_poll(monkeypatch):
    monkeypatch.setattr(login_module, "_LOGIN_RESULT_TIMEOUT_SECONDS", 0.2)
    monkeypatch.setattr(login_module, "_LOGIN_FORM_STABLE_SECONDS", 0.03)


@pytest.mark.asyncio
async def test_perform_login_fails_fast_when_login_form_remains_visible():
    page = _FakePage()

    started = time.monotonic()
    ok = await login_module.perform_login(page, "bad-user", "bad-password")
    elapsed = time.monotonic() - started

    assert ok is False
    assert elapsed < 0.5
    assert page.filled["input#userid"] == "bad-user"
    assert page.filled["input#pwd"] == "bad-password"


@pytest.mark.asyncio
async def test_perform_login_succeeds_when_url_leaves_login():
    class SuccessPage(_FakePage):
        async def click(self, selector: str, timeout: int = 0):
            if selector == "a.btn_login":
                self.url = "https://canvas.ssu.ac.kr/"

    page = SuccessPage()

    ok = await login_module.perform_login(page, "student", "password")

    assert ok is True
