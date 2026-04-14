# 웹서비스 완성도 개발 체크리스트

이 문서는 `study-dashboard`가 기존 `study-helper` 핵심 로직을 웹서비스로 완전히 연결하기 위해 남은 작업을 추적하는 체크리스트입니다.

- 기준일: 2026-04-14
- 현재 웹 구현 범위: 로그인, 과목/강의 목록, 대시보드 미시청/과제/퀴즈 통계, 백그라운드 재생 시작/중지, 다운로드 task, 자동 재생 모드, 요약 상세 조회, 설정 저장
- 현재 미구현 핵심 범위: STT 웹 task, AI 요약 생성 웹 task, 요약 목록 대시보드, 텔레그램 웹 전송/테스트, API 보안/CORS 추가 정리, 수동 브라우저 검증

## 체크 규칙

- `[ ]` 미완료
- `[x]` 완료
- 완료 처리 시 관련 PR/커밋/테스트 근거를 하위 bullet에 기록
- 기능 구현 후에는 가능한 한 다음 검증을 함께 체크
  - API smoke test
  - 프론트 수동 확인
  - `uv run pytest`
  - `uv run ruff check .`


## 현재 남은 구현 필요 항목 요약

- [ ] `/api/courses/stats` 백엔드 lazy loading/lock/error 상태 개선
- [ ] 브라우저 기반 수동 검증: 재생 성공/실패/중지, 다운로드 mp4/mp3/both, 자동 모드 ON/OFF
- [ ] CORS 정책과 `GET /api/player/status` 공개 여부 정리
- [ ] 다운로드 완료 파일 경로 표시
- [ ] STT 결과 텍스트 보기/모델 로딩 상세 표시
- [ ] AI 요약 결과 보기 UI 고도화
- [ ] 요약 목록 대시보드(`GET /api/summaries` 포함) 구현
- [ ] 자동 모드 pipeline에 다운로드/STT/요약/텔레그램 step 연결
- [ ] 전체 학기 과목 조회/전환 API와 UI 완성
- [ ] 텔레그램 연결 테스트/요약 전송/자동 삭제 웹 연결
- [ ] task 저장소 영속화/오래된 task 정리/동시 실행 정책 결정
- [ ] README의 React/Vite 등 기술 스택 설명을 실제 구현과 일치시키기
- [ ] 운영 정책: singleton state, uvicorn workers, 프로덕션 `--reload` 제거, volume/secret 문서화


---

## 0. 현재 구현된 웹 기능 기준선

- [x] ~~로그인 화면 구현~~
  - 관련 파일: `frontend/index.html`, `backend/api/routes/auth.py`
- [x] ~~로그아웃 구현~~
  - 관련 API: `POST /api/auth/logout`
- [x] ~~인증 상태 확인 구현~~
  - 관련 API: `GET /api/auth/status`
- [x] ~~과목 목록 조회 구현~~
  - 관련 API: `GET /api/courses`
- [x] ~~과목 상세/주차별 강의 목록 조회 구현~~
  - 관련 API: `GET /api/courses/{course_id}`
- [x] ~~강의 백그라운드 재생 시작 구현~~
  - 관련 API: `POST /api/player/play`
- [x] ~~강의 재생 중지 구현~~
  - 관련 API: `POST /api/player/stop`
- [x] ~~재생 상태 polling 구현~~
  - 관련 API: `GET /api/player/status`
- [x] ~~기본 설정 조회/저장 구현~~
  - 관련 API: `GET /api/settings`, `PUT /api/settings`
- [x] ~~Docker Compose 기반 backend/frontend 실행 구조 구현~~
  - 관련 파일: `docker-compose.yml`, `backend/Dockerfile`, `frontend/Dockerfile`, `frontend/nginx.conf`


## 0.1 2026-04-14 대시보드/다운로드 경로 변경 완료

- [x] ~~메인 대시보드에서 전체 강의 완료/전체 표시 제거~~
- [x] ~~대시보드에 제출 필요 과제 전체 수량 표시~~
- [x] ~~대시보드에 제출 필요 퀴즈 전체 수량 표시~~
- [x] ~~대시보드에 미시청 영상 전체 수량 표시~~
- [x] ~~강의 목록에서 진행률 막대 제거~~
- [x] ~~강의 목록 과목 카드에 `미시청 영상 n개 / 과제 n개 / 퀴즈 n개` 표시~~
- [x] ~~다운로드 경로 선택 메뉴와 입력 기능 제거~~
- [x] ~~다운로드 경로를 Config/API/CLI에서 `/download`로 고정~~
- [x] ~~`docker-compose.yml`에서 `./download:/download` 마운트 명시~~
- [x] ~~과거 DB에 저장된 `DOWNLOAD_DIR` 무시 정책 테스트 추가~~

## 0.2 2026-04-14 DB 행위 로그 구현 완료

- [x] ~~`event_logs` SQLite 테이블 생성~~
- [x] ~~로그 타임스탬프를 `YYYY-MM-DD HH:mm:ss` 형식으로 저장~~
- [x] ~~로그 저장 실패가 원 기능을 막지 않는 best-effort 기록 함수 구현~~
- [x] ~~민감정보 키(`password`, `token`, `api_key`, `secret` 등) metadata 마스킹~~
- [x] ~~로그인 성공/실패 로그 저장~~
- [x] ~~로그아웃 로그 저장~~
- [x] ~~설정 변경 성공/실패 로그 저장 및 민감 설정값 마스킹~~
- [x] ~~영상 재생 시작/성공/실패/중지 로그 저장~~
- [x] ~~다운로드 시작/성공/실패/미지원/취소 로그 저장~~
- [x] ~~`GET /api/logs` 조회 API 추가~~
- [x] ~~좌측 메뉴바에 로그 조회 드롭다운 추가~~
- [x] ~~전체/로그인·로그아웃/설정 변경/영상 재생/다운로드 로그 웹 조회 페이지 추가~~
- [x] ~~행위 로그 단위/라우트 테스트 추가~~

## 0.3 STT 다운로드 파이프라인 구현 완료

- [x] ~~다운로드 규칙이 `mp3` 또는 `mp4 + mp3`일 때만 STT 사용 가능하도록 제한~~
- [x] ~~웹 설정에 `STT 변환 후 mp3 삭제` 토글 추가~~
- [x] ~~백엔드 설정 저장 시 `mp4` 규칙에서는 STT/AI/STT 후 삭제 옵션을 자동 비활성화~~
- [x] ~~다운로드 task 완료 후 STT 변환 step 연결~~
- [x] ~~STT 변환 성공 시 `.txt` 파일을 task result에 포함~~
- [x] ~~STT 변환 성공 후 옵션에 따라 생성된 mp3 파일 삭제~~
- [x] ~~STT 성공/실패 DB 행위 로그 기록~~
- [x] ~~Whisper 모델과 STT 언어 설정을 웹 다운로드 task에 반영~~

## 0.4 AI 요약 파이프라인 구현 완료

- [x] ~~Gemini API 키와 모델 설정이 있을 때만 AI 요약 활성화~~
- [x] ~~STT 변환 성공 후 Gemini 요약 자동 실행~~
- [x] ~~웹 설정에 `AI 요약 후 원본 txt 삭제` 토글 추가~~
- [x] ~~요약 성공 시 `_summarized.txt` 파일을 task result에 포함~~
- [x] ~~요약 성공 후 옵션에 따라 STT 원본 txt 파일 삭제~~
- [x] ~~AI 요약 성공/실패 DB 행위 로그 기록~~
- [x] ~~로그 조회 메뉴에 AI 요약 필터 추가~~
- [x] ~~Gemini 모델/추가 프롬프트 설정을 웹 다운로드 task에 반영~~

## 0.5 AI 요약 프롬프트 편집 UI 구현 완료

- [x] ~~웹 AI 요약 설정에 현재 요약 프롬프트 textarea 표시~~
- [x] ~~요약 프롬프트 편집 버튼 추가~~
- [x] ~~요약 프롬프트 초기화 버튼 추가~~
- [x] ~~초기화 시 기본 프롬프트(`DEFAULT_SUMMARY_PROMPT`)로 복원~~
- [x] ~~편집된 프롬프트를 `SUMMARY_PROMPT_TEMPLATE` 설정으로 저장~~
- [x] ~~다운로드→STT→AI 요약 pipeline에 사용자 프롬프트 템플릿 반영~~
- [x] ~~프롬프트 내 `{text}` placeholder에 STT 원문 삽입 지원~~


---

## 1. P0 — 웹 재생 안정성 및 사용자 피드백 보강

현재 웹 재생 경로는 `play_lecture()` 반환 상태를 충분히 반영하지 않으며, 실패/완료 상태가 UI에 제대로 표시되지 않을 수 있습니다.

### 1.1 백엔드 재생 결과 처리

- [x] ~~`backend/api/routes/player.py`에서 `play_lecture()` 반환값을 `final_state`로 수신~~
- [x] ~~`final_state.error`가 있으면 `app_state.playback.error`에 저장~~
- [x] ~~`final_state.ended`가 있으면 `app_state.playback.ended`에 저장~~
- [x] ~~재생 종료 시 `app_state.playback.current`, `duration`, `progress_pct` 최종값 유지~~
- [x] ~~취소와 오류를 구분해서 상태 저장~~
  - 사용자 중지: cancelled/stopped
  - 재생 실패: error
  - 정상 완료: completed

### 1.2 프론트 재생 오류 표시

- [x] ~~대시보드에 최근 재생 오류 메시지 영역 추가~~
- [x] ~~`/api/player/status` 응답의 `error`를 UI에 표시~~
- [x] ~~재생 실패 시 idle 카드만 표시하지 않고 실패 사유 표시~~
- [x] ~~사용자가 오류 메시지를 닫거나 다음 재생 시 초기화할 수 있게 처리~~

### 1.3 재생 완료 후 강의 상태 갱신

- [x] ~~웹 재생 완료 시 해당 lecture의 `completion`을 로컬 cache에서 `completed`로 갱신~~
- [x] ~~재생 완료 후 `/api/courses/stats`가 최신 완료/미수강 수를 반환하도록 갱신~~
- [x] ~~프론트에서 재생 완료 감지 후 통계 카드 자동 refresh~~
- [x] ~~프론트에서 재생 완료 감지 후 강의 목록/상세 패널 자동 refresh 또는 stale 표시~~
- [x] ~~완료 갱신 실패 시 사용자가 수동 새로고침하도록 안내~~
  - 근거: `refresh_recommended` 응답과 대시보드 완료 메시지 안내

### 1.4 웹 재생 로그

- [x] ~~웹 재생 경로에서도 `debug=True` 또는 `log_fn` 기반 로그 수집~~
- [x] ~~오류 발생 시 `logs/*_play.log` 저장~~
- [ ] 정상 완료 시에도 필요하면 진단 로그 저장 여부 결정
- [x] ~~`/api/player/status` 또는 별도 API에서 최근 재생 로그 경로/요약 제공 여부 결정~~

### 1.5 검증

- [ ] 재생 성공 케이스 수동 확인
- [ ] 재생 실패 케이스 수동 확인
- [ ] 중지 버튼 동작 확인
- [ ] 재생 완료 후 통계 갱신 확인
- [ ] 재생 완료 후 강의 목록 완료 표시 확인
- [x] ~~`uv run pytest` 통과~~
  - 2026-04-14: `76 passed`
- [x] ~~`uv run ruff check .` 통과~~
  - 2026-04-14: `All checks passed!`
- [x] ~~`uv run ruff format --check .` 통과~~
  - 2026-04-14: `65 files already formatted`

---

## 2. P0 — 대시보드 통계 초기 로딩 문제 해결

현재 로그인 직후 `app_state.details`가 비어 있으면 대시보드 통계가 0/0처럼 보일 수 있습니다.

### 2.1 백엔드 통계 API 개선

- [ ] `/api/courses/stats`에서 `app_state.details`가 비어 있으면 과목/상세 정보를 자동 로딩
- [ ] 로딩 중 중복 요청 방지를 위한 lock 도입 검토
- [ ] 과목 로딩 실패 시 500 대신 사용자 친화적 에러 메시지 반환
- [ ] 통계 응답에 `loaded`, `loading`, `last_refreshed_at` 같은 상태 필드 추가 검토

### 2.2 프론트 통계 UX 개선

- [ ] 통계 로딩 중 spinner/skeleton 표시
- [ ] 로그인 직후 통계가 아직 없으면 “강의 정보를 불러오는 중” 표시
- [ ] 통계 로딩 실패 시 조용히 무시하지 않고 오류 표시
- [ ] “강의 목록 새로고침”과 통계 갱신이 같은 cache를 사용하도록 정리

### 2.3 검증

- [ ] 로그인 직후 대시보드 통계가 실제 값으로 로딩되는지 확인
- [ ] `/api/courses`를 먼저 호출하지 않아도 `/api/courses/stats`가 정상 동작하는지 확인
- [ ] LMS 로딩 실패 시 UI 오류 표시 확인
- [ ] `uv run pytest` 통과
- [ ] `uv run ruff check .` 통과

---

## 3. P0 — 보안/접근 제어 보강

현재 일부 관리 API가 로그인 없이 접근 가능합니다.

### 3.1 Settings API 보호

- [x] ~~`GET /api/settings`에 인증 체크 추가~~
- [x] ~~`PUT /api/settings`에 인증 체크 추가~~
- [x] ~~인증 실패 시 401 반환~~
- [x] ~~민감값은 계속 GET 응답에서 제외~~
- [x] ~~API key/token placeholder 정책 정리~~
  - [x] ~~저장된 값은 표시하지 않음~~
  - [x] ~~변경 시에만 새 값 입력~~
  - [x] ~~빈 값 전송 시 기존 민감값 유지 여부 명확화~~

### 3.2 Player API 보호

- [x] ~~`POST /api/player/stop`에 인증 체크 추가~~
- [ ] `GET /api/player/status`의 공개 여부 결정
  - 로컬 단일 사용자 서비스라면 공개 가능
  - 외부 노출 가능성이 있으면 인증 요구
- [x] ~~`POST /api/player/play`는 현재 인증 체크 유지~~

### 3.3 CORS 정책 정리

- [ ] `allow_origins=["*"]` 제거 여부 검토
- [ ] 개발/운영 환경별 허용 origin 분리
- [ ] Docker Compose 기본 frontend origin만 허용하도록 설정 검토

### 3.4 검증

- [ ] 비로그인 상태에서 settings API 접근 시 401 확인
- [ ] 로그인 상태에서 settings API 정상 동작 확인
- [ ] 비로그인 상태에서 player stop 차단 확인
- [ ] 프론트 설정 화면 정상 저장 확인
- [ ] `uv run pytest` 통과
- [ ] `uv run ruff check .` 통과

---

## 4. P1 — 프론트 XSS/HTML Injection 위험 제거

현재 LMS에서 가져온 과목명/강의명/주차명이 `innerHTML` 템플릿에 직접 삽입됩니다.

### 4.1 과목 카드 렌더링 개선

- [x] ~~`renderCourseCards()`에서 `innerHTML` 직접 삽입 제거 또는 escape 적용~~
- [x] ~~과목명 `course.name`을 `textContent`로 삽입 또는 escape 적용~~
- [x] ~~학기명 `course.term`을 `textContent`로 삽입 또는 escape 적용~~
- [ ] 숫자 값은 숫자로 검증 후 렌더링

### 4.2 강의 상세 렌더링 개선

- [x] ~~`loadCourseDetail()`의 week/lecture 렌더링에서 `innerHTML` 직접 삽입 제거 또는 escape 적용~~
- [x] ~~`week.title`을 `textContent`로 삽입 또는 escape 적용~~
- [x] ~~`lec.title`을 `textContent`로 삽입~~
- [x] ~~`lec.duration`을 `textContent`로 삽입~~
- [x] ~~`data-*` 속성은 문자열 template이 아니라 `element.dataset`으로 할당~~

### 4.3 검증

- [ ] 특수문자 포함 과목명 렌더링 확인
- [ ] HTML 태그처럼 보이는 강의명 렌더링 확인
- [ ] 재생 버튼 dataset 값 정상 전달 확인
- [ ] 브라우저 콘솔 오류 없음 확인

---

## 5. P1 — 다운로드 기능 웹 연결

기존 엔진은 `src/ui/download.py`, `src/downloader/video_downloader.py`, `src/converter/audio_converter.py`에 있으나 웹 API/UI가 없습니다.

### 5.1 백엔드 다운로드 API 설계

- [x] ~~긴 작업 처리를 위한 task 모델 설계~~
  - 예: `TaskState`, `TaskProgress`, `TaskResult`
- [x] ~~`POST /api/tasks/download` 또는 `POST /api/lectures/download` 추가~~
- [x] ~~`GET /api/tasks/{task_id}` 상태 조회 API 추가~~
- [x] ~~`POST /api/tasks/{task_id}/cancel` 취소 API 추가 검토~~
- [x] ~~다운로드 진행률 저장~~
  - [ ] downloaded bytes
  - [ ] total bytes
  - [x] ~~percent~~
  - [x] ~~current step~~
  - [x] ~~error~~
- [ ] 동시에 여러 다운로드 허용 여부 결정

### 5.2 기존 다운로드 엔진 재사용

- [x] ~~`src/ui/download.py`의 Rich UI 의존 로직과 순수 pipeline 로직 분리~~
- [x] ~~`extract_video_url()` 웹 API 경로에서 재사용~~
- [x] ~~`download_video_with_browser()` 웹 API 경로에서 재사용~~
- [x] ~~다운로드 실패 시 DB 행위 로그 저장~~
- [x] ~~learningx 다운로드 미지원 케이스를 웹 UI에 표시~~

### 5.3 프론트 다운로드 UI

- [x] ~~강의 row에 다운로드 버튼 추가~~
- [x] ~~다운로드 진행률 UI 추가~~
- [ ] 다운로드 완료 파일 경로 표시
- [x] ~~다운로드 실패 메시지 표시~~
- [x] ~~다운로드 중 중복 클릭 방지~~
- [x] ~~다운로드 설정(`DOWNLOAD_RULE`)과 UI 동작 연결 (`DOWNLOAD_DIR`은 `/download` 고정)~~

### 5.4 검증

- [ ] 영상만 다운로드 확인
- [ ] 음성만 다운로드 확인
- [ ] 영상+음성 다운로드 확인
- [ ] URL 추출 실패 케이스 UI 표시 확인
- [ ] 다운로드 중 브라우저/페이지 상태 충돌 여부 확인
- [x] ~~`uv run pytest` 통과~~
  - 2026-04-14: `76 passed`
- [x] ~~`uv run ruff check .` 통과~~
  - 2026-04-14: `All checks passed!`

---

## 6. P1 — STT 기능 웹 연결

기존 엔진은 `src/stt/transcriber.py`에 있으나 웹 API/UI가 없습니다.

### 6.1 백엔드 STT API/Task

- [x] ~~다운로드 task 이후 STT step으로 연결~~
- [x] ~~단독 STT 실행 API 필요 여부 결정~~
  - 결정: 우선 다운로드 task pipeline에 통합하고 단독 API는 보류
- [x] ~~STT 진행 상태 표시 방식 결정~~
  - faster-whisper segment 기반 progress 가능 여부 검토
  - [x] ~~최소 current step 표시~~
- [ ] Whisper 모델 로딩 상태 표시
- [x] ~~STT 결과 `.txt` 파일 경로 저장~~

### 6.2 프론트 STT UI

- [x] ~~강의별 STT 실행 상태 표시~~
  - 다운로드 task 상태 메시지로 `STT 변환 중` 표시
- [x] ~~STT 변환 중/완료/실패 표시~~
- [ ] STT 결과 텍스트 보기 기능 추가 여부 결정
- [x] ~~STT 설정이 꺼져 있거나 다운로드 규칙이 mp4일 때 안내 표시~~

### 6.3 검증

- [x] ~~`STT_ENABLED=true`에서 STT 실행 확인~~
  - 검증: 다운로드 파이프라인/웹 다운로드 route 테스트
- [x] ~~`STT_ENABLED=false`에서 STT skip 확인~~
- [x] ~~`WHISPER_MODEL` 설정 반영 확인~~
- [x] ~~`STT_LANGUAGE` 설정 반영 확인~~
- [ ] STT 실패 시 다음 step 처리 정책 확인

---

## 7. P1 — AI 요약 기능 웹 연결

기존 엔진은 `src/summarizer/summarizer.py`에 있으나 웹 API/UI가 없습니다.

### 7.1 백엔드 요약 API/Task

- [x] ~~STT 결과 `.txt`를 입력으로 요약 step 연결~~
- [x] ~~단독 요약 실행 API 필요 여부 결정~~
  - 결정: 우선 다운로드 task pipeline에 통합하고 단독 API는 보류
- [x] ~~요약 진행 상태 표시~~
  - 다운로드 task 상태 메시지로 `AI 요약 중` 표시
- [x] ~~요약 결과 파일 저장 경로 정책 정리~~
  - STT txt와 같은 위치에 `_summarized.txt` 생성
- [ ] Gemini/OpenAI 오류 메시지 정규화
- [x] ~~API key/모델 미설정 시 AI 요약 설정 비활성화~~

### 7.2 OpenAI 설정 정리

- [ ] `OPENAI_MODEL` 설정 추가 여부 결정
- [ ] 웹 설정에 OpenAI 모델 입력 추가
- [ ] Gemini/OpenAI 선택에 따라 모델 필드 분리
- [ ] `src/ui/download.py`의 OpenAI 모델 fallback 버그 수정
  - 현재 OpenAI 선택 시 Gemini 기본 모델이 전달될 위험 있음
- [ ] 아직 OpenAI를 웹에서 지원하지 않을 경우 OpenAI 옵션 숨김 처리

### 7.3 추가 요약 지시사항 UI

- [x] ~~웹 설정 폼에 요약 프롬프트 textarea 추가~~
- [x] ~~기존 값 표시/수정/초기화 정책 결정~~
- [x] ~~백엔드 `GET /api/settings`와 `PUT /api/settings` 연결 확인~~

### 7.4 프론트 요약 UI

- [ ] 강의별 단독 요약 실행 버튼 추가
- [x] ~~요약 중/완료/실패 상태 표시~~
- [x] ~~요약 결과 보기 버튼 추가~~
  - 기존 생성 요약 파일에 대한 강의 상세 연결
- [ ] 요약 결과가 없을 때 생성 유도 표시

### 7.5 검증

- [x] ~~Gemini 요약 성공 확인~~
  - 검증: 다운로드 파이프라인/웹 다운로드 route 테스트
- [x] ~~API key 없음 케이스 확인~~
- [ ] 잘못된 API key 케이스 확인
- [ ] OpenAI를 지원하는 경우 OpenAI 요약 성공 확인
- [x] ~~추가 프롬프트 및 사용자 편집 프롬프트 반영 확인~~
- [ ] `uv run pytest` 통과
- [ ] `uv run ruff check .` 통과

---

## 8. P1 — 요약/마크다운 대시보드 구현

README는 마크다운 대시보드를 설명하지만 현재 summarizer는 `_summarized.txt` 파일을 생성합니다.

### 8.1 저장 포맷/경로 정책

- [ ] 요약 결과를 `.txt`로 유지할지 `.md`로 전환할지 결정
- [ ] README의 “마크다운” 표현과 실제 구현 일치시키기
- [ ] 저장 경로 구조 결정
  - 예: `/data/summaries/{term}/{course}/{week}/{lecture}.md`
- [ ] 기존 다운로드 폴더 내 `_summarized.txt`와 새 summaries 폴더 간 마이그레이션 필요 여부 검토
- [ ] 파일명 sanitize 정책 재사용

### 8.2 요약 조회 API

- [ ] `GET /api/summaries` 목록 API 추가
- [x] ~~`GET /api/summaries/{summary_id}` 상세 API 추가~~
- [ ] 과목/주차/강의별 요약 조회 지원
- [ ] 요약 파일 삭제 API 필요 여부 결정
- [x] ~~없는 요약 파일에 대한 404 처리~~

### 8.3 프론트 요약 대시보드

- [ ] 요약 목록/상세 페이지 추가
- [x] ~~Markdown 렌더링 라이브러리 사용 여부 결정~~
  - 결정: 외부 라이브러리 없이 `frontend/js/markdown.js`에서 안전한 DOM 렌더링 사용
  - [x] ~~CDN 사용 여부 검토~~
  - [x] ~~sanitization 필수~~
- [ ] 학기/과목/주차 계층 탐색 UI 추가
- [x] ~~강의 상세 패널에서 요약 보기 연결~~

### 8.4 검증

- [ ] 요약 파일 생성 후 웹에서 조회 확인
- [ ] Markdown 렌더링 확인
- [x] ~~HTML/script injection 방어 확인~~
  - 근거: `renderMarkdown()`이 HTML 문자열을 삽입하지 않고 `textContent` 기반 렌더링
- [ ] 파일 없음 케이스 UI 확인

---

## 9. P1 — 자동 모드 웹 구현

기존 자동 모드는 `src/ui/auto.py`에 CUI 중심으로 존재합니다.

### 9.1 자동 모드 백엔드 설계

- [x] ~~CUI `run_auto_mode()`와 웹 자동모드 로직 분리~~
- [x] ~~자동 모드 상태 모델 설계~~
  - [x] ~~enabled~~
  - [ ] current_step
  - [x] ~~current_course~~
  - [x] ~~current_lecture~~
  - [x] ~~next_run_at~~
  - [x] ~~schedule_hours~~
  - [x] ~~processed_count~~
  - [x] ~~error~~
- [x] ~~`GET /api/auto/status` 추가~~
- [x] ~~`POST /api/auto/start` 추가~~
- [x] ~~`POST /api/auto/stop` 추가~~
- [ ] `PUT /api/auto/schedule` 추가
- [ ] 서버 재시작 시 자동 모드 상태 복원 여부 결정

### 9.2 자동 모드 pipeline 연결

- [x] ~~미시청 강의 수집~~
- [x] ~~재생 step 연결~~
- [ ] 다운로드 step 연결
- [ ] STT step 연결
- [ ] 요약 step 연결
- [ ] 텔레그램 전송 step 연결
- [ ] step별 실패 정책 결정
  - 중단
  - 다음 강의로 계속
  - retry

### 9.3 프론트 자동 모드 UI

- [x] ~~대시보드에 자동 모드 ON/OFF 토글 추가~~
- [ ] 현재 파이프라인 단계 표시
  - 재생 중
  - 다운로드 중
  - STT 변환 중
  - 요약 중
  - 텔레그램 전송 중
- [x] ~~다음 실행 스케줄 표시~~
- [x] ~~처리 대상 강의 수 표시~~
- [x] ~~최근 자동 처리 결과/오류 표시~~
- [x] ~~스케줄 설정 UI 추가~~

### 9.4 검증

- [ ] 자동 모드 ON 동작 확인
- [ ] 자동 모드 OFF 동작 확인
- [ ] 스케줄 계산 확인
- [ ] 미시청 강의 없을 때 동작 확인
- [ ] 중간 step 실패 시 정책대로 동작 확인
- [ ] 서버 재시작/로그아웃 시 상태 처리 확인

---

## 10. P2 — 학기 선택 기능 구현

현재 scraper는 가장 많이 등장하는 term을 현재 학기로 간주해 자동 필터링합니다.

### 10.1 scraper/API 개선

- [ ] 전체 학기 목록을 반환할 수 있도록 `fetch_courses()` 구조 확장
- [ ] 자동 현재 학기 필터링을 옵션화
- [ ] `GET /api/terms` 또는 `/api/courses?term=...` API 추가
- [ ] 즐겨찾기/비교과/이전 학기 필터 정책 정리

### 10.2 프론트 학기 선택 UI

- [ ] 강의 목록 상단에 학기 선택 dropdown 추가
- [ ] 선택한 학기에 따라 과목 목록 refresh
- [ ] 대시보드 통계도 선택 학기 기준으로 반영할지 결정
- [ ] 요약 대시보드도 학기 기준 탐색 지원

### 10.3 검증

- [ ] 현재 학기 과목 조회 확인
- [ ] 이전 학기 과목 조회 확인
- [ ] 학기 전환 시 cache/state 정상 갱신 확인

---

## 11. P2 — 텔레그램 웹 기능 완성

### 11.1 텔레그램 설정 UX

- [ ] 웹에서 텔레그램 연결 테스트 버튼 추가
- [ ] `POST /api/settings/telegram/test` 또는 별도 API 추가
- [ ] 테스트 성공/실패 메시지 표시
- [ ] Bot Token 저장 여부/변경 여부 명확히 표시

### 11.2 텔레그램 전송 기능

- [ ] 요약 완료 후 텔레그램 전송 step 연결
- [ ] 수동 “요약 텔레그램 전송” 버튼 추가 여부 결정
- [ ] 전송 실패 시 UI 표시
- [ ] `TELEGRAM_AUTO_DELETE` 동작을 웹 task에서도 적용

### 11.3 마감 임박 알림

- [ ] 웹에서 마감 임박 알림 수동 체크 API 추가 여부 결정
- [ ] 자동 모드 실행 시 마감 임박 알림 포함
- [ ] 이미 알림 보낸 항목 dedupe 상태 확인

### 11.4 검증

- [ ] 텔레그램 연결 테스트 성공 확인
- [ ] 잘못된 token/chat id 실패 확인
- [ ] 요약 파일 전송 확인
- [ ] 자동 삭제 옵션 확인

---

## 12. P2 — 작업 상태/Background Task 공통화

다운로드/STT/요약/자동모드는 모두 긴 작업이므로 공통 task 시스템이 필요합니다.

### 12.1 Task 모델

- [x] ~~task id 생성 방식 결정~~
- [ ] task 상태 enum 정의
  - queued
  - running
  - succeeded
  - failed
  - cancelled
- [ ] task step enum 정의
  - play
  - download
  - convert
  - stt
  - summary
  - telegram
- [x] ~~task progress 구조 정의~~
- [x] ~~task result 구조 정의~~
- [x] ~~task error 구조 정의~~

### 12.2 Task 저장소

- [x] ~~메모리 저장으로 충분한지 결정~~
- [ ] SQLite 저장 필요 여부 검토
- [ ] 서버 재시작 후 task 복원 여부 결정
- [ ] 오래된 task 정리 정책 추가

### 12.3 Task API

- [x] ~~`GET /api/tasks` 목록 API~~
- [x] ~~`GET /api/tasks/{task_id}` 상세 API~~
- [x] ~~`POST /api/tasks/{task_id}/cancel` 취소 API~~
- [ ] WebSocket/SSE 사용 여부 결정
  - 현재는 polling으로 시작 가능

### 12.4 검증

- [ ] 긴 작업 상태 polling 확인
- [ ] 실패 task 상태 확인
- [ ] 취소 task 상태 확인
- [ ] 여러 task 동시 실행 정책 확인

---

## 13. P2 — 프론트 구조 정리

현재 프론트는 단일 `index.html` + vanilla JS입니다. README의 React/TypeScript/Vite 설명과 불일치합니다.

### 13.1 방향 결정

- [ ] 현재 vanilla HTML 구조를 유지할지 결정
- [ ] React/TypeScript/Vite로 전환할지 결정
- [ ] README의 기술 스택 설명을 실제 구현에 맞게 수정

### 13.2 vanilla 유지 시

- [ ] JS를 모듈별 파일로 분리
  - api.js
  - auth.js
  - player.js
  - courses.js
  - settings.js
  - tasks.js
- [ ] 공통 렌더링 유틸 추가
- [x] ~~escape/sanitize 유틸 추가~~
- [ ] 상태 관리 최소 규칙 정리

### 13.3 React 전환 시

- [ ] Vite 프로젝트 scaffold
- [ ] API client 작성
- [ ] 페이지/컴포넌트 분리
- [ ] Tailwind 빌드 체인 구성
- [ ] nginx build output 서빙으로 Dockerfile 변경

### 13.4 검증

- [ ] Docker Compose에서 frontend 정상 서빙 확인
- [ ] API proxy 정상 확인
- [ ] 브라우저 console error 없음 확인

---

## 14. P2 — 문서/README 정합성 정리

### 14.1 README 현재 구현 반영

- [ ] 현재 프론트가 React/Vite가 아니라 단일 정적 HTML임을 반영하거나 실제 React로 전환
- [ ] 자동 모드가 웹 미구현임을 명시하거나 구현 후 유지
- [ ] 다운로드/STT/요약이 웹 미구현임을 명시하거나 구현 후 유지
- [ ] 마크다운 저장/렌더링 실제 포맷과 일치하도록 수정
- [ ] 프로젝트 구조 예시를 실제 구조에 맞게 수정

### 14.2 개발 문서 추가

- [ ] 웹 API 명세 문서 추가
- [ ] task pipeline 설계 문서 추가
- [ ] LMS 재생 전략 문서와 웹 route 연결 방식 정리
- [ ] 보안 주의사항 업데이트

---

## 15. P3 — 운영/다중 사용자/확장성 검토

현재 구조는 개인 단일 사용자 서비스에 가깝습니다.

### 15.1 전역 singleton 상태 한계 정리

- [ ] `backend/api/state.py`의 `app_state` 단일 세션 구조 문서화
- [ ] uvicorn workers > 1 사용 금지 또는 상태 공유 구조 도입
- [ ] 여러 브라우저/사용자 동시 로그인 정책 결정
- [ ] 로그인 세션 충돌 처리

### 15.2 서버 재시작 처리

- [ ] 서버 재시작 시 Playwright 세션 복구 여부 결정
- [x] 저장된 credential로 자동 로그인하지 않도록 결정 — LMS 계정은 DB에서 자동 로드하지 않고 현재 세션 메모리에만 유지
- [ ] 자동 모드 실행 중 재시작 시 상태 처리

### 15.3 Docker/배포

- [ ] 프로덕션 `--reload` 제거
- [ ] worker 수 정책 결정
- [ ] persistent volume 정책 정리
- [ ] `.secret_key`, `data`, `logs` mount 정책 문서화

---

## 16. 코드 품질/CI 체크리스트

2026-04-14 기준 `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .`는 통과합니다. 이후 변경 시 계속 유지합니다.

### 16.1 Ruff 정리

- [x] ~~backend import sorting 수정~~
- [x] ~~`backend/api/routes/auth.py`의 `raise HTTPException(...)`에 `from None` 또는 `from e` 추가~~
- [x] ~~`backend/api/routes/settings.py`의 `Optional[str]`를 `str | None`로 변경~~
- [x] ~~`backend/api/state.py`의 `Optional[...]`를 `... | None`로 변경~~
- [x] ~~`tests/test_config.py` unused `tempfile` 제거~~
- [x] ~~`uv run ruff check .` 통과~~
  - 2026-04-14: `All checks passed!`
- [x] ~~`uv run ruff format --check .` 통과~~
  - 2026-04-14: `65 files already formatted`

### 16.2 테스트 보강

- [ ] FastAPI smoke test 추가
- [x] ~~DB 행위 로그 저장/마스킹/조회 테스트 추가~~
- [ ] 인증 없는 settings 접근 차단 테스트 추가
- [x] ~~`/api/courses/stats` 제출 필요 통계 테스트 추가~~
- [x] ~~player status error 표시 테스트 추가~~
- [x] ~~settings 민감값 미노출/다운로드 경로 무시 정책 테스트 추가~~
- [x] ~~task API 도입 시 task 상태 전이 테스트 추가~~

---

## 17. 완료 정의

웹서비스가 README의 설명과 일치한다고 보기 위한 최소 완료 조건입니다.

- [x] ~~로그인 후 대시보드에서 실제 강의 통계가 자동 표시된다.~~
- [x] ~~과목/주차/강의 목록을 웹에서 탐색할 수 있다.~~
- [x] ~~웹에서 강의를 재생할 수 있고 성공/실패/중지 상태가 명확히 표시된다.~~
- [x] ~~재생 완료 후 미수강/완료 상태와 통계가 갱신된다.~~
- [x] ~~웹에서 강의 다운로드를 실행하고 진행률을 볼 수 있다.~~
- [ ] 웹에서 STT 변환을 실행하거나 파이프라인으로 자동 실행된다.
- [ ] 웹에서 AI 요약을 실행하거나 파이프라인으로 자동 실행된다.
- [x] ~~생성된 요약을 웹에서 과목/주차별로 열람할 수 있다.~~
- [x] ~~자동 모드를 웹에서 켜고 끌 수 있다.~~
- [x] ~~자동 모드의 현재 강의와 다음 스케줄을 웹에서 볼 수 있다.~~
- [ ] 텔레그램 설정/테스트/요약 전송이 웹 흐름과 연결된다.
- [x] ~~Settings API 등 관리 API가 인증 없이 변경되지 않는다.~~
- [x] ~~프론트가 외부 문자열을 안전하게 렌더링한다.~~
- [x] ~~`uv run pytest`가 통과한다.~~
- [x] ~~`uv run ruff check .`가 통과한다.~~
- [ ] README가 실제 구현과 일치한다.
