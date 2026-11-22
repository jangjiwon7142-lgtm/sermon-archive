"""네이버 블로그 설교전문(categoryNo=17) 증분 수집기. 토큰 0.

사용:
  python scripts/1_crawl.py            # 전체 (이미 받은 글은 건너뜀)
  python scripts/1_crawl.py --limit 5  # 최신 5편만 (테스트)
"""
import argparse
import json
import random
import time
import urllib.parse
from pathlib import Path

import requests
from bs4 import BeautifulSoup

BLOG_ID = "sdongbujbch"
CATEGORY = 17
ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
RAW = DATA / "raw"
LIST_URL = "https://blog.naver.com/PostTitleListAsync.naver"
VIEW_URL = "https://m.blog.naver.com/PostView.naver"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Referer": f"https://blog.naver.com/{BLOG_ID}",
}
BODY_SELECTORS = [".se-main-container", "#postViewArea", ".post_ct", "#viewTypeSelector"]


def sleep():
    time.sleep(random.uniform(1.0, 1.5))


def fetch_list(session, limit=None):
    """전체 logNo 목록(제목·게시일 포함). 기존 목록과 병합해 신규만 추가."""
    path = DATA / "post_list.json"
    known = {p["logNo"]: p for p in json.loads(path.read_text(encoding="utf-8"))} if path.exists() else {}
    posts, page, total = [], 1, None
    while True:
        r = session.get(
            LIST_URL,
            params={"blogId": BLOG_ID, "categoryNo": CATEGORY, "currentPage": page, "countPerPage": 30},
            headers=HEADERS,
            timeout=20,
        )
        r.raise_for_status()
        j = json.loads(r.text.replace("\\'", "'"), strict=False)  # 네이버 응답에 잘못된 \' 이스케이프가 있음
        total = int(j.get("totalCount", 0))
        items = j.get("postList", [])
        if not items:
            break
        for it in items:
            posts.append(
                {
                    "logNo": it["logNo"],
                    "title": urllib.parse.unquote_plus(it["title"]),
                    "addDate": it.get("addDate", ""),
                }
            )
        if len(posts) >= total or (limit and len(posts) >= limit):
            break
        page += 1
        sleep()
    for p in posts:
        known[p["logNo"]] = p
    merged = sorted(known.values(), key=lambda p: int(p["logNo"]), reverse=True)
    path.write_text(json.dumps(merged, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"목록: 이번 {len(posts)}편 / 누적 {len(merged)}편 (카테고리 총 {total}편)")
    return merged


def extract_text(html):
    soup = BeautifulSoup(html, "html.parser")
    for sel in BODY_SELECTORS:
        box = soup.select_one(sel)
        if box:
            break
    else:
        return ""
    for t in box.select("script, style, .se-module-image, .se-module-oglink, .se-module-file"):
        t.decompose()
    paras = box.select(".se-text-paragraph")
    lines = [p.get_text("", strip=False) for p in paras] if paras else box.get_text("\n").splitlines()
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None, help="최신 N편만 처리")
    args = ap.parse_args()

    RAW.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    posts = fetch_list(session, args.limit)
    if args.limit:
        posts = posts[: args.limit]

    failed_path = DATA / "failed.json"
    failed = []
    done = skipped = 0
    for p in posts:
        out = RAW / f"{p['logNo']}.txt"
        if out.exists() and out.stat().st_size > 0:
            skipped += 1
            continue
        try:
            r = session.get(
                VIEW_URL, params={"blogId": BLOG_ID, "logNo": p["logNo"]}, headers=HEADERS, timeout=30
            )
            r.raise_for_status()
            text = extract_text(r.text)
            if len(text.strip()) < 50:
                raise ValueError(f"본문이 너무 짧음({len(text.strip())}자)")
            out.write_text(text, encoding="utf-8")
            done += 1
            print(f"저장 {p['logNo']} ({len(text)}자) {p['title'][:30]}")
        except Exception as e:  # noqa: BLE001
            failed.append({"logNo": p["logNo"], "title": p["title"], "error": str(e)})
            print(f"실패 {p['logNo']}: {e}")
        sleep()

    failed_path.write_text(json.dumps(failed, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"완료: 신규 {done} / 건너뜀 {skipped} / 실패 {len(failed)}")


if __name__ == "__main__":
    main()
