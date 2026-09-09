import csv
import json
from datetime import date

from pyproj import Transformer

SRC = "data/식품_일반음식점_경기시흥시.csv"
OUT = "data/노포_시흥시.json"

# 좌표정보(X,Y)는 Bessel 중부원점TM(EPSG:5174) -> 카카오맵용 WGS84(EPSG:4326)로 변환
to_wgs84 = Transformer.from_crs("EPSG:5174", "EPSG:4326", always_xy=True)

TODAY = date(2026, 9, 9)


def grade(years):
    if years >= 20:
        return "찐노포"
    if years >= 10:
        return "동네 터줏대감"
    return None


def parse_date(s):
    s = s.strip()
    if not s:
        return None
    try:
        return date.fromisoformat(s[:10])
    except ValueError:
        return None


rows = []
with open(SRC, encoding="cp949", newline="") as f:
    for row in csv.DictReader(f):
        if row["영업상태명"] != "영업/정상":
            continue

        opened = parse_date(row["인허가일자"])
        if not opened:
            continue

        years = (TODAY - opened).days // 365
        g = grade(years)
        if not g:
            continue

        x, y = row["좌표정보(X)"].strip(), row["좌표정보(Y)"].strip()
        if not x or not y:
            continue
        lng, lat = to_wgs84.transform(float(x), float(y))

        rows.append({
            "name": row["사업장명"],
            "address": row["도로명주소"].strip() or row["지번주소"].strip(),
            "category": row["위생업태명"],
            "openedDate": opened.isoformat(),
            "yearsOpen": years,
            "grade": g,
            "phone": row["전화번호"].strip() or None,
            "lat": round(lat, 6),
            "lng": round(lng, 6),
        })

with open(OUT, "w", encoding="utf-8") as f:
    json.dump(rows, f, ensure_ascii=False, indent=2)

print(f"{len(rows)}건 저장 -> {OUT}")
