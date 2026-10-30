/* ============================================================
   app.js — 诗海图谱：数据装载与全部图表
   ============================================================ */
const D = {};
const $ = id => document.getElementById(id);

const PERIOD_COLOR = {
  "先秦": "#8a5a3b", "秦汉": "#9c6b4f", "魏晋南北朝": "#6b4f7a", "隋唐五代": "#b23a2f",
  "宋辽金": "#2f5d73", "元": "#4f7d7a", "明": "#5b7c5a", "清": "#a9823f", "近现代": "#8c6d8f",
};
const GENRE_COLOR = {
  "近体诗": "#2f5d73", "古体诗": "#5b7c5a", "词曲": "#b23a2f", "文赋": "#a9823f", "其他": "#8a7f70",
};
const COM_COLORS = ["#b23a2f", "#2f5d73", "#5b7c5a", "#a9823f", "#6b4f7a", "#8a5a3b", "#4f7d7a", "#8c6d8f"];

function periodColor(p) { return PERIOD_COLOR[p] || "#8a7f70"; }

/* ---------- 通用 ---------- */
function H(host, w, h, pad = [18, 18, 34, 54]) {
  const c = frame(host, w, h, pad);
  return c;
}
function addTitle(c, x, y, s, size = 11.5) { text(c.g, x, y, s, { size, fill: INK2, anchor: "start" }); }

function hoverRect(c, x, y, w, h, html) {
  const r = E("rect", { x, y, width: w, height: h, fill: "transparent" }, c.g);
  r.addEventListener("mousemove", e => c.show(html(e), e));
  r.addEventListener("mouseleave", () => c.hide());
  return r;
}

function axisLabel(c, str, x, y, anchor = "middle") {
  text(c.g, x, y, str, { size: 10.5, fill: INK3, anchor });
}

/* ---------- 概述：规模 ---------- */
function drawScale() {
  const P = D.core.periods, host = $("c-scale");
  const c = H(host, 660, 360, [24, 44, 48, 52]);
  const { x0, x1, y0, y1 } = c.inner;
  const n = P.length;
  const band = (x1 - x0) / n;
  const maxPoems = Math.max(...P.map(p => p.poems));
  const maxPoets = Math.max(...P.map(p => p.poets));
  const yP = linear(0, maxPoems * 1.08, y1, y0);
  const yT = linear(0, maxPoets * 1.12, y1, y0);
  const cx = i => x0 + band * (i + 0.5);

  // 诗作面积
  const pts = P.map((p, i) => [cx(i), yP(p.poems)]);
  E("path", {
    d: pathFrom(pts) + `L${x1},${y1}L${x0},${y1}Z`,
    fill: "rgba(47,93,115,.16)", stroke: "none"
  }, c.g);
  E("path", { d: smoothPath(pts), fill: "none", stroke: "#2f5d73", "stroke-width": 2.2 }, c.g);

  // 诗人线
  const pts2 = P.map((p, i) => [cx(i), yT(p.poets)]);
  E("path", { d: smoothPath(pts2), fill: "none", stroke: "#b23a2f", "stroke-width": 2, "stroke-dasharray": "5 4" }, c.g);

  // 轴
  const yt1 = ticks(0, maxPoems * 1.08, 4);
  yt1.forEach(t => {
    E("line", { x1: x0, x2: x1, y1: yP(t), y2: yP(t), stroke: LINE, "stroke-dasharray": "2 4", opacity: .5 }, c.g);
    text(c.g, x0 - 8, yP(t) + 4, fmt(t), { anchor: "end", size: 10 });
  });
  const yt2 = ticks(0, maxPoets * 1.12, 4);
  yt2.forEach(t => text(c.g, x1 + 8, yT(t) + 4, fmt(t), { size: 10 }));

  P.forEach((p, i) => {
    E("circle", { cx: cx(i), cy: yP(p.poems), r: 3.4, fill: "#fffdf8", stroke: "#2f5d73", "stroke-width": 1.8 }, c.g);
    E("circle", { cx: cx(i), cy: yT(p.poets), r: 3, fill: "#b23a2f" }, c.g);
    const t = text(c.g, cx(i), y1 + 16, p.period, { anchor: "middle", size: 10.5, fill: INK2 });
    hoverRect(c, cx(i) - band / 2, y0, band, y1 - y0, ev => {
      return `<b>${p.period}</b><br>诗人 ${fmt(p.poets)} 人<br>诗作 ${fmt(p.poems)} 首<br>
      人均 ${p.avg_poems} 首 · 基尼 ${p.gini}<br>体裁判 ${p.genre_effective} 种`;
    });
  });
  // 图例
  E("line", { x1: x0 + 6, x2: x0 + 30, y1: y0 - 8, y2: y0 - 8, stroke: "#2f5d73", "stroke-width": 2.2 }, c.g);
  text(c.g, x0 + 34, y0 - 5, "诗作数", { size: 10.5 });
  E("line", { x1: x0 + 86, x2: x0 + 110, y1: y0 - 8, y2: y0 - 8, stroke: "#b23a2f", "stroke-width": 2, "stroke-dasharray": "4 3" }, c.g);
  text(c.g, x0 + 114, y0 - 5, "诗人数", { size: 10.5 });
  $("n-scale").textContent = `峰值出现在${P.reduce((a, b) => a.poems > b.poems ? a : b).period}，`
    + `${P.reduce((a, b) => a.poets > b.poets ? a : b).period}的诗人数量最多。`;
}

/* ---------- 概述：体裁环 ---------- */
function drawDonut() {
  const G = D.core.genreGroups, host = $("c-donut");
  const c = H(host, 380, 360, [16, 16, 16, 16]);
  const cx = 165, cy = 168, R = 112, r = 68;
  const tot = G.reduce((s, g) => s + g.count, 0);
  let a0 = -Math.PI / 2;
  const col = g => GENRE_COLOR[g] || "#8a7f70";
  G.forEach(g => {
    const a1 = a0 + (g.count / tot) * Math.PI * 2;
    const large = a1 - a0 > Math.PI ? 1 : 0;
    const p = (R, a) => [cx + R * Math.cos(a), cy + R * Math.sin(a)];
    const q = (R, a) => [cx + R * Math.cos(a), cy + R * Math.sin(a)];
    const [x1, y1] = p(R, a0), [x2, y2] = p(R, a1), [x3, y3] = q(r, a0), [x4, y4] = q(r, a1);
    const seg = E("path", {
      d: `M${x1},${y1}A${R},${R},0,${large},1,${x2},${y2}L${x4},${y4}A${r},${r},0,${large},0,${x3},${y3}Z`,
      fill: col(g.group), opacity: .9, stroke: "#fffdf8", "stroke-width": 1.5,
    }, c.g);
    seg.addEventListener("mousemove", e => c.show(
      `<b>${g.group}</b><br>${fmt(g.count)} 首 · ${pct(g.count / tot)}`, e));
    seg.addEventListener("mouseleave", () => c.hide());
    a0 = a1;
  });
  text(c.g, cx, cy - 6, fmt(tot), { anchor: "middle", size: 20, fill: INK, weight: 600 });
  text(c.g, cx, cy + 16, "首（篇）", { anchor: "middle", size: 10.5 });
  // 图例
  let yy = 68;
  G.forEach(g => {
    E("rect", { x: 300, y: yy - 8, width: 9, height: 9, rx: 2, fill: col(g.group) }, c.g);
    text(c.g, 315, yy, g.group, { size: 11.5, fill: INK2 });
    text(c.g, 360, yy, pct(g.count / tot), { size: 10.5 });
    yy += 30;
  });
}

/* ---------- 概述：体裁流变 ---------- */
function drawStream() {
  const P = D.core.periods, host = $("c-stream");
  const groups = ["近体诗", "古体诗", "词曲", "文赋", "其他"];
  const data = P.map(p => {
    const tot = Object.values(p.genres).reduce((a, b) => a + b, 0) || 1;
    const o = {};
    groups.forEach(g => { o[g] = 0; });
    // 通过 genres 明细归类
    const GMAP = { "律诗": "近体诗", "绝句": "近体诗", "排律": "近体诗", "古风": "古体诗", "乐府曲辞": "古体诗", "四言诗": "古体诗", "骚": "古体诗", "琴操": "古体诗", "鼓吹曲": "古体诗", "词": "词曲", "曲": "词曲", "文": "文赋", "辞赋": "文赋", "赞": "文赋", "偈颂": "文赋", "联": "文赋", "句": "文赋", "六言诗": "其他" };
    for (const [g, v] of Object.entries(p.genres)) o[GMAP[g] || "其他"] += v / tot;
    return o;
  });
  const c = H(host, 1080, 380, [22, 24, 44, 210]);
  const { x0, x1, y0, y1 } = c.inner;
  const n = P.length;
  const xs = P.map((_, i) => x0 + (x1 - x0) * (i / (n - 1)));
  const y = linear(0, 1, y1, y0);
  const cum = data.map(d => {
    let s = 0; const arr = [];
    groups.forEach(g => { arr.push([s, s + d[g]]); s += d[g]; });
    return arr;
  });
  // 堆叠（以 0.5 为中心）
  const layers = groups.map((g, gi) => {
    const top = xs.map((_, i) => [xs[i], y(cum[i][gi][1])]);
    const bot = xs.map((_, i) => [xs[i], y(cum[i][gi][0])]).reverse();
    return { g, top, bot };
  });
  layers.forEach((L, gi) => {
    const d = smoothPath(L.top) + "L" + L.bot.map(p => `${p[0]},${p[1]}`).join("L") + "Z";
    const pth = E("path", { d, fill: GENRE_COLOR[L.g], opacity: .82, stroke: "#fffdf8", "stroke-width": .8 }, c.g);
    pth.addEventListener("mousemove", e => {
      const r = c.svg.getBoundingClientRect();
      const px = (e.clientX - r.left) / r.width * 1080;
      let best = 0, bd = 1e9;
      xs.forEach((xv, i) => { if (Math.abs(xv - px) < bd) { bd = Math.abs(xv - px); best = i; } });
      const p = P[best];
      c.show(`<b>${p.period}</b> · ${L.g}<br>${pct(data[best][L.g])}（约 ${fmt(Math.round(data[best][L.g] * p.parsed))} 首）`, e);
    });
    pth.addEventListener("mouseleave", () => c.hide());
  });
  y.ticks = ticks(0, 1, 5);
  y.ticks.forEach(t => {
    E("line", { x1: x0, x2: x1, y1: y(t), y2: y(t), stroke: LINE, "stroke-dasharray": "2 4", opacity: .45 }, c.g);
    text(c.g, x0 - 8, y(t) + 4, pct(t, 0), { anchor: "end", size: 10 });
  });
  P.forEach((p, i) => {
    text(c.g, xs[i], y1 + 18, p.period, { anchor: i === 0 ? "start" : i === n - 1 ? "end" : "middle", size: 10.5, fill: INK2 });
    text(c.g, xs[i], y1 + 32, fmt(p.poems), { anchor: i === 0 ? "start" : i === n - 1 ? "end" : "middle", size: 9.5, fill: INK3 });
  });
  // 图例放左侧
  let yy = y0 + 20;
  groups.forEach(g => {
    E("rect", { x: x0 - 196, y: yy - 9, width: 10, height: 10, rx: 2, fill: GENRE_COLOR[g] }, c.g);
    text(c.g, x0 - 180, yy, g, { size: 11.5, fill: INK2 });
    yy += 24;
  });
}

/* ---------- 概述：热力图 ---------- */
function drawHeat() {
  const Hm = D.core.heatmap, host = $("c-heat");
  const cols = Hm.genres.slice(0, 12);
  const rows = Hm.rows.slice().sort((a, b) => (a.mid || 0) - (b.mid || 0));
  const W = 1120, Hh = 56 + rows.length * 25 + 40;
  const c = H(host, W, Hh, [46, 20, 26, 92]);
  const { x0, x1, y0, y1 } = c.inner;
  const cw = (x1 - x0) / cols.length, ch = (y1 - y0) / rows.length;
  const totals = rows.map(r => r.values.reduce((a, b) => a + b, 0));
  const maxLog = Math.max(...rows.map(r => Math.log10(1 + Math.max(...r.values))));
  const color = v => {
    const t = Math.log10(1 + v) / (maxLog || 1);
    const a = [247, 242, 232], b = [178, 58, 47];
    return `rgb(${a.map((x, i) => Math.round(x + (b[i] - x) * Math.pow(t, .75))).join(",")})`;
  };
  rows.forEach((r, ri) => {
    const idx = cols.map(g => Hm.genres.indexOf(g));
    text(c.g, x0 - 10, y0 + ch * (ri + .5) + 4, r.dynasty, { anchor: "end", size: 10.5, fill: INK2 });
    cols.forEach((g, ci) => {
      const v = r.values[idx[ci]];
      E("rect", { x: x0 + ci * cw, y: y0 + ri * ch, width: cw - 1.5, height: ch - 1.5, fill: color(v), rx: 1.5 }, c.g);
      if (v / (totals[ri] || 1) > .06) {
        text(c.g, x0 + ci * cw + cw / 2, y0 + ri * ch + ch / 2 + 3.5, pct(v / totals[ri], 0),
          { anchor: "middle", size: 9, fill: "rgba(255,255,255,.92)" });
      }
      hoverRect(c, x0 + ci * cw, y0 + ri * ch, cw, ch, () =>
        `<b>${r.dynasty} · ${g}</b><br>${fmt(v)} 首（占该朝 ${pct(v / (totals[ri] || 1))}）`);
    });
  });
  cols.forEach((g, ci) => {
    text(c.g, x0 + ci * cw + cw / 2, y0 - 10, g, { anchor: "middle", size: 10, fill: INK2 });
  });
  text(c.g, x1, y1 + 24, "色深＝该体裁在朝内的相对比重（对数色阶）", { anchor: "end", size: 10 });
}

/* ---------- 诗人：rank-size ---------- */
function drawRank() {
  const Pr = D.core.productivity, host = $("c-rank");
  const c = H(host, 560, 360, [22, 20, 46, 56]);
  const { x0, x1, y0, y1 } = c.inner;
  const pts = Pr.rankSize;
  const maxR = pts[pts.length - 1].r, maxN = pts[0].n;
  const x = logScale(1, maxR, x0, x1), y = logScale(1, maxN, y1, y0);
  const xt = x.ticks().filter(t => t >= 1 && t <= maxR);
  const yt = y.ticks().filter(t => t >= 1 && t <= maxN);
  yt.forEach(t => E("line", { x1: x0, x2: x1, y1: y(t), y2: y(t), stroke: LINE, "stroke-dasharray": "2 4", opacity: .5 }, c.g));
  pts.forEach(p => {
    E("circle", { cx: x(p.r), cy: y(p.n), r: 1.5, fill: "#2f5d73", opacity: .55 }, c.g);
  });
  // 拟合线 log n = a + b log r
  const a = Pr.fit.intercept, b = Pr.fit.slope;
  const line = [[1, Math.exp(a + b * 0)], [maxR, Math.exp(a + b * Math.log(maxR))]];
  E("line", { x1: x(line[0][0]), y1: y(line[0][1]), x2: x(line[1][0]), y2: y(line[1][1]),
    stroke: "#b23a2f", "stroke-width": 2, "stroke-dasharray": "6 4" }, c.g);
  x.ticks = xt; y.ticks = yt;
  axisBottom(c.g, x, y1, { ticks: xt, format: t => fmt(t) });
  axisLeft(c.g, x0, y, { ticks: yt, format: t => fmt(t) });
  text(c.g, x1 - 4, y0 + 14, `拟合斜率 −${Pr.fit.alpha.toFixed(2)}　R²=${Pr.fit.r2.toFixed(3)}`, { anchor: "end", size: 11, fill: "#b23a2f" });
  text(c.g, (x0 + x1) / 2, y1 + 34, "诗人排名（对数）", { anchor: "middle", size: 10.5 });
  text(c.g, x0 - 8, y0 - 8, "诗作数（对数）", { anchor: "start", size: 10.5 });
  $("n-rank").textContent = `幂律指数 α≈${Pr.fit.alpha.toFixed(2)}（R²=${Pr.fit.r2.toFixed(3)}），`
    + `Hill 上尾估计 α≈${Pr.fit.hill_alpha.toFixed(2)}（前 ${Pr.fit.k} 位）。`
    + `前 1% 的诗人写下了全部诗作的 ${pct(Pr.shareTop10pct)}。`;
}

/* ---------- 诗人：洛伦兹 ---------- */
function drawLorenz() {
  const Pr = D.core.productivity, host = $("c-lorenz");
  const c = H(host, 520, 360, [22, 20, 46, 56]);
  const { x0, x1, y0, y1 } = c.inner;
  const x = linear(0, 1, x0, x1), y = linear(0, 1, y1, y0);
  E("line", { x1: x(0), y1: y(0), x2: x(1), y2: y(1), stroke: INK3, "stroke-dasharray": "5 4", "stroke-width": 1.2 }, c.g);
  const pts = Pr.lorenz.map(p => [x(p.p), y(p.c)]);
  E("path", { d: pathFrom(pts, true), fill: "rgba(178,58,47,.10)" }, c.g);
  E("path", { d: pathFrom(pts), fill: "none", stroke: "#b23a2f", "stroke-width": 2.2 }, c.g);
  [0, .25, .5, .75, 1].forEach(t => {
    text(c.g, x(t), y1 + 18, pct(t, 0), { anchor: "middle", size: 10 });
    text(c.g, x0 - 8, y(t) + 4, pct(t, 0), { anchor: "end", size: 10 });
  });
  text(c.g, (x0 + x1) / 2, y1 + 36, "诗人累计占比", { anchor: "middle", size: 10.5 });
  text(c.g, x0 - 8, y0 - 8, "诗作累计占比", { anchor: "start", size: 10.5 });
  text(c.g, x(0.72), y(0.30), "完全平等线", { size: 10, fill: INK3 });
  text(c.g, x(0.55), y(0.62), `Gini = ${Pr.gini.toFixed(3)}`, { size: 15, fill: "#b23a2f", weight: 600 });
  $("n-lorenz").textContent = `前 10 位诗人占全部诗作的 ${pct(Pr.thresholds[0].share)}，`
    + `前 100 位占 ${pct(Pr.thresholds[1].share)}，前 1000 位占 ${pct(Pr.thresholds[2].share)}。`;
}

/* ---------- 诗人：直方图 ---------- */
function drawHist() {
  const Pr = D.core.productivity, host = $("c-hist");
  const c = H(host, 520, 330, [22, 20, 46, 56]);
  const { x0, x1, y0, y1 } = c.inner;
  const bins = Pr.histogram;
  const x = logScale(1, bins[bins.length - 1].hi, x0, x1);
  const y = linear(0, Math.max(...bins.map(b => b.count)) * 1.06, y1, y0);
  const bw = (x1 - x0) / bins.length;
  bins.forEach((b, i) => {
    const xa = x0 + (x1 - x0) * i / bins.length + 1;
    const h = y1 - y(Math.max(b.count, 0));
    E("rect", { x: xa, y: y1 - h, width: bw - 2.5, height: h, fill: "#2f5d73", opacity: .78, rx: 1.5 }, c.g);
    hoverRect(c, xa, y0, bw - 2.5, y1 - y0, () =>
      `<b>${b.lo}–${b.hi - 1} 首</b><br>${fmt(b.count)} 位诗人`);
    if (b.count > 0 && i % 2 === 0) {
      text(c.g, xa + bw / 2, y1 + 16, `${b.lo}+`, { anchor: "middle", size: 9.5 });
    }
  });
  const yt = ticks(0, Math.max(...bins.map(b => b.count)) * 1.06, 4);
  yt.forEach(t => text(c.g, x0 - 8, y(t) + 4, fmt(t), { anchor: "end", size: 10 }));
  text(c.g, (x0 + x1) / 2, y1 + 34, "诗作数（对数分箱）", { anchor: "middle", size: 10.5 });
}

/* ---------- 诗人：Top 40 ---------- */
function drawTop() {
  const T = D.core.productivity.top.slice(0, 30), host = $("c-top");
  const W = 620, Hh = 30 + T.length * 16;
  const c = H(host, W, Hh, [8, 80, 26, 104]);
  const { x0, x1, y0, y1 } = c.inner;
  const max = T[0].poems;
  const bh = (y1 - y0) / T.length;
  T.forEach((p, i) => {
    const w = (x1 - x0) * p.poems / max;
    const yy = y0 + i * bh;
    const r = E("rect", { x: x0, y: yy + 1.5, width: Math.max(w, 1.5), height: bh - 3, fill: periodColor(p.period), opacity: .82, rx: 1 }, c.g);
    r.addEventListener("mousemove", e => c.show(`<b>${p.name}</b>（${p.dynasty}）<br>诗作 ${fmt(p.poems)} 首`, e));
    r.addEventListener("mouseleave", () => c.hide());
    text(c.g, x0 - 6, yy + bh / 2 + 3.2, p.name, { anchor: "end", size: 10, fill: INK2 });
    text(c.g, x0 + w + 5, yy + bh / 2 + 3.2, fmt(p.poems), { size: 9.5, fill: INK3 });
  });
}

/* ---------- 诗人：雷达 ---------- */
function drawRadar(profile) {
  const host = $("c-radar");
  const genres = Object.entries(profile.genres).sort((a, b) => b[1] - a[1]).slice(0, 6);
  if (genres.length < 3) {
    host.className = "chart";
    host.innerHTML = `<div class="loading" style="height:300px;text-align:center;line-height:1.9">体裁结构不可用<br><span style="font-size:12px">该诗人的题名列表被 Excel 单元格长度截断，仅剩单一文体</span></div>`;
    return;
  }
  const c = H(host, 420, 340, [10, 10, 10, 10]);
  const cx = 210, cy = 165, R = 118;
  const n = genres.length || 1;
  const ang = i => -Math.PI / 2 + i * 2 * Math.PI / n;
  const max = Math.max(...genres.map(g => g[1])) || 1;
  [.25, .5, .75, 1].forEach(t => {
    const pts = [];
    for (let i = 0; i < n; i++) pts.push([cx + R * t * Math.cos(ang(i)), cy + R * t * Math.sin(ang(i))]);
    E("path", { d: pathFrom(pts, true), fill: "none", stroke: LINE, "stroke-dasharray": "2 3" }, c.g);
  });
  genres.forEach((g, i) => {
    E("line", { x1: cx, y1: cy, x2: cx + R * Math.cos(ang(i)), y2: cy + R * Math.sin(ang(i)), stroke: LINE }, c.g);
    const lx = cx + (R + 24) * Math.cos(ang(i)), ly = cy + (R + 24) * Math.sin(ang(i));
    text(c.g, lx, ly + 3, g[0], { anchor: Math.abs(Math.cos(ang(i))) < .3 ? "middle" : (Math.cos(ang(i)) > 0 ? "start" : "end"), size: 10.5, fill: INK2 });
    text(c.g, lx, ly + 15, fmt(g[1]), { anchor: Math.abs(Math.cos(ang(i))) < .3 ? "middle" : (Math.cos(ang(i)) > 0 ? "start" : "end"), size: 9, fill: INK3 });
  });
  const pts = genres.map((g, i) => [cx + R * g[1] / max * Math.cos(ang(i)), cy + R * g[1] / max * Math.sin(ang(i))]);
  E("path", { d: pathFrom(pts, true), fill: "rgba(178,58,47,.16)", stroke: "#b23a2f", "stroke-width": 2 }, c.g);
  pts.forEach(p => E("circle", { cx: p[0], cy: p[1], r: 3.2, fill: "#b23a2f" }, c.g));
  text(c.g, cx, 320, "体裁结构（前六种）", { anchor: "middle", size: 10.5 });
}

/* ---------- 语言：横条 ---------- */
function drawBars(hostId, items, key, labelKey, color, opts = {}) {
  const host = $(hostId);
  const W = opts.w || 520, rows = items.length;
  const Hh = 26 + rows * (opts.rowH || 15.5);
  const c = H(host, W, Hh, [10, 46, 24, opts.padL || 44]);
  const { x0, x1, y0, y1 } = c.inner;
  const max = Math.max(...items.map(i => i[key]));
  const bh = (y1 - y0) / rows;
  items.forEach((it, i) => {
    const w = (x1 - x0) * it[key] / max;
    const yy = y0 + i * bh;
    const r = E("rect", { x: x0, y: yy + 1.2, width: Math.max(w, 1), height: bh - 2.2, fill: color, opacity: .78, rx: 1 }, c.g);
    r.addEventListener("mousemove", e => c.show(`<b>${it[labelKey]}</b><br>${fmt(it[key])} 次`, e));
    r.addEventListener("mouseleave", () => c.hide());
    text(c.g, x0 - 5, yy + bh / 2 + 3.2, it[labelKey], { anchor: "end", size: 10, fill: INK2 });
    text(c.g, x0 + w + 4, yy + bh / 2 + 3.2, fmt(it[key]), { size: 9, fill: INK3 });
  });
}

/* ---------- 语言：特征词 ---------- */
let currentPeriod = null;
function drawTerms(per) {
  currentPeriod = per;
  const T = D.text, host = $("c-terms");
  const rec = T.periodTerms[per];
  if (!rec || (!rec.pos.length && !rec.neg.length)) {
    host.innerHTML = `<div class="loading">「${per}」可切词的诗题不足，无法估计特征词</div>`;
    $("n-terms").textContent = "该时期样本过少（多为文、赋、颂类标题），故不展示。";
    return;
  }
  host.innerHTML = "";
  const pos = rec.pos.slice(0, 14), neg = rec.neg.slice(0, 8);
  const items = neg.map(r => ({ ...r, neg: true })).concat(pos.map(r => ({ ...r, neg: false })));
  const W = 1080, rows = items.length;
  const c = H(host, W, 40 + rows * 25, [12, 150, 34, 150]);
  const { x0, x1, y0, y1 } = c.inner;
  const maxPos = Math.max(...pos.map(i => Math.abs(i.z)), 2);
  const maxNeg = Math.max(...neg.map(i => Math.abs(i.z)), 2);
  const maxAll = Math.max(maxPos, maxNeg);
  const zero = x0 + (x1 - x0) * 0.5;
  const half = zero - x0;
  const len = z => half * Math.sqrt(Math.abs(z) / maxAll);
  items.forEach((it, i) => {
    const yy = y0 + i * 25;
    const w = len(it.z);
    const xx = it.z > 0 ? zero : zero - w;
    const r = E("rect", { x: xx, y: yy + 3, width: Math.max(w, 1.5), height: 17,
      fill: it.z > 0 ? "#b23a2f" : "#2f5d73", opacity: .8, rx: 2 }, c.g);
    r.addEventListener("mousemove", e => c.show(
      `<b>${it.w}</b><br>z = ${it.z} · 该期 ${fmt(it.f)} 次<br>相对倍数 ${it.lift}×`, e));
    r.addEventListener("mouseleave", () => c.hide());
    // 词条放在柱子外侧，z 值贴在零轴一侧
    text(c.g, it.z > 0 ? zero + w + 8 : zero - w - 8, yy + 16, it.w,
      { anchor: it.z > 0 ? "start" : "end", size: 12, fill: INK });
    text(c.g, it.z > 0 ? zero + 6 : zero - 6, yy + 15.5, it.z.toFixed(1),
      { anchor: it.z > 0 ? "start" : "end", size: 9.5, fill: "rgba(255,255,255,.9)" });
  });
  E("line", { x1: zero, x2: zero, y1: y0 - 4, y2: y1, stroke: INK3, "stroke-width": 1 }, c.g);
  text(c.g, zero, y1 + 22, "← 偏少于其他时期　　　z 值　　　偏多于其他时期 →", { anchor: "middle", size: 10 });
  text(c.g, x0, y0 - 6, "被冷落的词", { size: 10.5 });
  text(c.g, x1, y0 - 6, "被偏爱的词", { anchor: "end", size: 10.5 });
  $("n-terms").textContent = `${per}：共 ${fmt(rec.pos.length)} 条显著词条；`
    + `最强偏好「${pos[0].w}」（z=${pos[0].z}，${pos[0].lift}×）。`;
}

/* ---------- 语言：生命周期 ---------- */
function drawLife() {
  const L = D.extra.life, host = $("c-life");
  const cols = 2;
  const cw = 290, chh = 150;
  const W = 46 + cols * cw, Hh = 34 + Math.ceil(L.terms.length / cols) * chh;
  const c = H(host, W, Hh, [16, 16, 22, 44]);
  const centers = L.bins.slice(0, -1).map((b, i) => (b + L.bins[i + 1]) / 2);
  const maxRate = Math.max(...L.terms.flatMap(t => t.rate));
  L.terms.forEach((t, i) => {
    const cx0 = c.inner.x0 + (i % cols) * cw;
    const cy0 = c.inner.y0 + Math.floor(i / cols) * chh;
    const gw = cw - 20, gh = chh - 34;
    const x = linear(centers[0], centers[centers.length - 1], cx0, cx0 + gw);
    const y = linear(0, Math.max(...t.rate) * 1.15, cy0 + gh, cy0);
    E("line", { x1: cx0, x2: cx0 + gw, y1: cy0 + gh, y2: cy0 + gh, stroke: LINE }, c.g);
    const pts = t.rate.map((v, j) => [x(centers[j]), y(v)]);
    E("path", { d: pathFrom(pts), fill: "none", stroke: "#2f5d73", "stroke-width": 1.6 }, c.g);
    const pk = t.rate.indexOf(Math.max(...t.rate));
    E("circle", { cx: pts[pk][0], cy: pts[pk][1], r: 3, fill: "#b23a2f" }, c.g);
    text(c.g, cx0, cy0 - 6, t.w, { size: 13, fill: INK, weight: 600 });
    text(c.g, cx0 + gw, cy0 - 6, "峰值 " + L.bins[pk] + " 年", { anchor: "end", size: 9, fill: INK3 });
    text(c.g, cx0, cy0 + gh + 16, "每 50 年 · 千分比（纵轴各自归一）", { size: 8.5, fill: INK3 });
  });
}

/* ---------- 网络渲染器 ---------- */
function drawNetwork(hostId, nodes, links, opts) {
  const host = $(hostId);
  const W = opts.w || 520, Hh = opts.h || 420;
  const c = H(host, W, Hh, [12, 12, 12, 12]);
  const { x0, x1, y0, y1 } = c.inner;
  const ox = (x0 + x1) / 2, oy = (y0 + y1) / 2;
  // 按 90 分位缩放，避免个别离群点把主体压成一小团
  const q = (arr, p) => { const a = arr.slice().sort((m, n) => m - n); return a[Math.min(a.length - 1, Math.floor(a.length * p))] || 1; };
  const sx = Math.max(q(nodes.map(n => Math.abs(n.x)), 0.9), 1e-6);
  const sy = Math.max(q(nodes.map(n => Math.abs(n.y)), 0.9), 1e-6);
  const clamp = v => Math.max(-1, Math.min(1, v));
  const px = p => ox + clamp(p.x / sx) * (x1 - x0) * .46;
  const py = p => oy + clamp(p.y / sy) * (y1 - y0) * .46;
  const byId = {};
  nodes.forEach(n => byId[n.id] = n);
  const linkG = E("g", {}, c.g);
  const nodeG = E("g", {}, c.g);
  const maxW = Math.max(...links.map(l => l.w));
  links.forEach(l => {
    const a = byId[l.source], b = byId[l.target];
    if (!a || !b) return;
    E("line", {
      x1: px(a), y1: py(a), x2: px(b), y2: py(b),
      stroke: opts.linkColor || "rgba(90,80,60,.22)",
      "stroke-width": 0.5 + 2.2 * (l.w / maxW),
    }, linkG);
  });
  const maxF = Math.max(...nodes.map(n => n.f || n.poems || 1));
  nodes.forEach(n => {
    const r = opts.rFn ? opts.rFn(n) : 3 + 11 * Math.sqrt((n.f || 1) / maxF);
    const g = E("g", {}, nodeG);
    const circle = E("circle", { cx: px(n), cy: py(n), r, fill: opts.color(n), opacity: .85, stroke: "#fffdf8", "stroke-width": 1 }, g);
    circle.addEventListener("mousemove", e => c.show(opts.tip(n), e));
    circle.addEventListener("mouseleave", () => { c.hide(); nodeG.style.opacity = 1; });
    if (opts.label !== false && (!opts.labelFn || opts.labelFn(n))) {
      const t = text(c.g, px(n) + r + 2.5, py(n) + 3.4, n.id, { size: opts.labelSize || 9.5, fill: INK2 });
      t.setAttribute("style", "paint-order:stroke;stroke:#fffdf8;stroke-width:2.6px;stroke-linejoin:round");
    }
  });
  return c;
}

/* ---------- 主题 ---------- */
const TOPIC_NAMES = ["纪游·行旅","病中·述怀","仕宦·纪程","岁时·节令","独处·感怀","山居·即事","唱和·奉酬","怀古·访胜","雅集·饯别","咏花·赠答"];
function renderTopics() {
  const T = D.topics;
  const cards = $("topic-cards");
  cards.innerHTML = T.topics.map((t, i) => {
    const name = TOPIC_NAMES[i] || ("主题 " + i);
    const words = t.words.slice(0, 8).map(w => w.w).join(" · ");
    return `<div class="topic">
      <h4>${name}<span style="float:right;font-size:11px;color:var(--ink3)">${pct(t.share)}</span></h4>
      <div class="bar"><i style="width:${Math.min(100, t.share / Math.max(...T.topics.map(x => x.share)) * 100)}%"></i></div>
      <p>${words}</p>
      <p style="color:var(--ink3);margin-top:6px">一致性 ${t.coherence}</p>
    </div>`;
  }).join("");

  // 主题×时期
  const host = $("c-topicheat");
  const periods = D.core.periods.map(p => p.period);
  const W = 620, Hh = 30 + T.K * 26 + 44;
  const c = H(host, W, Hh, [10, 14, 40, 96]);
  const { x0, x1, y0, y1 } = c.inner;
  const cw = (x1 - x0) / periods.length, ch = (y1 - y0) / T.K;
  const maxv = Math.max(...T.byPeriod.flatMap(r => Object.values(r)));
  periods.forEach((p, ci) => {
    text(c.g, x0 + ci * cw + cw / 2, y0 - 8, p, { anchor: "middle", size: 9.5 });
  });
  T.topics.forEach((t, ri) => {
    text(c.g, x0 - 6, y0 + ch * (ri + .5) + 3.5, TOPIC_NAMES[ri] || ("T" + ri), { anchor: "end", size: 9.5, fill: INK2 });
    periods.forEach((p, ci) => {
      const v = T.byPeriod[ri][p] || 0;
      const a = Math.pow(v / maxv, .8);
      E("rect", { x: x0 + ci * cw, y: y0 + ri * ch, width: cw - 1.5, height: ch - 1.5, rx: 1.5, fill: `rgba(47,93,115,${0.08 + a * .85})` }, c.g);
      if (a > .55) text(c.g, x0 + ci * cw + cw / 2, y0 + ri * ch + ch / 2 + 3, pct(v, 0), { anchor: "middle", size: 8.5, fill: "#fff" });
      hoverRect(c, x0 + ci * cw, y0 + ri * ch, cw, ch, () => `<b>${TOPIC_NAMES[ri]} · ${p}</b><br>平均 θ = ${v}`);
    });
  });

  // 规模 + 一致性
  const host2 = $("c-topicshare");
  const c2 = H(host2, 480, 30 + T.K * 28, [12, 60, 30, 120]);
  const { x0: a0, x1: a1, y0: b0, y1: b1 } = c2.inner;
  const maxShare = Math.max(...T.topics.map(t => t.share));
  const bh = (b1 - b0) / T.K;
  T.topics.forEach((t, i) => {
    const w = (a1 - a0) * t.share / maxShare;
    const yy = b0 + i * bh;
    E("rect", { x: a0, y: yy + 3, width: w, height: bh - 10, fill: "#b23a2f", opacity: .75, rx: 2 }, c2.g);
    text(c2.g, a0 - 5, yy + bh / 2 + 3, TOPIC_NAMES[i] || ("T" + i), { anchor: "end", size: 9.5, fill: INK2 });
    text(c2.g, a0 + w + 4, yy + bh / 2 + 3, pct(t.share), { size: 9, fill: INK3 });
    const cx = a0 + (a1 - a0) * (t.coherence + 6) / 12;
    E("circle", { cx, cy: yy + bh / 2, r: 3, fill: "#2f5d73" }, c2.g);
  });
  text(c2.g, a1, b1 + 18, "● 一致性分数（右侧标尺 −6…6）", { anchor: "end", size: 9.5, fill: INK3 });
  $("n-topics").textContent = `平均一致性 ${T.meanCoherence}（UMass，越高越好）；样本 ${fmt(T.docs)} 条诗题，词表 ${fmt(T.vocab)} 词。`;

  // 代表诗题
  const host3 = $("c-topictitles");
  host3.className = "";
  host3.innerHTML = `<div style="display:grid;grid-template-columns:repeat(2,1fr);gap:10px 26px;font-size:12.5px">
    ${T.titles.map((arr, i) => `<div><b style="color:var(--accent)">${TOPIC_NAMES[i]}</b><br>
      ${arr.slice(0, 3).map(x => `· ${x.title.length > 32 ? x.title.slice(0, 32) + "…" : x.title}${x.poet ? ` <span style="color:var(--ink3)">（${x.poet}）</span>` : ""}`).join("<br>")}
    </div>`).join("")}</div>`;
}

/* ---------- 地理 ---------- */
function drawGeo() {
  const G = D.geo;
  drawBars("c-prov", G.provinces.slice(0, 22).map(p => ({ name: p.name, count: p.count, places: p.places })),
    "count", "name", "#5b7c5a", { w: 540, rowH: 17, padL: 70 });

  // places
  const host = $("c-places");
  const items = G.topPlaces.slice(0, 26);
  const c = H(host, 540, 30 + items.length * 16, [10, 70, 26, 86]);
  const { x0, x1, y0, y1 } = c.inner;
  const max = items[0].count, bh = (y1 - y0) / items.length;
  items.forEach((p, i) => {
    const w = (x1 - x0) * p.count / max, yy = y0 + i * bh;
    const r = E("rect", { x: x0, y: yy + 1.4, width: Math.max(w, 1), height: bh - 2.4, fill: "#a9823f", opacity: .8, rx: 1 }, c.g);
    r.addEventListener("mousemove", e => c.show(`<b>${p.place}</b>（${p.region}）<br>${fmt(p.count)} 次`, e));
    r.addEventListener("mouseleave", () => c.hide());
    text(c.g, x0 - 5, yy + bh / 2 + 3.2, p.place, { anchor: "end", size: 10.5, fill: INK2 });
    text(c.g, x0 + w + 4, yy + bh / 2 + 3.2, fmt(p.count), { size: 9, fill: INK3 });
  });

  // 地名时代曲线：小多图（各自纵轴）
  const periods = G.periods;
  const top8 = G.topPlaces.slice(0, 8);
  const host2 = $("c-geotime");
  const cols = 4, cw = 250, chh = 150;
  const c2 = H(host2, 40 + cols * cw, 34 + Math.ceil(top8.length / cols) * chh, [18, 14, 12, 44]);
  const totals = periods.map(p => D.core.periods.find(q => q.period === p).parsed);
  top8.forEach((p, i) => {
    const series = periods.map((q, j) => (p.byPeriod[q] || 0) / totals[j] * 1000);
    const gx = c2.inner.x0 + (i % cols) * cw;
    const gy = c2.inner.y0 + Math.floor(i / cols) * chh;
    const gw = cw - 24, gh = chh - 40;
    const x = linear(0, periods.length - 1, gx, gx + gw);
    const y = linear(0, Math.max(...series) * 1.18 || 1, gy + gh, gy);
    E("line", { x1: gx, x2: gx + gw, y1: gy + gh, y2: gy + gh, stroke: LINE }, c2.g);
    const col = COM_COLORS[i % 4];
    const pts = series.map((v, j) => [x(j), y(v)]);
    E("path", { d: smoothPath(pts), fill: "none", stroke: col, "stroke-width": 1.7 }, c2.g);
    const pk = series.indexOf(Math.max(...series));
    E("circle", { cx: pts[pk][0], cy: pts[pk][1], r: 3, fill: "#b23a2f" }, c2.g);
    text(c2.g, gx, gy - 5, p.place, { size: 12.5, fill: INK, weight: 600 });
    text(c2.g, gx + gw, gy - 5, `峰值 ${periods[pk]} · ${series[pk].toFixed(1)}‰`, { anchor: "end", size: 8.5, fill: INK3 });
    text(c2.g, gx, gy + gh + 13, "先秦 → 近现代", { size: 8, fill: INK3 });
    pts.forEach((pt, j) => {
      const cc = E("circle", { cx: pt[0], cy: pt[1], r: 4.5, fill: "transparent" }, c2.g);
      cc.addEventListener("mousemove", e => c2.show(`<b>${p.place}</b> · ${periods[j]}<br>每千首 ${series[j].toFixed(2)} 次`, e));
      cc.addEventListener("mouseleave", () => c2.hide());
    });
  });
  $("n-geo").textContent = `全部诗题中有 ${pct(G.titleWithPlace)} 至少提及一处地名；`
    + `最常出现的三个地名是 ${G.topPlaces.slice(0, 3).map(p => p.place).join("、")}。`;
}

/* ---------- 初始化与交互 ---------- */
function setKpis() {
  const S = D.core.summary;
  const vals = [
    [fmt(S.persons), "诗人"],
    [fmt(S.poems), "诗作（原表）"],
    [fmt(S.parsed), "已解析诗题"],
    [S.genres, "种体裁"],
    [S.gini.toFixed(3), "产量基尼系数"],
    [pct(S.harmonyRate), "唱和题名占比"],
  ];
  $("kpis").innerHTML = vals.map(v => `<div class="kpi"><b>${v[0]}</b><span>${v[1]}</span></div>`).join("");
  $("gen-date").textContent = new Date().toISOString().slice(0, 10);
}

function setupPoetSearch() {
  const P = D.poets.profiles;
  const byName = {};
  P.forEach(p => { if (!byName[p.name]) byName[p.name] = p; });
  const show = p => {
    $("poet-name").textContent = p.name;
    $("poet-meta").textContent = `${p.dynasty} · ${p.period} · 诗作 ${fmt(p.poems)} 首`
      + (p.parsed && p.parsed < p.poems * 0.92 ? `（原表题名受单元格长度限制，仅解析 ${fmt(p.parsed)} 条）` : "")
      + ` · 唱和题名 ${pct(p.harmony)}`;
    $("poet-words").innerHTML = p.words.map(w => `<span>${w.w} ${w.f}</span>`).join("");
    $("poet-titles").innerHTML = p.titles.map(t => `<li>${t.t}<span>${t.g}</span></li>`).join("");
    drawRadar(p);
  };
  show(P.find(p => p.name === "杜甫") || P[0]);
  const input = $("poet-search");
  input.addEventListener("input", () => {
    const q = input.value.trim();
    if (!q) return;
    const hit = P.find(p => p.name === q) || P.find(p => p.name.includes(q));
    if (hit) { show(hit); $("poet-hint").textContent = ""; }
    else $("poet-hint").textContent = "未收录（档案只含产量前 1200 位）";
  });
  $("poet-hint").textContent = `共收录 ${fmt(P.length)} 位高产诗人（可试：杜甫、李白、苏轼、白居易）`;
}

function setupChips() {
  const host = $("period-chips");
  const periods = D.text.periods;
  host.innerHTML = periods.map((p, i) =>
    `<span class="chip ${i === 4 ? "active" : ""}" data-period="${p}">${p}</span>`).join("");
  host.querySelectorAll(".chip").forEach(ch => ch.addEventListener("click", () => {
    host.querySelectorAll(".chip").forEach(x => x.classList.remove("active"));
    ch.classList.add("active");
    drawTerms(ch.dataset.period);
  }));
  drawTerms(periods[4] || periods[0]);
}

function renderDownloads() {
  const files = [
    ["01_分期统计.csv", "九个时期的规模、体裁构成、基尼与唱和率"],
    ["02_体裁统计.csv", "18 种体裁的篇数与作者数"],
    ["03_诗人产量Top500.csv", "产量最高的五百位诗人"],
    ["04_高频词Top300.csv", "自动发现词条的词频"],
    ["05_分期特征词.csv", "log-odds z 值全表"],
    ["06_主题模型_词分布.csv", "十个主题 × 词的概率矩阵"],
    ["07_地名统计.csv", "地名与今省区对应次数"],
    ["08_诗人档案Top1200.csv", "体裁结构与常用词"],
  ];
  $("downloads").innerHTML = files.map(f =>
    `<a href="tables/${encodeURI(f[0])}" download><b>${f[0]}</b><span>${f[1]}</span></a>`).join("");
}

const rendered = new Set();
function renderView(name) {
  if (rendered.has(name)) return;
  rendered.add(name);
  if (name === "overview") { drawScale(); drawDonut(); drawStream(); drawHeat(); }
  if (name === "poets") { drawRank(); drawLorenz(); drawHist(); drawTop(); setupPoetSearch(); }
  if (name === "language") {
    drawBars("c-chars", D.text.charsTop.slice(0, 26).map(x => ({ name: x.c, count: x.f })), "count", "name", "#2f5d73", { w: 500, rowH: 15 });
    drawBars("c-words", D.text.wordsTop.slice(0, 26), "f", "w", "#b23a2f", { w: 500, rowH: 15 });
    setupChips(); drawLife();
    const NF = D.net.nodes.map(n => n.f), F0 = Math.min(...NF), F1 = Math.max(...NF);
    const ramp = ["#9fb6bd", "#7f9aa5", "#5d7f8c", "#3d6170"];
    const fcol = f => ramp[Math.min(3, Math.floor((f - F0) / (F1 - F0 + 1e-9) * 4))];
    const netTop = new Set(D.net.nodes.slice().sort((a, b) => b.f - a.f).slice(0, 26).map(n => n.id));
    drawNetwork("c-net", D.net.nodes, D.net.links, {
      w: 480, h: 440, color: n => fcol(n.f),
      rFn: n => 3 + 10 * Math.sqrt((n.deg || 1) / Math.max(...D.net.nodes.map(x => x.deg || 1))),
      tip: n => `<b>${n.id}</b><br>出现 ${fmt(n.f)} 次 · 连边 ${n.deg} 条`,
      labelSize: 9
    });
  }
  if (name === "topics") renderTopics();
  if (name === "networks") {
    const maxP = Math.max(...D.simnet.nodes.map(n => n.poems));
    const big = new Set(D.simnet.nodes.slice().sort((a, b) => b.poems - a.poems).slice(0, 30).map(n => n.id));
    drawNetwork("c-simnet", D.simnet.nodes, D.simnet.links, {
      w: 1080, h: 560, color: n => periodColor(n.period),
      rFn: n => 2.4 + 10 * Math.sqrt(n.poems / maxP),
      tip: n => `<b>${n.id}</b>（${n.dynasty}）<br>诗作 ${fmt(n.poems)} 首<br>社区 ${n.comm + 1}`,
      labelSize: 9.5, linkColor: "rgba(120,100,70,.16)",
      labelFn: n => big.has(n.id)
    });
    // 唱和
    const P = D.core.periods, host = $("c-harmony");
    const c = H(host, 520, 320, [20, 20, 44, 52]);
    const { x0, x1, y0, y1 } = c.inner;
    const x = linear(0, P.length - 1, x0, x1);
    const maxr = Math.max(...P.map(p => p.harmony_rate)) * 1.15;
    const y = linear(0, maxr, y1, y0);
    ticks(0, maxr, 4).forEach(t => {
      E("line", { x1: x0, x2: x1, y1: y(t), y2: y(t), stroke: LINE, "stroke-dasharray": "2 4", opacity: .5 }, c.g);
      text(c.g, x0 - 8, y(t) + 4, pct(t, 0), { anchor: "end", size: 10 });
    });
    const pts = P.map((p, i) => [x(i), y(p.harmony_rate)]);
    E("path", { d: smoothPath(pts), fill: "none", stroke: "#b23a2f", "stroke-width": 2.2 }, c.g);
    pts.forEach((pt, i) => {
      E("circle", { cx: pt[0], cy: pt[1], r: 3.5, fill: "#fffdf8", stroke: "#b23a2f", "stroke-width": 1.8 }, c.g);
      text(c.g, pt[0], y1 + 17, P[i].period, { anchor: "middle", size: 9.5 });
    });
    text(c.g, (x0 + x1) / 2, y1 + 36, "按时期（题名含唱和/寄赠语汇的比例）", { anchor: "middle", size: 10 });

    // 熵 vs 产量
    const E2 = D.extra, host2 = $("c-entropy");
    const c2 = H(host2, 520, 320, [20, 20, 44, 56]);
    const { x0: a0, x1: a1, y0: b0, y1: b1 } = c2.inner;
    const xs = E2.points.map(p => p.x), es = E2.points.map(p => p.e);
    const x2 = logScale(4, Math.max(...xs) * 1.1, a0, a1);
    const y2 = linear(0, Math.max(...es) * 1.05, b1, b0);
    E2.points.forEach(p => {
      E("circle", { cx: x2(p.x), cy: y2(p.e), r: 2.2, fill: periodColor(p.p), opacity: .45 }, c2.g);
    });
    x2.ticks = x2.ticks().filter(t => t >= 4);
    axisBottom(c2.g, x2, b1, { ticks: x2.ticks.filter(t => t <= Math.max(...xs) * 1.1), format: t => fmt(t) });
    ticks(0, Math.max(...es) * 1.05, 4).forEach(t => {
      text(c2.g, a0 - 8, y2(t) + 4, t.toFixed(1), { anchor: "end", size: 10 });
      E("line", { x1: a0, x2: a1, y1: y2(t), y2: y2(t), stroke: LINE, "stroke-dasharray": "2 4", opacity: .4 }, c2.g);
    });
    text(c2.g, (a0 + a1) / 2, b1 + 32, "诗作数（对数）", { anchor: "middle", size: 10.5 });
    text(c2.g, a0 - 8, b0 - 8, "体裁熵 H", { size: 10.5 });
    const r = corr(xs.map(Math.log), es);
    $("n-entropy").textContent = `样本 ${fmt(E2.n)} 位诗人（诗作 ≥4）；产量与体裁熵的皮尔逊相关 r=${r.toFixed(3)}（对产量取对数）。`;
    $("n-simnet").textContent = `共 ${D.simnet.nodes.length} 位诗人、${D.simnet.links.length} 条边；`
      + `边权重为 TF-IDF 余弦相似度（≥${D.simnet.threshold}）。同一时期的人往往自然聚在一起，但跨代的影响线也清晰可见。`;
  }
  if (name === "geo") drawGeo();
  if (name === "data") renderDownloads();
}

function corr(a, b) {
  const n = a.length;
  const ma = a.reduce((s, x) => s + x, 0) / n, mb = b.reduce((s, x) => s + x, 0) / n;
  let sa = 0, sb = 0, sab = 0;
  for (let i = 0; i < n; i++) { const da = a[i] - ma, db = b[i] - mb; sa += da * da; sb += db * db; sab += da * db; }
  return sab / Math.sqrt(sa * sb);
}

/* ---------- 启动 ---------- */
async function boot() {
  const names = ["core", "text", "topics", "geo", "poets", "net", "simnet", "extra"];
  try {
    const jsons = await Promise.all(names.map(n => fetch(`data/${n}.json`).then(r => {
      if (!r.ok) throw new Error(n);
      return r.json();
    })));
    names.forEach((n, i) => D[n] = jsons[i]);
  } catch (e) {
    console.error("[boot] 数据加载失败", e);
    document.querySelectorAll(".chart").forEach(c => c.innerHTML = `<div class="loading">数据加载失败：${e.message}</div>`);
    return;
  }
  setKpis();
  const activate = name => {
    if (!document.getElementById("view-" + name)) return;
    document.querySelectorAll("#tabs button").forEach(b => b.classList.toggle("active", b.dataset.view === name));
    document.querySelectorAll("section.view").forEach(s => s.classList.remove("active"));
    $("view-" + name).classList.add("active");
    renderView(name);
  };
  document.querySelectorAll("#tabs button").forEach(btn => btn.addEventListener("click", () => {
    activate(btn.dataset.view);
    history.replaceState(null, "", "#" + btn.dataset.view);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }));
  const hash = (location.hash || "").replace("#", "");
  if (hash && document.getElementById("view-" + hash)) activate(hash);
  else renderView("overview");
}
boot();
