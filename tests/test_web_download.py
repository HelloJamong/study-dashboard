"""웹 다운로드 task route 테스트."""

import pytest
from backend.api.routes import tasks as tasks_route
from backend.api.state import PlaybackProgress, app_state
from backend.api.task_manager import task_manager
from fastapi import HTTPException

from src import event_log
from src.config import Config
from src.scraper.models import Course


class _FakeScraper:
    _page = object()


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
    app_state.current_course_id = ""
    app_state.playback = PlaybackProgress()
    app_state.play_task = None
    app_state.play_task_id = None
    app_state.auto.enabled = False
    app_state.auto.task = None
    app_state.auto.task_id = None
    task_manager.clear()


def _seed_course() -> Course:
    course = Course(id="42", long_name="테스트 과목", href="/courses/42", term="2026-1")
    app_state.scraper = _FakeScraper()
    app_state.user_id = "student"
    app_state.courses = [course]
    return course


@pytest.fixture(autouse=True)
def reset_state(monkeypatch, tmp_path):
    import src.db as db_module

    monkeypatch.setattr(db_module, "_db_path", lambda: tmp_path / "app.db")
    _reset_app_state()
    Config.DOWNLOAD_DIR = str(tmp_path)
    Config.DOWNLOAD_ENABLED = "true"
    Config.DOWNLOAD_RULE = "mp4"
    yield
    _reset_app_state()


@pytest.mark.asyncio
async def test_start_download_creates_managed_task(monkeypatch, tmp_path):
    course = _seed_course()
    called = {}

    async def fake_download_lecture_media(**kwargs):
        called.update(kwargs)
        kwargs["on_stage"]("downloading", "테스트 다운로드 중", 50)
        return {
            "download_rule": kwargs["rule"],
            "download_dir": kwargs["download_dir"],
            "files": [{"type": "mp4", "path": str(tmp_path / "lecture.mp4")}],
        }

    monkeypatch.setattr("src.downloader.pipeline.download_lecture_media", fake_download_lecture_media)

    response = await tasks_route.start_download(
        tasks_route.DownloadTaskRequest(
            course_id=course.id,
            lecture_url="https://canvas.ssu.ac.kr/courses/42/items/1",
            lecture_title="1강",
            week_label="1주차",
        )
    )
    managed = task_manager.get(response["task_id"])
    await managed.task

    assert response["started"] is True
    assert managed.kind == "download"
    assert managed.status == "completed"
    assert managed.result["download_rule"] == "mp4"
    assert managed.result["files"][0]["type"] == "mp4"
    assert called["course_name"] == "테스트 과목"
    events = event_log.list_events(event_type="download", limit=10)
    assert [event["action"] for event in events] == ["download_complete", "download_start"]
    assert events[0]["status"] == "success"
    assert event_log.is_timestamp_format(events[0]["created_at"])


@pytest.mark.asyncio
async def test_start_download_rejects_while_playing():
    course = _seed_course()
    app_state.is_playing = True

    with pytest.raises(HTTPException) as exc:
        await tasks_route.start_download(
            tasks_route.DownloadTaskRequest(
                course_id=course.id,
                lecture_url="https://canvas.ssu.ac.kr/courses/42/items/1",
                lecture_title="1강",
                week_label="1주차",
            )
        )

    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_start_download_requires_enabled_setting():
    course = _seed_course()
    Config.DOWNLOAD_ENABLED = "false"

    with pytest.raises(HTTPException) as exc:
        await tasks_route.start_download(
            tasks_route.DownloadTaskRequest(
                course_id=course.id,
                lecture_url="https://canvas.ssu.ac.kr/courses/42/items/1",
                lecture_title="1강",
                week_label="1주차",
            )
        )

    assert exc.value.status_code == 409
    assert "영상 다운로드" in exc.value.detail
