# 诗海图谱 · Poetry Atlas

以一张「人物诗作表」（47,573 位诗人、原表声明 1,996,305 首/篇、可解析题名 1,825,049 条）为语料，
做的一次**文本挖掘 + 数字人文可视化**实验。

网页是纯静态的：没有构建步骤、没有外部 CDN、没有后端。所有图表由 `docs/assets/` 下的自写 SVG 引擎
在浏览器里实时绘制，可直接部署到 GitHub Pages。

> 展示层（网页、JSON、CSV、Excel）统一使用简体中文；原始语料与诗题中的异体字在分析前已做归一。
> 分析脚本内部仍以原表字串作键，最后由 `scripts/to_simplified.py` 统一转换输出。

---

## 一、在线与本地预览

- **线上地址：<https://woaadan.github.io/poetry-atlas/>**（GitHub Pages，已部署）
- 仓库：<https://github.com/woaadan/poetry-atlas>
- 本地：双击 `本地预览.ps1`，或在该目录执行

  ```bash
  python -m http.server 8811 --directory docs
  # 浏览器打开 http://127.0.0.1:8811/
  ```

  直接双击 `docs/index.html` 不行——浏览器会以 `file://` 打开并拒绝加载 JSON，必须走一个本地 HTTP 服务。

## 二、目录结构

```
poetry_atlas/
├─ docs/                      ← 可直接部署的站点（GitHub Pages 目录）
│  ├─ index.html
│  ├─ .nojekyll
│  ├─ assets/   style.css · viz.js（零依赖图表库） · app.js（各图逻辑）
│  ├─ data/     core.json text.json topics.json geo.json poets.json net.json simnet.json extra.json
│  └─ tables/   10 份可下载的 CSV 数据表
├─ scripts/                   ← 分析管线（Python 3 + numpy / pandas / openpyxl）
│  ├─ extract.py              xlsx → persons.csv / poems.csv
│  ├─ dynasty.py              224 种断代标签 → 9 个时期 + 年份区间
│  ├─ textmine.py             n-gram 统计、凝固度+邻接熵新词发现、最长匹配分词
│  ├─ build_core.py           分期 / 体裁 / 产量分布 / 热力 / 唱和
│  ├─ places.py               228 条名胜地名 → 今省区
│  ├─ build_text.py           词频、log-odds、LDA、共现网、诗人网、地理、词条生命周期
│  ├─ mds_layout.py           用经典 MDS 计算两张网络的二维坐标
│  ├─ make_tables.py          导出 docs/tables/*.csv
│  ├─ make_workbook.py        汇总为 诗海图谱_数据表.xlsx
│  ├─ to_simplified.py        展示层简繁转换（附 t2s.json 词表）
│  └─ smoke_test.js           无浏览器冒烟测试（Node，最小 DOM 桩）
├─ 诗海图谱_数据表.xlsx        8 个工作表的数据汇总
├─ 本地预览.ps1
├─ deploy_github.ps1
├─ .gitignore
└─ README.md
```

> `data/`（约 200 MB 的中间 CSV 与缓存）不入库、也不随包交付；按第三节重跑即可再生成。

## 三、复现

依赖：`numpy pandas openpyxl`；Node 仅用于冒烟测试。

```bash
# 1) 改 scripts/extract.py 顶部的 SRC 为 xlsx 路径
python scripts/extract.py      # ~1 分钟：1,825,049 条题名
python scripts/textmine.py     # ~6 分钟：n-gram + 邻接熵新词发现（得到 1,995 个词条）
python scripts/build_core.py   # ~1 分钟
python scripts/build_text.py   # ~10 分钟（含 35 轮 LDA 吉布斯采样；结果缓存于 data/cache/lda.pkl）
python scripts/mds_layout.py   # 数秒：重算网络坐标
python scripts/make_tables.py  # 数秒
python scripts/make_workbook.py
python scripts/to_simplified.py  # 展示层统一为简体（可重复执行）
node scripts/smoke_test.js     # 可选：验证 7 个视图的图表函数不报错
```

`build_text.py` 会把 LDA 结果缓存到 `data/cache/lda.pkl`，改动下游逻辑时不会再等采样。
设环境变量 `REFRESH_LDA=1` 可强制重跑主题模型。

## 四、部署到 GitHub Pages

推荐用脚本（需要已安装 git、已建好空仓库、配置好凭据）：

```powershell
.\deploy_github.ps1 -Repo poetry-atlas -User <你的账号>
```

手动版：

```bash
git init
git add .
git commit -m "poetry atlas"
git branch -M main
git remote add origin https://github.com/<账号>/poetry-atlas.git
git push -u origin main
```

然后仓库 **Settings → Pages → Source: Deploy from a branch → Branch: main，Folder: /docs**，保存。
约 1 分钟后访问 `https://<账号>.github.io/poetry-atlas/`。

`docs/.nojekyll` 已就位，避免以下划线开头的文件被 Jekyll 忽略。

## 五、方法

| 环节 | 做法 |
| --- | --- |
| 语料解析 | 按「；」切分诗题，右端匹配 18 种体裁后缀；解析出 1,825,049 条题名（占声明总数 91.4%） |
| 断代归一 | 224 种原始标签按「朝代名 + 初/中/晚/末」规则映射到 9 个时期与年份区间 |
| 新词发现 | 二字/三字 n-gram 的凝固度 PMI + 左右邻接信息熵，双阈值筛出 1,995 个词条，再补诗学词表 |
| 分词 | 最长匹配；未登录片段保留单字 |
| 时期特征词 | log-odds ratio with informative Dirichlet prior（Monroe et al. 2008），z 值排序；仅比较诗体 |
| 主题模型 | 坍缩吉布斯采样 LDA，K=10，α=0.15，β=0.01，35 轮，8 万条诗体题名；UMass 一致性评估 |
| 网络 | 词共现 PMI 加权、每词保留 3 强边；诗人 TF-IDF 余弦 + 4-NN；二维坐标用经典 MDS |
| 分布 | 双对数最小二乘拟合幂指数 + Hill 上尾估计；洛伦兹曲线与基尼系数 |
| 地理 | 228 条地名表扫描诗题，映射到今省区（含「江南」「塞外」等区域泛称） |

**口径提醒**

1. 全部统计针对**诗题（标题）**，不含诗正文。
2. 「诗作数」按原表声明的 `诗作总数` 计；文本挖掘用实际解析出的题名。
3. 90 位极高产诗人的题名列表被 Excel 单元格 32,767 字符上限截断（如乾隆声明 43,290 首、仅解析 3,378 条），
   因此其体裁结构不可靠，页面中会标注这一点。
4. 组诗的不同首分别计数，重复题名会抬高词频。
5. 地名映射为本次分析所加，属推定，供参考。
6. 简繁转换词表派生自 OpenCC 的 `TSCharacters.txt`（Apache-2.0），已随包附于 `scripts/t2s.json`。

## 六、数据来源

数据来自用户提供的《人物诗作表》（47,574 行 × 8 列）。断代、体裁、集句/步韵标记沿用原表口径；
分期、地名映射、全部统计量与图表为本次分析生成。页面与脚本可自由修改，数据版权归原整理者。
