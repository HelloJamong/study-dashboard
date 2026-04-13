# Changelog

## [v26.04.06] - 2026-04-14

### 프론트 XSS/HTML Injection 방어

#### 수정
- **`esc()` 헬퍼 추가** (`frontend/index.html`)
  - `document.createElement('div').textContent` 기반 HTML 이스케이프 유틸
  - `&`, `<`, `>`, `"`, `'` 등 모든 특수문자를 안전하게 변환
- **`renderCourseCards()` 보호**
  - `course.name`, `course.term` → `esc()` 적용
  - 숫자 값(`pending`, `total`, `pct`)은 연산 결과이므로 현행 유지
- **`loadCourseDetail()` 주차/강의 렌더링 보호**
  - `week.title` → `esc()` 적용
  - 강의 row의 `data-url`, `data-title`, `data-week`, `data-course` → `innerHTML` 템플릿 문자열 대신 `element.dataset` 직접 할당
  - `lec.title`, `lec.duration` → `element.textContent` 직접 할당 (innerHTML 우회)
  - `lec.completion` → `'completed'` / `'incomplete'` 두 값만 허용하도록 화이트리스트 검증
- **오류 메시지 보호**
  - 강의 목록/상세 오류 div의 `err.message` → `esc()` 적용

## [v26.04.05] - 2026-04-14

### 보안 접근 제어 보강

#### 수정
- **Settings API 인증 추가** (`backend/api/routes/settings.py`)
  - `GET /api/settings`, `PUT /api/settings` 모두 `_require_auth()` 추가
  - 비로그인 상태에서 설정 조회/변경 시 401 반환
- **Auto status API 인증 추가** (`backend/api/routes/auto.py`)
  - `GET /api/auto/status`에 `_require_auth()` 추가 (start/stop은 기존에 이미 인증 적용)
- **미조치 항목 결정**
  - `GET /api/player/status`: 로컬 단일 사용자 서비스 특성상 공개 유지
  - `allow_origins=["*"]` CORS: 로컬 전용 배포 환경이므로 현행 유지

## [v26.04.04] - 2026-04-13

### 대시보드 통계 초기 로딩 및 로그아웃 버튼 가시성 개선

#### 수정
- **대시보드 통계 초기 로딩 문제** (`frontend/index.html`)
  - 로그인 직후 대시보드 진입 시 통계가 0/0으로 잘못 표시되던 문제 수정
  - `loadStats()` 호출 시 백엔드 `details`가 비어있으면(과목 미로딩 상태) `GET /api/courses`를 먼저 호출해 `app_state.details`를 채운 뒤 통계를 재조회하도록 개선
  - 이미 과목이 로드된 세션에서는 추가 요청 없이 즉시 통계 갱신 유지
- **로그아웃 버튼 가시성** (`frontend/index.html`)
  - 설정 등 페이지 내용이 길어질 때 로그아웃 버튼이 화면 밖으로 밀려 보이지 않던 문제 수정
  - `#app-shell`을 `min-h-screen` → `h-screen overflow-hidden`으로, `aside`에 `overflow-y-auto` 추가
  - 사이드바가 뷰포트 내에서 독립 스크롤하므로 어느 페이지에서도 로그아웃 버튼 항상 접근 가능

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
- **로그인 실패/지연 처리 보강** (`backend/api/routes/auth.py`, `frontend/index.html`)
  - 백엔드 로그인 시도에 45초 제한을 적용해 Playwright 로그인 대기가 무한히 이어지지 않도록 함
  - cancellation에 즉시 응답하지 않는 Playwright 작업도 timeout 시 사용자 응답을 막지 않도록 처리
  - 잘못된 계정/비밀번호 입력 시 SSO 로그인 폼 잔류, alert, 오류 문구를 짧은 폴링으로 감지해 실패 메시지를 더 빠르게 반환 (`src/auth/login.py`)
  - 로그인 성공/실패 판정 단위 테스트 추가 (`tests/test_login.py`) — 폼 잔류 시 빠른 실패, URL 전환 시 성공 시나리오 검증
  - 프론트 로그인 요청에 60초 timeout을 적용하고 실패/timeout 메시지를 로그인 카드에 표시
  - 학번/비밀번호 미입력 시 즉시 경고 메시지 표시
- **로컬 HTTPS 지원** (`frontend/nginx.conf`, `docker-compose.yml`)
  - nginx가 443/TLS를 직접 처리하고 `http://localhost:3000`을 `https://localhost:3443`으로 리다이렉트
  - backend 포트 `8000`은 로컬 호스트에만 바인딩해 브라우저 트래픽은 nginx HTTPS 프록시를 거치도록 조정
  - 최소 보안 헤더(HSTS, nosniff, SAMEORIGIN, Referrer-Policy) 추가
  - stale inline JS 캐시 방지를 위해 정적 응답에 `Cache-Control: no-store` 적용
- **로컬 인증서 생성 도구/문서**
  - `scripts/generate-local-cert.sh`: self-signed localhost 인증서 생성
  - `docs/https-local.md`: HTTPS 실행 및 인증서 신뢰 안내
  - `certs/.gitkeep`: 인증서 디렉터리만 추적하고 실제 인증서/키는 gitignore로 제외

#### 변경
- `POST /api/player/stop`에 로그인 상태 검사를 추가해 비인증 중지 요청을 차단
- backend/test 코드의 Ruff 지적 사항 정리
  - import 정렬
  - `HTTPException` 재발생 원인 명시 (`from None` / `from e`)
  - `Optional[...]` 타입 표기를 `... | None`으로 변경
  - 미사용 import 제거
- `docs/web-completeness-checklist.md`의 완료 항목을 체크 및 취소선으로 표시
- 로컬 HTTPS 인증서 실파일(`certs/local.crt`, `certs/local.key`)을 git 대상에서 제외

#### 검증
- `uv run pytest` — 41 passed
- `uv run ruff check .` — All checks passed
- FastAPI smoke 확인
  - `GET /api/health` → 200
  - `GET /api/auth/status` → 200
  - `GET /api/player/status` → 200
  - 비로그인 `POST /api/player/stop` → 401
  - nginx 설정 검증(`nginx -t`) → successful
  - `docker compose build frontend` → successful

#### 남은 확인
- 실제 LMS 계정으로 재생 성공/실패/중지 케이스 수동 검증 필요
- 브라우저에서 self-signed 인증서 경고 수락 또는 trust store 등록 필요
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
