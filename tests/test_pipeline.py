"""파이프라인 보조 로직 + 오프라인(--no-claude) 실행 테스트."""
import json

from src.pipeline import _load_boosting_words, run


def test_load_boosting_words_pulls_glossary_values():
    words = _load_boosting_words()
    assert "BLUM" in words          # brands_materials 의 결과값
    assert "식기세척기" in words      # fixtures 의 결과값
    # 1글자나 메타는 들어오지 않는다
    assert all(len(w) >= 2 for w in words)


def test_run_offline_from_transcript_no_claude(tmp_path):
    """STT·Claude 없이 전사본 → 사전 치환 교정본까지 생성되는지."""
    raw = tmp_path / "raw.json"
    raw.write_text(json.dumps({
        "engine": "clova", "audio_filename": "t.m4a", "full_text": "",
        "segments": [{"speaker": "1", "start_ms": 0, "end_ms": 1000, "text": "블룸 경첩"}],
    }, ensure_ascii=False), encoding="utf-8")

    result = run(transcript_path=str(raw), use_claude=False)

    assert set(result) == {"raw_json", "clean_txt"}
    clean = open(result["clean_txt"], encoding="utf-8").read()
    assert "BLUM" in clean


def test_run_requires_audio_or_transcript():
    try:
        run()
    except ValueError as e:
        assert "audio_path" in str(e) or "transcript_path" in str(e)
    else:
        raise AssertionError("audio/transcript 둘 다 없으면 ValueError 가 나야 한다")
