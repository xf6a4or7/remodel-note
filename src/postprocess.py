"""STT 결과 후처리: (1) 용어 사전 기계 치환 → (2) Claude 문맥 교정.

목표: 클로바노트 수동 교정 작업을 자동화. 현장 용어 오인식을 사전으로 1차 잡고,
사전으로 못 잡는 문맥 의존 오인식은 Claude가 처리한다. 추정이 들어간 교정은
하단 [교정 메모]로 분리해 사람이 검토할 수 있게 한다.
"""
from __future__ import annotations

import json
import os
import re

from anthropic import Anthropic

from .stt.base import Transcript


def load_glossary(path: str) -> dict[str, str]:
    """glossary.json 의 모든 카테고리를 하나의 평면 치환 사전으로 합친다."""
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    flat: dict[str, str] = {}
    for key, val in raw.items():
        if key.startswith("_"):
            continue
        if isinstance(val, dict):
            for k, v in val.items():
                if k.startswith("_") or not isinstance(v, str):
                    continue
                flat[k] = v
    return flat


def apply_glossary(text: str, glossary: dict[str, str]) -> str:
    """한 번에(single-pass) 치환한다.

    긴 키를 우선 매칭하고, 이미 치환된 구간은 다시 매칭하지 않는다.
    (str.replace 를 반복하면 '레그라 박스'→'레그라박스' 뒤에 '박스' 키가 다시 걸려
    결과를 망가뜨릴 수 있어, 정규식 단일 패스로 막는다.)
    """
    pairs = {w: r for w, r in glossary.items() if w != r}
    if not pairs:
        return text
    pattern = re.compile("|".join(re.escape(w) for w in sorted(pairs, key=len, reverse=True)))
    return pattern.sub(lambda m: pairs[m.group(0)], text)


CORRECTION_SYSTEM = """너는 한국 인테리어·시공 현장 상담 녹취록을 교정하는 전문가다.
STT(음성→텍스트) 결과에는 현장 용어·브랜드명·치수가 잘못 인식된 부분이 많다.
다음 원칙으로 교정하라:
- 문맥상 명백한 오인식만 고친다. 말투·구어체는 살린다.
- 자재명, 브랜드(BLUM, 보쉬, 지멘스 등), 공법 용어, 치수(950mm 등)를 우선 점검한다.
- 화자 구분은 입력의 화자 라벨을 유지한다.
- 추정이 들어간 교정(확실하지 않은 것)은 본문에 반영하되, 끝에 [교정 메모] 섹션으로
  '원래표현 → 교정표현 (이유)' 형식으로 모아 표기한다.
- 출력은 교정된 녹취록 본문 + [교정 메모] 두 부분만. 다른 설명은 쓰지 않는다."""


def claude_correct(readable_text: str, model: str = "claude-opus-4-8") -> str:
    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    msg = client.messages.create(
        model=model,
        max_tokens=8000,
        system=CORRECTION_SYSTEM,
        messages=[{
            "role": "user",
            "content": f"다음 녹취록을 교정해줘:\n\n{readable_text}",
        }],
    )
    return "".join(block.text for block in msg.content if block.type == "text")


def postprocess(transcript: Transcript, glossary_path: str,
                use_claude: bool = True) -> str:
    """Transcript → 교정된 읽기 쉬운 텍스트(화자별)."""
    glossary = load_glossary(glossary_path)
    # 1) 세그먼트별 사전 치환
    for seg in transcript.segments:
        seg.text = apply_glossary(seg.text, glossary)
    readable = transcript.to_readable()
    # 2) Claude 문맥 교정
    if use_claude:
        readable = claude_correct(readable)
    return readable
