// Run the preview page's script (path in argv[2]) against stubs and check the focus square: position and colour after
// each state the camera reports. Called by tests/test_fake_camera.py when node is installed.
const fs = require("fs");
const els = {};
const mk = () => ({style: {}, clientWidth: 640, getBoundingClientRect: () => ({left: 0, top: 0}), addEventListener() {}});
for (const id of ["f", "img", "pt", "s", "shot", "shotbox"]) els[id] = mk();
let states = [], t = 0;
const timers = [];
const posts = [];
const ctx = {
  document: {getElementById: id => els[id]},
  fetch: async (url, opts) => { if (opts) posts.push(opts.headers ? url + " " + JSON.stringify(opts.headers) : url); return {status: 200, blob: async () => "img", json: async () => states.shift() || {}}; },
  URL: {createObjectURL: b => "blob:" + b}, alert: m => { throw new Error(m); },
  addEventListener() {}, setInterval: (fn, ms) => timers.push(fn), Date: {now: () => t}, console, location: {search: ""}, URLSearchParams,
  Promise, Math, Array,
};
require("vm").createContext(ctx);
require("vm").runInContext(fs.readFileSync(process.argv[2], "utf8"), ctx);
const base = {aw: 3, ah: 2, cols: 13, rows: 7};
const step = async (label, s, expect) => {
  states = [{...base, ...s}];
  await ctx.refresh();
  const p = els.pt.style;
  const cell = [Math.round((parseFloat(p.left) - 0) / (640 / 13)) + 1, Math.round((parseFloat(p.top) - 640 / 3 * 0.0 - (480 - 640 * 2 / 3) / 2) / (640 * 2 / 3 / 7)) + 1];
  const ok = p.borderColor === expect.colour && cell[0] === expect.col && cell[1] === expect.row;
  console.log((ok ? "ok   " : "FAIL ") + label, p.borderColor, cell.join(","));
  if (!ok) process.exitCode = 1;
};
(async () => {
  await step("idle at the centre", {col: 7, row: 4, af: 0}, {colour: "#fff", col: 7, row: 4});
  els.img.onpointerdown({clientX: 100, clientY: 160});   // a click in column 3, row 3 of the picture
  await step("just clicked, camera still reports the old cell", {col: 7, row: 4, af: 0}, {colour: "#fff", col: 3, row: 3});
  await step("camera reports the new cell, not focused yet", {col: 3, row: 3, af: 0}, {colour: "#fff", col: 3, row: 3});
  await step("focused", {col: 3, row: 3, af: 1}, {colour: "#0f0", col: 3, row: 3});
  await step("focus failed", {col: 3, row: 3, af: 2}, {colour: "#f00", col: 3, row: 3});
  await step("released", {col: 3, row: 3, af: 0}, {colour: "#fff", col: 3, row: 3});
  els.img.onpointerdown({clientX: 500, clientY: 300});   // column 11, row 5
  t = 500;
  await step("second click, camera still on the old cell", {col: 3, row: 3, af: 0}, {colour: "#fff", col: 11, row: 5});
  t = 3000;   // the camera never confirmed: after 2 s the camera's own cell wins again
  await step("click never confirmed", {col: 3, row: 3, af: 0}, {colour: "#fff", col: 3, row: 3});
  // held: "down" is sent again every second until "up"; a repeat that was queued before "up" is dropped
  const tick = () => new Promise(r => setImmediate(r));
  els.img.onpointerup(); await tick();   // let go of the clicks above
  posts.length = 0;
  els.f.onpointerdown(); await tick();
  timers[0](); await tick();              // timers[0] is the repeat, timers[1] the refresh
  timers[0](); els.img.onpointerup(); await tick();
  timers[0](); await tick();              // nothing is held now
  const held = posts.join(" ");
  const ok = held === "/focus/down /focus/down /focus/up";
  console.log((ok ? "ok   " : "FAIL ") + "held button repeats down, then up:", held);
  if (!ok) process.exitCode = 1;
  // the Shoot button: hidden unless the server says "shoot", posts with the X-Fuji header, shows the picture it gets back
  await step("server without --shoot", {col: 3, row: 3, af: 0}, {colour: "#fff", col: 3, row: 3});
  const hidden = els.s.hidden;
  states = [{...base, col: 3, row: 3, af: 0, shoot: true}]; await ctx.refresh();
  posts.length = 0;
  els.s.onclick(); await tick(); await tick();
  const ok2 = hidden === true && els.s.hidden === false && posts.join(" ") === '/shoot {"X-Fuji":"1"}' && els.shot.src === "blob:img" && els.shotbox.hidden === false && els.s.disabled === false;
  console.log((ok2 ? "ok   " : "FAIL ") + "shoot button:", hidden, els.s.hidden, posts.join(" "), els.shot.src, els.s.disabled);
  if (!ok2) process.exitCode = 1;
})();
