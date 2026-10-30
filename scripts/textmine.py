# -*- coding: utf-8 -*-
"""文本挖掘第一阶段：字/词频统计 + 无监督新词发现 + 最长匹配分词。

方法：以「凝固度（PMI）」与「左右邻接信息熵」双阈值从诗题中自动发现词，
辅以诗学领域补充词表，再做最长匹配分词。不依赖外部分词器。
"""
import os, re, json, pickle, math
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
CACHE = os.path.join(DATA, "cache")
os.makedirs(CACHE, exist_ok=True)

PUNCT = re.compile(r"[^\u3400-\u9fffA-Za-z0-9]+")
DIGIT = re.compile(r"[0-9０-９一二三四五六七八九十百千萬万廿卅]+")

VARIANT = {
    "絕": "絶", "绝": "絶", "卽": "即", "淸": "清", "峯": "峰", "羣": "群", "眞": "真",
    "衆": "眾", "衆": "眾", "敎": "教", "隣": "鄰", "廻": "回", "逈": "迥", "塚": "冢",
    "藁": "稿", "甯": "寧", "慙": "慚", "麤": "粗", "谿": "溪", "蹤": "踪", "咏": "詠",
    "叹": "嘆", "啸": "嘯", "垒": "壘", "笺": "箋", "棊": "棋", "鷄": "雞", "携": "攜",
    "巖": "岩", "嵓": "岩", "龢": "和", "煇": "輝", "嵗": "歲", "嵗": "歲", "刦": "劫",
    "刧": "劫", "刼": "劫", "牕": "窗", "窻": "窗", "牎": "窗", "缾": "瓶", "甁": "瓶",
    "棊": "棋", "碁": "棋", "鷰": "燕", "鵶": "鴉", "鵞": "鵝", "鳬": "鳧", "鳧": "鳧",
    "鉅": "巨", "钜": "巨", "鈎": "鉤", "钩": "鉤", "鉤": "鉤", "綫": "線", "线": "線",
    "牀": "床", "粧": "妝", "妆": "妝", "奬": "獎", "奖": "獎", "奬": "獎", "衞": "衛",
    "卫": "衛", "衹": "只", "祇": "只", "祗": "只", "閒": "閑", "闲": "閑", "閑": "閑",
}
VAR_TABLE = str.maketrans(VARIANT)

# 诗学领域补充词表（保证题材/地点/意象类词条可解释）
CURATED = """江南 江北 春風 秋風 春夜 秋夜 夏夜 冬夜 春日 秋日 夏日 冬日 早春 暮春 初秋 晚秋
春曉 秋曉 春興 秋興 春望 秋望 春遊 秋遊 春雨 秋雨 夜雨 暮雨 微雨 細雨 風雨 烟雨 烟波
梅花 桃花 杏花 梨花 荷花 蓮花 菊花 桂花 海棠 牡丹 芍藥 杜鵑 芙蓉 楊柳 垂柳 松竹 竹枝
明月 新月 殘月 落日 夕陽 斜陽 孤舟 扁舟 歸舟 漁舟 孤燈 寒燈 殘燈 故鄉 故園 家山 鄉愁
長安 洛陽 金陵 姑蘇 錢塘 西湖 太湖 洞庭 瀟湘 江南 塞北 邊塞 關山 玉門 陽關 劍門 三峽
廬山 黃山 泰山 華山 峨眉 天台 武當 羅浮 武夷 終南 輞川 桃源 赤壁 秦淮 揚州 蘇州 杭州
黃鶴樓 岳陽樓 滕王閣 鸛雀樓 岳陽 武昌 成都 京師 燕京 上都 嶺南 海南 蜀中 巴蜀 荆楚 吳越
登臨 登高 登樓 望遠 懷古 詠史 詠物 詠懷 感懷 遣懷 抒懷 即事 即景 雜興 漫興 遣興 偶成
送別 贈別 留別 別後 贈答 酬答 唱和 唱酬 懷人 憶舊 憶昔 寄懷 寄遠 思鄉 悼亡 傷逝 哭亡
田園 村居 山居 隱居 歸隱 幽居 閒居 閒適 山行 舟行 夜泊 旅宿 客中 病中 夢中 雪中 雨後
題畫 題壁 題扇 題跋 寫真 觀畫 聽琴 彈琴 對弈 飲酒 獨酌 醉後 小酌 雅集 招飲 餞別 夜宴
早朝 直廬 應制 御製 詔令 貶謫 遷謫 量移 致仕 乞歸 歸省 省親 展墓 掃墓 生辰 壽詩
上元 元宵 清明 寒食 端午 七夕 中秋 重陽 除夕 歲暮 歲除 元日 人日 花朝 浴佛 臘日
邊愁 從軍 出塞 入塞 塞下 關塞 征人 戍卒 戰城南 兵車 甲馬 干戈 烽火 羽檄 捷報
梅花 詠梅 訪梅 探梅 賞梅 觀梅 折梅 落梅 殘梅 早梅 紅梅 白梅 墨梅 瓶梅 盆梅 梅影
山水 江湖 田家 農家 漁家 樵夫 漁父 牧童 村舍 茅屋 草堂 精舍 僧舍 禪房 道院 書齋
古寺 山寺 佛寺 祠堂 陵墓 故宮 廢苑 荒園 舊宅 遺址 古城 故壘 斷碑 殘碑 苔痕
春日 春色 春光 春意 春寒 春晴 春陰 春水 春江 春山 春草 春樹 春風 春雪 春雷
秋色 秋光 秋意 秋聲 秋陰 秋水 秋江 秋山 秋草 秋樹 秋蟬 秋雁 秋月 秋霜 秋露 秋懷
夏日 夏日 夏景 夏日 暑中 苦熱 納涼 避暑 消暑 夏夜 夏雨 初夏 首夏 仲夏 季夏
冬日 冬景 歲寒 苦寒 寒夜 冬夜 圍爐 詠雪 賞雪 踏雪 雪霽 雪後 雪中 冰霜 朔風
歸雁 孤雁 征鴻 雁字 杜宇 子規 鷓鴣 杜鵑 黃鸝 白鷗 沙鷗 鷗鷺 鸕鶿 鶺鴒 鶯啼 蟬鳴
青海 黃河 長江 大江 漢水 湘江 贛江 珠江 淮水 渭水 涇水 洛水 汾水 錢塘江 富春江
五嶺 南嶺 秦嶺 太行 匡廬 虎丘 靈巖 栖霞 孤山 焦山 金山 北固 采石 牛渚 新亭
秋浦 秋江 瓜洲 京口 潤州 常州 湖州 嘉興 紹興 寧波 台州 溫州 福州 泉州 漳州 潮州
廣州 桂林 柳州 邕州 黔中 滇池 大理 昆明 成都 重慶 夔州 江陵 襄陽 樊城 南陽 許昌
汴京 開封 洛陽 西安 咸陽 太原 大同 宣府 遼東 薊北 幽州 范陽 漁陽 盧龍 榆關 山海關""".split()

TITLE_MIN_FREQ = 150


def norm_text(t):
    t = t.translate(VAR_TABLE)
    # 数字统一为占位符，避免「十首」「二年」干扰
    t = DIGIT.sub("#", t)
    t = PUNCT.sub("\x00", t)
    return t


def build_ngrams(titles, orders=(2, 3)):
    uni = Counter()
    ngr = {n: Counter() for n in orders}
    for t in titles:
        t = norm_text(t)
        for ch in t:
            if ch != "\x00" and ch != "#":
                uni[ch] += 1
        for n in orders:
            c = ngr[n]
            for i in range(len(t) - n + 1):
                seg = t[i:i + n]
                if "\x00" in seg or "#" in seg:
                    continue
                c[seg] += 1
    return uni, ngr


def neighbor_entropy(cands, titles):
    left = defaultdict(Counter)
    right = defaultdict(Counter)
    maxlen = max(len(c) for c in cands) if cands else 0
    lookup = set(cands)
    for t in titles:
        t = norm_text(t)
        L = len(t)
        for i in range(L):
            for n in range(2, maxlen + 1):
                if i + n > L:
                    break
                seg = t[i:i + n]
                if seg in lookup:
                    left[seg][t[i - 1] if i > 0 else "^"] += 1
                    right[seg][t[i + n] if i + n < L else "$"] += 1
    out = {}
    for w in cands:
        def H(c):
            tot = sum(c.values())
            if tot <= 1:
                return 0.0
            return -sum((v / tot) * math.log(v / tot) for v in c.values())
        out[w] = min(H(left[w]), H(right[w]))
    return out


def discover(titles):
    uni, ngr = build_ngrams(titles)
    total = sum(uni.values())
    freq_all = Counter()
    for c in ngr.values():
        freq_all.update(c)

    cand = {}
    for n, c in ngr.items():
        for seg, f in c.items():
            if f < TITLE_MIN_FREQ or len(set(seg)) == 1:
                continue
            p = sum(uni[ch] for ch in seg)
            if not p:
                continue
            pmi = math.log((f / total) / (p / total) ** n)
            if pmi < (2.0 if n == 2 else 3.5):
                continue
            cand[seg] = {"freq": f, "pmi": round(pmi, 3), "n": n}
    print("cohesion candidates:", len(cand))

    ent = neighbor_entropy(cand, titles)
    words = {}
    for s, st in cand.items():
        e = ent.get(s, 0.0)
        if e < 0.9:
            continue
        words[s] = {"freq": st["freq"], "pmi": st["pmi"], "entropy": round(e, 3), "len": st["n"]}

    for w in CURATED:
        words.setdefault(w, {"freq": int(freq_all.get(w, 0)), "pmi": None, "entropy": None,
                             "len": len(w), "manual": True})
    # 去掉纯数字式、单字重复
    for bad in list(words):
        if re.fullmatch(r"[#\d]+", bad):
            del words[bad]
    print("discovered words:", len(words))
    return uni, ngr, words


def tokenize(t, vocab, maxlen):
    t = norm_text(t)
    out, i, L = [], 0, len(t)
    while i < L:
        if t[i] in "\x00#":
            i += 1
            continue
        hit = None
        for n in range(min(maxlen, L - i), 1, -1):
            seg = t[i:i + n]
            if "\x00" in seg or "#" in seg:
                continue
            if seg in vocab:
                hit = seg
                break
        if hit:
            out.append(hit)
            i += len(hit)
        else:
            out.append(t[i])
            i += 1
    return out


def main():
    import pandas as pd
    df = pd.read_csv(os.path.join(DATA, "poems.csv"), dtype=str, keep_default_na=False)
    titles = df["title"].tolist()
    print("titles:", len(titles))
    uni, ngr, words = discover(titles)
    with open(os.path.join(CACHE, "words.json"), "w", encoding="utf-8") as f:
        json.dump(words, f, ensure_ascii=False)

    vocab = set(words)
    maxlen = max(len(w) for w in vocab)
    toks = [tokenize(t, vocab, maxlen) for t in titles]
    with open(os.path.join(CACHE, "tokens.pkl"), "wb") as f:
        pickle.dump(toks, f, protocol=4)

    tc = Counter(w for ts in toks for w in ts)
    multi = Counter(w for w in tc if len(w) >= 2 for _ in range(tc[w]))
    print("top words:", multi.most_common(60))
    print("titles with >=1 word:", sum(1 for ts in toks if any(len(x) >= 2 for x in ts)) / len(toks))
    json.dump({"words": multi.most_common(2000),
               "chars": Counter(c for ts in toks for c in "".join(ts)).most_common(300),
               "vocab": len(vocab)},
              open(os.path.join(CACHE, "token_counts.json"), "w", encoding="utf-8"), ensure_ascii=False)


if __name__ == "__main__":
    main()
