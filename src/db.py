"""SQLite 기반 설정 저장소.

data/app.db (Docker: /data/app.db) 에 key-value 방식으로 설정을 저장한다.
민감값은 호출 쪽에서 crypto.py로 암호화한 뒤 전달해야 한다.

테이블 생성은 _connect() 내부에서 자동으로 수행되므로 별도 init() 호출 없이도
get/set을 즉시 사용할 수 있다. init()는 명시적 초기화가 필요한 경우를 위해 공개한다.
"""

import sqlite3
from pathlib import Path


def _db_path() -> Path:
    base = Path("/data") if Path("/data").exists() else Path("data")
    return base / "app.db"


def _connect() -> sqlite3.Connection:
    """DB 연결을 반환한다. 테이블이 없으면 자동 생성한다."""
    path = _db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    _ensure_schema(conn)
    return conn


def _ensure_schema(conn: sqlite3.Connection) -> None:
    """앱에서 사용하는 SQLite 테이블을 생성한다."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key        TEXT PRIMARY KEY,
            value      TEXT NOT NULL DEFAULT '',
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS event_logs (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id       TEXT NOT NULL UNIQUE,
            created_at     TEXT NOT NULL,
            actor_user_id  TEXT,
            session_id     TEXT,
            event_type     TEXT NOT NULL,
            action         TEXT NOT NULL,
            status         TEXT NOT NULL,
            target_type    TEXT,
            target_id      TEXT,
            course_id      TEXT,
            course_name    TEXT,
            lecture_title  TEXT,
            lecture_url    TEXT,
            week_label     TEXT,
            message        TEXT,
            error_code     TEXT,
            error_message  TEXT,
            log_path       TEXT,
            metadata_json  TEXT
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_event_logs_created_at ON event_logs(created_at DESC)")
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_event_logs_event_type_created_at ON event_logs(event_type, created_at DESC)"
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_event_logs_status_created_at ON event_logs(status, created_at DESC)")


def init() -> None:
    """DB 및 settings 테이블을 명시적으로 초기화한다. 앱 시작 시 호출 권장."""
    with _connect():
        pass


def get(key: str, default: str = "") -> str:
    """키에 해당하는 값을 반환한다. 없으면 default 반환."""
    with _connect() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else default


def set(key: str, value: str) -> None:
    """단일 키-값을 저장한다 (없으면 삽입, 있으면 갱신)."""
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO settings (key, value, updated_at)
            VALUES (?, ?, datetime('now'))
            ON CONFLICT(key) DO UPDATE
                SET value      = excluded.value,
                    updated_at = excluded.updated_at
            """,
            (key, value),
        )


def set_many(pairs: dict) -> None:
    """여러 키-값을 단일 트랜잭션으로 저장한다."""
    with _connect() as conn:
        conn.executemany(
            """
            INSERT INTO settings (key, value, updated_at)
            VALUES (?, ?, datetime('now'))
            ON CONFLICT(key) DO UPDATE
                SET value      = excluded.value,
                    updated_at = excluded.updated_at
            """,
            [(k, v) for k, v in pairs.items()],
        )
