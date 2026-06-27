"""STT 엔진 선택 팩토리.

환경변수 STT_ENGINE (clova | whisper) 또는 인자로 엔진을 고른다.
"""
from __future__ import annotations

import os

from .base import STTEngine, Transcript, Segment


def get_engine(name: str | None = None, **kwargs) -> STTEngine:
    name = (name or os.environ.get("STT_ENGINE", "clova")).lower()
    if name == "clova":
        from .clova import ClovaSpeechEngine
        return ClovaSpeechEngine(**kwargs)
    if name == "whisper":
        from .whisper import WhisperEngine
        return WhisperEngine(**kwargs)
    raise ValueError(f"알 수 없는 STT 엔진: {name} (clova 또는 whisper)")


__all__ = ["get_engine", "STTEngine", "Transcript", "Segment"]
