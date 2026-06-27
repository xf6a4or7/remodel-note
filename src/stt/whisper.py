"""OpenAI Whisper STT 구현 (교체용).

CLOVA Speech 대신 쓰고 싶을 때를 위한 자리. Whisper API 자체는 화자분리를 주지
않으므로, segments의 speaker는 모두 "1"로 채워진다. 화자 구분이 꼭 필요하면
이후 analyze 단계에서 Claude가 문맥으로 추정하거나, pyannote 같은 별도 화자분리를
붙여야 한다.

활성화하려면:
  pip install openai
  .env 에 OPENAI_API_KEY, STT_ENGINE=whisper
"""
from __future__ import annotations

import os

from .base import STTEngine, Transcript, Segment


class WhisperEngine(STTEngine):
    name = "whisper"

    def __init__(self, api_key: str | None = None, model: str = "whisper-1"):
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.model = model

    def transcribe(self, audio_path: str) -> Transcript:
        try:
            from openai import OpenAI
        except ImportError as e:
            raise ImportError("Whisper를 쓰려면 'pip install openai' 가 필요합니다.") from e

        client = OpenAI(api_key=self.api_key)
        with open(audio_path, "rb") as f:
            result = client.audio.transcriptions.create(
                model=self.model,
                file=f,
                language="ko",
                response_format="verbose_json",
                timestamp_granularities=["segment"],
            )

        # 최신 SDK는 segment를 객체(속성 접근)로, 구버전은 dict로 준다. 둘 다 지원.
        def _f(seg, key, default=0):
            return seg.get(key, default) if isinstance(seg, dict) else getattr(seg, key, default)

        segments: list[Segment] = []
        for seg in getattr(result, "segments", []) or []:
            segments.append(Segment(
                speaker="1",  # Whisper는 화자분리 미지원
                start_ms=int(float(_f(seg, "start", 0)) * 1000),
                end_ms=int(float(_f(seg, "end", 0)) * 1000),
                text=str(_f(seg, "text", "")).strip(),
            ))

        return Transcript(
            engine=self.name,
            audio_filename=os.path.basename(audio_path),
            full_text=result.text,
            segments=segments,
        )
