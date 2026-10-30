/* 无浏览器冒烟测试：用最小 DOM 桩执行 viz.js + app.js，验证所有图表函数不抛异常。 */
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const WEB = path.resolve(__dirname, "..", "docs");

class El {
  constructor(tag) {
    this.tagName = tag; this.children = []; this.attrs = {}; this.style = {};
    this.dataset = {}; this._html = ""; this.textContent = ""; this.parentNode = null;
    this.classList = { add() {}, remove() {}, contains() { return false; } };
    this._listeners = {};
  }
  setAttribute(k, v) { this.attrs[k] = v; }
  getAttribute(k) { return this.attrs[k]; }
  appendChild(c) { this.children.push(c); c.parentNode = this; return c; }
  removeChild(c) { this.children = this.children.filter(x => x !== c); }
  addEventListener(t, f) { (this._listeners[t] = this._listeners[t] || []).push(f); }
  set innerHTML(v) { this._html = v; }
  get innerHTML() { return this._html; }
  getBoundingClientRect() { return { left: 0, top: 0, width: 900, height: 420 }; }
  querySelectorAll() { return []; }
  querySelector() { return null; }
  get firstChild() { return this.children[0] || null; }
}

const nodes = {};
const document = {
  createElementNS: (ns, tag) => new El(tag),
  createElement: tag => new El(tag),
  getElementById: id => (nodes[id] = nodes[id] || new El("div")),
  querySelectorAll: () => [],
  querySelector: () => null,
  body: new El("body"),
  documentElement: new El("html"),
};
const window = { scrollTo() {}, innerWidth: 1440, addEventListener() {}, location: { href: "http://x/" } };
const sandbox = {
  document, window, console, Math, Date, JSON, Object, Array, Number, String, Boolean,
  isNaN, parseFloat, parseInt, setTimeout, Promise, fetch: async (url) => {
    const p = path.join(WEB, url.replace(/^https?:\/\/[^/]+\//, ""));
    const txt = fs.readFileSync(p, "utf8");
    return { ok: true, json: async () => JSON.parse(txt) };
  },
};
sandbox.globalThis = sandbox;
vm.createContext(sandbox);

for (const f of ["assets/viz.js", "assets/app.js"]) {
  vm.runInContext(fs.readFileSync(path.join(WEB, f), "utf8"), sandbox, { filename: f });
}

process.on("unhandledRejection", e => console.log("UNHANDLED:", e && e.message));
(async () => {
  await new Promise(r => setTimeout(r, 400));
  let ok = 0, fail = 0;
  for (const v of ["overview", "poets", "language", "topics", "networks", "geo", "data"]) {
    try {
      sandbox.renderView(v);
      ok++;
      const ids = Object.keys(nodes).filter(k => nodes[k].children.length > 0).length;
      console.log(`  ${v.padEnd(10)} ok  (svg hosts with content: ${ids})`);
    } catch (e) {
      fail++;
      console.log(`  ${v.padEnd(10)} FAIL ${e.message}\n${String(e.stack).split("\n").slice(1, 4).join("\n")}`);
    }
  }
  console.log(`\nrendered ${ok}/7 views, ${fail} failed`);
  process.exit(fail ? 1 : 0);
})();
