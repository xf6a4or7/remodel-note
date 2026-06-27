# Render 배포 가이드 (비개발자용 · 신용카드 불필요)

Render에 remodel-note 웹 페이지를 올려서, 폰/PC에서 링크만 열면 녹취를 올리고
회의록을 받는 상태를 만듭니다. **신용카드 없이** GitHub 로그인으로 가입됩니다.

> 끝나면: `https://remodel-note.onrender.com` 같은 주소를 열어 → 녹취 업로드 → 회의록 다운로드.

장점: 가입에 카드 불필요 · 무료 · **HTTPS(암호화) 자동** · 우리 GitHub 레포에서 바로 배포.
단점 하나: 아무도 안 쓰면 15분 뒤 잠들고, 다음 접속 때 깨어나는 데 약 1분 걸립니다(가끔 쓰는 용도엔 무방).

소요 시간: 약 10~15분.

---

## 0. 미리 준비할 것 (키 3개)

| 항목 | 값 |
|------|------|
| `CLOVA_SPEECH_INVOKE_URL`, `CLOVA_SPEECH_SECRET` | 네이버 클라우드 CLOVA Speech 도메인에서 발급 |
| `ANTHROPIC_API_KEY` | console.anthropic.com → API Keys |
| `APP_PASSWORD` | **직접 정하는 접속 비밀번호** (예: `hyunjang2026`) |

---

## 1. Render 가입

1. https://render.com → **Get Started** → **GitHub로 로그인** (카드 입력 없음)
2. Render가 GitHub 접근 권한을 물어보면 허용. (레포 `xf6a4or7/remodel-note` 접근 허용)

---

## 2. 배포하기 (Blueprint 방식 — 가장 간단)

1. Render 대시보드 → **New +** → **Blueprint**
2. 레포 목록에서 **`xf6a4or7/remodel-note`** 선택 → **Connect**
3. Render가 레포의 `render.yaml`을 자동으로 읽어 서비스를 구성합니다 → **Apply**

> Blueprint가 안 보이면: **New +** → **Web Service** → 같은 레포 선택 →
> "Language(런타임)"이 **Docker**로 잡히는지 확인 → 무료 플랜(Free) 선택.

---

## 3. 키 입력 (환경변수)

배포를 누르면 Render가 값이 비어있는 환경변수 입력을 요청합니다.
아래 4개를 채우세요 (STT_ENGINE은 이미 `clova`로 채워져 있음):

| 변수 | 넣을 값 |
|------|---------|
| `APP_PASSWORD` | 직접 정한 접속 비밀번호 |
| `CLOVA_SPEECH_INVOKE_URL` | CLOVA Invoke URL |
| `CLOVA_SPEECH_SECRET` | CLOVA Secret |
| `ANTHROPIC_API_KEY` | 클로드 API 키 |

저장하면 자동으로 빌드·배포가 시작됩니다 (처음 몇 분 걸림).

---

## 4. 완료 — 사용하기

배포가 끝나면 화면 상단에 주소가 나옵니다 (예: `https://remodel-note.onrender.com`).

1. 브라우저(폰/PC)에서 그 주소를 엽니다.
2. 로그인 창이 뜨면 — 아이디는 아무거나, 비밀번호는 `APP_PASSWORD`.
3. 녹취 파일 업로드 → 처리 화면에서 기다리면 → 회의록/요약/요구사항 다운로드.

> 처음 접속이나 한참 안 쓴 뒤 접속하면 **깨어나는 데 ~1분** 걸립니다. 잠깐 기다리면 됩니다.
> 업로드 후 처리 중에는 그 화면을 닫지 말고 켜두세요(자동으로 완료를 기다립니다).

---

## 업데이트 (코드가 바뀌었을 때)

Render는 GitHub `main` 브랜치에 새 커밋이 올라오면 **자동으로 다시 배포**합니다.
별도 작업이 필요 없어요. (수동으로 하려면 Render 대시보드 → **Manual Deploy**.)

키를 바꾸려면: Render 대시보드 → 서비스 → **Environment** → 값 수정 → 저장(자동 재배포).

---

## 키 변경·로그 보기

- **로그**: 대시보드 → 서비스 → **Logs** (오류가 나면 여기서 원인 확인)
- **재시작**: 대시보드 → **Manual Deploy** → Deploy latest commit

---

## 보안 참고

- 주소(URL)는 HTTPS로 암호화됩니다. 접속은 `APP_PASSWORD`로 잠겨 있습니다.
- 비밀번호는 충분히 길고 추측 어렵게 정하세요. 링크와 비번이 새면 누구나 접속할 수 있습니다.
- 고객 녹취는 처리 후 서버의 임시 공간에 잠시 남았다가 재시작 시 사라집니다(영구 저장 안 함).
