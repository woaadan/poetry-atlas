# -*- coding: utf-8 -*-
"""把展示层（网页、JSON、CSV、工作簿）统一转换为简体中文。

分析脚本仍以原始繁体字串作为数据键；本脚本只处理输出层，
转换后会合并因简繁归一而重复的词条/节点，保证图表一致。
"""
import os, re, json, csv, glob, shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# 词表随包附在 scripts/t2s.json（由 OpenCC 的 TSCharacters.txt 派生，Apache-2.0）
DICT_SRC = os.environ.get("T2S_DICT", os.path.join(os.path.dirname(os.path.abspath(__file__)), "t2s.json"))

def load_map(path):
    if path.endswith(".json"):
        return json.load(open(path, encoding="utf-8"))
    m = {}
    for line in open(path, encoding="utf-8"):
        line = line.rstrip("\n")
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        k, v = parts[0], parts[1].split(" ")[0]
        if len(k) == 1 and len(v) == 1 and k != v:
            m[k] = v
    return m

MAP = load_map(DICT_SRC)
print("t2s entries:", len(MAP))
TABLE = str.maketrans(MAP)

FIX = {"干隆": "乾隆", "干坤": "乾坤", "干清": "乾清"}

def s(text):
    if not isinstance(text, str):
        return text
    out = text.translate(TABLE)
    for a, b in FIX.items():
        out = out.replace(a, b)
    return out

def walk(obj):
    if isinstance(obj, str):
        return s(obj)
    if isinstance(obj, list):
        return [walk(x) for x in obj]
    if isinstance(obj, dict):
        return {s(k): walk(v) for k, v in obj.items()}
    return obj

def main():
    W = os.path.join(ROOT, "docs")

    # ---------- 1) HTML / CSS / JS ----------
    for f in [os.path.join(W, "index.html"), os.path.join(W, "assets", "app.js"),
              os.path.join(W, "assets", "style.css")]:
        src = open(f, encoding="utf-8").read()
        open(f, "w", encoding="utf-8").write(s(src))
        print("converted", os.path.basename(f))

    # ---------- 2) JSON ----------
    def dedupe_wordlist(lst, key, val):
        agg = {}
        for it in lst:
            k = it[key]
            if k in agg:
                agg[k][val] += it[val]
            else:
                agg[k] = dict(it)
        return sorted(agg.values(), key=lambda x: -x[val])

    for name in ["core", "text", "topics", "geo", "poets", "net", "simnet", "extra"]:
        p = os.path.join(W, "data", name + ".json")
        data = walk(json.load(open(p, encoding="utf-8")))
        if name == "text":
            data["wordsTop"] = dedupe_wordlist(data["wordsTop"], "w", "f")[:120]
            data["charsTop"] = dedupe_wordlist(data["charsTop"], "c", "f")[:100]
            for per, rec in data["periodTerms"].items():
                seen = {}
                for r in rec["pos"]:
                    if r["w"] not in seen or abs(r["z"]) > abs(seen[r["w"]]["z"]):
                        seen[r["w"]] = r
                rec["pos"] = sorted(seen.values(), key=lambda x: -x["z"])[:18]
                seen = {}
                for r in rec["neg"]:
                    if r["w"] not in seen or abs(r["z"]) > abs(seen[r["w"]]["z"]):
                        seen[r["w"]] = r
                rec["neg"] = sorted(seen.values(), key=lambda x: x["z"])[:10]
        if name == "net":
            agg = {}
            for n in data["nodes"]:
                if n["id"] in agg:
                    agg[n["id"]]["f"] += n["f"]; agg[n["id"]]["deg"] = max(agg[n["id"]]["deg"], n["deg"])
                else:
                    agg[n["id"]] = dict(n)
            data["nodes"] = list(agg.values())
            links, seen = [], set()
            for l in data["links"]:
                if l["source"] == l["target"]:
                    continue
                a, b = sorted((l["source"], l["target"]))
                if (a, b) in seen:
                    continue
                seen.add((a, b)); links.append(l)
            data["links"] = links
        if name == "simnet":
            agg = {}
            for n in data["nodes"]:
                if n["id"] in agg:
                    agg[n["id"]]["poems"] = max(agg[n["id"]]["poems"], n["poems"])
                else:
                    agg[n["id"]] = dict(n)
            data["nodes"] = list(agg.values())
            links, seen = [], set()
            for l in data["links"]:
                if l["source"] == l["target"]:
                    continue
                a, b = sorted((l["source"], l["target"]))
                if (a, b) in seen:
                    continue
                seen.add((a, b)); links.append(l)
            data["links"] = links
        json.dump(data, open(p, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
        print("converted", name + ".json")

    # ---------- 3) CSV ----------
    for f in glob.glob(os.path.join(W, "tables", "*.csv")):
        with open(f, encoding="utf-8-sig", newline="") as fh:
            rows = list(csv.reader(fh))
        rows = [[s(c) for c in row] for row in rows]
        with open(f, "w", encoding="utf-8-sig", newline="") as fh:
            csv.writer(fh).writerows(rows)
    print("converted csv tables")

    # ---------- 4) README ----------
    rp = os.path.join(ROOT, "README.md")
    text = open(rp, encoding="utf-8").read()
    open(rp, "w", encoding="utf-8").write(s(text))
    print("converted README")


if __name__ == "__main__":
    main()
