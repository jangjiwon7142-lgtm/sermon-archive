# sermon-archive 작업 규칙

서울동부교회 네이버 블로그 `sdongbujbch` 의 **설교전문 카테고리(categoryNo=17, 260편)** 를 수집·요약해
GitHub Pages(`docs/`)로 공개하는 프로젝트.

## 역할 분리 (토큰 절약 원칙)
- 대량 수집·전처리는 파이썬(`scripts/`)이 한다. 클로드 코드는 요약·검수만 한다.
- Aside 브라우저는 구조 확인에만 쓴다(읽기 전용, guard 권한). 전체 글을 Aside로 수집하지 않는다.
- 요약 시 채팅창에 요약 본문을 출력하지 않는다. 파일에만 쓰고 "처리 logNo 목록 + 남은 개수"만 1줄 보고.
- 10편 처리마다 `/clear`. 요약 모델은 Haiku 또는 Sonnet.

## 수집 대상
- 목록: `https://blog.naver.com/PostTitleListAsync.naver?blogId=sdongbujbch&categoryNo=17&currentPage={page}&countPerPage=30`
- 본문: `https://m.blog.naver.com/PostView.naver?blogId=sdongbujbch&logNo={logNo}`
- 글 URL(source_url): 위 본문 URL 형식 그대로.
- 다른 카테고리(주일설교 50편=영상 위주, 성경강연회 108편)는 대상이 아니다.
- 요청 간 1.0~1.5초 랜덤 딜레이, User-Agent/Referer 포함, 이미 있는 `data/raw/{logNo}.txt` 는 건너뜀(증분).

## 본문 구조 (샘플 5편 확인 결과)
- 본문 컨테이너: `.se-main-container`, 텍스트 블록: `.se-main-container .se-text`
- 본문은 텍스트다(영상 아님). 길이 약 2.6만~3.5만 자 → 입력 토큰이 크므로 전처리 필수.
- 2026년 글: 이미지 썸네일 + 첨부파일(.docx) + 텍스트 1블록. 설교자 줄은 본문에 없고 제목에만 있다.
- 2020년 글: 첨부파일(.hwp) + 텍스트 1블록. 본문 첫머리에 날짜·성경장·제목·설교자 순으로 적힌 경우가 있다.
- 본문 끝은 기도문과 "아멘". 뒤는 빈 줄.

## 제거 대상 (전처리)
- 첫 줄의 "첨부파일 … .docx/.hwp 파일 다운로드" 안내
- 이미지 캡션/썸네일 alt, 연속 빈 줄·제로폭 공백
- 고정 반복 공지·하단 인사말은 없다. 설교자별 인사("안녕하세요…")는 본문이므로 지우지 않는다.
- 제외할 글: 설교 글이 아닌 NOTICE("서울동부교회 공식 블로그 이용 관련 안내", logNo 222947640713 — 카테고리 밖 공지).

## 메타데이터 1차 추출 규칙 (정규식)
제목 형식이 통일되어 있지 않다. 확인된 변형:
1. `2026.11.08 제목 설교자직분(교회)`
2. `20261025 제목 - 최재수 목사(광양서부)`
3. `26. 10. 4. 제목, 이준민목사`
4. `2026.09.20_제목_이준민 목사`
5. 연도 없는 날짜(예: `12.20.`)가 있다 → 발행일(`.se_publishDate`)의 연도로 보완하고 `date_uncertain: true` 표시.

- date: 제목 앞 날짜를 설교일(주일)로 쓴다. 발행일은 설교일보다 2~9일 늦다. 둘 다 저장(`date`, `published`).
- preacher: 제목 끝의 `이름 + 직분(목사/P/p/전도사/e=장로) + (교회)`. 직분 표기(P, p, 목사)는 통일하고 별칭 맵으로 동일인 표기를 맞춘다. 파싱 실패 시 빈 값 + `needs_review: true`.
- scripture: 본문에서 `\S+ \d+장 \d+절` 형태가 구어체로 나온다. 2020년 글은 본문 상단에 성경장+절 번호 인용. 첫 번째 성경 본문 언급을 1차 후보로 잡고 요약 단계에서 검수한다.
- 같은 설교가 중복 게시될 수 있다(제목 띄어쓰기만 다름). 날짜+정규화 제목이 같으면 `duplicate_of` 로 표시하고 최종 JSON에서는 하나만 남긴다.

## 최종 JSON 스키마 (`data/items/{logNo}.json`)
```json
{
  "id": "logNo",
  "date": "YYYY-MM-DD",
  "published": "YYYY-MM-DD",
  "year": 2026,
  "title": "설교 제목(날짜·설교자 제거)",
  "preacher": "이준민 목사",
  "church": "서울동부",
  "scripture": {"book": "", "chapter": 0, "verse": "", "raw": ""},
  "topics": ["태그2~3개"],
  "summary_short": "1~2문장",
  "key_points": ["3~5개"],
  "key_quote": "1문장",
  "source_url": "https://m.blog.naver.com/PostView.naver?blogId=sdongbujbch&logNo=..."
}
```
- 공개 파일 `docs/sermons.json` 에는 설교 **전문을 넣지 않는다**(저작권·용량). 메타·요약·source_url만.
- `data/raw/` 는 `.gitignore` 로 제외(원문 비공개).
- key_quote는 원문 그대로 1문장만 인용(요약·각색 금지).

## 고정 주제 태그 사전 (이 중에서만 2~3개 선택)
믿음, 은혜, 기도, 고난, 가정, 구원, 성령, 교회, 사랑, 순종, 소망, 회개, 감사, 전도, 헌신, 말씀, 동행, 재림, 예배, 성장

(필요하면 추가하되 사용자 승인 후 이 목록에 반영한다.)

## 증분 업데이트
주 1회: `python scripts/1_crawl.py && python scripts/2_clean.py` → 미처리 `data/clean/` 만 요약 → `python scripts/3_build_json.py` → 커밋·푸시.
