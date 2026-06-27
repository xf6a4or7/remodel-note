# remodel-note

인테리어 상담·통화 녹취를 업로드하면 **STT → 용어 교정 → 구조화 분석 → 회의록/요구사항 문서**까지 자동으로 만들어주는 파이프라인.

## 흐름

```
audio/ (음성)
  → STT (CLOVA Speech / Whisper 교체 가능)
  → 용어 사전 치환 + Claude 문맥 교정
  → Claude 구조화 분석 (공간별·자재별 요구사항 태깅)
  → output/
       ├─ *_회의록.docx     (개요·결정·미결·요청·액션·견적)
       ├─ *_요구사항.json
       └─ *_요약.md
```

## 설치

```bash
pip install -r requirements.txt
cp .env.example .env   # 그리고 .env 에 키 입력
```

## 환경변수(.env)

| 변수 | 설명 |
|------|------|
| `CLOVA_SPEECH_INVOKE_URL` | NCP CLOVA Speech 도메인의 Invoke URL |
| `CLOVA_SPEECH_SECRET` | CLOVA Speech Secret Key |
| `ANTHROPIC_API_KEY` | Claude API 키 (교정·분석용) |
| `STT_ENGINE` | `clova`(기본) 또는 `whisper` |

> NCP 콘솔에서 CLOVA Speech 도메인을 만들면 Invoke URL과 Secret이 발급됩니다.
> 로컬 파일 업로드 방식(`/recognizer/upload`)을 쓰므로 Object Storage 없이도 동작합니다.

## 사용

```bash
python cli.py audio/녹취.m4a                    # 전체: STT → 교정 → 분석 → 회의록/요구사항
python cli.py audio/녹취.m4a --no-claude        # STT + 사전 치환만 (교정본까지, Claude 미사용)
python cli.py audio/녹취.m4a --engine whisper   # STT 엔진 교체

# STT 결과(transcripts/raw/*.json)를 그대로 두고 교정·분석만 다시 돌리기
# (CLOVA 재호출 없이 프롬프트/사전만 바꿔 반복 실험할 때 유용)
python cli.py --transcript transcripts/raw/녹취_20260627_120000.json
```

| 옵션 | 동작 | 필요한 키 |
|------|------|-----------|
| (기본) | STT→교정→분석→문서 전체 | CLOVA + Anthropic |
| `--no-claude` | 교정본(`transcripts/clean/*.txt`)까지만 | CLOVA (또는 `--transcript`면 없음) |
| `--transcript X.json` | STT 건너뛰고 저장된 전사본으로 재실행 | Anthropic (`--no-claude`면 없음) |
| `--engine whisper` | STT 엔진을 Whisper로 | OpenAI |

### 빠른 체험 (API 키 없이)

샘플 전사본으로 사전 치환 동작을 바로 확인할 수 있습니다.

```bash
python cli.py --transcript examples/sample_transcript.json --no-claude
cat transcripts/clean/sample_transcript_*.txt   # 블룸→BLUM, 아이소핑크→이소핑크 등 치환 확인
```

## 개발 / 테스트

```bash
pip install -r requirements-dev.txt
pytest                       # 사전 치환·전사본 직렬화·docx 생성·분석 파싱 검증 (API 미사용)
```

## 웹으로 쓰기 (서버 배포)

터미널 없이 브라우저(폰/PC)에서 녹취를 올리고 회의록을 받는 웹 페이지가 있습니다.

```bash
pip install -r requirements-web.txt
APP_PASSWORD=원하는비번 gunicorn -w 1 -b 0.0.0.0:8000 web.app:app
# 브라우저에서 http://<서버주소>:8000 접속 → 업로드 → 다운로드
```

- 업로드 즉시 처리 화면으로 이동하고, 긴 녹취도 백그라운드로 처리됩니다.
- `APP_PASSWORD` 를 설정하면 접속 시 비밀번호로 잠깁니다(인터넷 공개 시 필수).
- Docker로도 실행 가능(`Dockerfile` 포함).
- 오라클 클라우드(OCI) **무료 서버**에 올리는 단계별 안내: **[docs/DEPLOY_OCI.md](docs/DEPLOY_OCI.md)**

## 용어 사전

`config/glossary.json` 에 현장 용어 오인식 교정 규칙이 있습니다.
새 오인식을 발견하면 `"잘못된표현": "올바른표현"` 형태로 계속 추가하세요.
이 단어들은 CLOVA Speech 부스팅 키워드로도 자동 활용되어 인식률을 높입니다.

## 구조

```
remodel-note/
├─ cli.py                 진입점
├─ CLAUDE.md              개발 지침 (코드 작업 시 준수)
├─ config/glossary.json   용어 교정 사전
├─ src/
│  ├─ stt/                STT 엔진 (base/clova/whisper, 교체 가능)
│  ├─ postprocess.py      용어 치환 + Claude 교정
│  ├─ analyze.py          구조화 분석
│  ├─ docgen.py           회의록 docx 생성
│  └─ pipeline.py         전체 오케스트레이션
├─ web/app.py             웹 업로드 서버 (Flask)
├─ Dockerfile             컨테이너 배포용
├─ docs/DEPLOY_OCI.md     OCI 무료 서버 배포 가이드
├─ examples/              샘플 전사본 (오프라인 체험용)
├─ tests/                 pytest (API 미사용)
├─ audio/                 입력 음성 (git 제외)
├─ transcripts/           중간 산출물 (git 제외)
└─ output/                최종 산출물 (git 제외)
```

## 개인정보 주의

`audio/`, `transcripts/`, `output/`, `.env` 는 `.gitignore` 로 깃에서 제외됩니다.
**고객 녹취·전사본·회의록은 절대 커밋되지 않습니다.** 코드만 버전관리됩니다.
