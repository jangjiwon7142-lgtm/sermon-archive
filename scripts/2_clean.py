"""원문 정제 + 제목/본문 정규식 1차 메타 추출. 토큰 0.

사용: python scripts/2_clean.py  (이미 처리된 data/clean/{logNo}.json 은 건너뜀)
"""
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
RAW, CLEAN = DATA / "raw", DATA / "clean"

BOOKS = (
    "창세기 출애굽기 레위기 민수기 신명기 여호수아 사사기 룻기 사무엘상 사무엘하 열왕기상 열왕기하 "
    "역대상 역대하 에스라 느헤미야 에스더 욥기 시편 잠언 전도서 아가 이사야 예레미야 예레미야애가 "
    "에스겔 다니엘 호세아 요엘 아모스 오바댜 요나 미가 나훔 하박국 스바냐 학개 스가랴 말라기 "
    "마태복음 마가복음 누가복음 요한복음 사도행전 로마서 고린도전서 고린도후서 갈라디아서 에베소서 "
    "빌립보서 골로새서 데살로니가전서 데살로니가후서 디모데전서 디모데후서 디도서 빌레몬서 히브리서 "
    "야고보서 베드로전서 베드로후서 요한일서 요한이서 요한삼서 유다서 요한계시록"
).split()
BOOK_RE = "|".join(sorted(BOOKS, key=len, reverse=True))
SCRIPTURE_RE = re.compile(rf"({BOOK_RE})\s*(\d+)\s*장\s*(?:(\d+(?:\s*[-~]\s*\d+)?)\s*절)?")

TITLE_MAP = {"목사": "목사", "목사님": "목사", "P": "목사", "p": "목사", "전도사": "전도사", "강도사": "강도사",
             "장로": "장로", "E": "장로", "e": "장로"}
ROLE = r"(?:(?:담임|부)\s*)?(?:목사님|목사|전도사|강도사|장로|[Pp]|[Ee])"
PREACHER_RE = re.compile(rf"(?<![가-힣A-Za-z])([가-힣]{{2,4}})\s*({ROLE})(?![A-Za-z가-힣])\s*(?:\(([^)]*)\))?")
# 별칭 맵: 표기 흔들림 → 대표 표기 (필요 시 추가)
ALIAS = {}


def parse_date(title, published):
    pub_year = int(published[:4]) if published else None
    title = title.replace("﻿", "").replace("​", "").strip()
    pats = [
        (r"^\s*(\d{4})\s*년\s*(\d{1,2})\s*월\s*(\d{1,2})\s*일", "ymd"),
        (r"^\s*(\d{4})(\d{2})(\d{2})(?!\d)", "ymd"),
        (r"^\s*(\d{4})\s*[.\-]\s*(\d{1,2})\s*[.\-]\s*(\d{1,2})\.?", "ymd"),
        (r"^\s*(\d{2})\s*\.\s*(\d{1,2})\s*\.\s*(\d{1,2})\.?", "yymd"),
        (r"^\s*(\d{1,2})\s*\.\s*(\d{1,2})\.?", "md"),
    ]
    for pat, kind in pats:
        m = re.match(pat, title)
        if not m:
            continue
        g = [int(x) for x in m.groups()]
        if kind == "ymd":
            y, mo, d = g
        elif kind == "yymd":
            y, mo, d = 2000 + g[0], g[1], g[2]
        else:
            if not pub_year:
                continue
            y, mo, d = pub_year, g[0], g[1]
        if 1 <= mo <= 12 and 1 <= d <= 31:
            return f"{y:04d}-{mo:02d}-{d:02d}", m.end(), kind == "md"
    return None, 0, False


def parse_published(add_date):
    m = re.match(r"(\d{4})\.\s*(\d{1,2})\.\s*(\d{1,2})", add_date or "")
    return f"{int(m[1]):04d}-{int(m[2]):02d}-{int(m[3]):02d}" if m else ""


def parse_title(title, published):
    title = title.replace("﻿", "").replace("​", "").strip()
    date, end, uncertain = parse_date(title, published)
    rest = title[end:] if date else title
    pre, church = "", ""
    ms = list(PREACHER_RE.finditer(rest))
    m = None
    for cand in reversed(ms):  # 끝쪽 매치 우선
        if not rest[cand.end():].strip(" -_,"):
            m = cand
            break
    if m is None and ms:
        m = ms[0]
    if m:
        name, role, church = m.group(1), m.group(2), (m.group(3) or "")
        role = re.sub(r"^(담임|부)\s*", "", role)
        pre = f"{ALIAS.get(name, name)} {TITLE_MAP.get(role, role)}"
        rest = rest[: m.start()] + " " + rest[m.end():]
    church = re.sub(r"교회$", "", church.strip())
    clean_title = re.sub(r"\s+", " ", rest).strip(" -_,.·")
    needs_review = not date or not pre or not clean_title or uncertain
    return {
        "date": date or "",
        "date_uncertain": uncertain,
        "title": clean_title,
        "preacher": pre,
        "church": church,
        "needs_review": needs_review,
    }


def clean_text(raw):
    lines = []
    for ln in raw.replace("​", "").replace("\xa0", " ").splitlines():
        ln = ln.strip()
        if re.match(r"^첨부파일", ln) or re.search(r"\.(docx?|hwp|pdf)\s*(파일)?\s*다운로드", ln):
            continue
        lines.append(ln)
    text = "\n".join(lines)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def scripture_candidates(text):
    ms = [(m.group(1), int(m.group(2)), (m.group(3) or "").replace(" ", "")) for m in SCRIPTURE_RE.finditer(text)]
    if not ms:
        return []
    first = ms[0]
    top = Counter((b, c) for b, c, _ in ms).most_common(3)
    out = [{"book": first[0], "chapter": first[1], "verse": first[2], "raw": f"{first[0]} {first[1]}장" + (f" {first[2]}절" if first[2] else "")}]
    for (b, c), n in top:
        if (b, c) != (first[0], first[1]):
            out.append({"book": b, "chapter": c, "verse": "", "raw": f"{b} {c}장", "count": n})
    return out


def main():
    CLEAN.mkdir(parents=True, exist_ok=True)
    plist = {p["logNo"]: p for p in json.loads((DATA / "post_list.json").read_text(encoding="utf-8"))}
    done = skipped = 0
    for f in sorted(RAW.glob("*.txt")):
        log = f.stem
        out = CLEAN / f"{log}.json"
        if out.exists():
            skipped += 1
            continue
        meta = plist.get(log, {"title": "", "addDate": ""})
        published = parse_published(meta["addDate"])
        info = parse_title(meta["title"], published)
        text = clean_text(f.read_text(encoding="utf-8"))
        rec = {
            "id": log,
            "title_raw": meta["title"],
            "published": published,
            **info,
            "year": int(info["date"][:4]) if info["date"] else (int(published[:4]) if published else None),
            "scripture_candidates": scripture_candidates(text),
            "chars": len(text),
            "source_url": f"https://m.blog.naver.com/PostView.naver?blogId=sdongbujbch&logNo={log}",
            "text": text,
        }
        out.write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
        done += 1
    print(f"정제 완료: 신규 {done} / 건너뜀 {skipped}")


if __name__ == "__main__":
    main()
