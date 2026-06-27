"""용어 사전 치환 로직 테스트 (Claude 미사용 경로)."""
import os

from src.postprocess import load_glossary, apply_glossary, postprocess
from src.stt.base import Transcript, Segment

GLOSSARY = os.path.join(os.path.dirname(__file__), "..", "config", "glossary.json")


def test_load_glossary_flattens_categories_and_skips_meta():
    flat = load_glossary(GLOSSARY)
    assert flat["블룸"] == "BLUM"
    assert flat["식기 세척기"] == "식기세척기"
    # "_speaker_hints", "_comment" 같은 메타 키는 제외된다
    assert not any(k.startswith("_") for k in flat)


def test_apply_glossary_replaces_known_terms():
    flat = load_glossary(GLOSSARY)
    out = apply_glossary("상부장은 블룸 경첩, 아이소핑크 단열", flat)
    assert "BLUM" in out
    assert "이소핑크" in out
    assert "블룸" not in out


def test_apply_glossary_longest_key_first():
    """긴 키('레그라 박스')가 짧은 키보다 먼저 치환되어 부분 겹침이 안 생긴다."""
    g = {"레그라 박스": "레그라박스", "박스": "BOX"}
    assert apply_glossary("레그라 박스 주세요", g) == "레그라박스 주세요"


def test_postprocess_without_claude_applies_dictionary_only():
    t = Transcript(
        engine="clova", audio_filename="x.m4a", full_text="",
        segments=[Segment(speaker="1", start_ms=0, end_ms=1000, text="블룸 경첩")],
    )
    out = postprocess(t, GLOSSARY, use_claude=False)
    assert "BLUM" in out
    assert "블룸" not in out
