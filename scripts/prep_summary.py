"""요약용 압축 입력 생성. 토큰 0.

data/clean 중 data/items 에 아직 없는 글을 대상으로 data/prep/{logNo}.txt 를 만든다.
본문이 18,000자 초과면 앞·중간·끝 각 6,000자만 남긴다.
사용: python scripts/prep_summary.py [--batch N]   # 미처리 N편씩 묶어 data/queue.json 에 기록
"""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
PART, LIMIT = 6000, 18000


def compress(text):
    if len(text) <= LIMIT:
        return text
    mid = len(text) // 2
    return "\n[…중략…]\n".join([text[:PART], text[mid - PART // 2 : mid + PART // 2], text[-PART:]])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch", type=int, default=5)
    args = ap.parse_args()
    (DATA / "prep").mkdir(exist_ok=True)
    (DATA / "items").mkdir(exist_ok=True)
    todo = []
    for f in sorted((DATA / "clean").glob("*.json"), key=lambda p: -int(p.stem)):
        if (DATA / "items" / f.name).exists():
            continue
        c = json.loads(f.read_text(encoding="utf-8"))
        cand = "; ".join(s["raw"] for s in c["scripture_candidates"]) or "없음"
        head = (
            f"id: {c['id']}\n제목원문: {c['title_raw']}\n추출메타: date={c['date']} preacher={c['preacher']} "
            f"church={c['church']}\n성경구절후보: {cand}\n---\n"
        )
        (DATA / "prep" / f"{c['id']}.txt").write_text(head + compress(c["text"]), encoding="utf-8")
        todo.append(c["id"])
    batches = [todo[i : i + args.batch] for i in range(0, len(todo), args.batch)]
    (DATA / "queue.json").write_text(json.dumps(batches, indent=0), encoding="utf-8")
    print(f"미처리 {len(todo)}편 → {len(batches)}배치(각 {args.batch}편). data/queue.json")


if __name__ == "__main__":
    main()
