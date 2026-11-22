"""data/clean + data/items → docs/sermons.json (원문 전문 제외). 토큰 0.

- 요약(items)이 있으면 병합, 없으면 정규식 메타만 담는다(summarized: false).
- 같은 날짜+정규화 제목의 중복 글은 하나만 남긴다(가장 오래된 logNo 유지).
사용: python scripts/3_build_json.py
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA, DOCS = ROOT / "data", ROOT / "docs"
REQUIRED = ["id", "date", "year", "title", "preacher", "source_url"]


def norm(s):
    return re.sub(r"[\s\W_]+", "", s or "")


def main():
    DOCS.mkdir(exist_ok=True)
    recs = {}
    ov_path = DATA / "overrides.json"  # 수동 보정(정규식이 못 잡은 글)
    overrides = json.loads(ov_path.read_text(encoding="utf-8")) if ov_path.exists() else {}
    for f in (DATA / "clean").glob("*.json"):
        c = json.loads(f.read_text(encoding="utf-8"))
        cand = c.get("scripture_candidates") or []
        rec = {
            "id": c["id"],
            "date": c["date"],
            "published": c["published"],
            "year": c["year"],
            "title": c["title"],
            "preacher": c["preacher"],
            "church": c["church"],
            "scripture": {k: cand[0][k] for k in ("book", "chapter", "verse", "raw")} if cand else None,
            "topics": [],
            "summary_short": "",
            "key_points": [],
            "key_quote": "",
            "source_url": c["source_url"],
            "summarized": False,
            "needs_review": c["needs_review"],
        }
        item = DATA / "items" / f"{c['id']}.json"
        if item.exists():
            rec.update({k: v for k, v in json.loads(item.read_text(encoding="utf-8")).items() if v not in (None, "")})
            rec["summarized"] = True
        ov = overrides.get(c["id"])
        if ov:
            rec.update(ov)
            rec["needs_review"] = False
        recs[c["id"]] = rec

    seen, out, dups = {}, [], 0
    for r in sorted(recs.values(), key=lambda r: int(r["id"])):  # 오래된 logNo 먼저
        key = (r["date"], norm(r["title"]))
        if r["date"] and key in seen:
            dups += 1
            continue
        seen[key] = r["id"]
        out.append(r)
    out.sort(key=lambda r: (r["date"] or r["published"], r["id"]), reverse=True)

    missing = [r["id"] for r in out if any(not r.get(k) for k in REQUIRED)]
    (DOCS / "sermons.json").write_text(
        json.dumps({"count": len(out), "items": out}, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
    )
    print(f"빌드: {len(out)}편 (중복 제거 {dups}) / 요약 완료 {sum(r['summarized'] for r in out)} / 필수필드 누락 {len(missing)}")
    if missing:
        print("누락 logNo:", ", ".join(missing[:30]))


if __name__ == "__main__":
    main()
