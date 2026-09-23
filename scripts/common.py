import json
import time
import urllib.parse
import urllib.request

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


DEFAULT_HEADERS = {"User-Agent": "nopo-matjip-map/1.0 (https://github.com/cmkim84-boop/nopo-matjip-map)"}


def fetch(url, data=None, headers=None):
    body = urllib.parse.urlencode(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers={**DEFAULT_HEADERS, **(headers or {})})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                return r.read().decode("utf-8")
        except Exception:
            time.sleep(1)
    return None


def geocode_address(address, kakao_key):
    """주소 문자열 → 좌표. 정확한 도로명/지번 주소가 있을 때 사용."""
    url = "https://dapi.kakao.com/v2/local/search/address.json?" + urllib.parse.urlencode({"query": address})
    req = urllib.request.Request(url, headers={"Authorization": f"KakaoAK {kakao_key}"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                data = json.load(r)
            docs = data.get("documents")
            if not docs:
                return None
            doc = docs[0]
            return {"lat": float(doc["y"]), "lng": float(doc["x"])}
        except Exception:
            time.sleep(1)
    return None


def geocode_keyword(query, kakao_key):
    """가게명 등 키워드 → 장소 검색. 정확한 주소가 없을 때 최선의 추정으로 사용(오매칭 가능)."""
    url = "https://dapi.kakao.com/v2/local/search/keyword.json?" + urllib.parse.urlencode({"query": query})
    req = urllib.request.Request(url, headers={"Authorization": f"KakaoAK {kakao_key}"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                data = json.load(r)
            docs = data.get("documents")
            if not docs:
                return None
            doc = docs[0]
            return {
                "lat": float(doc["y"]),
                "lng": float(doc["x"]),
                "address": doc.get("road_address_name") or doc.get("address_name"),
            }
        except Exception:
            time.sleep(1)
    return None
