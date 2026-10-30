# -*- coding: utf-8 -*-
"""用经典多维标度（MDS）为两个网络计算二维坐标——比力导向更稳定、可复现。"""
import os, json, pickle, math
from collections import Counter, defaultdict
import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(ROOT, "docs", "data")
CACHE = os.path.join(ROOT, "data", "cache")


def mds(D2, dim=2):
    n = D2.shape[0]
    J = np.eye(n) - np.ones((n, n)) / n
    B = -0.5 * J @ D2 @ J
    w, V = np.linalg.eigh(B)
    idx = np.argsort(w)[::-1][:dim]
    X = V[:, idx] * np.sqrt(np.maximum(w[idx], 0))
    return X


def rescale(X):
    scale = np.percentile(np.abs(X), 99.5) + 1e-9
    return np.clip(X / scale, -1.15, 1.15)


def mds_from_sim(S):
    S = np.asarray(S, dtype=float)
    np.fill_diagonal(S, 1.0)
    D2 = np.maximum(2 - 2 * S, 0)
    X = mds(D2)
    # 旋转到「第一主成分水平」，便于阅读
    X = X - X.mean(0)
    return rescale(X)


# ---------- 诗人网络 ----------
p = pd.read_csv(os.path.join(ROOT, "data", "persons_enriched.csv"))
docs = pickle.load(open(os.path.join(CACHE, "docs.pkl"), "rb"))
poems = pd.read_csv(os.path.join(ROOT, "data", "poems.csv"), dtype=str, keep_default_na=False)
pid = poems["person_id"].astype(int).values

sim = json.load(open(os.path.join(D, "simnet.json"), encoding="utf-8"))
names = [n["id"] for n in sim["nodes"]]
want = set(names)
name_by_id = {}
row = p.set_index("id")
# 取这些诗人的文档
idx_by_name = defaultdict(list)
for i, x in enumerate(pid):
    idx_by_name[int(x)].append(i)
word_cnt = [Counter(w for i in idx_by_name[int(r.id)] for w in docs[i] if len(w) >= 2)
            for r in p[p["name"].isin(want)].itertuples()]
sub = p[p["name"].isin(want)]
# 按 names 顺序取
name2cnt = {}
for r, c in zip(sub.itertuples(), word_cnt):
    name2cnt.setdefault(r.name, c)
vocab = Counter()
for n in names:
    vocab.update(name2cnt.get(n, Counter()))
words = [w for w, _ in vocab.most_common(1200)]
wi = {w: i for i, w in enumerate(words)}
M = np.zeros((len(names), len(words)), dtype=np.float32)
for r, n in enumerate(names):
    c = name2cnt.get(n, Counter())
    for w, v in c.items():
        if w in wi:
            M[r, wi[w]] = v
idfv = np.log(len(names) / ((M > 0).sum(0) + 1)) + 1
M = np.log1p(M) * idfv
M /= (np.linalg.norm(M, axis=1, keepdims=True) + 1e-9)
S = M @ M.T
X = mds_from_sim(S)
for i, n in enumerate(sim["nodes"]):
    n["x"], n["y"] = round(float(X[i, 0]), 4), round(float(X[i, 1]), 4)
json.dump(sim, open(os.path.join(D, "simnet.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print("poets MDS ok; corr(cos, 1-dist) sample:",
      round(float(np.corrcoef(S[np.triu_indices(160, 1)], 1 - np.linalg.norm(X[:, None] - X[None], axis=2)[np.triu_indices(160, 1)] / 2)[0, 1]), 3))

# ---------- 词网络 ----------
net = json.load(open(os.path.join(D, "net.json"), encoding="utf-8"))
wn = [n["id"] for n in net["nodes"]]
wset = set(wn)
cnt = [Counter(w for w in d if w in wset) for d in docs]
V = np.zeros((len(wn), len(wn)))
pos = {w: i for i, w in enumerate(wn)}
for c in cnt:
    ks = list(c)
    for i in range(len(ks)):
        for j in range(i + 1, len(ks)):
            a, b = pos[ks[i]], pos[ks[j]]
            V[a, b] += 1; V[b, a] += 1
N = max(1, sum(1 for c in cnt if c))
tot = V.sum() / 2 + 1e-9
rowsum = V.sum(1) + 1e-9
P = V / tot
pa = rowsum / (tot * 2)
with np.errstate(divide="ignore", invalid="ignore"):
    ppmi = np.maximum(np.log(P / (pa[:, None] * pa[None, :])), 0)
    ppmi[~np.isfinite(ppmi)] = 0
np.fill_diagonal(ppmi, 0)
norm = np.linalg.norm(ppmi, axis=1, keepdims=True) + 1e-9
Sw = (ppmi / norm) @ (ppmi / norm).T
np.fill_diagonal(Sw, 1.0)
Xw = mds_from_sim(Sw)
for i, n in enumerate(net["nodes"]):
    n["x"], n["y"] = round(float(Xw[i, 0]), 4), round(float(Xw[i, 1]), 4)
json.dump(net, open(os.path.join(D, "net.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print("words MDS ok")
