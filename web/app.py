"""remodel-note 웹 업로드 서버.

브라우저(폰/PC)에서 녹취 파일을 올리면 백그라운드로 파이프라인을 돌려
회의록(.docx)·요구사항(.json)·요약(.md)을 만들어 다운로드하게 한다.

- 긴 녹취도 끊기지 않도록: 업로드 즉시 작업 페이지로 보내고, 처리는 백그라운드에서.
- 인터넷에 공개되므로 APP_PASSWORD 가 설정되면 Basic 인증으로 잠근다.
- 작업 상태는 output/jobs/{id}.json 파일에 저장 (재시작·다중 워커에도 안전).

실행:
  pip install -r requirements-web.txt
  APP_PASSWORD=원하는비번 gunicorn -w 1 -b 0.0.0.0:8000 web.app:app
"""
from __future__ import annotations

import json
import os
import uuid
from concurrent.futures import ThreadPoolExecutor

from flask import (Flask, Response, abort, redirect, render_template_string,
                   request, send_file, url_for)

from dotenv import load_dotenv

load_dotenv()

from src.pipeline import run  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AUDIO_DIR = os.path.join(ROOT, "audio")
JOBS_DIR = os.path.join(ROOT, "output", "jobs")
os.makedirs(AUDIO_DIR, exist_ok=True)
os.makedirs(JOBS_DIR, exist_ok=True)

ALLOWED_EXT = {".m4a", ".mp3", ".mp4", ".wav", ".aac", ".flac", ".ogg"}
MAX_UPLOAD_MB = int(os.environ.get("MAX_UPLOAD_MB", "200"))
APP_PASSWORD = os.environ.get("APP_PASSWORD", "")

# 한 번에 하나씩 처리 (API 과호출·메모리 폭주 방지)
_executor = ThreadPoolExecutor(max_workers=1)

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_MB * 1024 * 1024

# 다운로드 가능한 산출물: 작업 결과 키 -> 사용자에게 보일 파일 이름
# (클로드 키가 없으면 회의록/요약/요구사항은 안 생기고 교정본·전사본만 생긴다)
DOWNLOADABLE = {
    "minutes_docx": "회의록.docx",
    "summary_md": "요약.md",
    "requirements_json": "요구사항.json",
    "clean_txt": "교정본.txt",
    "raw_json": "전사본.json",
}


# ---------- 인증 ----------
@app.before_request
def _require_password():
    if request.path == "/healthz":
        return  # 상태 점검(호스팅 헬스체크)은 인증 없이 통과
    if not APP_PASSWORD:
        return  # 비번 미설정이면 잠그지 않음 (로컬 테스트용)
    auth = request.authorization
    if not auth or auth.password != APP_PASSWORD:
        return Response("로그인이 필요합니다.", 401,
                        {"WWW-Authenticate": 'Basic realm="remodel-note"'})


@app.get("/healthz")
def healthz():
    return "ok", 200


# ---------- 작업 상태 파일 ----------
def _job_path(job_id: str) -> str:
    return os.path.join(JOBS_DIR, f"{job_id}.json")


def _write_status(job_id: str, data: dict):
    with open(_job_path(job_id), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _read_status(job_id: str) -> dict | None:
    path = _job_path(job_id)
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _process(job_id: str, audio_path: str, original_name: str):
    # 클로드 키가 있으면 전체(분석·회의록), 없으면 받아쓰기+용어 교정까지만.
    use_claude = bool(os.environ.get("ANTHROPIC_API_KEY"))
    message = ("STT → 교정 → 분석 → 회의록 생성 중..." if use_claude
               else "STT → 용어 교정 중... (클로드 키 없음: 교정본까지만)")
    _write_status(job_id, {"status": "processing", "filename": original_name,
                           "message": message})
    try:
        result = run(audio_path, use_claude=use_claude)
        _write_status(job_id, {"status": "done", "filename": original_name,
                               "outputs": result})
    except Exception as e:  # noqa: BLE001 - 무엇이 터지든 사용자에게 메시지로 보여준다
        _write_status(job_id, {"status": "error", "filename": original_name,
                               "error": str(e)})


# ---------- 라우트 ----------
@app.get("/")
def index():
    return render_template_string(INDEX_HTML)


@app.post("/upload")
def upload():
    file = request.files.get("audio")
    if not file or not file.filename:
        return render_template_string(INDEX_HTML, error="파일을 선택해주세요."), 400

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXT:
        return render_template_string(
            INDEX_HTML,
            error=f"지원하지 않는 형식입니다 ({ext}). 음성 파일: {', '.join(sorted(ALLOWED_EXT))}"), 400

    job_id = uuid.uuid4().hex[:12]
    safe_name = os.path.basename(file.filename).replace("/", "_").replace("\\", "_")
    saved_path = os.path.join(AUDIO_DIR, f"{job_id}_{safe_name}")
    file.save(saved_path)

    _write_status(job_id, {"status": "queued", "filename": safe_name})
    _executor.submit(_process, job_id, saved_path, safe_name)
    return redirect(url_for("job", job_id=job_id))


@app.get("/job/<job_id>")
def job(job_id: str):
    status = _read_status(job_id)
    if status is None:
        abort(404)
    downloads = []
    if status.get("status") == "done":
        outputs = status.get("outputs", {})
        for key, label in DOWNLOADABLE.items():
            if key in outputs and os.path.exists(outputs[key]):
                downloads.append((key, label))
    return render_template_string(JOB_HTML, job_id=job_id, status=status, downloads=downloads)


@app.get("/download/<job_id>/<kind>")
def download(job_id: str, kind: str):
    status = _read_status(job_id)
    if status is None or kind not in DOWNLOADABLE:
        abort(404)
    path = status.get("outputs", {}).get(kind)
    if not path or not os.path.exists(path):
        abort(404)
    # 작업 결과로 등록된 경로만 내려준다 (임의 경로 접근 차단)
    return send_file(path, as_attachment=True, download_name=DOWNLOADABLE[kind])


INDEX_HTML = """<!doctype html>
<html lang="ko"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>remodel-note · 녹취 업로드</title>
<style>
  body{font-family:system-ui,"맑은 고딕",sans-serif;background:#f4f6fa;margin:0;color:#1f3a5f}
  .card{max-width:520px;margin:8vh auto;background:#fff;border-radius:16px;padding:32px;
        box-shadow:0 8px 30px rgba(31,58,95,.12)}
  h1{font-size:22px;margin:0 0 4px} p.sub{color:#5b6b82;margin:0 0 24px;font-size:14px}
  input[type=file]{width:100%;padding:14px;border:2px dashed #2e75b6;border-radius:12px;
        background:#f7faff;margin-bottom:16px;box-sizing:border-box}
  button{width:100%;padding:16px;font-size:17px;font-weight:700;color:#fff;background:#2e75b6;
        border:0;border-radius:12px;cursor:pointer}
  button:hover{background:#1f3a5f}
  .err{background:#fdecec;color:#c0392b;padding:12px;border-radius:10px;margin-bottom:16px;font-size:14px}
  .hint{color:#8190a5;font-size:13px;margin-top:18px;line-height:1.6}
</style></head><body>
<div class="card">
  <h1>🎙️ 녹취 업로드</h1>
  <p class="sub">인테리어 상담 녹취 → 회의록·요구사항 자동 생성</p>
  {% if error %}<div class="err">{{ error }}</div>{% endif %}
  <form method="post" action="/upload" enctype="multipart/form-data">
    <input type="file" name="audio" accept=".m4a,.mp3,.mp4,.wav,.aac,.flac,.ogg" required>
    <button type="submit">업로드하고 회의록 만들기</button>
  </form>
  <div class="hint">지원: m4a, mp3, wav 등 · 긴 녹취는 처리에 몇 분 걸릴 수 있어요.<br>
  업로드 후 처리 화면에서 자동으로 완료를 기다립니다.</div>
</div></body></html>"""


JOB_HTML = """<!doctype html>
<html lang="ko"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
{% if status.status in ['queued','processing'] %}<meta http-equiv="refresh" content="4">{% endif %}
<title>remodel-note · 처리 상태</title>
<style>
  body{font-family:system-ui,"맑은 고딕",sans-serif;background:#f4f6fa;margin:0;color:#1f3a5f}
  .card{max-width:520px;margin:8vh auto;background:#fff;border-radius:16px;padding:32px;
        box-shadow:0 8px 30px rgba(31,58,95,.12)}
  h1{font-size:20px;margin:0 0 18px}
  .file{color:#5b6b82;font-size:14px;margin-bottom:20px;word-break:break-all}
  .spin{display:inline-block;width:18px;height:18px;border:3px solid #cfe0f3;border-top-color:#2e75b6;
        border-radius:50%;animation:s .8s linear infinite;vertical-align:middle;margin-right:8px}
  @keyframes s{to{transform:rotate(360deg)}}
  .proc{background:#eaf2fb;padding:16px;border-radius:12px;font-size:15px}
  .err{background:#fdecec;color:#c0392b;padding:16px;border-radius:12px;font-size:14px;word-break:break-all}
  a.dl{display:block;text-align:center;padding:15px;margin:10px 0;background:#2e75b6;color:#fff;
       text-decoration:none;border-radius:12px;font-weight:700;font-size:16px}
  a.dl:hover{background:#1f3a5f}
  a.back{display:inline-block;margin-top:18px;color:#2e75b6;font-size:14px}
</style></head><body>
<div class="card">
  <h1>📄 처리 상태</h1>
  <div class="file">파일: {{ status.filename }}</div>
  {% if status.status in ['queued','processing'] %}
    <div class="proc"><span class="spin"></span>{{ status.message or '대기 중...' }}<br>
    <small style="color:#8190a5">이 화면은 자동으로 새로고침됩니다. 닫지 말고 기다려주세요.</small></div>
  {% elif status.status == 'done' %}
    <div class="proc" style="background:#e9f7ef;color:#1e7e4f">✅ 완료! 아래에서 받으세요.</div>
    {% for kind, label in downloads %}
      <a class="dl" href="/download/{{ job_id }}/{{ kind }}">⬇️ {{ label }}</a>
    {% endfor %}
  {% else %}
    <div class="err">⚠️ 처리 중 오류가 발생했습니다.<br>{{ status.error }}</div>
  {% endif %}
  <a class="back" href="/">← 새 녹취 올리기</a>
</div></body></html>"""
