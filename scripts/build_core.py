# -*- coding: utf-8 -*-
"""核心统计：分期、体裁、产量分布、地理、唱和。"""
import os, re, json, math
import numpy as np
import pandas as pd
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dynasty import normalize, PERIOD_ORDER, PERIOD_YEAR

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
WEB = os.path.join(ROOT, "docs", "data")
os.makedirs(WEB, exist_ok=True)

GENRE_GROUP = {
    "律詩": "近體詩", "絶句": "近體詩", "排律": "近體詩",
    "古風": "古體詩", "樂府曲辭": "古體詩", "四言詩": "古體詩", "騷": "古體詩",
    "琴操": "古體詩", "鼓吹曲": "古體詩",
    "詞": "詞曲", "曲": "詞曲",
    "文": "文賦", "辭賦": "文賦", "贊": "文賦", "偈頌": "文賦", "聯": "文賦", "句": "文賦",
    "六言詩": "其他", "": "其他",
}
GENRE_ORDER = ["律詩", "絶句", "古風", "文", "詞", "排律", "曲", "聯", "四言詩",
               "偈頌", "樂府曲辭", "句", "六言詩", "辭賦", "贊", "騷", "琴操", "鼓吹曲"]


def gini(x):
    x = np.sort(np.asarray(x, dtype=float))
    n = len(x)
    if n == 0 or x.sum() == 0:
        return 0.0
    idx = np.arange(1, n + 1)
    return float((2 * (idx * x).sum()) / (n * x.sum()) - (n + 1) / n)


def entropy(counts):
    c = np.asarray(counts, dtype=float)
    p = c / c.sum()
    p = p[p > 0]
    return float(-(p * np.log(p)).sum())


def lorenz(x, points=101):
    x = np.sort(np.asarray(x, dtype=float))
    c = np.cumsum(x)
    n = len(x)
    xs = np.linspace(0, 1, points)
    ys = np.interp(xs, np.concatenate([[0], np.arange(1, n + 1) / n]), np.concatenate([[0], c / c[-1]]))
    return [{"p": round(float(a), 4), "c": round(float(b), 4)} for a, b in zip(xs, ys)]


def powerlaw_fit(counts):
    x = np.sort(np.asarray(counts, dtype=float))[::-1]
    x = x[x > 0]
    ranks = np.arange(1, len(x) + 1)
    lim = min(len(x), 30000)
    lr = np.log(ranks[:lim]); lc = np.log(x[:lim])
    b, a = np.polyfit(lr, lc, 1)
    pred = a + b * lr
    ss_res = ((lc - pred) ** 2).sum(); ss_tot = ((lc - lc.mean()) ** 2).sum()
    r2 = 1 - ss_res / ss_tot
    # Hill estimator（上尾指数）
    k = min(2000, len(x) - 1)
    xk = x[k]
    hill = k / np.log(x[:k] / xk).sum() if k > 0 else float("nan")
    return {"slope": round(float(b), 4), "intercept": round(float(a), 4),
            "alpha": round(float(-b), 4), "r2": round(float(r2), 4),
            "hill_alpha": round(float(hill), 4), "k": int(k), "n": int(len(x))}


def main():
    p = pd.read_csv(os.path.join(DATA, "persons.csv"))
    d = pd.read_csv(os.path.join(DATA, "poems.csv"), dtype=str, keep_default_na=False)
    print(p.shape, d.shape)

    norm = {lab: normalize(lab) for lab in p["dynasty"].unique()}
    p["period"] = p["dynasty"].map(lambda x: norm[x][0])
    p["canon"] = p["dynasty"].map(lambda x: norm[x][1])
    p["mid"] = p["dynasty"].map(lambda x: norm[x][4])
    d["period"] = d["dynasty"].map(lambda x: norm[x][0])
    d["canon"] = d["dynasty"].map(lambda x: norm[x][1])
    d["mid"] = d["dynasty"].map(lambda x: norm[x][4])
    d["genre"] = d["genre"].fillna("").replace("", "其他")
    d["group"] = d["genre"].map(GENRE_GROUP).fillna("其他")
    d["title_len"] = d["title"].str.replace(r"[^\u3400-\u9fff]", "", regex=True).str.len()
    d["harmony"] = d["title"].str.contains(r"和.{1,12}[韵韻]|次.{1,12}[韵韻]|步.{0,6}[韵韻]|用.{1,12}[韵韻]|酬|贈|赠|寄.{1,8}(?:詩|诗|友|君)|答.{1,8}(?:見|见)?(?:寄|贈|赠)", regex=True, na=False)

    # ---------- 分期 ----------
    order = [x for x in PERIOD_ORDER if x in set(p["period"])]
    periods = []
    for per in order:
        pp = p[p["period"] == per]
        dd = d[d["period"] == per]
        gc = dd["genre"].value_counts()
        periods.append({
            "period": per, "year": PERIOD_YEAR[per],
            "poets": int(len(pp)), "poems": int(pp["declared_count"].sum()), "parsed": int(len(dd)),
            "unique_titles": int(dd["title"].nunique()),
            "avg_poems": round(float(pp["declared_count"].mean()), 2),
            "median_poems": float(pp["declared_count"].median()),
            "gini": round(gini(pp["declared_count"].values), 4),
            "genre_entropy": round(entropy(gc.values), 4),
            "genre_effective": round(float(math.exp(entropy(gc.values))), 3),
            "harmony_rate": round(float(dd["harmony"].mean()), 4),
            "genres": {g: int(gc.get(g, 0)) for g in GENRE_ORDER},
        })

    # ---------- 朝代（归一名） ----------
    grp = p.groupby("canon").agg(poets=("id", "size"), poems=("declared_count", "sum"),
                                 mid=("mid", "median"), period=("period", "first")).reset_index()
    grp = grp[grp.poets >= 15].sort_values("poems", ascending=False)
    dynasties = grp.head(28).to_dict("records")
    for r in dynasties:
        r["poets"] = int(r["poets"]); r["poems"] = int(r["poems"]); r["mid"] = float(r["mid"])

    # ---------- 体裁 ----------
    gcount = d["genre"].value_counts()
    genres = [{"genre": g, "count": int(gcount.get(g, 0)),
               "group": GENRE_GROUP.get(g, "其他"),
               "poets": int(d[d.genre == g]["person_id"].nunique())} for g in GENRE_ORDER if gcount.get(g, 0)]

    # ---------- 产量分布 ----------
    counts = p["declared_count"].values
    counts_sorted = np.sort(counts)[::-1]
    step = max(1, len(counts_sorted) // 4000)
    rank_points = [{"r": int(i), "n": int(counts_sorted[i - 1])} for i in range(1, len(counts_sorted) + 1, step)]
    hist_bins = [1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233, 377, 610, 987, 1600, 3400, 8000, 20000, 60000]
    hist = []
    for i in range(len(hist_bins) - 1):
        lo, hi = hist_bins[i], hist_bins[i + 1]
        hist.append({"lo": lo, "hi": hi, "count": int(((counts >= lo) & (counts < hi)).sum())})
    hist.append({"lo": hist_bins[-2], "hi": int(counts.max()) + 1,
                 "count": int((counts >= hist_bins[-2]).sum())})
    top_poets = p.sort_values(["declared_count", "id"], ascending=[False, True]).head(40)
    productivity = {
        "rankSize": rank_points,
        "lorenz": lorenz(counts),
        "gini": round(gini(counts), 4),
        "fit": powerlaw_fit(counts),
        "histogram": hist,
        "shareTop1": round(float(counts_sorted[:475].sum() / counts.sum()), 4),
        "shareTop10pct": round(float(counts_sorted[:int(len(counts_sorted) * 0.1)].sum() / counts.sum()), 4),
        "thresholds": [{"k": k, "share": round(float(counts_sorted[:k].sum() / counts.sum()), 4)}
                       for k in (10, 100, 1000, 5000)],
        "top": [{"id": int(r.id), "name": r.name, "dynasty": r.dynasty, "period": r.period,
                 "poems": int(r.declared_count)} for r in top_poets.itertuples()],
    }

    # ---------- 朝代 × 体裁热力 ----------
    top_canon = [x["canon"] for x in dynasties[:20]]
    heat = []
    sub = d[d.canon.isin(top_canon)]
    piv = sub.pivot_table(index="canon", columns="genre", values="title", aggfunc="size", fill_value=0)
    piv = piv.reindex(index=top_canon, columns=[g for g in GENRE_ORDER if g in piv.columns])
    mids = {r["canon"]: r["mid"] for r in dynasties}
    heat_rows = [{"dynasty": i, "mid": mids.get(i, 0), "values": [int(v) for v in piv.loc[i].values],
                  "total": int(piv.loc[i].sum())} for i in piv.index]
    heat_rows.sort(key=lambda r: r["mid"])
    heat_genres = list(piv.columns)

    # ---------- 唱和 / 集句 ----------
    harmony_by_period = [{"period": r["period"], "rate": r["harmony_rate"]} for r in periods]
    jiju = int(p["jiju"].sum()); buyun = int(p["buyun"].sum())

    # ---------- 标题长度 ----------
    bins = list(range(0, 41, 2))
    len_hist = []
    for per in order:
        v = d[d.period == per]["title_len"].values
        v = np.clip(v, 0, 40)
        h, _ = np.histogram(v, bins=bins)
        len_hist.append({"period": per, "data": [int(x) for x in h],
                         "mean": round(float(d[d.period == per]["title_len"].mean()), 2)})

    # ---------- 体裁大类 ----------
    groups = d["group"].value_counts()
    genre_groups = [{"group": k, "count": int(v)} for k, v in groups.items()]

    summary = {
        "persons": int(len(p)), "poems": int(p["declared_count"].sum()), "parsed": int(len(d)),
        "uniqueTitles": int(d["title"].nunique()),
        "genres": int(d["genre"].nunique()), "dynastyLabels": int(p["dynasty"].nunique()),
        "periods": len(order),
        "jiju": jiju, "buyun": buyun,
        "avgPoems": round(float(p["declared_count"].mean()), 2),
        "medianPoems": float(p["declared_count"].median()),
        "maxPoems": int(p["declared_count"].max()),
        "gini": round(gini(p["declared_count"].values), 4),
        "topGenre": gcount.index[0], "topGenreCount": int(gcount.iloc[0]),
        "harmonyRate": round(float(d["harmony"].mean()), 4),
        "yearSpan": [int(p["mid"].min()), int(p["mid"].max())],
    }

    out = {"summary": summary, "periods": periods, "dynasties": dynasties, "genres": genres,
           "productivity": productivity, "heatmap": {"rows": heat_rows, "genres": heat_genres},
           "harmony": {"byPeriod": harmony_by_period, "jiju": jiju, "buyun": buyun},
           "titleLength": {"bins": bins, "byPeriod": len_hist}, "genreGroups": genre_groups}
    with open(os.path.join(WEB, "core.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
    p["harmony"] = p["id"].map(d.groupby("person_id")["harmony"].mean()).fillna(0)
    p.to_csv(os.path.join(DATA, "persons_enriched.csv"), index=False, encoding="utf-8-sig")
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    print("periods:", [(x["period"], x["poets"], x["poems"]) for x in periods])
    print("fit:", productivity["fit"], "gini:", productivity["gini"])
    print("harmony rate:", summary["harmonyRate"])


if __name__ == "__main__":
    main()
