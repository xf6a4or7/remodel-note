# OCI 배포 가이드 (비개발자용)

오라클 클라우드(OCI)의 **무료 서버**에 remodel-note 웹 페이지를 올려서,
폰/PC에서 링크만 열면 녹취를 올리고 회의록을 받는 상태를 만듭니다.

> 끝나면: `http://<서버주소>:8000` 을 열어 → 녹취 업로드 → 회의록 다운로드.

비용 정리: **서버는 무료**(OCI Always Free). 실제 돈은 녹취를 처리할 때 쓰는
**CLOVA Speech + Claude API 사용료**만 나갑니다 (쓴 만큼).

소요 시간: 처음 한 번 약 30~40분. 그다음부터는 그냥 쓰기만 하면 됩니다.

---

## 0. 미리 준비할 것 (키 3개)

`.env` 파일에 넣을 값들입니다. 미리 발급받아 메모해두세요.

| 항목 | 어디서 |
|------|--------|
| `CLOVA_SPEECH_INVOKE_URL`, `CLOVA_SPEECH_SECRET` | 네이버 클라우드 콘솔 → CLOVA Speech 도메인 생성 |
| `ANTHROPIC_API_KEY` | console.anthropic.com → API Keys |
| `APP_PASSWORD` | **직접 정하는 접속 비밀번호** (아무나 못 쓰게 잠그는 용도) |

---

## 1. OCI 계정 만들기

1. https://www.oracle.com/cloud/free/ → **Start for free**
2. 이메일·휴대폰 인증, 카드 등록(무료 등급은 과금 안 됨, 본인확인용), 지역은 **춘천(South Korea Central)** 권장.
3. 가입 완료 후 콘솔(https://cloud.oracle.com) 로그인.

---

## 2. 무료 서버(VM) 만들기

1. 콘솔 메뉴 → **Compute → Instances → Create instance**
2. 설정:
   - **Image**: Canonical Ubuntu 22.04
   - **Shape**: `VM.Standard.A1.Flex` (ARM, Always Free) — 1 OCPU / 6GB 면 충분
     - 안 보이면 `VM.Standard.E2.1.Micro` (AMD, Always Free) 선택
   - **SSH keys**: "Generate a key pair for me" → **private key 다운로드**(`ssh-key.key`) 꼭 저장
3. **Create** → 잠시 후 인스턴스의 **Public IP address** 를 메모.

---

## 3. 방화벽 열기 (8000 포트)

OCI는 기본적으로 포트가 막혀 있습니다. 두 군데를 엽니다.

**(A) 보안 목록(Security List)**
1. 인스턴스 화면 → **Virtual cloud network** 클릭 → **Security Lists** → 기본 목록
2. **Add Ingress Rules**:
   - Source CIDR: `0.0.0.0/0`
   - IP Protocol: TCP, Destination Port: `8000`
   - Add.

**(B) 서버 내부 방화벽** — 4단계에서 접속한 뒤 아래 명령 한 줄:
```bash
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 8000 -j ACCEPT && sudo netfilter-persistent save
```

---

## 4. 서버 접속

다운로드한 키로 SSH 접속 (Mac/Linux 터미널 또는 Windows PowerShell):
```bash
chmod 400 ssh-key.key
ssh -i ssh-key.key ubuntu@<서버 Public IP>
```

---

## 5. 코드 받고 실행 (Docker 사용 — 가장 간단)

서버 안에서 차례로 실행합니다.

```bash
# Docker 설치
sudo apt-get update && sudo apt-get install -y docker.io git
sudo systemctl enable --now docker

# 코드 받기
git clone https://github.com/xf6a4or7/remodel-note.git
cd remodel-note

# 키 입력: .env 파일 만들기
cp .env.example .env
nano .env     # 값 채우고 저장(Ctrl+O, Enter, Ctrl+X)
```

`.env` 에 `APP_PASSWORD=원하는비밀번호` 줄도 추가하세요 (예: `APP_PASSWORD=hyunjang2026`).

```bash
# 이미지 빌드 & 실행
sudo docker build -t remodel-note .
sudo docker run -d --name remodel --restart always \
  --env-file .env -p 8000:8000 remodel-note
```

---

## 6. 완료 — 사용하기

브라우저(폰/PC)에서:
```
http://<서버 Public IP>:8000
```
- 접속하면 비밀번호를 물어봅니다 (아이디는 아무거나, 비번은 `APP_PASSWORD`).
- 녹취 파일 업로드 → 처리 화면에서 기다리면 → 회의록/요약/요구사항 다운로드.

서버는 `--restart always` 라서 재부팅돼도 자동으로 다시 켜집니다.

---

## 업데이트 (코드가 바뀌었을 때)

```bash
cd remodel-note && git pull
sudo docker build -t remodel-note .
sudo docker rm -f remodel
sudo docker run -d --name remodel --restart always --env-file .env -p 8000:8000 remodel-note
```

상태/로그 확인:
```bash
sudo docker logs -f remodel
```

---

## 보안 참고 (꼭 읽어주세요)

- 지금 구성은 **HTTP**(암호화 없음) + 비밀번호 잠금입니다. 링크와 비번이 새면 누구나 접속할 수 있어요.
- 고객 녹취는 민감 정보이므로, 본격 운영 시 **도메인 + HTTPS**(예: Caddy 자동 인증서)를 얹는 걸 권장합니다. 필요하면 이 부분도 도와드릴 수 있어요.
- `APP_PASSWORD` 는 충분히 길게, 추측 어렵게 설정하세요.
