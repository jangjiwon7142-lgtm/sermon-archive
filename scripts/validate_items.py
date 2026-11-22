"""data/items 검증. 토큰 0.
- 스키마 필드, 태그 사전, key_quote 원문 일치(공백 제거 후 부분문자열), key_points 개수 확인
- 불합격 파일은 data/items_bad/ 로 옮겨 다음 배치에서 재처리되게 한다.
사용: python scripts/validate_items.py
"""
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
TAGS = set("믿음 은혜 기도 고난 가정 구원 성령 교회 사랑 순종 소망 회개 감사 전도 헌신 말씀 동행 재림 예배 성장".split())


def squash(s):
    return re.sub(r"[\s\W_]+", "", s or "")


def main():
    bad_dir = DATA / "items_bad"
    ok = bad = 0
    for f in sorted((DATA / "items").glob("*.json")):
        errs = []
        try:
            it = json.loads(f.read_text(encoding="utf-8"))
            clean = json.loads((DATA / "clean" / f.name).read_text(encoding="utf-8"))
        except Exception as e:  # noqa: BLE001
            errs.append(f"읽기실패:{e}")
            it = clean = None
        if it:
            if not (2 <= len(it.get("topics", [])) <= 3) or not set(it["topics"]) <= TAGS:
                errs.append(f"topics:{it.get('topics')}")
            if not it.get("summary_short"):
                errs.append("summary_short 없음")
            if not (3 <= len(it.get("key_points", [])) <= 5):
                errs.append("key_points 개수")
            q = squash(it.get("key_quote", ""))
            if not q or q not in squash(clean["text"]):
                errs.append("key_quote 원문 불일치")
            sc = it.get("scripture")
            if not sc or not sc.get("book"):
                errs.append("scripture 없음")
        if errs:
            bad_dir.mkdir(exist_ok=True)
            shutil.move(str(f), bad_dir / f.name)
            print("불합격", f.stem, errs)
            bad += 1
        else:
            ok += 1
    print(f"검증: 합격 {ok} / 불합격 {bad}")


if __name__ == "__main__":
    main()
