"""공통 백그라운드 태스크 관리자 테스트."""

import asyncio

import pytest
from backend.api.task_manager import ManagedTask, task_manager


@pytest.fixture(autouse=True)
def clear_tasks():
    task_manager.clear()
    yield
    task_manager.clear()


@pytest.mark.asyncio
async def test_task_manager_tracks_completed_task():
    async def work(managed: ManagedTask):
        managed.update(stage="testing", message="실행 중", progress_pct=50)
        await asyncio.sleep(0)
        return {"ok": True}

    managed = task_manager.create("test", work)
    await managed.task

    payload = managed.to_dict()
    assert payload["status"] == "completed"
    assert payload["stage"] == "completed"
    assert payload["progress_pct"] == 100
    assert payload["result"] == {"ok": True}


@pytest.mark.asyncio
async def test_task_manager_can_cancel_running_task():
    started = asyncio.Event()

    async def work(managed: ManagedTask):
        managed.update(stage="waiting")
        started.set()
        await asyncio.sleep(10)

    managed = task_manager.create("test", work)
    await started.wait()

    assert await task_manager.cancel(managed.id) is True
    assert managed.status == "cancelled"
    assert managed.stage == "cancelled"


@pytest.mark.asyncio
async def test_task_manager_marks_suppressed_cancellation_as_cancelled():
    started = asyncio.Event()

    async def work(managed: ManagedTask):
        managed.update(stage="waiting")
        started.set()
        try:
            await asyncio.sleep(10)
        except asyncio.CancelledError:
            return {"cleaned_up": True}

    managed = task_manager.create("test", work)
    await started.wait()

    assert await task_manager.cancel(managed.id) is True
    assert managed.status == "cancelled"
    assert managed.result == {"cleaned_up": True}
