/* ============================================================
   viz.js — 一个零依赖的 SVG 图表工具箱
   (为离线环境编写；无 CDN、无构建步骤)
   ============================================================ */
const NS = "http://www.w3.org/2000/svg";
const PALETTE = ["#b23a2f","#2f5d73","#5b7c5a","#a9823f","#6b4f7a","#8a5a3b","#4f7d7a","#9c6b4f","#7a8450","#8c6d8f"];
const INK = "#1e1a15", INK2 = "#4a4238", INK3 = "#8a7f70", LINE = "#ddd2bf";

function E(tag, attrs, parent) {
  const el = document.createElementNS(NS, tag);
  if (attrs) for (const k in attrs) {
    if (attrs[k] === null || attrs[k] === undefined) continue;
    el.setAttribute(k, attrs[k]);
  }
  if (parent) parent.appendChild(el);
  return el;
}

function fmt(n, digits = 0) {
  if (n === null || n === undefined || isNaN(n)) return "–";
  if (Math.abs(n) >= 1e8) return (n / 1e8).toFixed(2) + " 億";
  if (Math.abs(n) >= 1e4) return (n / 1e4).toFixed(1) + " 萬";
  if (Math.abs(n) < 1 && n !== 0) return n.toFixed(digits || 3);
  return n.toLocaleString("en-US", { maximumFractionDigits: digits });
}
function pct(n, d = 1) { return (n * 100).toFixed(d) + "%"; }

function makeSVG(host, w, h) {
  host.innerHTML = "";
  host.classList.add("chart");
  const svg = E("svg", { viewBox: `0 0 ${w} ${h}`, preserveAspectRatio: "xMidYMid meet" }, host);
  const tip = document.createElement("div");
  tip.className = "tooltip";
  host.appendChild(tip);
  return {
    svg, w, h, host,
    tip,
    show(html, evt) {
      const r = host.getBoundingClientRect();
      tip.innerHTML = html;
      tip.style.opacity = 1;
      tip.style.left = (evt.clientX - r.left) + "px";
      tip.style.top = (evt.clientY - r.top) + "px";
    },
    hide() { tip.style.opacity = 0; },
  };
}

function linear(d0, d1, r0, r1) {
  const k = (r1 - r0) / ((d1 - d0) || 1);
  const f = x => r0 + (x - d0) * k;
  f.inv = y => d0 + (y - r0) / k;
  f.domain = [d0, d1]; f.range = [r0, r1];
  return f;
}
function logScale(d0, d1, r0, r1) {
  const l0 = Math.log10(Math.max(d0, 1e-9)), l1 = Math.log10(d1);
  const f = x => r0 + (Math.log10(Math.max(x, 1e-9)) - l0) / ((l1 - l0) || 1) * (r1 - r0);
  f.inv = y => Math.pow(10, l0 + (y - r0) / (r1 - r0) * (l1 - l0));
  f.domain = [d0, d1]; f.range = [r0, r1];
  f.ticks = (n = 5) => {
    const out = [];
    const start = Math.floor(l0), end = Math.ceil(l1);
    for (let e = start; e <= end; e++) {
      const base = Math.pow(10, e);
      for (const m of [1, 2, 5]) {
        const v = m * base;
        if (v >= Math.pow(10, l0) - 1e-9 && v <= Math.pow(10, l1) + 1e-9) out.push(v);
      }
    }
    return out;
  };
  return f;
}
function ticks(min, max, n = 5) {
  const span = max - min || 1;
  const step0 = span / n;
  const p = Math.pow(10, Math.floor(Math.log10(step0)));
  const err = step0 / p;
  const step = (err >= 7.5 ? 10 : err >= 3.5 ? 5 : err >= 1.5 ? 2 : 1) * p;
  const out = [];
  for (let v = Math.ceil(min / step) * step; v <= max + 1e-9; v += step) out.push(+v.toFixed(10));
  return out;
}

function axisBottom(g, x, y, opts = {}) {
  const tk = opts.ticks || x.ticks && x.ticks();
  E("line", { x1: x.range[0], x2: x.range[1], y1: y, y2: y, stroke: LINE }, g);
  (tk || []).forEach(t => {
    const px = x(t);
    E("line", { x1: px, x2: px, y1: y, y2: y + 4, stroke: LINE }, g);
    const tEl = E("text", { x: px, y: y + 17, "text-anchor": "middle", fill: INK3, "font-size": opts.size || 11 }, g);
    tEl.textContent = opts.format ? opts.format(t) : t;
  });
  if (opts.label) {
    const t = E("text", { x: (x.range[0] + x.range[1]) / 2, y: y + (opts.labelGap || 34), "text-anchor": "middle", fill: INK3, "font-size": 11 }, g);
    t.textContent = opts.label;
  }
}
function axisLeft(g, x, y, opts = {}) {
  E("line", { x1: x, x2: x, y1: y.range[0], y2: y.range[1], stroke: LINE }, g);
  const tk = opts.ticks || [];
  tk.forEach(t => {
    const py = y(t);
    E("line", { x1: x - 4, x2: x, y1: py, y2: py, stroke: LINE }, g);
    const tEl = E("text", { x: x - 8, y: py + 4, "text-anchor": "end", fill: INK3, "font-size": opts.size || 11 }, g);
    tEl.textContent = opts.format ? opts.format(t) : t;
  });
}
function gridY(g, x, y, tk, w) {
  tk.forEach(t => {
    E("line", { x1: x.range[0], x2: x.range[0] + w, y1: y(t), y2: y(t), stroke: LINE, "stroke-dasharray": "2 4", opacity: .65 }, g);
  });
}
function pathFrom(pts, close = false) {
  if (!pts.length) return "";
  let d = `M${pts[0][0].toFixed(2)},${pts[0][1].toFixed(2)}`;
  for (let i = 1; i < pts.length; i++) d += `L${pts[i][0].toFixed(2)},${pts[i][1].toFixed(2)}`;
  return close ? d + "Z" : d;
}
function smoothPath(pts, tension = 0.35) {
  if (pts.length < 2) return pathFrom(pts);
  let d = `M${pts[0][0]},${pts[0][1]}`;
  for (let i = 0; i < pts.length - 1; i++) {
    const p0 = pts[i - 1] || pts[i], p1 = pts[i], p2 = pts[i + 1], p3 = pts[i + 2] || p2;
    const c1x = p1[0] + (p2[0] - p0[0]) * tension / 3, c1y = p1[1] + (p2[1] - p0[1]) * tension / 3;
    const c2x = p2[0] - (p3[0] - p1[0]) * tension / 3, c2y = p2[1] - (p3[1] - p1[1]) * tension / 3;
    d += `C${c1x.toFixed(2)},${c1y.toFixed(2)} ${c2x.toFixed(2)},${c2y.toFixed(2)} ${p2[0].toFixed(2)},${p2[1].toFixed(2)}`;
  }
  return d;
}
function legend(host, items) {
  const d = document.createElement("div");
  d.className = "legend";
  d.innerHTML = items.map(it => `<span><i style="background:${it.color}"></i>${it.label}</span>`).join("");
  host.appendChild(d);
  return d;
}
function text(g, x, y, str, opts = {}) {
  const t = E("text", {
    x, y, "text-anchor": opts.anchor || "start", fill: opts.fill || INK3,
    "font-size": opts.size || 11, "font-weight": opts.weight || 400,
  }, g);
  t.textContent = str;
  return t;
}

/* 生成一条「暖色纸底」的坐标框 */
function frame(host, w, h, pad) {
  const c = makeSVG(host, w, h);
  const g = E("g", {}, c.svg);
  c.g = g;
  c.inner = {
    x0: pad[3], x1: w - pad[1], y0: pad[0], y1: h - pad[2],
  };
  return c;
}
