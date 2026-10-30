# -*- coding: utf-8 -*-
"""由分析结果导出可下载的 CSV 数据表（docs/tables/）。"""
import os, csv, json
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB = os.path.join(ROOT, "docs", "data")
OUT = os.path.join(ROOT, "docs", "tables")
os.makedirs(OUT, exist_ok=True)

J = {n: json.load(open(os.path.join(WEB, n + ".json"), encoding="utf-8"))
     for n in ("core", "text", "topics", "geo", "poets", "net", "simnet", "extra")}


def write(name, header, rows):
    with open(os.path.join(OUT, name), "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
    print(name, len(rows))


# 01 分期统计
P = J["core"]["periods"]
write("01_分期统计.csv",
      ["时期", "代表性年份", "诗人数", "诗作数", "独立诗题", "人均诗作", "中位数", "基尼系数",
       "体裁熵", "等效体裁数", "唱和题名率", "律诗", "绝句", "古风", "文", "词", "排律", "曲", "联"],
      [[p["period"], p["year"], p["poets"], p["poems"], p["unique_titles"], p["avg_poems"],
        p["median_poems"], p["gini"], p["genre_entropy"], p["genre_effective"], p["harmony_rate"],
        p["genres"].get("律詩", 0), p["genres"].get("絶句", 0), p["genres"].get("古風", 0),
        p["genres"].get("文", 0), p["genres"].get("詞", 0), p["genres"].get("排律", 0),
        p["genres"].get("曲", 0), p["genres"].get("聯", 0)] for p in P])

# 02 体裁
write("02_体裁统计.csv", ["体裁", "大类", "篇数", "占比", "作者数"],
      [[g["genre"], g["group"], g["count"], round(g["count"] / J["core"]["summary"]["poems"], 5), g["poets"]]
       for g in J["core"]["genres"]])

# 03 Top500
pp = pd.read_csv(os.path.join(ROOT, "data", "persons_enriched.csv"))
top = pp.sort_values("declared_count", ascending=False).head(500)
write("03_诗人产量Top500.csv", ["人物ID", "姓名", "朝代", "分期", "诗作数", "已解析诗题", "独立诗题", "集句诗", "步韵诗", "唱和率"],
      [[int(r.id), r.name, r.dynasty, r.period, int(r.declared_count), int(r.poem_count), int(r.unique_titles),
        int(r.jiju), int(r.buyun), round(float(r.harmony), 4)] for r in top.itertuples()])

# 04 高频词
write("04_高频词Top300.csv", ["词", "频次"], [[w["w"], w["f"]] for w in J["text"]["wordsTop"][:300]])

# 05 分期特征词
rows = []
for per, rec in J["text"]["periodTerms"].items():
    for r in rec["pos"]:
        rows.append([per, r["w"], r["z"], r["f"], r["lift"]])
    for r in rec["neg"]:
        rows.append([per, r["w"], r["z"], r["f"], r["lift"]])
write("05_分期特征词.csv", ["时期", "词", "z值", "该期频次", "相对倍数"], rows)

# 06 主题
rows = []
for i, t in enumerate(J["topics"]["topics"]):
    for j, w in enumerate(t["words"]):
        rows.append([i, w["w"], round(w["p"], 6), j + 1, t["share"], t["coherence"]])
write("06_主题模型_词分布.csv", ["主题编号", "词", "p(词|主题)", "排名", "主题占比", "一致性"], rows)

# 07 地名
write("07_地名统计.csv", ["地名", "今省区/区域", "出现次数", "占比"],
      [[p["place"], p["region"], p["count"], round(p["count"] / J["core"]["summary"]["poems"], 6)]
       for p in J["geo"]["topPlaces"]])

# 08 诗人档案
rows = []
for p in J["poets"]["profiles"]:
    gs = "；".join(f"{k}:{v}" for k, v in p["genres"].items())
    ws = "、".join(w["w"] for w in p["words"][:8])
    rows.append([p["id"], p["name"], p["dynasty"], p["period"], p["poems"], gs, ws, p["harmony"]])
write("08_诗人档案Top1200.csv", ["人物ID", "姓名", "朝代", "分期", "诗作数", "体裁结构", "常用词", "唱和率"], rows)

# 09 地名 × 时期
per = J["geo"]["periods"]
write("09_地名时期分布.csv", ["地名"] + per,
      [[p["place"]] + [p["byPeriod"].get(q, 0) for q in per] for p in J["geo"]["topPlaces"]])

# 10 主题 × 时期
write("10_主题时期分布.csv", ["主题编号"] + [p["period"] for p in P],
      [[i] + [J["topics"]["byPeriod"][i][p["period"]] for p in P] for i in range(J["topics"]["K"])])
print("done")
