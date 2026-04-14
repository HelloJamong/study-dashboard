"""DB 행위 로그 저장소 테스트."""

from datetime import datetime
from unittest.mock import patch

from src import event_log


def _make_db(tmp_path):
    import src.db as db_module

    return patch.object(db_module, "_db_path", return_value=tmp_path / "app.db")


def test_record_event_saves_timestamp_and_masks_sensitive_metadata(tmp_path):
    with _make_db(tmp_path):
        assert event_log.record_event(
            event_type="settings",
            action="update",
            status="success",
            actor_user_id="student",
            metadata={
                "GOOGLE_API_KEY": "secret-key",
                "nested": {"TELEGRAM_BOT_TOKEN": "token"},
                "normal": "value",
            },
        )

        events = event_log.list_events(limit=1)

    assert len(events) == 1
    assert event_log.is_timestamp_format(events[0]["created_at"])
    assert events[0]["metadata"]["GOOGLE_API_KEY"] == "[redacted]"
    assert events[0]["metadata"]["nested"]["TELEGRAM_BOT_TOKEN"] == "[redacted]"
    assert events[0]["metadata"]["normal"] == "value"


def test_event_timestamp_format_uses_requested_shape():
    ts = event_log.event_timestamp(datetime(2026, 4, 14, 9, 8, 7, tzinfo=event_log.KST))
    assert ts == "2026-04-14 09:08:07"


def test_record_event_failure_does_not_raise(monkeypatch):
    def fail(**kwargs):
        raise RuntimeError("db unavailable")

    monkeypatch.setattr(event_log, "_insert_event", fail)

    assert event_log.record_event(event_type="auth", action="login", status="success") is False


def test_mask_user_id():
    assert event_log.mask_user_id("20261234") == "2026****"
    assert event_log.mask_user_id("abc") == "***"
    assert event_log.mask_user_id(None) is None
