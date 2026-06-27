"""analyze() 의 JSON 파싱 테스트 — Anthropic 호출은 목으로 대체."""
from unittest.mock import patch, MagicMock

import src.analyze as analyze_mod


def _mock_anthropic(return_text):
    """messages.create 가 주어진 텍스트를 담은 응답을 돌려주도록 하는 가짜 클라이언트."""
    block = MagicMock()
    block.type = "text"
    block.text = return_text
    msg = MagicMock()
    msg.content = [block]
    client = MagicMock()
    client.messages.create.return_value = msg
    return client


def test_analyze_parses_plain_json(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test")
    payload = '{"meeting_overview": {"title": "상담"}, "decisions": []}'
    with patch.object(analyze_mod, "Anthropic", return_value=_mock_anthropic(payload)):
        result = analyze_mod.analyze("녹취 내용")
    assert result["meeting_overview"]["title"] == "상담"


def test_analyze_strips_markdown_code_fence(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test")
    fenced = '```json\n{"meeting_overview": {"title": "코드펜스"}}\n```'
    with patch.object(analyze_mod, "Anthropic", return_value=_mock_anthropic(fenced)):
        result = analyze_mod.analyze("녹취 내용")
    assert result["meeting_overview"]["title"] == "코드펜스"
