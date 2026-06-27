"""CLOVA Speech(네이버 클라우드) 장문 인식 - 로컬 파일 업로드 방식.

엔드포인트: {INVOKE_URL}/recognizer/upload
- multipart/form-data
  - params: JSON 문자열 (언어, 화자분리, 부스팅 등)
  - media : 음성 파일
- 헤더: X-CLOVASPEECH-API-KEY: {SECRET}

응답 segments[] 구조:
  { "start": ms, "end": ms, "text": "...", "speaker": {"label": "1", "name": "A"} }
"""
from __future__ import annotations

import json
import os

import requests

from .base import STTEngine, Transcript, Segment


class ClovaSpeechEngine(STTEngine):
    name = "clova"

    def __init__(self, invoke_url: str | None = None, secret: str | None = None,
                 boosting_words: list[str] | None = None):
        self.invoke_url = (invoke_url or os.environ["CLOVA_SPEECH_INVOKE_URL"]).rstrip("/")
        self.secret = secret or os.environ["CLOVA_SPEECH_SECRET"]
        # 현장 용어 인식률을 높이는 부스팅 키워드 (한글/영어만, 1음절 제외)
        self.boosting_words = boosting_words or []

    def transcribe(self, audio_path: str) -> Transcript:
        params = {
            "language": "ko-KR",
            "completion": "sync",          # 동기: 응답으로 바로 결과 수신
            "wordAlignment": True,
            "fullText": True,
            "diarization": {"enable": True},   # 화자 분리
            "noiseFiltering": True,
        }
        if self.boosting_words:
            # 부스팅은 콤마로 구분된 단어 문자열 하나로 전달
            params["boostings"] = [{"words": ",".join(self.boosting_words)}]

        url = f"{self.invoke_url}/recognizer/upload"
        headers = {
            "Accept": "application/json;UTF-8",
            "X-CLOVASPEECH-API-KEY": self.secret,
        }

        with open(audio_path, "rb") as f:
            files = {
                "media": f,
                "params": (None, json.dumps(params), "application/json"),
            }
            resp = requests.post(url, headers=headers, files=files, timeout=1800)

        resp.raise_for_status()
        data = resp.json()

        if data.get("result") not in ("COMPLETED", "SUCCEEDED"):
            raise RuntimeError(f"CLOVA Speech 실패: {data.get('message')} / 전체응답={data}")

        segments: list[Segment] = []
        for seg in data.get("segments", []):
            speaker_label = str(seg.get("speaker", {}).get("label", "?"))
            segments.append(Segment(
                speaker=speaker_label,
                start_ms=int(seg.get("start", 0)),
                end_ms=int(seg.get("end", 0)),
                text=seg.get("text", "").strip(),
            ))

        full_text = data.get("text", "") or "\n".join(s.text for s in segments)

        return Transcript(
            engine=self.name,
            audio_filename=os.path.basename(audio_path),
            full_text=full_text,
            segments=segments,
        )
