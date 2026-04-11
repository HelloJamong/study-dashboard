"""config.py / db.py 단위 테스트."""

import tempfile
from pathlib import Path
from unittest.mock import patch

from src.config import _default_download_dir, _read_version


def test_read_version():
    """CHANGELOG.md에서 버전을 정상적으로 파싱한다."""
    version = _read_version()
    assert version != "unknown"
    parts = version.split("-")[0].split(".")
    assert len(parts) == 3
    assert all(p.isdigit() for p in parts)


def test_default_download_dir():
    """OS별 기본 다운로드 경로가 빈 문자열이 아니어야 한다."""
    path = _default_download_dir()
    assert path
    assert isinstance(path, str)


# ── db.py 테스트 ───────────────────────────────────────────────


def _make_db(tmp_path: Path):
    """임시 경로에 격리된 DB 모듈 패치를 반환하는 컨텍스트."""
    import src.db as db_module

    return patch.object(db_module, "_db_path", return_value=tmp_path / "app.db")


def test_db_get_set(tmp_path):
    """set 후 get이 동일한 값을 반환한다."""
    import src.db as db

    with _make_db(tmp_path):
        db.set("FOO", "bar")
        assert db.get("FOO") == "bar"


def test_db_get_default(tmp_path):
    """존재하지 않는 키는 default를 반환한다."""
    import src.db as db

    with _make_db(tmp_path):
        assert db.get("MISSING") == ""
        assert db.get("MISSING", "fallback") == "fallback"


def test_db_set_many(tmp_path):
    """set_many로 여러 값을 한 번에 저장한다."""
    import src.db as db

    with _make_db(tmp_path):
        db.set_many({"A": "1", "B": "2", "C": "3"})
        assert db.get("A") == "1"
        assert db.get("B") == "2"
        assert db.get("C") == "3"


def test_db_set_many_upsert(tmp_path):
    """기존 키는 갱신, 새 키는 삽입된다."""
    import src.db as db

    with _make_db(tmp_path):
        db.set("X", "old")
        db.set_many({"X": "new", "Y": "added"})
        assert db.get("X") == "new"
        assert db.get("Y") == "added"


def test_db_migrate_from_env(tmp_path):
    """기존 .env 파일 내용이 DB로 마이그레이션된다."""
    import src.db as db

    env_file = tmp_path / ".env"
    env_file.write_text(
        "# 주석은 무시\n"
        "LMS_USER_ID=student123\n"
        "LMS_PASSWORD=secret\n"
        "\n"
        "DOWNLOAD_RULE=both\n",
        encoding="utf-8",
    )

    with _make_db(tmp_path):
        result = db.migrate_from_env(env_file)
        assert result is True
        assert db.get("LMS_USER_ID") == "student123"
        assert db.get("LMS_PASSWORD") == "secret"
        assert db.get("DOWNLOAD_RULE") == "both"


def test_db_migrate_skips_when_data_exists(tmp_path):
    """DB에 이미 설정이 있으면 마이그레이션을 건너뛴다."""
    import src.db as db

    env_file = tmp_path / ".env"
    env_file.write_text("LMS_USER_ID=new_value\n", encoding="utf-8")

    with _make_db(tmp_path):
        db.set("LMS_USER_ID", "existing")
        result = db.migrate_from_env(env_file)
        assert result is False
        assert db.get("LMS_USER_ID") == "existing"


def test_db_migrate_no_env_file(tmp_path):
    """env 파일이 없으면 False를 반환하고 오류가 없어야 한다."""
    import src.db as db

    with _make_db(tmp_path):
        result = db.migrate_from_env(tmp_path / "nonexistent.env")
        assert result is False


def test_db_init_idempotent(tmp_path):
    """init()을 여러 번 호출해도 오류가 없어야 한다."""
    import src.db as db

    with _make_db(tmp_path):
        db.init()
        db.init()
        db.init()
