import json

SOURCES = ["data/노포_백년가게.json", "data/노포_오래가게.json"]
OUT = "data/노포.json"


def normalize(s):
    return (s or "").replace(" ", "").lower()


def load(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return []


def main():
    merged = {}  # id -> shop
    key_index = {}  # (normalized name, normalized address) -> id

    for path in SOURCES:
        for shop in load(path):
            dup_key = (normalize(shop["name"]), normalize(shop["address"]))
            existing_id = shop["id"] if shop["id"] in merged else key_index.get(dup_key)

            if existing_id:
                existing = merged[existing_id]
                for src in shop.get("source", []):
                    if src not in existing["source"]:
                        existing["source"].append(src)
                continue

            merged[shop["id"]] = shop
            key_index[dup_key] = shop["id"]

    results = list(merged.values())
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"{len(results)}건 병합 -> {OUT}")


if __name__ == "__main__":
    main()
