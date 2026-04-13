# 로컬 HTTPS 실행 가이드

nginx 프론트 컨테이너는 HTTPS를 지원합니다.

- HTTP: `http://localhost:3000` → `https://localhost:3443`으로 리다이렉트
- HTTPS: `https://localhost:3443`
- Backend API는 nginx가 Docker 내부 네트워크에서 `http://backend:8000`으로 프록시합니다.
- Backend의 호스트 포트 `8000`은 개발/헬스체크용으로 `127.0.0.1`에만 바인딩됩니다.

## 1. 로컬 인증서 생성

저장소 루트에서 실행합니다.

```bash
./scripts/generate-local-cert.sh
```

생성 파일:

```text
certs/local.crt
certs/local.key
```

이 파일들은 로컬 비밀/인증서라 git에 커밋하지 않습니다.

## 2. Docker Compose 실행

```bash
docker compose up -d --build
```

접속:

```text
https://localhost:3443
```

기존 HTTP 주소로 접근하면 HTTPS로 이동합니다.

```text
http://localhost:3000 -> https://localhost:3443
```

## 3. 자체 서명 인증서 경고

기본 스크립트는 self-signed 인증서를 생성합니다. 브라우저는 최초 접속 시 경고를 표시합니다.

개인 로컬 테스트에서는 경고를 수락해도 됩니다. 경고 없이 사용하려면 `certs/local.crt`를 OS 또는 브라우저 trust store에 추가하세요.

## 4. 인증서 파일이 없을 때

`certs/local.crt`와 `certs/local.key`가 없으면 nginx가 시작하지 못합니다. 이 경우 먼저 인증서를 생성하세요.

```bash
./scripts/generate-local-cert.sh
```

## 5. 확인 명령

```bash
curl -k https://localhost:3443/api/health
```

정상 응답:

```json
{"status":"ok"}
```
