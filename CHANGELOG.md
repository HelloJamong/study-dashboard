# Changelog

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
