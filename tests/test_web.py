"""웹 업로드 서버 라우트 테스트 — 파이프라인은 목으로 대체 (API·네트워크 미사용)."""
import io

import pytest

from web import app as webapp


@pytest.fixture
def client(tmp_path, monkeypatch):
    # 백그라운드 실행을 동기로 바꿔 테스트에서 바로 결과 확인
    monkeypatch.setattr(webapp._executor, "submit", lambda fn, *a, **k: fn(*a, **k))
    monkeypatch.setattr(webapp, "APP_PASSWORD", "")  # 테스트는 잠금 해제

    def fake_run(audio_path, use_claude=True):
        docx = tmp_path / "회의록.docx"
        docx.write_text("dummy", encoding="utf-8")
        return {"minutes_docx": str(docx)}

    monkeypatch.setattr(webapp, "run", fake_run)
    return webapp.app.test_client()


def test_upload_then_done_and_download(client):
    data = {"audio": (io.BytesIO(b"fake audio bytes"), "녹취.m4a")}
    r = client.post("/upload", data=data, content_type="multipart/form-data")
    assert r.status_code == 302  # 작업 페이지로 리다이렉트

    job_url = r.headers["Location"]
    page = client.get(job_url).get_data(as_text=True)
    assert "완료" in page

    job_id = job_url.rsplit("/", 1)[1]
    dl = client.get(f"/download/{job_id}/minutes_docx")
    assert dl.status_code == 200
    assert dl.headers["Content-Disposition"].count("회의록.docx") or \
           "attachment" in dl.headers["Content-Disposition"]


def test_rejects_unsupported_extension(client):
    data = {"audio": (io.BytesIO(b"x"), "메모.txt")}
    r = client.post("/upload", data=data, content_type="multipart/form-data")
    assert r.status_code == 400
    assert "지원하지 않는" in r.get_data(as_text=True)


def test_claude_used_only_when_key_present(tmp_path, monkeypatch):
    monkeypatch.setattr(webapp._executor, "submit", lambda fn, *a, **k: fn(*a, **k))
    monkeypatch.setattr(webapp, "APP_PASSWORD", "")
    seen = {}

    def rec(audio_path, use_claude=True):
        seen["use_claude"] = use_claude
        p = tmp_path / "clean.txt"
        p.write_text("교정본", encoding="utf-8")
        return {"clean_txt": str(p)}

    monkeypatch.setattr(webapp, "run", rec)
    c = webapp.app.test_client()

    # 키 없음 → 교정본까지만 (use_claude=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    c.post("/upload", data={"audio": (io.BytesIO(b"x"), "a.m4a")},
           content_type="multipart/form-data")
    assert seen["use_claude"] is False

    # 키 있음 → 전체 파이프라인 (use_claude=True)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    c.post("/upload", data={"audio": (io.BytesIO(b"x"), "b.m4a")},
           content_type="multipart/form-data")
    assert seen["use_claude"] is True


def test_password_protects_routes(monkeypatch):
    monkeypatch.setattr(webapp, "APP_PASSWORD", "secret")
    c = webapp.app.test_client()
    assert c.get("/").status_code == 401
    ok = c.get("/", headers={"Authorization": "Basic " + _basic("any", "secret")})
    assert ok.status_code == 200


def _basic(user, pw):
    import base64
    return base64.b64encode(f"{user}:{pw}".encode()).decode()
