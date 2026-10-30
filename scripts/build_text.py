# -*- coding: utf-8 -*-
"""文本挖掘第二阶段：词频、时期特征词（log-odds）、LDA 主题、共现网络、
诗人相似网络、题名地理、诗人档案与词条生命周期。"""
import os, re, json, math, pickle, random
from collections import Counter, defaultdict
import numpy as np
import pandas as pd
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from places import PLACES
from dynasty import normalize, PERIOD_ORDER

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
WEB = os.path.join(ROOT, "docs", "data")
CACHE = os.path.join(DATA, "cache")
os.makedirs(WEB, exist_ok=True)
RNG = np.random.default_rng(20251030)
random.seed(20251030)

GENRE_WORDS = {"絶句", "絕句", "绝句", "律詩", "律诗", "古風", "古风", "排律", "樂府", "乐府",
               "聯", "联", "詞", "词", "曲", "賦", "赋", "吟", "行", "篇", "首", "章", "二首",
               "三首", "四首", "五首", "十首", "其一", "其二", "組詩", "组诗"}
STOPW = {"先生", "學士", "学士", "侍郎", "太守", "尚書", "尚书", "相公", "諸公", "诸公", "大夫",
         "進士", "进士", "侍御", "明府", "秀才", "副使", "夫人", "使君", "同年", "不允", "賦此",
         "赋此", "此題", "此韵", "此韻", "原韻", "原韵", "前韻", "前韵", "元韻", "元韵",
         "次韻", "次韵", "用韻", "用韵", "疊韻", "叠韵", "月日", "詩首", "诗首", "偈頌", "偈颂",
         "二首", "三首", "四首", "五首", "六首", "七首", "八首", "九首", "十首", "其四", "其五",
         "郎中", "員外", "员外", "待制", "觀文", "观文", "直學士", "待講", "待讲",
         "辭免", "辞免", "恩命", "特授", "太常", "方伯", "提舉", "提举", "提刑",
         "轉運", "转运", "通判", "樞密", "枢密", "吏部", "禮部", "礼部", "兵部",
         "刑部", "工部", "户部", "戶部", "給事", "给事", "修撰", "資政", "资政",
         "御史", "主簿", "判官", "寺丞", "大理", "比部", "員外郎", "员外郎", "少卿",
         "博士", "教授", "承旨", "中丞", "舍人", "常侍", "參政", "参政", "節度",
         "节度", "觀察", "观察", "制置", "安撫", "安抚", "轉運使", "宣徽", "金紫"}


# ---------------- 工具 ----------------
def merge_bigrams(tokens):
    """把连续的未登录单字合并为二字组，保证全语料可覆盖。"""
    out = []
    buf = []
    for w in tokens:
        if len(w) == 1:
            buf.append(w)
            continue
        if buf:
            out.extend(_pairs(buf)); buf = []
        out.append(w)
    if buf:
        out.extend(_pairs(buf))
    return out


def _pairs(chars):
    return ["".join(chars[i:i + 2]) for i in range(0, len(chars) - 1, 2)] + ([chars[-1]] if len(chars) % 2 else [])


def entropy(p):
    p = np.asarray([x for x in p if x > 0], dtype=float)
    return float(-(p * np.log(p)).sum())


def label_propagation(nodes, adj, iters=40):
    comm = {n: i for i, n in enumerate(nodes)}
    for _ in range(iters):
        changed = 0
        for n in nodes:
            if not adj[n]:
                continue
            c = Counter(comm[m] for m in adj[n])
            best = max(c.items(), key=lambda x: (x[1], -x[0]))[0]
            if comm[n] != best:
                comm[n] = best; changed += 1
        if not changed:
            break
    remap, out = {}, {}
    for n in nodes:
        if comm[n] not in remap:
            remap[comm[n]] = len(remap)
        out[n] = remap[comm[n]]
    return out


def fr_layout(nodes, edges, iters=500, seed=7):
    """Fruchterman–Reingold 力导向布局（单位方格内的标准实现）。"""
    n = len(nodes)
    if n <= 2:
        return {v: [round(-1 + 2 * i / max(n, 1), 4), 0.0] for i, v in enumerate(nodes)}
    idx = {v: i for i, v in enumerate(nodes)}
    rng = np.random.default_rng(seed)
    pos = rng.uniform(-0.5, 0.5, (n, 2))
    k = 1.0 / math.sqrt(n)
    nbr = defaultdict(list)
    for a, b, wt in edges:
        nbr[idx[a]].append((idx[b], wt)); nbr[idx[b]].append((idx[a], wt))
    t = 0.1
    for it in range(iters):
        diff = pos[:, None, :] - pos[None, :, :]
        dist = np.sqrt((diff ** 2).sum(2)) + 1e-9
        np.fill_diagonal(dist, 1e9)
        rep = (k * k / (dist * dist))[:, :, None] * diff
        disp = rep.sum(1)
        for a, lst in nbr.items():
            for b, wt in lst:
                d = pos[a] - pos[b]
                dd = np.linalg.norm(d) + 1e-9
                f = (dd * dd / k) * (0.6 + 0.4 * min(wt / 2.0, 1.0))
                disp[a] -= d / dd * f
        ln = np.linalg.norm(disp, axis=1) + 1e-12
        step = np.minimum(ln, t)
        pos += disp / ln[:, None] * step[:, None]
        t = max(0.1 * (1 - it / iters), 0.003)
    # 用 98 分位数缩放，避免离群点压缩主体
    scale = np.percentile(np.abs(pos), 98) + 1e-9
    pos = np.clip(pos / scale, -1, 1)
    return {nodes[i]: [round(float(pos[i, 0]), 4), round(float(pos[i, 1]), 4)] for i in range(n)}


# ---------------- LDA ----------------
def lda(docs, K=10, alpha=0.15, beta=0.01, iters=45, seed=1):
    vocab = sorted({w for d in docs for w in d})
    w2i = {w: i for i, w in enumerate(vocab)}
    V = len(vocab)
    enc = [np.array([w2i[w] for w in d], dtype=np.int32) for d in docs]
    D = len(enc)
    rng = np.random.default_rng(seed)
    nzw = np.zeros((K, V), dtype=np.int32)
    ndz = np.zeros((D, K), dtype=np.int32)
    nz = np.zeros(K, dtype=np.int32)
    zs = []
    for d, toks in enumerate(enc):
        z = rng.integers(0, K, len(toks))
        zs.append(z)
        for t, zz in zip(toks, z):
            nzw[zz, t] += 1; ndz[d, zz] += 1; nz[zz] += 1
    for it in range(iters):
        for d, toks in enumerate(enc):
            for i in range(len(toks)):
                t = toks[i]; z = zs[d][i]
                nzw[z, t] -= 1; ndz[d, z] -= 1; nz[z] -= 1
                p = (nzw[:, t] + beta) * (ndz[d] + alpha) / (nz + beta * V)
                p = p / p.sum()
                zz = int(rng.choice(K, p=p))
                zs[d][i] = zz
                nzw[zz, t] += 1; ndz[d, zz] += 1; nz[zz] += 1
        print("  lda iter", it + 1, "done", flush=True)
    phi = (nzw + beta) / (nzw.sum(1, keepdims=True) + beta * V)
    theta = (ndz + alpha) / (ndz.sum(1, keepdims=True) + alpha * K)
    return vocab, phi, theta, enc


def coherence(enc, phi, vocab, topn=10):
    """UMass 一致性：以整数词 id 计文档频次与共现频次。"""
    df = Counter()
    co = Counter()
    for toks in enc:
        s = list(dict.fromkeys(toks.tolist()))
        for w in s:
            df[w] += 1
        for i in range(len(s)):
            for j in range(i + 1, len(s)):
                a, b = sorted((s[i], s[j]))
                co[(a, b)] += 1
    scores = []
    for k in range(phi.shape[0]):
        top = np.argsort(phi[k])[::-1][:topn]
        sc = 0.0; cnt = 0
        for i in range(1, len(top)):
            for j in range(i):
                a, b = sorted((int(top[i]), int(top[j])))
                sc += math.log((co[(a, b)] + 1) / (df[b] + 1)); cnt += 1
        scores.append(sc / max(cnt, 1))
    return scores, df, co


def main():
    p = pd.read_csv(os.path.join(DATA, "persons_enriched.csv"))
    d = pd.read_csv(os.path.join(DATA, "poems.csv"), dtype=str, keep_default_na=False)
    d["genre"] = d["genre"].fillna("").replace("", "其他")
    pmap = p.set_index("id")[["period", "canon", "mid"]].to_dict("index")
    pmid2name = p.set_index("id")["name"].to_dict()
    pid_arr = d["person_id"].astype(int).values
    periods = pd.Series([pmap[i]["period"] for i in pid_arr])
    mids = pd.Series([pmap[i]["mid"] for i in pid_arr])

    toks = pickle.load(open(os.path.join(CACHE, "tokens.pkl"), "rb"))
    print("tokens loaded", len(toks))
    docs = [[w for w in t if len(w) >= 2 and w not in GENRE_WORDS and w not in STOPW] for t in toks]
    with open(os.path.join(CACHE, "docs.pkl"), "wb") as f:
        pickle.dump(docs, f, protocol=4)

    cnt = Counter(w for t in docs for w in t)
    good = [(w, c) for w, c in cnt.items() if len(w) >= 2 and c >= 5]
    good.sort(key=lambda x: -x[1])
    print("vocab:", len(good), "top:", good[:20])

    # ---------- 词频 ----------
    words_top = [{"w": w, "f": int(c)} for w, c in good[:120]]
    chars = Counter(ch for t in toks for ch in t if len(ch) == 1)
    chars_top = [{"c": k, "f": int(v)} for k, v in chars.most_common(100)]

    # ---------- 时期特征词（log-odds + informative Dirichlet prior）----------
    per_idx = periods.values
    periods_list = [x for x in PERIOD_ORDER if (per_idx == x).any()]
    poetic = d["genre"].isin({"律詩", "絶句", "古風", "排律", "四言詩", "六言詩",
                              "樂府曲辭", "騷", "詞", "曲", "琴操", "鼓吹曲"}).values
    per_cnt = {x: Counter() for x in periods_list}
    for i, x in enumerate(per_idx):
        if poetic[i]:
            per_cnt[x].update(docs[i])
    N = {x: sum(per_cnt[x].values()) for x in periods_list}
    Nall = sum(N.values())
    term_tot = Counter()
    for x in periods_list:
        term_tot.update(per_cnt[x])
    alpha0 = 2500.0
    per_terms = {}
    for x in periods_list:
        rest = Counter()
        for y in periods_list:
            if y != x:
                rest.update(per_cnt[y])
        Nr = Nall - N[x]
        rows = []
        for w, tot in term_tot.items():
            if tot < 80 or len(w) < 2:
                continue
            yp, yr = per_cnt[x].get(w, 0), rest.get(w, 0)
            if yp < 8:
                continue
            ai = alpha0 * (yp + yr) / Nall
            dp = math.log((yp + ai) / (N[x] + alpha0 - yp - ai))
            dr = math.log((yr + ai) / (Nr + alpha0 - yr - ai))
            delta = dp - dr
            var = 1.0 / (yp + ai) + 1.0 / (yr + ai)
            rows.append({"w": w, "z": round(delta / math.sqrt(var), 2), "f": int(yp),
                         "lift": round(math.exp(delta), 2)})
        rows.sort(key=lambda r: -r["z"])
        per_terms[x] = {"pos": rows[:18], "neg": rows[-10:][::-1]}

    # ---------- LDA（带缓存，便于反复调试下游）----------
    docs_ids = [i for i, t in enumerate(docs)
                if poetic[i] and sum(1 for w in t if len(w) >= 2) >= 2]
    print("lda candidate docs:", len(docs_ids))
    lda_cache = os.path.join(CACHE, "lda.pkl")
    K = 10
    if os.path.exists(lda_cache) and not os.environ.get("REFRESH_LDA"):
        sample_ids, vocab, phi, theta, enc, coh = pickle.load(open(lda_cache, "rb"))
        print("lda loaded from cache:", phi.shape)
    else:
        sample_ids = RNG.choice(docs_ids, size=min(80000, len(docs_ids)), replace=False)
        sample_txt = [docs[i] for i in sample_ids]
        vocab, phi, theta, enc = lda(sample_txt, K=K, iters=35)
        coh, df, co = coherence(enc, phi, vocab, topn=10)
        pickle.dump((sample_ids, vocab, phi, theta, enc, coh), open(lda_cache, "wb"), protocol=4)
    print("coherence:", [round(x, 2) for x in coh])
    topic_labels = []
    topics = []
    for k in range(K):
        top = [{"w": vocab[i], "p": round(float(phi[k, i]), 5)} for i in np.argsort(phi[k])[::-1][:12]]
        share = float((theta[:, k] > 0.15).mean())
        topics.append({"id": k, "words": top, "share": round(share, 4), "coherence": round(coh[k], 3)})
    # 主题-时期分布
    sid_period = [periods.values[i] for i in sample_ids]
    topic_period = []
    for k in range(K):
        row = {}
        for per in periods_list:
            m = np.array([x == per for x in sid_period])
            row[per] = round(float(theta[m, k].mean()) if m.any() else 0, 4)
        topic_period.append(row)
    # 主题代表诗题
    topic_titles = []
    for k in range(K):
        best = np.argsort(theta[:, k])[::-1][:8]
        topic_titles.append([{"title": d["title"].iloc[sample_ids[i]], "p": round(float(theta[i, k]), 3),
                              "poet": pmid2name.get(int(pid_arr[sample_ids[i]]), "")} for i in best])
    lda_out = {"K": K, "topics": topics, "byPeriod": topic_period, "labels": topic_labels,
               "titles": topic_titles, "meanCoherence": round(float(np.mean(coh)), 3),
               "docs": len(sample_ids), "vocab": len(vocab), "iters": 35,
               "alpha": 0.15, "beta": 0.01}

    # ---------- 词共现网络（PMI）----------
    topn = 64
    net_words = [w for w, c in good if len(w) >= 2][:topn]
    nset = set(net_words)
    pair = Counter(); single = Counter(); hit = 0
    for t in docs:
        s = [w for w in t if w in nset]
        if s: hit += 1
        if len(s) < 2:
            if s: single[s[0]] += 1
            continue
        s = list(dict.fromkeys(s))
        for w in s:
            single[w] += 1
        for i in range(len(s)):
            for j in range(i + 1, len(s)):
                pair[tuple(sorted((s[i], s[j])))] += 1
    tot_pairs = sum(pair.values())
    N = max(hit, 1)
    links = []
    for (a, b), c in pair.items():
        if c < 5: continue
        pmi = math.log((c / N) / ((single[a] / N) * (single[b] / N)))
        links.append({"source": a, "target": b, "w": int(c), "pmi": round(pmi, 3)})
    links.sort(key=lambda x: -(x["pmi"] + math.log(x["w"])))
    print("pairs:", len(pair), "links:", len(links))
    # 每个词只保留 PMI 最高的 3 条边，得到稀疏 kNN 图，社区结构更清晰
    per = defaultdict(int)
    knn = []
    for l in links:
        if per[l["source"]] >= 3 and per[l["target"]] >= 3:
            continue
        knn.append(l)
        per[l["source"]] += 1
        per[l["target"]] += 1
        if len(knn) >= 150:
            break
    links = knn
    deg = Counter()
    for l in links:
        deg[l["source"]] += 1; deg[l["target"]] += 1
    nodes = [w for w in net_words if deg[w] > 0]
    adj = defaultdict(list)
    for l in links:
        adj[l["source"]].append(l["target"]); adj[l["target"]].append(l["source"])
    comm = label_propagation(nodes, adj)
    pos = fr_layout(nodes, [(l["source"], l["target"], l["pmi"]) for l in links], iters=520)
    net_out = {"nodes": [{"id": w, "f": int(cnt[w]), "deg": int(deg[w]), "comm": comm[w],
                          "x": pos[w][0], "y": pos[w][1]} for w in nodes],
               "links": links, "pairs": tot_pairs}

    # ---------- 诗人相似网络（TF-IDF 余弦）----------
    pv = p.sort_values("declared_count", ascending=False).head(160)
    ids = set(pv["id"].astype(int))
    by_poet = defaultdict(Counter)
    for i, pid in enumerate(d["person_id"].astype(int)):
        if pid in ids:
            by_poet[pid].update([w for w in docs[i] if len(w) >= 2])
    vocab1500 = [w for w, c in good if len(w) >= 2][:1400]
    vi = {w: i for i, w in enumerate(vocab1500)}
    M = np.zeros((len(pv), len(vocab1500)), dtype=np.float32)
    for r, pid in enumerate(pv["id"].astype(int)):
        for w, c in by_poet[pid].items():
            if w in vi:
                M[r, vi[w]] = c
    dfv = (M > 0).sum(0) + 1
    idf = np.log(len(pv) / dfv) + 1
    M = np.log1p(M) * idf
    norm = np.linalg.norm(M, axis=1) + 1e-9
    M = M / norm[:, None]
    S = M @ M.T
    np.fill_diagonal(S, 0)
    sim_links = []
    for r in range(len(pv)):
        order = np.argsort(S[r])[::-1][:4]
        for c in order:
            if S[r, c] < 0.08: continue
            a, b = sorted((r, int(c)))
            if a == b: continue
            sim_links.append((a, b, float(S[r, c])))
    sim_links = sorted(set((a, b, round(w, 3)) for a, b, w in sim_links), key=lambda x: -x[2])[:420]
    names = pv["name"].tolist()
    adj2 = defaultdict(list)
    for a, b, w in sim_links:
        adj2[names[a]].append(names[b]); adj2[names[b]].append(names[a])
    comm2 = label_propagation(names, adj2)
    pos2 = fr_layout(names, [(names[a], names[b], w * 20) for a, b, w in sim_links], iters=600, seed=3)
    periods_pv = pv["period"].tolist()
    sim_out = {"nodes": [{"id": names[i], "dynasty": pv["dynasty"].iloc[i], "period": periods_pv[i],
                          "poems": int(pv["declared_count"].iloc[i]),
                          "parsed": int(pv["poem_count"].iloc[i]), "comm": comm2[names[i]],
                          "x": pos2[names[i]][0], "y": pos2[names[i]][1]} for i in range(len(pv))],
               "links": [{"source": names[a], "target": names[b], "w": round(w, 3)} for a, b, w in sim_links],
               "metric": "TF-IDF 余弦相似度", "k": 4, "threshold": 0.08}

    # ---------- 地理 ----------
    names_sorted = sorted(PLACES, key=len, reverse=True)
    pat = re.compile("|".join(map(re.escape, names_sorted)))
    place_cnt = Counter(); place_period = defaultdict(Counter)
    for i, t in enumerate(d["title"].tolist()):
        hits = set(m.group(0) for m in pat.finditer(t))
        if not hits: continue
        per = periods.values[i]
        for h in hits:
            place_cnt[h] += 1
            place_period[h][per] += 1
    prov = Counter()
    prov_places = defaultdict(list)
    for pl, c in place_cnt.items():
        pv_ = PLACES[pl]
        prov[pv_] += c
        prov_places[pv_].append({"place": pl, "count": int(c)})
    for k in prov_places:
        prov_places[k].sort(key=lambda x: -x["count"])
    geo_out = {"provinces": [{"name": k, "count": int(v), "places": prov_places[k][:8]}
                             for k, v in prov.most_common()],
               "topPlaces": [{"place": k, "count": int(v), "region": PLACES[k],
                              "byPeriod": {q: int(place_period[k].get(q, 0)) for q in periods_list}}
                             for k, v in place_cnt.most_common(40)],
               "periods": periods_list,
               "titleWithPlace": round(float(sum(1 for t in d["title"].tolist() if pat.search(t)) / len(d)), 4)}

    # ---------- 诗人档案 ----------
    top_poets = p.sort_values("declared_count", ascending=False).head(1200)
    id2row = {int(r.id): r for r in top_poets.itertuples()}
    poet_docs = defaultdict(list)
    for i, pid in enumerate(d["person_id"].astype(int)):
        if pid in id2row:
            poet_docs[pid].append(i)
    profiles = []
    for pid, rows_idx in poet_docs.items():
        r = id2row[pid]
        sub = d.iloc[rows_idx]
        gc = sub["genre"].value_counts()
        wc = Counter(w for i in rows_idx for w in docs[i] if len(w) >= 2)
        profiles.append({
            "id": pid, "name": r.name, "dynasty": r.dynasty, "period": r.period,
            "poems": int(r.declared_count), "parsed": int(r.poem_count),
            "genres": {g: int(c) for g, c in gc.head(8).items()},
            "words": [{"w": w, "f": int(c)} for w, c in wc.most_common(10)],
            "titles": [{"t": t, "g": g} for t, g in zip(sub["title"].head(14), sub["genre"].head(14))],
            "harmony": round(float(sub["title"].str.contains(
                r"和.{1,12}[韵韻]|次.{1,12}[韵韻]|步.{0,6}[韵韻]|酬|贈|赠", regex=True).mean()), 3),
        })
    profiles.sort(key=lambda x: -x["poems"])

    # ---------- 体裁多样性与产量 ----------
    sc = []
    d_genre = d["genre"].values
    d_pid = pid_arr
    by_pid = defaultdict(list)
    for i, pid in enumerate(d_pid):
        by_pid[pid].append(i)
    cand = p[p.declared_count >= 4].sample(min(4500, int((p.declared_count >= 4).sum())), random_state=7)
    for r in cand.itertuples():
        rows_idx = by_pid.get(int(r.id), [])
        sub = [d_genre[i] for i in rows_idx]
        if len(sub) < 4:
            continue
        cc = Counter(sub)
        sc.append({"x": int(r.declared_count), "e": round(entropy([c / len(sub) for c in cc.values()]), 3),
                   "p": r.period, "n": r.name, "g": len(cc)})
    scatter_out = {"points": sc, "n": len(sc)}
    print("scatter points:", len(sc))

    # ---------- 词条生命周期 ----------
    bins = list(range(-600, 2051, 50))
    life_terms = ["江南", "梅花", "秋夜", "贈別", "田園", "邊塞", "金陵", "西湖"]
    midv = mids.values.astype(float)
    b_idx = np.digitize(midv, bins) - 1
    tot_bin = np.bincount(b_idx[b_idx >= 0], minlength=len(bins) - 1)
    life = []
    for w in life_terms:
        c = np.zeros(len(bins) - 1)
        for i, t in enumerate(docs):
            if w in t:
                c[b_idx[i]] += 1
        rate = np.divide(c, np.maximum(tot_bin, 1))
        # 三窗滑动平均，抑制小样本抖动
        pad = np.pad(rate, 1, mode="edge")
        sm = np.convolve(pad, [0.25, 0.5, 0.25], mode="valid")
        life.append({"w": w, "counts": [int(x) for x in c],
                     "rate": [round(float(x) * 1000, 3) for x in sm]})
    life_out = {"bins": bins, "terms": life}

    text_out = {"wordsTop": words_top, "charsTop": chars_top, "periodTerms": per_terms,
                "periods": periods_list, "vocab": len(good),
                "coverage": round(float(np.mean([1 if any(len(w) >= 2 for w in t) else 0 for t in docs])), 4)}
    json.dump(text_out, open(os.path.join(WEB, "text.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    json.dump(lda_out, open(os.path.join(WEB, "topics.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    json.dump(net_out, open(os.path.join(WEB, "net.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    json.dump(sim_out, open(os.path.join(WEB, "simnet.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    json.dump(geo_out, open(os.path.join(WEB, "geo.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    json.dump({"profiles": profiles}, open(os.path.join(WEB, "poets.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    json.dump({**scatter_out, **{"life": life_out}}, open(os.path.join(WEB, "extra.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print("done. topics:", [(t["words"][0]["w"], t["share"]) for t in topics])
    print("geo provinces:", len(prov), "places:", len(place_cnt))
    print("simnet:", len(sim_out["nodes"]), "nodes", len(sim_out["links"]), "links")


if __name__ == "__main__":
    main()
