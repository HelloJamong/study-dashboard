# Gemini API 키 발급 가이드

AI 요약 기능을 사용하려면 Google Gemini API 키가 필요합니다.

---

## 1. Google AI Studio 접속

[https://aistudio.google.com](https://aistudio.google.com) 에 접속합니다.

Google 계정으로 로그인합니다.

---

## 2. API 키 생성

1. 좌측 사이드바에서 **"Get API key"** 를 클릭합니다.
2. **"Create API key"** 버튼을 클릭합니다.
3. 새 프로젝트를 생성하거나 기존 Google Cloud 프로젝트를 선택합니다.
4. 생성된 API 키를 복사합니다.

> API 키는 생성 직후에만 전체 값을 확인할 수 있습니다. 반드시 안전한 곳에 저장해두세요.

---

## 3. study-helper에 API 키 등록

실행 후 과목 목록 화면에서 `setting`을 입력해 설정 화면으로 이동합니다.

```
과목 선택 (0: 종료 / setting: 설정): setting
```

설정 화면에서 **AI 요약 설정** 항목을 선택한 뒤 발급받은 API 키를 입력합니다.

또는 `.env` 파일을 직접 수정할 수 있습니다:

```env
AI_ENABLED=true
AI_AGENT=gemini
GOOGLE_API_KEY=AIzaSy...
GEMINI_MODEL=gemini-2.5-flash
```

---

## 무료 사용량

Gemini API는 무료 티어를 제공합니다. 개인 학습 용도에서는 무료 한도 내에서 충분히 사용할 수 있습니다.

최신 요금 및 한도는 [https://ai.google.dev/pricing](https://ai.google.dev/pricing) 에서 확인하세요.
