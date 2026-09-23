import hashlib
import html
import json
import os
import re
import sys
import time
from datetime import date

from common import fetch, geocode_keyword

WIKI_URL = "https://en.wikipedia.org/wiki/Oraegage"
OUT = "data/노포_오래가게.json"
TODAY = date(2026, 9, 10)

KAKAO_REST_KEY = os.environ.get("KAKAO_REST_KEY")
if not KAKAO_REST_KEY:
    sys.exit("환경변수 KAKAO_REST_KEY를 설정하세요 (카카오 개발자센터 > 플랫폼 키 > REST API 키)")

# 위키피디아 표의 Type 값 중 "맛집" 컨셉에 맞는 음식 관련 업종만 포함
FOOD_TYPES = {
    "Restaurant", "Food store", "Bakery", "Tteok store",
    "Coffeehouse", "Tea shop", "Confectionary store", "Pub",
}
TYPE_TO_CATEGORY = {
    "Bakery": "카페/베이커리",
    "Confectionary store": "카페/베이커리",
    "Tteok store": "카페/베이커리",
    "Coffeehouse": "카페/베이커리",
    "Tea shop": "카페/베이커리",
}
DEFAULT_CATEGORY = "기타"


def clean_cell(cell):
    cell = re.sub(r"<sup[^>]*>.*?</sup>", "", cell, flags=re.S)
    cell = re.sub(r"<[^>]+>", "", cell)
    return html.unescape(cell).strip()


def parse_table(page_html):
    m = re.search(r'<table class="wikitable sortable" id="[^"]*">(.*?)</table>', page_html, re.S)
    if not m:
        sys.exit("오래가게 표를 찾을 수 없습니다 (위키피디아 페이지 구조가 바뀌었을 수 있음)")
    rows = re.findall(r'<tr id="[^"]*">(.*?)</tr>', m.group(1), re.S)

    items = []
    for row in rows[1:]:  # 첫 행은 헤더
        cells = re.findall(r"<td[^>]*>(.*?)</td>", row, re.S)
        if len(cells) < 4:
            continue
        name, biz_type, established, district = (clean_cell(c) for c in cells[:4])
        items.append({"name": name, "type": biz_type, "established": established, "district": district})
    return items


def parse_year(established):
    m = re.search(r"(\d{4})", established)
    return int(m.group(1)) if m else None


def main():
    page_html = fetch(WIKI_URL)
    if not page_html:
        sys.exit("위키피디아 페이지를 가져오지 못했습니다")

    items = [i for i in parse_table(page_html) if i["type"] in FOOD_TYPES]
    print(f"음식 관련 오래가게 {len(items)}건 (전체 표 항목 중 필터링됨)")

    results = []
    skipped = 0
    for i, item in enumerate(items):
        place = geocode_keyword(f"서울 {item['name']}", KAKAO_REST_KEY)
        if not place or "서울" not in (place["address"] or ""):
            skipped += 1
            continue

        year = parse_year(item["established"])
        years_open = (TODAY.year - year) if year else None
        stable_id = hashlib.md5((item["name"] + place["address"]).encode("utf-8")).hexdigest()[:12]

        results.append({
            "id": stable_id,
            "name": item["name"],
            "address": place["address"],
            "bizType": item["type"],
            "foodCategory": TYPE_TO_CATEGORY.get(item["type"], DEFAULT_CATEGORY),
            "openedDate": None,  # 위키 자료는 연도만 제공, 등급 계산에 필요한 정밀 개업일자 없음
            "yearsOpen": years_open,
            "grade": None,  # 정밀 개업일자가 없어 등급은 매기지 않음 (source 배지만 표시)
            "hours": None,
            "phone": None,
            "homepage": None,
            "amenities": [],
            "intro": f"서울시 오래가게 선정 ({item['district']}구)" if item["district"] else "서울시 오래가게 선정",
            "source": ["오래가게"],
            "lat": round(place["lat"], 6),
            "lng": round(place["lng"], 6),
        })
        if (i + 1) % 10 == 0:
            print(f"{i + 1}/{len(items)} 처리, 실패 {skipped}건")
        time.sleep(0.15)

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"{len(results)}건 저장 -> {OUT} (좌표 매칭 실패 {skipped}건 제외)")


if __name__ == "__main__":
    main()
