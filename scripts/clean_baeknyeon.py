import csv
import glob
import json
import os
import sys
import time
import urllib.parse
import urllib.request

SRC = glob.glob("C:/Users/user/Downloads/*백년가게*.csv")[0]
OUT = "data/노포_백년가게.json"
KAKAO_REST_KEY = os.environ.get("KAKAO_REST_KEY")
if not KAKAO_REST_KEY:
    sys.exit("환경변수 KAKAO_REST_KEY를 설정하세요 (카카오 개발자센터 > 플랫폼 키 > REST API 키)")

# 백년가게 데이터는 개업연도/업력이 없고, 음식점 외 업종(이미용/철물/서적 등)도
# 섞여 있어 아래 키워드에 해당하는 비-음식점 업종은 제외한다.
EXCLUDE = [
    "가구", "가발", "가전", "수리", "철물", "안전용품", "악기", "인쇄", "문구", "서적", "서점",
    "도서", "교구", "교육", "학원", "미용", "이용", "이미용", "헤어", "피부관리", "화장품",
    "안경", "렌즈", "시계", "귀금속", "보청기", "양복", "한복", "의류", "포목", "주단", "신발",
    "구두", "모자", "가방", "잡화", "침구", "이불", "열쇠", "도장", "인장", "농약", "비료",
    "종묘", "농자재", "곡물", "양곡", "참기름", "들기름", "고춧가루", "젓갈", "건어물",
    "냉동수산물", "수산물 도매", "수산물중개", "정육", "식육판매", "식육전문", "과일류", "청과",
    "화훼", "생화", "화원", "꽃집", "꽃배달", "문방사우", "사진", "웨딩", "세탁", "숙박", "여관",
    "자동차", "오토바이", "자전거", "전자제품", "전자부품", "의료",
    "액세서리", "공예", "도자기", "자기타일", "실크원단", "원단", "한지", "죽제품", "완구",
    "스포츠용품", "운동용품", "운동구", "체육시설", "음향", "음반", "전동기", "모터", "펌프",
    "자동판매기", "사무기기", "사무용가구", "금고", "광고물", "간판", "인테리어", "도배", "장판",
    "방수", "건축자재", "건축재료", "목공", "목재", "위생도기", "타일", "벽지", "바닥재",
    "상패", "명찰", "보험", "태권도", "평생교육", "패션학원", "종합디자인", "종합인테리어",
    "토탈미용", "인삼제품", "홍삼음료", "한약", "선박부품", "관상어", "수족관", "귀금속/시계",
    "그릇", "대중탕", "뜨개", "정장", "방화문", "부자재", "소품", "수예품",
    "슈퍼마켓", "양돈", "유리제품", "의복", "장화", "주방기기", "지물포", "진열대", "농업 약품",
]


def is_food(biz):
    return not any(k in biz for k in EXCLUDE)


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


with open(SRC, encoding="cp949", newline="") as f:
    rows = list(csv.DictReader(f))

rows = [r for r in rows if is_food(r["주요사업"])]
print(f"음식점 필터링: {len(rows)}건")

results = []
skipped = 0
for i, r in enumerate(rows):
    base_addr = r["기본주소"].strip()
    detail = r["상세주소"].strip()
    coord = geocode(base_addr)
    if not coord:
        skipped += 1
        continue
    lat, lng = coord
    results.append({
        "name": r["업체명"],
        "address": (base_addr + " " + detail).strip(),
        "category": r["주요사업"],
        "grade": "찐노포",
        "phone": r["연락처"].strip() or None,
        "lat": round(lat, 6),
        "lng": round(lng, 6),
    })
    if (i + 1) % 100 == 0:
        print(f"{i + 1}/{len(rows)} 처리, 지오코딩 실패 {skipped}건")
    time.sleep(0.05)

with open(OUT, "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print(f"{len(results)}건 저장 -> {OUT} (지오코딩 실패 {skipped}건 제외)")
