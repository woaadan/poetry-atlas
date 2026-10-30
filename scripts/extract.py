# -*- coding: utf-8 -*-
"""Extract 人物诗作表.xlsx into tidy tables for the Poetry Atlas."""
import os, re, json, csv, unicodedata
import openpyxl

SRC = r"C:\Users\11487\Desktop\数字人文\文本挖掘\人物诗作表.xlsx"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data")
os.makedirs(OUT, exist_ok=True)

GENRES = ["樂府曲辭", "四言詩", "六言詩", "鼓吹曲", "排律", "偈頌", "辭賦", "琴操",
          "律詩", "絶句", "古風", "聯", "詞", "曲", "文", "贊", "騷", "句"]
GENRE_FIX = {"絶": "絶句", "古": "古風", "绝句": "絶句", "律诗": "律詩", "古风": "古風"}


def split_genre(seg: str):
    seg = seg.strip()
    if "·" not in seg:
        return seg, ""
    title, tail = seg.rsplit("·", 1)
    tail = tail.strip()
    if tail in GENRES or tail in GENRE_FIX:
        return title.strip(), tail
    # 标题本身含「·」：整段当标题
    return seg, ""


wb = openpyxl.load_workbook(SRC, read_only=True, data_only=True)
ws = wb.worksheets[0]
rows = list(ws.iter_rows(values_only=True))
wb.close()
print("rows:", len(rows))

persons, poems = [], []
for r in rows[1:]:
    if not r or (r[0] is None and r[1] is None):
        continue
    pid, name, dyn, count, plist, jiju, buyun, dist = (list(r) + [None] * 8)[:8]
    name = str(name or "").strip()
    dyn = str(dyn or "").strip()
    plist = plist or ""
    recs = []
    for p in re.split(r"[；;]", plist):
        if not p.strip():
            continue
        title, genre = split_genre(p)
        genre = GENRE_FIX.get(genre, genre)
        title = re.sub(r"\s+", " ", title).strip()
        if title:
            recs.append((title, genre))
    persons.append({
        "id": pid, "name": name, "dynasty": dyn, "declared_count": count,
        "poem_count": len(recs), "unique_titles": len(set(t for t, _ in recs)),
        "jiju": 1 if jiju not in (None, "", 0) else 0,
        "buyun": 1 if buyun not in (None, "", 0) else 0,
        "dist_raw": str(dist or "").strip(),
    })
    for title, genre in recs:
        poems.append((pid, name, dyn, title, genre))

print("persons:", len(persons), "poems:", len(poems))

with open(os.path.join(OUT, "persons.csv"), "w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(persons[0].keys()))
    w.writeheader(); w.writerows(persons)
with open(os.path.join(OUT, "poems.csv"), "w", encoding="utf-8-sig", newline="") as f:
    w = csv.writer(f)
    w.writerow(["person_id", "name", "dynasty", "title", "genre"])
    w.writerows(poems)

from collections import Counter
g = Counter(x[4] for x in poems)
print("genre:", g.most_common(25))
print("empty genre:", g.get("", 0))
json.dump({"persons": len(persons), "poems": len(poems), "genre": g.most_common(30)},
          open(os.path.join(OUT, "_audit.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
