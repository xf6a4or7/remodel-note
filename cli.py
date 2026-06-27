#!/usr/bin/env python3
"""remodel-note CLI

사용법:
  python cli.py audio/녹취.m4a                    # 전체 파이프라인 (STT→교정→분석→문서)
  python cli.py audio/녹취.m4a --no-claude        # STT + 사전 치환만 (교정본까지)
  python cli.py audio/녹취.m4a --engine whisper   # STT 엔진 강제 지정
  python cli.py --transcript transcripts/raw/녹취_xxxxxx.json   # STT 건너뛰고 교정·분석 재실행

.env 파일에 API 키가 설정되어 있어야 합니다. (.env.example 참고)
"""
import argparse
import sys

from dotenv import load_dotenv

load_dotenv()  # .env 로드

from src.pipeline import run  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description="인테리어 상담 녹취 → 회의록/요구사항 자동화")
    parser.add_argument("audio", nargs="?", help="음성 파일 경로 (예: audio/녹취.m4a)")
    parser.add_argument("--transcript", metavar="JSON",
                        help="저장된 전사본(raw json)으로 STT를 건너뛰고 교정·분석만 재실행")
    parser.add_argument("--no-claude", action="store_true",
                        help="Claude 교정·분석 생략 (STT + 사전 치환만, 교정본까지)")
    parser.add_argument("--engine", choices=["clova", "whisper"], default=None,
                        help="STT 엔진 강제 지정 (기본: .env의 STT_ENGINE)")
    args = parser.parse_args()

    if not args.audio and not args.transcript:
        parser.error("음성 파일 경로 또는 --transcript 중 하나는 필요합니다.")

    try:
        result = run(args.audio, transcript_path=args.transcript,
                     use_claude=not args.no_claude, engine_name=args.engine)
    except FileNotFoundError as e:
        print(f"오류: 파일을 찾을 수 없습니다 - {e.filename or args.audio}", file=sys.stderr)
        sys.exit(1)
    except KeyError as e:
        print(f"오류: 환경변수 누락 {e}. .env 파일을 확인하세요.", file=sys.stderr)
        sys.exit(1)

    print("\n=== 산출물 ===")
    for k, v in result.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
