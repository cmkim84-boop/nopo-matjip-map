import hashlib
import html
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import date

LIST_URL = "https://www.sbiz.or.kr/hdst/main/ohndMarketList.do"
DETAIL_URL = "https://www.sbiz.or.kr/hdst/main/ohndMarketDetail.do"
OUT = "data/노포_백년가게.json"
TODAY = date(2026, 9, 10)

KAKAO_REST_KEY = os.environ.get("KAKAO_REST_KEY")
if not KAKAO_REST_KEY:
    sys.exit("환경변수 KAKAO_REST_KEY를 설정하세요 (카카오 개발자센터 > 플랫폼 키 > REST API 키)")

CATEGORY_RULES = [
    ("카페/베이커리", ["제과", "제빵", "빵", "케이크", "카페", "커피", "한과", "과자", "찐빵", "호두과자"]),
    ("중식", ["중식", "중화", "짜장", "짬뽕", "탕수육", "중국요리", "중국음식"]),
    ("일식", ["일식", "초밥", "스시", "돈가스", "돈까스", "라멘", "사시미", "복어", "메밀"]),
    ("양식", ["양식", "스테이크", "경양식", "파스타", "피자"]),
    ("해산물", ["회", "활어", "물회", "조개", "장어", "해물", "수산물", "젓갈", "게장", "전복", "굴", "낙지", "매운탕"]),
    ("고기/구이", ["구이", "삼겹살", "생고기", "한우", "곱창", "막창", "갈비", "불고기", "육회", "차돌"]),
    ("한식", ["한식", "국밥", "해장국", "백반", "정식", "찌개", "전골", "곰탕", "설렁탕", "육개장",
              "비빔밥", "보쌈", "족발", "수육", "삼계탕", "백숙", "닭볶음탕", "청국장", "된장", "순대", "추어탕"]),
    ("분식/면류", ["분식", "떡볶이", "칼국수", "국수", "냉면", "막국수", "만두", "라면", "우동", "쫄면"]),
]


def categorize(name, intro):
    text = f"{name} {intro or ''}"
    for label, keywords in CATEGORY_RULES:
        if any(k in text for k in keywords):
            return label
    return "기타"


def fetch(url, data=None):
    body = urllib.parse.urlencode(data).encode() if data else None
    req = urllib.request.Request(url, data=body)
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                return r.read().decode("utf-8")
        except Exception:
            time.sleep(1)
    return None


def collect_rcpn_nos():
    ids = []
    html1 = fetch(LIST_URL, {"currentPage": 1, "pageSize": 16, "viewType": "list", "searchTpbsCd": "HPTC006"})
    total_pages = int(re.search(r"\[1/(\d+) 페이지\]", html1).group(1))
    ids += re.findall(r"fn_goPage\('([^']+)','rcpnNo'", html1)
    print(f"음식점업 총 {total_pages}페이지")
    for page in range(2, total_pages + 1):
        page_html = fetch(LIST_URL, {"currentPage": page, "pageSize": 16, "viewType": "list", "searchTpbsCd": "HPTC006"})
        ids += re.findall(r"fn_goPage\('([^']+)','rcpnNo'", page_html)
        if page % 10 == 0:
            print(f"목록 {page}/{total_pages}페이지, 누적 {len(ids)}건")
        time.sleep(0.2)
    return ids


def text_of(pattern, s, flags=0):
    m = re.search(pattern, s, flags)
    return html.unescape(m.group(1)).strip() if m else None


def parse_detail(rcpn_no, page_html):
    name = text_of(r"<h6>([^<]+)</h6>", page_html)
    biz_type = text_of(r"업종</dt>\s*<dd>([^<]*)</dd>", page_html)
    opened_raw = text_of(r"창업일</dt>\s*<dd>([^<]*)</dd>", page_html)
    hours = text_of(r"영업시간</dt>\s*<dd>([^<]*)</dd>", page_html)
    phone = text_of(r"연락처</dt>\s*<dd>([^<]*)</dd>", page_html)
    address = text_of(r"주소</dt>\s*<dd>([^<]*)</dd>", page_html)
    homepage = text_of(r"홈페이지</dt>\s*<dd>(?:<a[^>]*>)?([^<]*)", page_html)
    intro = text_of(r"<h6>소개글</h6>\s*<div>\s*<p>([\s\S]*?)</p>", page_html)

    amenities = []
    info_start = page_html.find(">업종<")
    info_end = page_html.find("store_intro")
    if info_start != -1 and info_end != -1:
        info_section = page_html[info_start:info_end]
        ul_match = re.search(r"<ul>([\s\S]*?)</ul>", info_section)
        if ul_match:
            for li_class, label in re.findall(r'<li class="([^"]*)"><i[^>]*></i>([^<]+)</li>', ul_match.group(1)):
                if "on" in li_class.split():
                    amenities.append(label.strip())

    if not name or not address:
        return None

    opened = None
    if opened_raw:
        m = re.match(r"(\d{4})-(\d{2})-(\d{2})", opened_raw)
        if m:
            try:
                opened = date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
            except ValueError:
                opened = None

    years_open = (TODAY - opened).days // 365 if opened else None
    if years_open is not None and years_open >= 20:
        grade = "찐노포"
    elif years_open is not None and years_open >= 10:
        grade = "동네 터줏대감"
    else:
        grade = "찐노포"  # 창업일 파싱 실패 시에도 백년가게 인증 자체가 20년 이상 요건이므로 찐노포로 처리

    clean_intro = intro.replace("\n", " ").strip() if intro else None
    # 재수집 때마다 rcpnNo가 바뀔 수 있어, 즐겨찾기/방문기록 키가 안정적으로 유지되도록
    # 이름+주소 기반 해시를 id로 사용한다.
    stable_id = hashlib.md5((name + address).encode("utf-8")).hexdigest()[:12]

    return {
        "id": stable_id,
        "name": name,
        "address": address,
        "bizType": biz_type,
        "foodCategory": categorize(name, clean_intro),
        "openedDate": opened.isoformat() if opened else None,
        "yearsOpen": years_open,
        "grade": grade,
        "hours": hours or None,
        "phone": phone.replace(" ", "") if phone else None,
        "homepage": homepage or None,
        "amenities": amenities,
        "intro": clean_intro,
    }


def geocode(address):
    url = "https://dapi.kakao.com/v2/local/search/address.json?" + urllib.parse.urlencode({"query": address})
    req = urllib.request.Request(url, headers={"Authorization": f"KakaoAK {KAKAO_REST_KEY}"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                data = json.load(r)
            docs = data.get("documents")
            if not docs:
                return None
            doc = docs[0]
            return float(doc["y"]), float(doc["x"])
        except Exception:
            time.sleep(1)
    return None


def main():
    ids = collect_rcpn_nos()
    ids = list(dict.fromkeys(ids))
    print(f"수집된 매장 ID {len(ids)}건, 상세페이지 조회 시작")

    results = []
    skipped = 0
    for i, rcpn_no in enumerate(ids):
        detail_html = fetch(DETAIL_URL, {"rcpnNo": rcpn_no})
        if not detail_html:
            skipped += 1
            continue
        shop = parse_detail(rcpn_no, detail_html)
        if not shop:
            skipped += 1
            continue

        coord = geocode(shop["address"])
        if not coord:
            skipped += 1
            continue
        shop["lat"], shop["lng"] = round(coord[0], 6), round(coord[1], 6)
        results.append(shop)

        if (i + 1) % 50 == 0:
            print(f"{i + 1}/{len(ids)} 처리, 실패 {skipped}건")
        time.sleep(0.15)

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"{len(results)}건 저장 -> {OUT} (실패 {skipped}건 제외)")


if __name__ == "__main__":
    main()
