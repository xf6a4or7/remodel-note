FROM python:3.11-slim

WORKDIR /app

# 의존성 먼저 설치 (캐시 활용)
COPY requirements.txt requirements-web.txt ./
RUN pip install --no-cache-dir -r requirements-web.txt

# 코드 복사
COPY . .

# 산출물/업로드 디렉터리 (이미지에 없을 수 있으니 보장)
RUN mkdir -p audio transcripts/raw transcripts/clean output/jobs

EXPOSE 8000

# 긴 녹취 처리는 백그라운드 스레드에서 도므로 워커 1개로 충분.
# 작업 상태는 파일에 저장되어 재시작에도 안전.
# PORT 환경변수가 있으면 그 포트에 바인딩(Render 등), 없으면 8000(로컬/OCI).
CMD ["sh", "-c", "exec gunicorn -w 1 -b 0.0.0.0:${PORT:-8000} --timeout 120 web.app:app"]
