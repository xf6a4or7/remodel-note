"""Transcript 직렬화 / 역직렬화 라운드트립 테스트 (--transcript 재실행의 기반)."""
from src.stt.base import Transcript, Segment


def test_to_json_from_json_roundtrip():
    original = Transcript(
        engine="clova", audio_filename="녹취.m4a", full_text="전체 텍스트",
        segments=[
            Segment(speaker="1", start_ms=0, end_ms=8000, text="안녕하세요"),
            Segment(speaker="2", start_ms=8000, end_ms=20000, text="네 반갑습니다"),
        ],
    )
    restored = Transcript.from_json(original.to_json())
    assert restored.engine == original.engine
    assert restored.audio_filename == original.audio_filename
    assert len(restored.segments) == 2
    assert restored.segments[1].text == "네 반갑습니다"
    assert restored.segments[1].start_ms == 8000


def test_to_readable_formats_speaker_and_timestamp():
    t = Transcript(
        engine="clova", audio_filename="x", full_text="",
        segments=[Segment(speaker="1", start_ms=65000, end_ms=70000, text="테스트")],
    )
    assert t.to_readable() == "[01:05] 화자1: 테스트"
