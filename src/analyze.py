"""교정된 녹취록 → 구조화된 분석 결과(JSON).

산출물 docgen에서 회의록 docx를 만들 때 이 구조를 그대로 쓴다.
인테리어 상담 도메인에 맞춰 필드를 설계했다.
"""
from __future__ import annotations

import json
import os

from anthropic import Anthropic


ANALYZE_SYSTEM = """너는 한국 인테리어·리모델링 상담 녹취록을 분석해 구조화하는 전문가다.
입력 녹취록을 읽고 아래 JSON 스키마에 정확히 맞춰 한국어로 출력하라.
JSON 외의 텍스트(설명, 마크다운 코드펜스)는 절대 출력하지 마라.

스키마:
{
  "meeting_overview": {
    "title": "미팅 제목(예: OO아파트 50평 복층 1차 상담)",
    "date": "추정 날짜 또는 빈 문자열",
    "participants": ["강대표님", "최대표님", "여자고객님", ...],
    "summary": "3~5문장 요약"
  },
  "decisions": [
    {"topic": "예: 아일랜드 높이", "decision": "950mm 확정", "note": "비고"}
  ],
  "pending_items": [
    {"item": "예: 복층 계단 위치", "priority": "high|medium|low", "action_needed": "현장 확인 필요 등"}
  ],
  "customer_requirements": [
    {"space": "주방|거실|욕실|침실|발코니|공통",
     "category": "자재|구조|설비|디자인|예산|기타",
     "requirement": "고객 요청/선호 내용",
     "raw_quote": "관련 발화 짧게(선택)"}
  ],
  "action_items": [
    {"task": "할 일", "owner": "담당(예: 강대표님/고객)", "due": "기한 또는 빈 문자열"}
  ],
  "estimate_notes": [
    {"item": "견적 관련 언급(자재/수량/금액 등)", "detail": "내용"}
  ]
}

규칙:
- 녹취에 없는 내용을 지어내지 마라. 모르면 빈 배열/빈 문자열.
- pending_items 의 priority 는 상담 맥락상 시급성으로 판단.
- customer_requirements 는 공간별·카테고리별로 최대한 잘게 쪼개라."""


def analyze(corrected_text: str, model: str = "claude-opus-4-8") -> dict:
    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    msg = client.messages.create(
        model=model,
        max_tokens=8000,
        system=ANALYZE_SYSTEM,
        messages=[{
            "role": "user",
            "content": f"다음 녹취록을 분석해 JSON으로:\n\n{corrected_text}",
        }],
    )
    text = "".join(b.text for b in msg.content if b.type == "text").strip()
    # 혹시 코드펜스가 붙으면 제거
    if text.startswith("```"):
        text = text.split("```", 2)[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()
    return json.loads(text)
