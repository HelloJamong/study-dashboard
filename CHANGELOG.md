# Changelog

## [v26.04.03] - 2026-04-03

### 웹 재생 안정성 및 피드백 보강

#### 추가
- **웹 재생 상태 확장** (`backend/api/state.py`)
  - `PlaybackProgress.status`: `idle` / `playing` / `completed` / `error` / `stopped` 상태 구분
  - `PlaybackProgress.log_path`: 웹 재생 실패 시 저장된 진단 로그 경로 노출
- **웹 재생 결과 처리 강화** (`backend/api/routes/player.py`)
  - `play_lecture()` 반환값을 검사해 완료/오류/중지 상태를 명확히 반영
  - 재생 실패 시 `logs/*_web_play.log` 진단 로그 저장
  - 재생 완료 시 캐시된 강의 항목의 `completion`을 즉시 `completed`로 갱신
- **대시보드 재생 피드백 UI** (`frontend/index.html`)
  - 재생 완료/중지/실패 메시지 표시
  - 실패 시 `/api/player/status`의 `error`와 `log_path` 표시
  - 재생 완료 감지 후 통계와 강의 목록 캐시 자동 갱신
- **웹 player route 회귀 테스트** (`tests/test_web_player.py`)
  - 재생 완료 후 강의 completion 갱신 검증
  - 재생 오류가 status/error/log_path에 유지되는지 검증

#### 변경
- `POST /api/player/stop`에 로그인 상태 검사를 추가해 비인증 중지 요청을 차단
- backend/test 코드의 Ruff 지적 사항 정리
  - import 정렬
  - `HTTPException` 재발생 원인 명시 (`from None` / `from e`)
  - `Optional[...]` 타입 표기를 `... | None`으로 변경
  - 미사용 import 제거
- `docs/web-completeness-checklist.md`의 완료 항목을 체크 및 취소선으로 표시

#### 검증
- `uv run pytest` — 36 passed
- `uv run ruff check .` — All checks passed
- FastAPI smoke 확인
  - `GET /api/health` → 200
  - `GET /api/auth/status` → 200
  - `GET /api/player/status` → 200
  - 비로그인 `POST /api/player/stop` → 401

#### 남은 확인
- 실제 LMS 계정으로 재생 성공/실패/중지 케이스 수동 검증 필요
- 재생 완료 후 LMS 서버 출석 반영까지 실제 확인 필요

---

## [v26.04.02] - 2026-04-02

### 웹 대시보드 (Docker 풀스택 구성)

#### 추가
- **FastAPI 백엔드** (`backend/`)
  - `backend/main.py`: FastAPI 앱 진입점, 앱 시작 시 DB 초기화 및 `Config.load()` 호출
  - `backend/api/state.py`: 전역 앱 상태 (Playwright 세션, 재생 상태)
  - `backend/api/routes/auth.py`: `POST /api/auth/login|logout`, `GET /api/auth/status`
  - `backend/api/routes/courses.py`: `GET /api/courses`, `/api/courses/{id}`, `/api/courses/stats`, `POST /api/courses/refresh`
  - `backend/api/routes/player.py`: `POST /api/player/play|stop`, `GET /api/player/status`
  - `backend/api/routes/settings.py`: `GET|PUT /api/settings`
- **nginx 프론트엔드** (`frontend/`)
  - `frontend/index.html`: SPA 웹 대시보드 (로그인 / 대시보드 / 강의목록 / 설정)
  - `frontend/nginx.conf`: 정적 파일 서빙 + `/api/*` → 백엔드 프록시
  - `frontend/Dockerfile`: nginx:alpine 기반
- **Docker Compose 풀스택 구성** (`docker-compose.yml`)
  - `backend`: FastAPI + Playwright, 소스 볼륨 마운트 + `--reload` 핫 리로드
  - `frontend`: nginx, HTML/nginx.conf 볼륨 마운트로 재빌드 없이 즉시 반영
- **의존성 추가** (`pyproject.toml`): `fastapi>=0.115.0`, `uvicorn[standard]>=0.32.0`
- `uv.lock` 재생성

#### 변경
- `backend/Dockerfile`: ENTRYPOINT/CMD 분리 — `docker-compose.yml`의 `command:`로 오버라이드 가능
- 루트 `Dockerfile` (TUI 전용) 제거 — 웹 대시보드로 대체

---

## [v26.04.01] - 2026-04-01

### 초기 구성

study-helper(HelloJamong/study-helper) 프로젝트에서 마이그레이션.

### 추가
- **SQLite 기반 설정 저장소** (`src/db.py`)
  - 기존 `.env` 파일 방식에서 `data/app.db`로 전환
  - `get / set / set_many` key-value API
  - `migrate_from_env()`: 기존 `.env` 보유 시 최초 실행 시 자동 마이그레이션
- **`Config.load()`** (`src/config.py`)
  - 클래스 속성을 앱 시작 시 DB에서 일괄 로드하는 명시적 초기화 메서드 추가
  - `python-dotenv` 의존성 제거 (`pyproject.toml`)
- **텔레그램 알림** (`src/notifier/`)
  - 재생 완료·실패 알림 (`telegram_notifier.py`)
  - 마감 임박 항목 감지 및 알림 (`deadline_checker.py`)
- **자동 모드** (`src/ui/auto.py`): 미완료 강의 일괄 재생
- **버전 체크** (`src/updater.py`): 과목 로딩과 병렬로 GitHub 최신 버전 확인
- **STT 엔진**: faster-whisper (CTranslate2 기반, torch 불필요)
- **GitHub Actions 워크플로우** (CI, Docker 릴리즈) — 재건 중 자동 실행 비활성화
