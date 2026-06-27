"""STT 엔진 공통 인터페이스.

CLOVA Speech, Whisper 등 어떤 엔진을 쓰든 동일한 형태의 결과를 돌려주도록
표준 구조를 정의한다. 엔진을 교체해도 이후 단계(postprocess/analyze)는 그대로 동작한다.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from typing import Optional
import json


@dataclass
class Segment:
    """화자 분리된 발화 한 덩어리."""
    speaker: str          # 예: "1", "2" (엔진이 준 화자 라벨) 또는 식별된 이름
    start_ms: int         # 시작 시각 (밀리초)
    end_ms: int           # 종료 시각 (밀리초)
    text: str             # 발화 내용


@dataclass
class Transcript:
    """STT 전체 결과."""
    engine: str                       # "clova" | "whisper"
    audio_filename: str
    full_text: str                    # 전체 텍스트 (화자 구분 없이 이어붙인 것)
    segments: list[Segment] = field(default_factory=list)

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, indent=2)

    @classmethod
    def from_dict(cls, data: dict) -> "Transcript":
        """to_json()으로 저장한 전사본을 다시 읽어들인다 (STT 재실행 없이 교정·분석)."""
        segments = [Segment(**s) for s in data.get("segments", [])]
        return cls(
            engine=data.get("engine", "unknown"),
            audio_filename=data.get("audio_filename", ""),
            full_text=data.get("full_text", ""),
            segments=segments,
        )

    @classmethod
    def from_json(cls, text: str) -> "Transcript":
        return cls.from_dict(json.loads(text))

    def to_readable(self) -> str:
        """화자: 발화 형태의 읽기 쉬운 텍스트."""
        lines = []
        for s in self.segments:
            ts = _fmt_ts(s.start_ms)
            lines.append(f"[{ts}] 화자{s.speaker}: {s.text}")
        return "\n".join(lines)


def _fmt_ts(ms: int) -> str:
    total_sec = ms // 1000
    h, rem = divmod(total_sec, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h:d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


class STTEngine(ABC):
    """모든 STT 엔진이 구현해야 하는 인터페이스."""

    name: str = "base"

    @abstractmethod
    def transcribe(self, audio_path: str) -> Transcript:
        """음성 파일 경로를 받아 Transcript를 반환한다."""
        raise NotImplementedError
