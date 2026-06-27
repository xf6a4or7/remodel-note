"""전체 파이프라인 오케스트레이션.

audio → STT → 교정 → 분석 → (회의록 docx + 요구사항 json + 요약 md)
각 중간 산출물을 디스크에 남겨 디버깅/재실행이 쉽도록 한다.
"""
from __future__ import annotations

import json
import os
from datetime import datetime

from .stt import get_engine, Transcript
from .postprocess import postprocess
from .analyze import analyze
from .docgen import build_minutes

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GLOSSARY = os.path.join(ROOT, "config", "glossary.json")
RAW_DIR = os.path.join(ROOT, "transcripts", "raw")
CLEAN_DIR = os.path.join(ROOT, "transcripts", "clean")
OUT_DIR = os.path.join(ROOT, "output")


def _load_boosting_words() -> list[str]:
    """glossary 의 교정 '결과값'들을 부스팅 키워드로 활용(한글/영어, 2음절 이상)."""
    with open(GLOSSARY, encoding="utf-8") as f:
        raw = json.load(f)
    words = set()
    for key, val in raw.items():
        if key.startswith("_") or not isinstance(val, dict):
            continue
        for v in val.values():
            if isinstance(v, str) and len(v.strip()) >= 2:
                words.add(v.strip())
    return sorted(words)


def run(audio_path: str | None = None, *, transcript_path: str | None = None,
        use_claude: bool = True, engine_name: str | None = None) -> dict:
    """audio_path 또는 transcript_path 중 하나는 반드시 필요.
    transcript_path를 주면 STT를 건너뛰고 저장된 전사본(raw json)으로 교정·분석만 재실행한다.
    """
    if not audio_path and not transcript_path:
        raise ValueError("audio_path 또는 transcript_path 중 하나가 필요합니다.")

    source = transcript_path or audio_path
    base = os.path.splitext(os.path.basename(source))[0]
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    tag = f"{base}_{stamp}"

    for d in (RAW_DIR, CLEAN_DIR, OUT_DIR):
        os.makedirs(d, exist_ok=True)

    # 1) STT (또는 저장된 전사본 로드)
    if transcript_path:
        print(f"[1/4] 전사본 로드 중... (STT 건너뜀: {transcript_path})")
        with open(transcript_path, encoding="utf-8") as f:
            transcript = Transcript.from_json(f.read())
        raw_json = transcript_path
    else:
        print(f"[1/4] STT 변환 중... ({engine_name or os.environ.get('STT_ENGINE','clova')})")
        kwargs = {}
        if (engine_name or os.environ.get("STT_ENGINE", "clova")) == "clova":
            kwargs["boosting_words"] = _load_boosting_words()
        engine = get_engine(engine_name, **kwargs)
        transcript = engine.transcribe(audio_path)

        raw_json = os.path.join(RAW_DIR, f"{tag}.json")
        with open(raw_json, "w", encoding="utf-8") as f:
            f.write(transcript.to_json())
        print(f"      원본 저장: {raw_json}")

    # 2) 후처리(교정)
    print("[2/4] 용어 교정 + 문맥 교정 중...")
    corrected = postprocess(transcript, GLOSSARY, use_claude=use_claude)
    clean_txt = os.path.join(CLEAN_DIR, f"{tag}.txt")
    with open(clean_txt, "w", encoding="utf-8") as f:
        f.write(corrected)
    print(f"      교정본 저장: {clean_txt}")

    # --no-claude: 교정본까지만 만들고 분석·문서 생성은 건너뛴다 (Claude API 미사용)
    if not use_claude:
        print("완료! (--no-claude: 분석·회의록 생략)")
        return {"raw_json": raw_json, "clean_txt": clean_txt}

    # 3) 분석
    print("[3/4] 구조화 분석 중...")
    analysis = analyze(corrected)
    req_json = os.path.join(OUT_DIR, f"{tag}_요구사항.json")
    with open(req_json, "w", encoding="utf-8") as f:
        json.dump(analysis, f, ensure_ascii=False, indent=2)
    print(f"      분석 저장: {req_json}")

    # 4) 문서 생성
    print("[4/4] 회의록 docx 생성 중...")
    docx_path = os.path.join(OUT_DIR, f"{tag}_회의록.docx")
    build_minutes(analysis, docx_path)

    summary_md = os.path.join(OUT_DIR, f"{tag}_요약.md")
    _write_summary_md(analysis, summary_md)

    print("완료!")
    return {
        "raw_json": raw_json,
        "clean_txt": clean_txt,
        "requirements_json": req_json,
        "minutes_docx": docx_path,
        "summary_md": summary_md,
    }


def _write_summary_md(analysis: dict, path: str):
    ov = analysis.get("meeting_overview", {})
    lines = [f"# {ov.get('title','상담 요약')}", ""]
    if ov.get("summary"):
        lines += [ov["summary"], ""]
    lines.append("## 주요 결정")
    for d in analysis.get("decisions", []):
        lines.append(f"- {d.get('topic')}: {d.get('decision')}")
    lines.append("")
    lines.append("## 미결 항목")
    for x in analysis.get("pending_items", []):
        mark = "★ " if x.get("priority") == "high" else ""
        lines.append(f"- {mark}{x.get('item')} — {x.get('action_needed')}")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
