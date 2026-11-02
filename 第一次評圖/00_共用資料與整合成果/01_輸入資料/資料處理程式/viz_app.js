/* 市民大道南北分隔 — overlay analysis system
   Geometry arrives delta-encoded as integers at 1e-5 deg. It is projected to
   world Web-Mercator metres ONCE into Path2D objects; every frame just sets a
   canvas transform and strokes them. That is what keeps 10,938 buildings and
   12,768 POIs at interactive frame rates without a map library. */
'use strict';
const D = window.__BUNDLE__;
const css = v => getComputedStyle(document.documentElement).getPropertyValue(v).trim();

/* ---------------------------------------------------------------- decode --- */
const Q = 1e5, R = 6378137, DEG = Math.PI / 180;
const mx = lon => lon * DEG * R;
const my = lat => Math.log(Math.tan(Math.PI / 4 + lat * DEG / 2)) * R;
function decode(a) {                       // -> Float64Array [wx,wy,...]
  const n = a.length >> 1, o = new Float64Array(n * 2);
  let x = a[0], y = a[1];
  o[0] = mx(x / Q); o[1] = my(y / Q);
  for (let i = 1; i < n; i++) {
    x += a[2 * i]; y += a[2 * i + 1];
    o[2 * i] = mx(x / Q); o[2 * i + 1] = my(y / Q);
  }
  return o;
}
const pt = p => [mx(p[0] / Q), my(p[1] / Q)];

function pathOf(lines, close) {
  const P = new Path2D();
  for (const L of lines) {
    const c = decode(L);
    if (c.length < 4) continue;
    P.moveTo(c[0], c[1]);
    for (let i = 2; i < c.length; i += 2) P.lineTo(c[i], c[i + 1]);
    if (close) P.closePath();
  }
  return P;
}
function dotsPath(pts, r) {
  const P = new Path2D();
  for (const p of pts) { P.moveTo(p[0] + r, p[1]); P.arc(p[0], p[1], r, 0, 6.2832); }
  return P;
}

/* ------------------------------------------------------------- geometry --- */
const AX = decode(D.axis);
const G = {
  water: pathOf(D.water, true),
  green: pathOf(D.green, true),
  bldg: pathOf(D.buildings, true),
  r01: pathOf([...D.roads['0'], ...D.roads['1']]),
  r23: pathOf([...D.roads['2'], ...D.roads['3']]),
  r4: pathOf(D.roads['4']),
  r5: pathOf(D.roads['5']),
  metro: pathOf(D.rail.metro),
  trunkline: pathOf(D.rail.trunkline),
  elevated: pathOf(D.elevated),
  atgrade: pathOf(D.atgrade),
  ramps: pathOf(D.ramps),
  axis: pathOf([D.axis]),
  admin: pathOf(D.admin.named.map(x => x.g)),
  controls: pathOf(Object.values(D.detour.control_axes)),
};

/* buildings split into height buckets, north/south separated */
const HB = [0, 10, 20, 35, 60, 1e9];
const bldgBuckets = [];
for (let s = 0; s < 2; s++) for (let b = 0; b < HB.length - 1; b++) bldgBuckets.push(new Path2D());
(function () {
  for (let i = 0; i < D.buildings.length; i++) {
    const h = D.building_h[i], side = D.building_side[i];
    if (!h) continue;
    let b = 0; while (b < HB.length - 2 && h[0] >= HB[b + 1]) b++;
    const idx = (side > 0 ? 0 : 1) * (HB.length - 1) + b;
    const c = decode(D.buildings[i]);
    const P = bldgBuckets[idx];
    P.moveTo(c[0], c[1]);
    for (let k = 2; k < c.length; k += 2) P.lineTo(c[k], c[k + 1]);
    P.closePath();
  }
})();

/* POI paths per sector, and separately for the active-frontage subset */
const SECT = D.sectors;
const ACTIVE = new Set(['餐飲', '零售', '便利超市', '夜生活', '商辦', '金融', '旅宿', '醫療']);
const SEC_COL = ['#d2492a', '#8c3f7a', '#2f7f6f', '#3a76b8', '#5a5f9e', '#b8862c',
  '#7a6a52', '#6b7280', '#2e7d5b', '#c0553f', '#8a6a2f', '#a05c8a',
  '#3f8f7a', '#4b8f3f', '#9aa0a8'];
const poiBySector = SECT.map(() => []);
const poiXY = [];
for (const p of D.poi) {
  const w = [mx(p[0] / Q), my(p[1] / Q)];
  poiXY.push(w);
  poiBySector[p[2]].push(w);
}
const poiPath = poiBySector.map(a => dotsPath(a, 26));
const activePath = dotsPath(
  D.poi.filter(p => ACTIVE.has(SECT[p[2]])).map(p => [mx(p[0] / Q), my(p[1] / Q)]), 30);

const pierXY = D.piers.map(p => [mx(p[0] / Q), my(p[1] / Q)]);
const pierPath = dotsPath(pierXY, 14);
const infraPts = k => (D.infra[k] || []).map(o => ({ w: pt(o.p), o }));
const FB = infraPts('footbridges'), UP = infraPts('underpasses'), PK = infraPts('parking');
const stationXY = D.stations.filter(s => s.k === 's').map(s => ({ w: pt(s.p), n: s.n }));
const severedXY = D.severed.pts.map(p => [mx(p[0] / Q), my(p[1] / Q)]);
const crossXY = D.crossings.locs.map(l => ({ w: pt(l.p), l }));

/* detour probes: colour-coded, plus a N-S tick showing the probe pair */
const probes = D.detour.rows.map(r => ({ w: pt(r.ll), r }));

/* -------------------------------------------------------------- layers --- */
const L = [
  { id: 'water', g: '底圖', t: '水域', on: 1, sw: () => css('--north'), o: .35 },
  { id: 'green', g: '底圖', t: '綠地／公園', on: 1, sw: () => css('--good'), o: .3 },
  { id: 'bldg', g: '底圖', t: '建物量體', on: 1, sw: () => css('--ink-3') },
  { id: 'r01', g: '底圖', t: '快速道路／主幹道', on: 1, sw: () => css('--ink-2') },
  { id: 'r23', g: '底圖', t: '次要道路', on: 1, sw: () => css('--ink-3') },
  { id: 'r4', g: '底圖', t: '巷弄／服務道路', on: 0, sw: () => css('--ink-3') },
  { id: 'r5', g: '底圖', t: '人行道／步道', on: 0, sw: () => css('--ink-3') },
  { id: 'metro', g: '底圖', t: '捷運路線', on: 0, sw: () => css('--ink-2') },
  { id: 'stations', g: '底圖', t: '捷運車站', on: 1, sw: () => css('--ink') },

  { id: 'elevated', g: '市民大道', t: '高架橋面', on: 1, sw: () => css('--accent') },
  { id: 'atgrade', g: '市民大道', t: '平面車道', on: 1, sw: () => css('--deck') },
  { id: 'ramps', g: '市民大道', t: '車行匝道', on: 1, sw: () => css('--warn') },
  { id: 'axis', g: '市民大道', t: '分析軸線＋里程', on: 1, sw: () => css('--ink') },

  { id: 'active', g: '分隔證據', t: '活躍店面（看凹陷）', on: 0, e: 'E1', sw: () => css('--accent') },
  { id: 'detour', g: '分隔證據', t: '繞路係數取樣點', on: 1, e: 'E2', sw: () => css('--accent') },
  { id: 'fb', g: '分隔證據', t: '人行天橋／地下道', on: 1, e: 'E3', sw: () => css('--good') },
  { id: 'admin', g: '分隔證據', t: '里界／區界', on: 0, e: 'E4', sw: () => css('--south') },
  { id: 'trunkline', g: '分隔證據', t: '縱貫線（地下化）', on: 0, e: 'E5', sw: () => css('--ink-2') },
  { id: 'massing', g: '分隔證據', t: '建物高度分級（南北）', on: 0, e: 'E6', sw: () => css('--north') },
  { id: 'piers', g: '分隔證據', t: '橋墩 376 支', on: 0, e: 'E7', sw: () => css('--deck') },
  { id: 'severed', g: '分隔證據', t: '斷頭路端點', on: 0, e: 'E9', sw: () => css('--ink-3') },
  { id: 'cross', g: '分隔證據', t: '幾何穿越點', on: 0, e: 'E10', sw: () => css('--ink-3') },
  { id: 'controls', g: '分隔證據', t: '五條對照幹道', on: 0, sw: () => css('--north') },

  { id: 'poi', g: '產業分布', t: '全部產業 POI', on: 0, sw: () => css('--ink-2') },
];
const ON = {}; L.forEach(l => ON[l.id] = !!l.on);
const SECON = {}; SECT.forEach(s => SECON[s] = true);

/* --------------------------------------------------------------- canvas --- */
const cv = document.getElementById('map'), cx2 = cv.getContext('2d');
let W = 0, H = 0, DPR = 1;
const view = { cx: 0, cy: 0, k: 1 };
let hoverS = null, dragging = false;

function bboxOf(arr) {
  let a = 1e30, b = 1e30, c = -1e30, d = -1e30;
  for (let i = 0; i < arr.length; i += 2) {
    if (arr[i] < a) a = arr[i]; if (arr[i] > c) c = arr[i];
    if (arr[i + 1] < b) b = arr[i + 1]; if (arr[i + 1] > d) d = arr[i + 1];
  }
  return [a, b, c, d];
}
const AXB = bboxOf(AX);

function fit() {
  const pad = 1.10;
  const w = (AXB[2] - AXB[0]) * pad, h = (AXB[3] - AXB[1]) * pad + 1400;
  view.cx = (AXB[0] + AXB[2]) / 2; view.cy = (AXB[1] + AXB[3]) / 2;
  view.k = Math.min(W / w, H / h);
}
function resize() {
  DPR = Math.min(devicePixelRatio || 1, 2);
  const r = cv.getBoundingClientRect();
  W = r.width; H = r.height;
  cv.width = Math.round(W * DPR); cv.height = Math.round(H * DPR);
  if (!view.k || view.k === 1) fit();
  draw(); drawRuler();
}
const toScr = w => [W / 2 + (w[0] - view.cx) * view.k, H / 2 - (w[1] - view.cy) * view.k];
const toWorld = (px, py) => [view.cx + (px - W / 2) / view.k, view.cy - (py - H / 2) / view.k];

function setT() {
  cx2.setTransform(view.k * DPR, 0, 0, -view.k * DPR,
    (W / 2 - view.cx * view.k) * DPR, (H / 2 + view.cy * view.k) * DPR);
}
const lw = px => px / view.k;

/* colour ramps */
function detourColor(v) {
  if (v == null) return css('--ink-3');
  const t = Math.max(0, Math.min(1, (v - 1) / 2));
  const a = [58, 118, 184], b = [204, 69, 38];
  return `rgb(${a.map((x, i) => Math.round(x + (b[i] - x) * t)).join(',')})`;
}
const HCOL = [.20, .34, .50, .68, .88];

function draw() {
  cx2.setTransform(DPR, 0, 0, DPR, 0, 0);
  cx2.clearRect(0, 0, W, H);
  cx2.fillStyle = css('--surface'); cx2.fillRect(0, 0, W, H);
  const lod = dragging || view.k < 0.020;
  setT();
  cx2.lineCap = 'round'; cx2.lineJoin = 'round';

  if (ON.water) { cx2.fillStyle = css('--north'); cx2.globalAlpha = .22; cx2.fill(G.water); cx2.globalAlpha = 1; }
  if (ON.green) { cx2.fillStyle = css('--good'); cx2.globalAlpha = .20; cx2.fill(G.green); cx2.globalAlpha = 1; }

  if (ON.bldg && !ON.massing) {
    cx2.fillStyle = css('--ink-3'); cx2.globalAlpha = .26; cx2.fill(G.bldg);
    cx2.globalAlpha = .5; cx2.strokeStyle = css('--ink-3'); cx2.lineWidth = lw(.5);
    if (!lod) cx2.stroke(G.bldg);
    cx2.globalAlpha = 1;
  }
  if (ON.massing) {
    for (let s = 0; s < 2; s++) {
      const base = s === 0 ? css('--north') : css('--south');
      for (let b = 0; b < HB.length - 1; b++) {
        cx2.fillStyle = base; cx2.globalAlpha = HCOL[b];
        cx2.fill(bldgBuckets[s * (HB.length - 1) + b]);
      }
    }
    cx2.globalAlpha = 1;
  }

  if (ON.r5 && !lod) { cx2.strokeStyle = css('--ink-3'); cx2.globalAlpha = .5; cx2.lineWidth = lw(.7); cx2.stroke(G.r5); cx2.globalAlpha = 1; }
  if (ON.r4 && !lod) { cx2.strokeStyle = css('--ink-3'); cx2.globalAlpha = .7; cx2.lineWidth = lw(.9); cx2.stroke(G.r4); cx2.globalAlpha = 1; }
  if (ON.r23) { cx2.strokeStyle = css('--ink-3'); cx2.lineWidth = lw(1.2); cx2.stroke(G.r23); }
  if (ON.r01) { cx2.strokeStyle = css('--ink-2'); cx2.lineWidth = lw(2.4); cx2.stroke(G.r01); }
  if (ON.metro) {
    cx2.strokeStyle = css('--ink-2'); cx2.lineWidth = lw(1.6);
    cx2.setLineDash([lw(7), lw(5)]); cx2.stroke(G.metro); cx2.setLineDash([]);
  }
  if (ON.trunkline) {
    cx2.strokeStyle = css('--ink'); cx2.lineWidth = lw(4.5); cx2.globalAlpha = .30; cx2.stroke(G.trunkline);
    cx2.globalAlpha = 1; cx2.lineWidth = lw(1.4); cx2.setLineDash([lw(11), lw(6)]);
    cx2.strokeStyle = css('--ink'); cx2.stroke(G.trunkline); cx2.setLineDash([]);
  }
  if (ON.controls) {
    cx2.strokeStyle = css('--north'); cx2.lineWidth = lw(2.2);
    cx2.setLineDash([lw(9), lw(6)]); cx2.stroke(G.controls); cx2.setLineDash([]);
  }
  if (ON.admin) {
    cx2.strokeStyle = css('--south'); cx2.lineWidth = lw(7); cx2.globalAlpha = .35; cx2.stroke(G.admin);
    cx2.globalAlpha = 1; cx2.lineWidth = lw(1.6); cx2.stroke(G.admin);
  }

  if (ON.active) {
    cx2.fillStyle = css('--accent'); cx2.globalAlpha = .55; cx2.fill(activePath); cx2.globalAlpha = 1;
  }
  if (ON.poi) {
    for (let i = 0; i < SECT.length; i++) {
      if (!SECON[SECT[i]]) continue;
      cx2.fillStyle = SEC_COL[i]; cx2.globalAlpha = .68; cx2.fill(poiPath[i]);
    }
    cx2.globalAlpha = 1;
  }

  if (ON.atgrade) { cx2.strokeStyle = css('--deck'); cx2.lineWidth = lw(3.4); cx2.stroke(G.atgrade); }
  if (ON.ramps) { cx2.strokeStyle = css('--warn'); cx2.lineWidth = lw(2.2); cx2.stroke(G.ramps); }
  if (ON.elevated) {
    cx2.strokeStyle = css('--accent'); cx2.globalAlpha = .30; cx2.lineWidth = lw(17); cx2.stroke(G.elevated);
    cx2.globalAlpha = 1; cx2.lineWidth = lw(3.4); cx2.stroke(G.elevated);
  }
  if (ON.piers) {
    cx2.fillStyle = css('--ink'); cx2.globalAlpha = .8; cx2.fill(pierPath); cx2.globalAlpha = 1;
  }
  if (ON.severed) {
    cx2.strokeStyle = css('--ink-3'); cx2.lineWidth = lw(1.4);
    for (const p of severedXY) {
      cx2.beginPath(); cx2.moveTo(p[0] - lw(4), p[1] - lw(4)); cx2.lineTo(p[0] + lw(4), p[1] + lw(4));
      cx2.moveTo(p[0] - lw(4), p[1] + lw(4)); cx2.lineTo(p[0] + lw(4), p[1] - lw(4)); cx2.stroke();
    }
  }
  if (ON.axis) {
    cx2.strokeStyle = css('--ink'); cx2.lineWidth = lw(1); cx2.setLineDash([lw(14), lw(8)]);
    cx2.stroke(G.axis); cx2.setLineDash([]);
  }

  /* ---- screen-space marks ---- */
  cx2.setTransform(DPR, 0, 0, DPR, 0, 0);

  if (ON.cross) {
    for (const c of crossXY) {
      const s = toScr(c.w); if (s[0] < -20 || s[0] > W + 20) continue;
      cx2.beginPath(); cx2.arc(s[0], s[1], 3.6, 0, 6.2832);
      cx2.fillStyle = c.l.w ? css('--good') : css('--ink-3');
      cx2.globalAlpha = .85; cx2.fill(); cx2.globalAlpha = 1;
    }
  }
  if (ON.detour) {
    for (const p of probes) {
      const s = toScr(p.w); if (s[0] < -30 || s[0] > W + 30) continue;
      const ok = p.r.st === 'ok';
      const r = ok ? 4 + Math.min(6, (p.r.d - 1) * 3.4) : 4.5;
      cx2.beginPath(); cx2.arc(s[0], s[1], r, 0, 6.2832);
      cx2.fillStyle = ok ? detourColor(p.r.d) : css('--surface-2');
      cx2.fill();
      cx2.lineWidth = 1.2; cx2.strokeStyle = ok ? css('--surface') : css('--accent'); cx2.stroke();
      if (!ok) { cx2.fillStyle = css('--accent'); cx2.font = '600 9px ' + css('--mono'); cx2.textAlign = 'center'; cx2.fillText('?', s[0], s[1] + 3); }
    }
  }
  if (ON.fb) {
    const mk = (arr, col, ch) => {
      for (const f of arr) {
        const s = toScr(f.w); if (s[0] < -30 || s[0] > W + 30) continue;
        cx2.beginPath(); cx2.rect(s[0] - 6, s[1] - 6, 12, 12);
        cx2.fillStyle = col; cx2.fill();
        cx2.strokeStyle = css('--surface'); cx2.lineWidth = 1.4; cx2.stroke();
        cx2.fillStyle = css('--surface'); cx2.font = '700 9px ' + css('--mono');
        cx2.textAlign = 'center'; cx2.textBaseline = 'middle'; cx2.fillText(ch, s[0], s[1] + .5);
      }
    };
    mk(FB, css('--good'), '橋'); mk(UP, css('--north'), '道');
  }
  if (ON.stations) {
    cx2.textAlign = 'left'; cx2.textBaseline = 'middle';
    for (const st of stationXY) {
      const s = toScr(st.w); if (s[0] < -60 || s[0] > W + 60 || s[1] < -20 || s[1] > H + 20) continue;
      cx2.beginPath(); cx2.arc(s[0], s[1], 3.2, 0, 6.2832);
      cx2.fillStyle = css('--surface'); cx2.fill();
      cx2.strokeStyle = css('--ink'); cx2.lineWidth = 1.6; cx2.stroke();
      if (view.k > 0.028 && st.n) {
        cx2.font = '500 10.5px ' + css('--sans');
        cx2.fillStyle = css('--ink-2');
        cx2.fillText(st.n, s[0] + 6, s[1]);
      }
    }
  }
  /* chainage ticks on the axis */
  if (ON.axis) {
    cx2.font = '500 9.5px ' + css('--mono'); cx2.fillStyle = css('--ink-3');
    cx2.textAlign = 'center'; cx2.textBaseline = 'alphabetic';
    const step = view.k > 0.05 ? 250 : view.k > 0.022 ? 500 : 1000;
    for (let s = 0; s <= D.meta.axis_length_m; s += step) {
      const w = axisAt(s); if (!w) continue;
      const p = toScr(w); if (p[0] < 16 || p[0] > W - 16) continue;
      cx2.beginPath(); cx2.moveTo(p[0], p[1] - 5); cx2.lineTo(p[0], p[1] + 5);
      cx2.strokeStyle = css('--ink-3'); cx2.lineWidth = 1; cx2.stroke();
      cx2.fillText(s === 0 ? '0' : (s / 1000).toFixed(step < 500 ? 2 : 1) + 'k', p[0], p[1] - 8);
    }
  }
  if (hoverS != null) {
    const w = axisAt(hoverS);
    if (w) {
      const p = toScr(w);
      cx2.beginPath(); cx2.moveTo(p[0], 0); cx2.lineTo(p[0], H);
      cx2.strokeStyle = css('--accent'); cx2.lineWidth = 1.4;
      cx2.setLineDash([5, 4]); cx2.stroke(); cx2.setLineDash([]);
      cx2.beginPath(); cx2.arc(p[0], p[1], 5, 0, 6.2832);
      cx2.fillStyle = css('--accent'); cx2.fill();
    }
  }
  /* N / S orientation key */
  cx2.font = '700 11px ' + css('--mono'); cx2.textAlign = 'left';
  cx2.fillStyle = css('--north'); cx2.fillText('▲ 北 NORTH', 13, 22);
  cx2.fillStyle = css('--south'); cx2.fillText('▼ 南 SOUTH', 13, H - 13);
}

/* cumulative chainage of the axis polyline, for s -> point lookups */
const AXCUM = (function () {
  const c = new Float64Array(AX.length / 2); let t = 0;
  for (let i = 1; i < AX.length / 2; i++) {
    t += Math.hypot(AX[2 * i] - AX[2 * i - 2], AX[2 * i + 1] - AX[2 * i - 1]);
    c[i] = t;
  }
  return c;
})();
const AXLEN = AXCUM[AXCUM.length - 1];
function axisAt(s) {
  const t = s / D.meta.axis_length_m * AXLEN;
  if (t < 0 || t > AXLEN) return null;
  let lo = 0, hi = AXCUM.length - 1;
  while (lo < hi - 1) { const m = (lo + hi) >> 1; if (AXCUM[m] <= t) lo = m; else hi = m; }
  const f = (t - AXCUM[lo]) / Math.max(1e-9, AXCUM[hi] - AXCUM[lo]);
  return [AX[2 * lo] + (AX[2 * hi] - AX[2 * lo]) * f,
          AX[2 * lo + 1] + (AX[2 * hi + 1] - AX[2 * lo + 1]) * f];
}
function nearestOnAxis(w) {
  let best = 1e30, bs = 0, bside = 1;
  for (let i = 0; i < AX.length / 2 - 1; i++) {
    const ax = AX[2 * i], ay = AX[2 * i + 1], bx = AX[2 * i + 2], by = AX[2 * i + 3];
    const dx = bx - ax, dy = by - ay, l2 = dx * dx + dy * dy;
    let t = l2 ? ((w[0] - ax) * dx + (w[1] - ay) * dy) / l2 : 0;
    t = Math.max(0, Math.min(1, t));
    const px = ax + dx * t, py = ay + dy * t;
    const d = Math.hypot(w[0] - px, w[1] - py);
    if (d < best) {
      best = d; bs = (AXCUM[i] + Math.hypot(px - ax, py - ay)) / AXLEN * D.meta.axis_length_m;
      bside = (dx * (w[1] - ay) - dy * (w[0] - ax)) > 0 ? 1 : -1;
    }
  }
  const lat = Math.atan(Math.sinh(view.cy / R)) / DEG;
  return { s: bs, d: best * Math.cos(lat * DEG), side: bside };
}

/* ---------------------------------------------------------- interaction --- */
let last = null;
cv.addEventListener('pointerdown', e => {
  dragging = true; cv.classList.add('drag'); last = [e.clientX, e.clientY];
  cv.setPointerCapture(e.pointerId);
});
cv.addEventListener('pointerup', e => {
  dragging = false; cv.classList.remove('drag'); last = null; draw(); drawRuler();
});
cv.addEventListener('pointermove', e => {
  const r = cv.getBoundingClientRect();
  if (dragging && last) {
    view.cx -= (e.clientX - last[0]) / view.k;
    view.cy += (e.clientY - last[1]) / view.k;
    last = [e.clientX, e.clientY];
    draw(); drawRuler(); return;
  }
  readout(e.clientX - r.left, e.clientY - r.top);
});
cv.addEventListener('wheel', e => {
  e.preventDefault();
  const r = cv.getBoundingClientRect();
  const px = e.clientX - r.left, py = e.clientY - r.top;
  const before = toWorld(px, py);
  view.k *= Math.exp(-e.deltaY * 0.0016);
  view.k = Math.max(0.006, Math.min(1.6, view.k));
  const after = toWorld(px, py);
  view.cx += before[0] - after[0]; view.cy += before[1] - after[1];
  draw(); drawRuler();
}, { passive: false });

function zoomBy(f) { view.k = Math.max(0.006, Math.min(1.6, view.k * f)); draw(); drawRuler(); }
document.getElementById('zin').onclick = () => zoomBy(1.6);
document.getElementById('zout').onclick = () => zoomBy(1 / 1.6);
document.getElementById('zfit').onclick = () => { fit(); draw(); drawRuler(); };
document.getElementById('pcollapse').onclick = e => {
  const p = document.getElementById('panel');
  p.classList.toggle('collapsed');
  e.target.textContent = p.classList.contains('collapsed') ? '+' : '−';
};

const RO = document.getElementById('readout');
function readout(px, py) {
  const w = toWorld(px, py);
  const lon = w[0] / R / DEG, lat = Math.atan(Math.sinh(w[1] / R)) / DEG;
  const na = nearestOnAxis(w);
  /* nearest labelled thing within 14 px */
  let best = null, bd = 15;
  const test = (sw, label) => {
    const s = toScr(sw), d = Math.hypot(s[0] - px, s[1] - py);
    if (d < bd) { bd = d; best = label; }
  };
  if (ON.detour) for (const p of probes) test(p.w, p.r.st === 'ok'
    ? `繞路 ${p.r.d.toFixed(2)}x（走 ${p.r.net} m／直線 300 m，多走 ${Math.round(p.r.net - 300)} m）· 里程 ${Math.round(p.r.s)} m`
    : `里程 ${Math.round(p.r.s)} m：${p.r.st === 'no_network' ? '此處北側無已繪製的人行網路（資料缺口）' : '無路徑'}`);
  if (ON.fb) { for (const f of FB) test(f.w, `人行天橋 ${f.o.n.replace(/^Footbridge_/, '')} · 里程 ${Math.round(f.o.s)} m`);
               for (const f of UP) test(f.w, `地下道 ${f.o.n.replace(/^Nether_/, '')} · 距軸線 ${Math.round(f.o.d)} m`); }
  if (ON.stations) for (const s of stationXY) if (s.n) test(s.w, `捷運 ${s.n}`);
  if (ON.cross) for (const c of crossXY) test(c.w, `穿越點 里程 ${Math.round(c.l.s)} m · ${c.l.k.join('/')}${c.l.n.length ? ' · ' + c.l.n.join('、') : ''}${c.l.w ? '' : '（行人不可通行）'}`);
  if (ON.poi || ON.active) {
    for (let i = 0; i < D.poi.length; i++) {
      const p = D.poi[i];
      if (ON.poi && !SECON[SECT[p[2]]]) continue;
      if (!ON.poi && ON.active && !ACTIVE.has(SECT[p[2]])) continue;
      test(poiXY[i], `${SECT[p[2]]}${p[5] ? '｜' + p[5] : ''} · ${p[4] > 0 ? '北' : '南'}側 ${Math.abs(p[4])} m`);
    }
  }
  if (ON.piers) for (let i = 0; i < pierXY.length; i++)
    test(pierXY[i], `橋墩 高 ${D.piers[i][3]} m · ${D.piers[i][2] > 0 ? '北' : '南'}側`);

  RO.textContent = best
    ? best
    : `里程 ${na.s.toFixed(0)} m · ${na.side > 0 ? '北' : '南'}側 ${na.d.toFixed(0)} m · ${lat.toFixed(5)}, ${lon.toFixed(5)}`;
}

/* ---------------------------------------------------------------- panel --- */
(function () {
  const pb = document.getElementById('pbody');
  const groups = [...new Set(L.map(l => l.g))];
  for (const g of groups) {
    const d = document.createElement('div'); d.className = 'lgroup';
    d.innerHTML = `<div class="gl">${g}</div>`;
    for (const l of L.filter(x => x.g === g)) {
      const lab = document.createElement('label'); lab.className = 'lyr';
      lab.innerHTML =
        `<input type="checkbox" ${l.on ? 'checked' : ''} data-id="${l.id}">` +
        `<i class="sw" style="background:${l.sw()}"></i>` +
        `<span class="t">${l.t}</span>` +
        (l.e ? `<span class="eid">${l.e}</span>` : '');
      lab.querySelector('input').onchange = e => {
        ON[l.id] = e.target.checked;
        if (l.id === 'poi') secBox.style.display = e.target.checked ? '' : 'none';
        draw(); buildLegend();
      };
      d.appendChild(lab);
    }
    pb.appendChild(d);
  }
  /* sector filter, revealed with the POI layer */
  const secBox = document.createElement('div');
  secBox.className = 'lgroup'; secBox.style.display = 'none';
  secBox.innerHTML = `<div class="gl">產業類別篩選</div>`;
  SECT.forEach((s, i) => {
    const lab = document.createElement('label'); lab.className = 'lyr';
    const n = D.poi.filter(p => p[2] === i).length;
    lab.innerHTML = `<input type="checkbox" checked><i class="sw" style="background:${SEC_COL[i]}"></i>` +
      `<span class="t">${s}</span><span class="eid">${n}</span>`;
    lab.querySelector('input').onchange = e => { SECON[s] = e.target.checked; draw(); };
    secBox.appendChild(lab);
  });
  pb.appendChild(secBox);
})();

function buildLegend() {
  const el = document.getElementById('legend');
  const rows = [];
  if (ON.detour) rows.push(`<div class="lt">繞路係數 E2</div>
    <div class="bar">${[1, 1.4, 1.8, 2.2, 2.6, 3].map(v => `<i style="background:${detourColor(v)}"></i>`).join('')}</div>
    <div class="scale"><span>1.0x</span><span>2.0x</span><span>3.0x+</span></div>`);
  if (ON.massing) rows.push(`<div class="lt">建物高度 E6</div>
    <div class="row"><i class="dot" style="background:${css('--north')}"></i>北側</div>
    <div class="row"><i class="dot" style="background:${css('--south')}"></i>南側</div>
    <div class="bar">${HCOL.map(a => `<i style="background:${css('--ink-2')};opacity:${a}"></i>`).join('')}</div>
    <div class="scale"><span>&lt;10 m</span><span>20</span><span>35</span><span>60 m+</span></div>`);
  if (ON.fb) rows.push(`<div class="lt">立體穿越 E3</div>
    <div class="row"><i class="dot" style="background:${css('--good')};border-radius:2px"></i>人行天橋（軸線 150 m 內僅 3 座）</div>
    <div class="row"><i class="dot" style="background:${css('--north')};border-radius:2px"></i>人行地下道（軸線 150 m 內 0 座）</div>`);
  if (ON.active && !ON.detour) rows.push(`<div class="lt">活躍店面 E1</div>
    <div class="row"><i class="dot" style="background:${css('--accent')}"></i>餐飲／零售／辦公／金融等</div>`);
  if (!rows.length) rows.push(`<div class="lt">說明</div><div class="row">勾選左側圖層以疊加證據</div>`);
  el.innerHTML = rows.join('');
}

/* chainage ruler strip beneath the map */
function drawRuler() {
  const el = document.getElementById('ruler');
  const w = el.clientWidth; if (!w) return;
  let h = '';
  const step = 500;
  for (let s = 0; s <= D.meta.axis_length_m; s += step) {
    const p = toScr(axisAt(s) || [0, 0]);
    const f = p[0] / W;
    if (f < 0 || f > 1) continue;
    h += `<i style="left:${(f * 100).toFixed(3)}%"></i>` +
      `<b style="left:${(f * 100).toFixed(3)}%">${s}</b>`;
  }
  /* The proposal's three 潛力節點, at the chainages its own cross-street names
     resolve to (config.PDF_ZONES) — not eyeballed off the drawing. */
  const ZCOL = [css('--accent'), css('--good'), css('--south')];
  (D.zones ? D.zones.zones : []).forEach((z, i) => {
    const pa = toScr(axisAt(z.s0) || [0, 0])[0] / W;
    const pb2 = toScr(axisAt(z.s1) || [0, 0])[0] / W;
    const l = Math.max(0, pa), r2 = Math.min(1, pb2);
    if (r2 <= l) return;
    const stat = z.detour_mean == null ? '' :
      ` · 區內繞路平均 ${z.detour_mean.toFixed(2)}x、最差 ${z.detour_max.toFixed(2)}x`;
    h += `<div class="zone" title="${z.name}（${z.extent}，里程 ${z.s0}–${z.s1} m）${stat}" ` +
         `style="left:${l * 100}%;width:${(r2 - l) * 100}%;background:${ZCOL[i % 3]}"></div>`;
  });
  el.innerHTML = h;
}

/* =============================================================== charts === */
const SVGNS = 'http://www.w3.org/2000/svg';
function el(t, a, txt) {
  const e = document.createElementNS(SVGNS, t);
  for (const k in a) e.setAttribute(k, a[k]);
  if (txt != null) e.textContent = txt;
  return e;
}
const CTRL = ['八德路', '忠孝東路', '南京東路', '長安東路', '民生東路'];

/* --- E1 hero: density across the corridor -------------------------------- */
(function () {
  const svg = document.getElementById('ch_section');
  const w = 720, h = 300, m = { t: 16, r: 14, b: 42, l: 46 };
  const iw = w - m.l - m.r, ih = h - m.t - m.b;
  const cs = D.gradient['市民大道'].centres;
  const civ = D.gradient['市民大道'].active;
  const ctrls = CTRL.filter(k => D.gradient[k]).map(k => D.gradient[k].active);
  const ymax = Math.ceil(Math.max(...civ, ...ctrls.flat()) / 4) * 4;
  const X = v => m.l + (v + 600) / 1200 * iw;
  const Y = v => m.t + ih - v / ymax * ih;

  /* grid + axes */
  for (let v = 0; v <= ymax; v += 4) {
    svg.appendChild(el('line', { x1: m.l, x2: m.l + iw, y1: Y(v), y2: Y(v), stroke: css('--rule'), 'stroke-width': 1 }));
    svg.appendChild(el('text', { x: m.l - 7, y: Y(v) + 3.5, 'text-anchor': 'end', fill: css('--ink-3'),
      'font-family': css('--mono'), 'font-size': 9.5 }, v));
  }
  svg.appendChild(el('text', { x: m.l - 7, y: m.t - 5, 'text-anchor': 'end', fill: css('--ink-3'),
    'font-family': css('--mono'), 'font-size': 9 }, '筆/ha'));

  /* deck footprint band, drawn to real width (~34 m each side of centre) */
  svg.appendChild(el('rect', { x: X(-34), y: m.t, width: X(34) - X(-34), height: ih,
    fill: css('--accent'), opacity: .13 }));
  svg.appendChild(el('line', { x1: X(0), x2: X(0), y1: m.t, y2: m.t + ih,
    stroke: css('--accent'), 'stroke-width': 1.4, 'stroke-dasharray': '4 3' }));

  /* control envelope */
  let up = '', dn = '';
  cs.forEach((c, i) => {
    const lo = Math.min(...ctrls.map(a => a[i])), hi = Math.max(...ctrls.map(a => a[i]));
    up += `${i ? 'L' : 'M'}${X(c).toFixed(1)},${Y(hi).toFixed(1)}`;
    dn = `L${X(c).toFixed(1)},${Y(lo).toFixed(1)}` + dn;
  });
  svg.appendChild(el('path', { d: up + dn + 'Z', fill: css('--ink-3'), opacity: .22, stroke: 'none' }));
  const mean = cs.map((c, i) => ctrls.reduce((s, a) => s + a[i], 0) / ctrls.length);
  svg.appendChild(el('path', {
    d: cs.map((c, i) => `${i ? 'L' : 'M'}${X(c).toFixed(1)},${Y(mean[i]).toFixed(1)}`).join(''),
    fill: 'none', stroke: css('--ink-2'), 'stroke-width': 1.6, 'stroke-dasharray': '5 4'
  }));

  /* the axis itself */
  svg.appendChild(el('path', {
    d: cs.map((c, i) => `${i ? 'L' : 'M'}${X(c).toFixed(1)},${Y(civ[i]).toFixed(1)}`).join(''),
    fill: 'none', stroke: css('--accent'), 'stroke-width': 2.6, 'stroke-linejoin': 'round'
  }));

  /* x axis */
  svg.appendChild(el('line', { x1: m.l, x2: m.l + iw, y1: m.t + ih, y2: m.t + ih, stroke: css('--ink-2'), 'stroke-width': 1 }));
  for (const v of [-600, -400, -200, 0, 200, 400, 600]) {
    svg.appendChild(el('line', { x1: X(v), x2: X(v), y1: m.t + ih, y2: m.t + ih + 4, stroke: css('--ink-2'), 'stroke-width': 1 }));
    svg.appendChild(el('text', { x: X(v), y: m.t + ih + 15, 'text-anchor': 'middle', fill: css('--ink-3'),
      'font-family': css('--mono'), 'font-size': 9.5 }, Math.abs(v)));
  }
  svg.appendChild(el('text', { x: X(-400), y: m.t + ih + 31, 'text-anchor': 'middle',
    fill: css('--south'), 'font-family': css('--mono'), 'font-size': 10.5, 'font-weight': 600 }, '← 南 SOUTH  (m)'));
  svg.appendChild(el('text', { x: X(400), y: m.t + ih + 31, 'text-anchor': 'middle',
    fill: css('--north'), 'font-family': css('--mono'), 'font-size': 10.5, 'font-weight': 600 }, '(m)  NORTH 北 →'));

  /* callouts */
  const iMin = civ.indexOf(Math.min(...civ.filter((_, i) => Math.abs(cs[i]) <= 50)));
  const lab = (x, y, t, col, anchor) => {
    const g = svg.appendChild(el('g', {}));
    g.appendChild(el('text', { x, y, 'text-anchor': anchor || 'start', fill: col,
      'font-family': css('--sans'), 'font-size': 11, 'font-weight': 700 }, t));
  };
  lab(X(30) + 8, Y(D.gradient['市民大道'].inner_active) - 9,
    `市民大道 ${D.gradient['市民大道'].inner_active.toFixed(1)}/ha`, css('--accent'));
  lab(X(230), Y(mean[Math.round((230 + 600) / 25)]) - 10, '五條平行幹道範圍', css('--ink-2'));
  document.getElementById('ch_section_note').textContent =
    `市民大道中線 ±50 m 的活躍店面密度 ${D.gradient['市民大道'].active.length ? D.gradient['市民大道'].inner_active.toFixed(2) : ''}/ha，` +
    `到 200–400 m 外升到 ${D.gradient['市民大道'].ref_active.toFixed(2)}/ha；` +
    `五條控制組在中線的密度是 ` +
    `${Math.min(...CTRL.filter(k => D.gradient[k]).map(k => D.gradient[k].inner_active)).toFixed(2)}–` +
    `${Math.max(...CTRL.filter(k => D.gradient[k]).map(k => D.gradient[k].inner_active)).toFixed(2)}/ha，` +
    `全都高於自己 200–400 m 外的水準。`;
})();

/* --- E1b trough depth bars ----------------------------------------------- */
(function () {
  const svg = document.getElementById('ch_trough');
  const w = 420, h = 300, m = { t: 26, r: 58, b: 34, l: 66 };
  const iw = w - m.l - m.r, ih = h - m.t - m.b;
  const rows = [['市民大道', D.gradient['市民大道'].trough_active],
    ...CTRL.filter(k => D.gradient[k]).map(k => [k, D.gradient[k].trough_active])];
  const lim = Math.max(...rows.map(r => Math.abs(r[1]))) * 1.12;
  const X = v => m.l + (v + lim) / (2 * lim) * iw;
  const bh = ih / rows.length - 7;
  svg.appendChild(el('text', { x: X(-lim * .55), y: 14, 'text-anchor': 'middle', fill: css('--ink-2'),
    'font-family': css('--mono'), 'font-size': 9.5 }, '← 路緣隆起（正常街道）'));
  svg.appendChild(el('text', { x: X(lim * .55), y: 14, 'text-anchor': 'middle', fill: css('--accent'),
    'font-family': css('--mono'), 'font-size': 9.5, 'font-weight': 600 }, '路緣凹陷 →'));
  rows.forEach(([nm, v], i) => {
    const y = m.t + i * (ih / rows.length) + 3;
    const isC = nm === '市民大道';
    svg.appendChild(el('rect', { x: Math.min(X(0), X(v)), y, width: Math.abs(X(v) - X(0)), height: bh,
      fill: isC ? css('--accent') : css('--ink-3'), opacity: isC ? 1 : .5 }));
    svg.appendChild(el('text', { x: m.l - 8, y: y + bh / 2 + 4, 'text-anchor': 'end',
      fill: isC ? css('--ink') : css('--ink-2'), 'font-family': css('--sans'),
      'font-size': 11.5, 'font-weight': isC ? 700 : 400 }, nm));
    svg.appendChild(el('text', { x: v > 0 ? X(v) + 6 : X(v) - 6, y: y + bh / 2 + 4,
      'text-anchor': v > 0 ? 'start' : 'end', fill: isC ? css('--accent') : css('--ink-3'),
      'font-family': css('--mono'), 'font-size': 11, 'font-weight': 600 },
      (v * 100).toFixed(0) + '%'));
  });
  svg.appendChild(el('line', { x1: X(0), x2: X(0), y1: m.t - 4, y2: m.t + ih, stroke: css('--ink'), 'stroke-width': 1.3 }));
  svg.appendChild(el('text', { x: X(0), y: m.t + ih + 15, 'text-anchor': 'middle', fill: css('--ink-3'),
    'font-family': css('--mono'), 'font-size': 9.5 }, '0'));
})();

/* --- E2 detour comparison ------------------------------------------------ */
(function () {
  const svg = document.getElementById('ch_detour');
  const w = 720, h = 260, m = { t: 20, r: 96, b: 46, l: 76 };
  const iw = w - m.l - m.r, ih = h - m.t - m.b;
  const rows = [['市民大道', D.detour.summary.extra_walk_mean_m, D.detour.summary.detour_mean,
                 D.detour.summary.share_over_2x],
    ...D.detour.controls.map(c => [c.label, c.extra_walk_mean_m, c.detour_mean, c.share_over_2x])];
  const xmax = Math.ceil(Math.max(...rows.map(r => r[1])) / 50) * 50;
  const X = v => m.l + v / xmax * iw;
  const bh = ih / rows.length - 8;
  for (let v = 0; v <= xmax; v += 50) {
    svg.appendChild(el('line', { x1: X(v), x2: X(v), y1: m.t, y2: m.t + ih, stroke: css('--rule'), 'stroke-width': 1 }));
    svg.appendChild(el('text', { x: X(v), y: m.t + ih + 15, 'text-anchor': 'middle', fill: css('--ink-3'),
      'font-family': css('--mono'), 'font-size': 9.5 }, v));
  }
  svg.appendChild(el('text', { x: m.l + iw / 2, y: m.t + ih + 32, 'text-anchor': 'middle', fill: css('--ink-2'),
    'font-family': css('--mono'), 'font-size': 10 }, '平均多走的步行距離（公尺）'));
  rows.forEach(([nm, extra, ratio, over2], i) => {
    const y = m.t + i * (ih / rows.length) + 4;
    const isC = i === 0;
    svg.appendChild(el('rect', { x: m.l, y, width: X(extra) - m.l, height: bh,
      fill: isC ? css('--accent') : css('--ink-3'), opacity: isC ? 1 : .48 }));
    svg.appendChild(el('text', { x: m.l - 8, y: y + bh / 2 + 4, 'text-anchor': 'end',
      fill: isC ? css('--ink') : css('--ink-2'), 'font-family': css('--sans'),
      'font-size': 11.5, 'font-weight': isC ? 700 : 400 }, nm));
    svg.appendChild(el('text', { x: X(extra) + 7, y: y + bh / 2 + 4, fill: isC ? css('--accent') : css('--ink-3'),
      'font-family': css('--mono'), 'font-size': 10.5, 'font-weight': isC ? 600 : 400 },
      `${Math.round(extra)} m · ${ratio.toFixed(2)}x · >2x ${(over2 * 100).toFixed(0)}%`));
  });
  svg.appendChild(el('line', { x1: m.l, x2: m.l, y1: m.t, y2: m.t + ih, stroke: css('--ink'), 'stroke-width': 1.3 }));
  document.getElementById('ch_detour_note').textContent =
    `${D.detour.summary.n_ok} 組樣本成功計算（共 ${D.detour.summary.n_probes} 組）。` +
    `p90 = ${D.detour.summary.detour_p90.toFixed(2)}x、最差 ${D.detour.summary.detour_max.toFixed(2)}x（里程 6,000 m，多走 880 m）。` +
    `1 組因該處北側完全沒有已繪製的人行網路而無法計算，已標為資料缺口而非障礙。`;
})();

/* --- E2b offset invariance ----------------------------------------------- */
(function () {
  const svg = document.getElementById('ch_offset');
  const w = 420, h = 260, m = { t: 22, r: 20, b: 48, l: 52 };
  const iw = w - m.l - m.r, ih = h - m.t - m.b;
  const offs = [100, 150, 250];
  const O = offs.map(o => D.detour.offsets[o] || D.detour.offsets[String(o)]);
  const emax = 260;
  const bw = iw / offs.length;
  for (let v = 0; v <= emax; v += 50) {
    svg.appendChild(el('line', { x1: m.l, x2: m.l + iw, y1: m.t + ih - v / emax * ih, y2: m.t + ih - v / emax * ih,
      stroke: css('--rule'), 'stroke-width': 1 }));
    svg.appendChild(el('text', { x: m.l - 7, y: m.t + ih - v / emax * ih + 3.5, 'text-anchor': 'end',
      fill: css('--ink-3'), 'font-family': css('--mono'), 'font-size': 9.5 }, v));
  }
  svg.appendChild(el('text', { x: m.l - 7, y: m.t - 6, 'text-anchor': 'end', fill: css('--ink-3'),
    'font-family': css('--mono'), 'font-size': 9 }, 'm'));
  offs.forEach((o, i) => {
    const d = O[i]; if (!d) return;
    const x = m.l + i * bw + bw * .22, bwi = bw * .56;
    const hh = d.extra_walk_mean_m / emax * ih;
    svg.appendChild(el('rect', { x, y: m.t + ih - hh, width: bwi, height: hh, fill: css('--accent') }));
    svg.appendChild(el('text', { x: x + bwi / 2, y: m.t + ih - hh - 7, 'text-anchor': 'middle',
      fill: css('--accent'), 'font-family': css('--mono'), 'font-size': 11.5, 'font-weight': 600 },
      Math.round(d.extra_walk_mean_m) + ' m'));
    svg.appendChild(el('text', { x: x + bwi / 2, y: m.t + ih + 16, 'text-anchor': 'middle',
      fill: css('--ink-2'), 'font-family': css('--mono'), 'font-size': 10 }, '±' + o + ' m'));
    svg.appendChild(el('text', { x: x + bwi / 2, y: m.t + ih + 30, 'text-anchor': 'middle',
      fill: css('--ink-3'), 'font-family': css('--mono'), 'font-size': 10 }, d.detour_mean.toFixed(2) + 'x'));
  });
  svg.appendChild(el('line', { x1: m.l, x2: m.l + iw, y1: m.t + ih, y2: m.t + ih, stroke: css('--ink'), 'stroke-width': 1.3 }));
  svg.appendChild(el('text', { x: m.l + iw / 2, y: h - 4, 'text-anchor': 'middle', fill: css('--ink-3'),
    'font-family': css('--mono'), 'font-size': 9.5 }, '取樣距離 ／ 平均倍率'));
})();

/* --- F industry composition, north vs south ------------------------------ */
(function () {
  const svg = document.getElementById('ch_industry');
  const N = D.industry.north, S = D.industry.south;
  const rows = SECT.map(s => [s, N[s] || 0, S[s] || 0])
    .filter(r => r[1] + r[2] > 0)
    .sort((a, b) => (b[1] + b[2]) - (a[1] + a[2]));
  const tn = Object.values(N).reduce((a, b) => a + b, 0);
  const ts = Object.values(S).reduce((a, b) => a + b, 0);
  const w = 720, h = 430, m = { t: 30, r: 70, b: 30, l: 78 };
  const iw = w - m.l - m.r, ih = h - m.t - m.b;
  const half = iw / 2 - 26, mid = m.l + iw / 2;
  const pmax = Math.max(...rows.map(r => Math.max(r[1] / tn, r[2] / ts))) * 1.06;
  const bh = ih / rows.length - 5;
  svg.appendChild(el('text', { x: mid - half / 2, y: 13, 'text-anchor': 'middle', fill: css('--south'),
    'font-family': css('--mono'), 'font-size': 10.5, 'font-weight': 600 }, `南側 ${ts.toLocaleString()} 筆 ←`));
  svg.appendChild(el('text', { x: mid + half / 2, y: 13, 'text-anchor': 'middle', fill: css('--north'),
    'font-family': css('--mono'), 'font-size': 10.5, 'font-weight': 600 }, `→ 北側 ${tn.toLocaleString()} 筆`));
  svg.appendChild(el('text', { x: mid, y: 13, 'text-anchor': 'middle', fill: css('--ink-3'),
    'font-family': css('--mono'), 'font-size': 9 }, '佔比'));
  rows.forEach(([s, n, sv], i) => {
    const y = m.t + i * (ih / rows.length) + 2;
    const pn = n / tn / pmax * half, ps = sv / ts / pmax * half;
    const big = Math.abs((n / tn) / Math.max(sv / ts, 1e-9) - 1) > .5;
    svg.appendChild(el('rect', { x: mid - 24 - ps, y, width: ps, height: bh,
      fill: css('--south'), opacity: big ? .95 : .5 }));
    svg.appendChild(el('rect', { x: mid + 24, y, width: pn, height: bh,
      fill: css('--north'), opacity: big ? .95 : .5 }));
    svg.appendChild(el('text', { x: mid, y: y + bh / 2 + 4, 'text-anchor': 'middle',
      fill: big ? css('--ink') : css('--ink-2'), 'font-family': css('--sans'),
      'font-size': 11, 'font-weight': big ? 700 : 400 }, s));
    svg.appendChild(el('text', { x: mid - 26 - ps - 5, y: y + bh / 2 + 4, 'text-anchor': 'end',
      fill: css('--ink-3'), 'font-family': css('--mono'), 'font-size': 9.5 },
      (sv / ts * 100).toFixed(1) + '%'));
    svg.appendChild(el('text', { x: mid + 26 + pn + 5, y: y + bh / 2 + 4,
      fill: css('--ink-3'), 'font-family': css('--mono'), 'font-size': 9.5 },
      (n / tn * 100).toFixed(1) + '%'));
  });
  const ratio = (k) => ((N[k] || 0) / tn) / (((S[k] || 0) / ts) || 1e-9);
  document.getElementById('ch_industry_note').textContent =
    `最不對稱的類別：停車 北/南 ${ratio('停車').toFixed(2)}（北側 ${(N['停車'] / tn * 100).toFixed(1)}% vs 南側 ${(S['停車'] / ts * 100).toFixed(1)}%）、` +
    `綠地 ${ratio('綠地').toFixed(2)}、文化公共 ${ratio('文化公共').toFixed(2)}。` +
    `北側走廊被停車與服務性用途填滿，南側是綠地與文化設施（華山、中央藝文公園一帶）。`;
})();

/* --- F placebo test (the negative result) -------------------------------- */
(function () {
  const svg = document.getElementById('ch_placebo');
  const w = 420, h = 300, m = { t: 26, r: 20, b: 56, l: 54 };
  const iw = w - m.l - m.r, ih = h - m.t - m.b;
  const rows = [['市民大道\n(軸線)', D.industry.js, 1],
    ...D.industry.placebos.map(p => [(p.offset_m > 0 ? '北移 +' : '南移 −') + Math.abs(p.offset_m) + ' m', p.js, 0])];
  const ymax = Math.ceil(Math.max(...rows.map(r => r[1])) * 100 / 5) * 5 / 100;
  const bw = iw / rows.length;
  for (let v = 0; v <= ymax + 1e-9; v += .05) {
    const y = m.t + ih - v / ymax * ih;
    svg.appendChild(el('line', { x1: m.l, x2: m.l + iw, y1: y, y2: y, stroke: css('--rule'), 'stroke-width': 1 }));
    svg.appendChild(el('text', { x: m.l - 7, y: y + 3.5, 'text-anchor': 'end', fill: css('--ink-3'),
      'font-family': css('--mono'), 'font-size': 9.5 }, v.toFixed(2)));
  }
  svg.appendChild(el('text', { x: m.l - 7, y: m.t - 7, 'text-anchor': 'end', fill: css('--ink-3'),
    'font-family': css('--mono'), 'font-size': 9 }, 'JS'));
  /* band showing the placebo range */
  const pl = D.industry.placebos.map(p => p.js);
  const yhi = m.t + ih - Math.max(...pl) / ymax * ih, ylo = m.t + ih - Math.min(...pl) / ymax * ih;
  svg.appendChild(el('rect', { x: m.l, y: yhi, width: iw, height: ylo - yhi,
    fill: css('--ink-3'), opacity: .18 }));
  svg.appendChild(el('text', { x: m.l + iw - 4, y: yhi - 5, 'text-anchor': 'end', fill: css('--ink-2'),
    'font-family': css('--sans'), 'font-size': 10, 'font-weight': 600 }, '假想線的分歧度區間'));
  rows.forEach(([nm, v, isC], i) => {
    const x = m.l + i * bw + bw * .18, bwi = bw * .64;
    const hh = v / ymax * ih;
    svg.appendChild(el('rect', { x, y: m.t + ih - hh, width: bwi, height: hh,
      fill: isC ? css('--accent') : css('--ink-3'), opacity: isC ? 1 : .55 }));
    svg.appendChild(el('text', { x: x + bwi / 2, y: m.t + ih - hh - 6, 'text-anchor': 'middle',
      fill: isC ? css('--accent') : css('--ink-3'), 'font-family': css('--mono'),
      'font-size': 10, 'font-weight': 600 }, v.toFixed(3)));
    nm.split('\n').forEach((ln, k) =>
      svg.appendChild(el('text', { x: x + bwi / 2, y: m.t + ih + 15 + k * 12, 'text-anchor': 'middle',
        fill: isC ? css('--ink') : css('--ink-2'), 'font-family': css('--mono'),
        'font-size': 9.5, 'font-weight': isC ? 600 : 400 }, ln)));
  });
  svg.appendChild(el('line', { x1: m.l, x2: m.l + iw, y1: m.t + ih, y2: m.t + ih, stroke: css('--ink'), 'stroke-width': 1.3 }));
  const mx2 = Math.max(...pl);
  document.getElementById('ch_placebo_note').textContent =
    `軸線的 JS = ${D.industry.js.toFixed(3)}，落在假想線的 ${Math.min(...pl).toFixed(3)}–${mx2.toFixed(3)} 區間內，` +
    `偏北 300 m 的假想線（${mx2.toFixed(3)}）甚至更分歧。結論：南北產業組成的差異雖然統計顯著（chi² p ≈ ${D.industry.chi2_p.toExponential(0)}），` +
    `卻與市中心任意兩條相鄰街帶的差異無法區分——不採用為分隔證據。`;
})();

/* --- along-corridor strips ------------------------------------------------ */
(function () {
  const host = document.getElementById('strips');
  const AL = D.meta.axis_length_m;
  const SW = 900, SH0 = 52;
  const X = s => 34 + s / AL * (SW - 44);

  function frame(sh) {
    const svg = el('svg', { viewBox: `0 0 ${SW} ${sh}`, preserveAspectRatio: 'none' });
    svg.setAttribute('style', 'width:100%');
    return svg;
  }
  function addRow(labelTop, labelSub, sh, build) {
    const row = document.createElement('div'); row.className = 'striprow';
    row.innerHTML = `<div class="sl"><b>${labelTop}</b>${labelSub}</div>`;
    const svg = frame(sh);
    build(svg, sh);
    /* shared vertical gridlines every 1 km */
    for (let s = 1000; s < AL; s += 1000)
      svg.insertBefore(el('line', { x1: X(s), x2: X(s), y1: 0, y2: sh,
        stroke: css('--rule'), 'stroke-width': 1 }), svg.firstChild);
    row.appendChild(svg);
    svg.addEventListener('pointermove', e => {
      const r = svg.getBoundingClientRect();
      const f = (e.clientX - r.left) / r.width * SW;
      hoverS = Math.max(0, Math.min(AL, (f - 34) / (SW - 44) * AL));
      draw();
    });
    svg.addEventListener('pointerleave', () => { hoverS = null; draw(); });
    host.appendChild(row);
    return svg;
  }

  /* 1. detour along the corridor */
  addRow('繞路係數 E2', '1.0 = 沒有繞路', 62, (svg, sh) => {
    const y0 = sh - 9, ymax = 4;
    svg.appendChild(el('line', { x1: 34, x2: SW - 10, y1: y0 - (2 - 1) / (ymax - 1) * (sh - 20),
      y2: y0 - (2 - 1) / (ymax - 1) * (sh - 20), stroke: css('--accent'), 'stroke-width': 1,
      'stroke-dasharray': '4 3', opacity: .7 }));
    for (const r of D.detour.rows) {
      if (r.st !== 'ok') {
        svg.appendChild(el('rect', { x: X(r.s) - 3, y: 4, width: 6, height: sh - 13,
          fill: css('--accent'), opacity: .18 }));
        svg.appendChild(el('text', { x: X(r.s), y: sh - 1, 'text-anchor': 'middle',
          fill: css('--accent'), 'font-family': css('--mono'), 'font-size': 8 }, '缺'));
        continue;
      }
      const hh = (Math.min(r.d, ymax) - 1) / (ymax - 1) * (sh - 20);
      svg.appendChild(el('rect', { x: X(r.s) - 5, y: y0 - hh, width: 10, height: Math.max(1, hh),
        fill: detourColor(r.d) }));
    }
    svg.appendChild(el('line', { x1: 34, x2: SW - 10, y1: y0, y2: y0, stroke: css('--ink-2'), 'stroke-width': 1 }));
    svg.appendChild(el('text', { x: 30, y: y0 - (2 - 1) / (ymax - 1) * (sh - 20) + 3, 'text-anchor': 'end',
      fill: css('--accent'), 'font-family': css('--mono'), 'font-size': 8.5 }, '2x'));
  });

  /* 2. grade-separated crossings */
  addRow('立體穿越 E3', '天橋 / 地下道', 34, (svg, sh) => {
    svg.appendChild(el('line', { x1: 34, x2: SW - 10, y1: sh / 2, y2: sh / 2, stroke: css('--rule-2'), 'stroke-width': 1 }));
    for (const f of (D.infra.footbridges || [])) {
      if (f.d > 150) continue;
      svg.appendChild(el('rect', { x: X(f.s) - 4, y: sh / 2 - 9, width: 8, height: 18, fill: css('--good') }));
      svg.appendChild(el('text', { x: X(f.s), y: sh / 2 - 12, 'text-anchor': 'middle', fill: css('--good'),
        'font-family': css('--mono'), 'font-size': 8.5 }, (f.n.replace(/^Footbridge_/, '').split('_')[0]) || '橋'));
    }
    svg.appendChild(el('text', { x: SW - 12, y: sh / 2 + 3.5, 'text-anchor': 'end', fill: css('--ink-3'),
      'font-family': css('--mono'), 'font-size': 9 }, '6.53 km 內 3 座天橋、0 座地下道'));
  });

  /* 3. pier bents */
  addRow('橋墩排 E7', '132 排 · 中位間距 36 m', 30, (svg, sh) => {
    for (const b of D.bents)
      svg.appendChild(el('rect', { x: X(b.s) - .9, y: 6, width: 1.8, height: sh - 12,
        fill: css('--ink'), opacity: .55 }));
  });

  /* 4. building height north vs south */
  addRow('建物平均高 E6', '北 ▲ / 南 ▼（公尺）', 74, (svg, sh) => {
    const mid = sh / 2, hmax = 45;
    svg.appendChild(el('line', { x1: 34, x2: SW - 10, y1: mid, y2: mid, stroke: css('--ink-2'), 'stroke-width': 1 }));
    for (const s of D.massing.segments) {
      const x = X(s.s), bw = (SW - 44) / D.massing.segments.length * .74;
      if (s.north.h_mean) {
        const hh = Math.min(s.north.h_mean, hmax) / hmax * (mid - 6);
        svg.appendChild(el('rect', { x: x - bw / 2, y: mid - hh, width: bw, height: hh, fill: css('--north'), opacity: .85 }));
      }
      if (s.south.h_mean) {
        const hh = Math.min(s.south.h_mean, hmax) / hmax * (mid - 6);
        svg.appendChild(el('rect', { x: x - bw / 2, y: mid, width: bw, height: hh, fill: css('--south'), opacity: .85 }));
      }
    }
  });

  /* 5. POI count north vs south */
  addRow('POI 數 E1/F', '北 ▲ / 南 ▼（300 m 內）', 74, (svg, sh) => {
    const mid = sh / 2;
    const mx3 = Math.max(...D.industry.segments.map(s => Math.max(s.n, s.sn))) || 1;
    svg.appendChild(el('line', { x1: 34, x2: SW - 10, y1: mid, y2: mid, stroke: css('--ink-2'), 'stroke-width': 1 }));
    for (const s of D.industry.segments) {
      const x = X(s.s), bw = (SW - 44) / D.industry.segments.length * .74;
      svg.appendChild(el('rect', { x: x - bw / 2, y: mid - s.n / mx3 * (mid - 6), width: bw,
        height: s.n / mx3 * (mid - 6), fill: css('--north'), opacity: .8 }));
      svg.appendChild(el('rect', { x: x - bw / 2, y: mid, width: bw,
        height: s.sn / mx3 * (mid - 6), fill: css('--south'), opacity: .8 }));
    }
  });

  /* 6. administrative boundary + railway coincidence */
  addRow('行政界線 E4', `${D.admin.share_pct}% 的軸線是里/區界`, 26, (svg, sh) => {
    svg.appendChild(el('rect', { x: 34, y: 8, width: SW - 44, height: sh - 16,
      fill: css('--rule'), opacity: .6 }));
    for (const n of D.admin.named) {
      const half = Math.max(3, n.len / 2 / AL * (SW - 44));
      svg.appendChild(el('rect', { x: X(n.s) - half, y: 8, width: half * 2, height: sh - 16,
        fill: css('--south'), opacity: .9 }));
      if (n.len > 120)
        svg.appendChild(el('text', { x: X(n.s), y: sh / 2 + 3.5, 'text-anchor': 'middle',
          fill: css('--surface'), 'font-family': css('--mono'), 'font-size': 8.5, 'font-weight': 600 }, n.n));
    }
  });
  addRow('縱貫線 E5', `${D.railshare.pct}% 的軸線下方仍是鐵路`, 22, (svg, sh) => {
    svg.appendChild(el('rect', { x: 34, y: 6, width: (SW - 44) * D.railshare.pct / 100, height: sh - 12,
      fill: css('--ink'), opacity: .45 }));
    svg.appendChild(el('rect', { x: 34, y: 6, width: SW - 44, height: sh - 12,
      fill: 'none', stroke: css('--rule-2'), 'stroke-width': 1 }));
  });

  /* chainage axis at the bottom */
  const row = document.createElement('div'); row.className = 'striprow';
  row.innerHTML = `<div class="sl" style="color:var(--ink-3);font-family:var(--mono);font-size:10px">里程 m</div>`;
  const svg = frame(22); svg.setAttribute('style', 'width:100%;background:none;border:none');
  for (let s = 0; s <= AL; s += 500) {
    svg.appendChild(el('line', { x1: X(s), x2: X(s), y1: 0, y2: 5, stroke: css('--ink-2'), 'stroke-width': 1 }));
    if (s % 1000 === 0)
      svg.appendChild(el('text', { x: X(s), y: 16, 'text-anchor': 'middle', fill: css('--ink-3'),
        'font-family': css('--mono'), 'font-size': 9.5 }, s.toLocaleString()));
  }
  row.appendChild(svg); host.appendChild(row);
})();

/* --------------------------------------------------- stamp box & ribbon --- */
(function () {
  const ob = D.obstruction;
  const sb = [
    ['軸線長度', D.meta.axis_length_m.toLocaleString() + ' m'],
    ['分析單元', '200 m × 33 段'],
    ['取樣點', D.detour.summary.n_probes + ' 組（每 100 m）'],
    ['對照幹道', '5 條'],
    ['POI（tag 分類）', D.poi.length.toLocaleString() + ' 筆'],
    ['建物量體', D.massing.n_buildings.toLocaleString() + ' 棟'],
    ['橋墩', ob.n_pier_columns + ' 支 / ' + ob.n_pier_bents + ' 排'],
    ['座標系統', 'EPSG:3826 計算'],
  ];
  document.getElementById('stampbox').innerHTML =
    sb.map(([k, v]) => `<div><b>${k}</b>${v}</div>`).join('');

  const ribbon = [
    ['決定性判準', `+${(D.gradient['市民大道'].trough_active * 100).toFixed(0)}%`, 'bad',
      '路緣活動凹陷深度。五條對照幹道全為負值（活動被吸到路緣）。'],
    ['行人代價', `${Math.round(D.detour.summary.extra_walk_mean_m)} m`, 'bad',
      `平均多走的步行距離，對照組 ${Math.round(Math.min(...D.detour.controls.map(c => c.extra_walk_mean_m)))}–${Math.round(Math.max(...D.detour.controls.map(c => c.extra_walk_mean_m)))} m。`],
    ['立體穿越', `2.18 <small>km/處</small>`, 'bad',
      '6.53 km 只有 3 座人行天橋、0 座地下道；同段卻有 32 條車行匝道。'],
    ['行政分隔', `${D.admin.share_pct}<small>%</small>`, 'bad',
      '軸線同時是里界或區界的比例。南北在制度上就屬於不同單位。'],
    ['證據結算', `7 <small>支持 / 1 反證 / 2 不採用</small>`, '',
      '所有判準都與五條平行幹道對照；不利於假設的結果一併列出。'],
  ];
  document.getElementById('ribbon').innerHTML = ribbon.map(([k, v, c, n]) =>
    `<div><div class="k">${k}</div><div class="v tab ${c}">${v}</div><div class="n">${n}</div></div>`).join('');
})();

/* ------------------------------------------------------- evidence cards --- */
(function () {
  const host = document.getElementById('ev');
  const cls = { SUPPORTS: 'sup', CONTRADICTS: 'con', NEUTRAL: 'neu' };
  const vd = { SUPPORTS: '支持', CONTRADICTS: '反證', NEUTRAL: '不採用' };
  for (const e of D.verdict.evidence) {
    const d = document.createElement('div');
    d.className = 'evcard ' + cls[e.verdict];
    d.innerHTML =
      `<div class="tag">${e.id}<span class="vd">${vd[e.verdict]}</span></div>` +
      `<div class="body"><h3>${e.title}</h3>` +
      `<dl class="kv"><dt>值</dt><dd>${e.value}</dd>` +
      `<dt>對照</dt><dd class="cmp">${e.compare}</dd></dl>` +
      `<div class="why">${e.detail} <b>${e.why}</b></div></div>`;
    host.appendChild(d);
  }
})();

/* --------------------------------------------------- comparison table ---- */
(function () {
  const t = document.getElementById('cmp');
  const gr = D.gradient, det = {}; D.detour.controls.forEach(c => det[c.label] = c);
  const sev = {}; (D.severed.controls || []).forEach(c => sev[c.label] = c);
  const crs = {}; (D.crossings.controls || []).forEach(c => crs[c.label] = c);
  const rows = ['市民大道', ...CTRL];
  t.innerHTML =
    `<thead><tr><th>幹道</th><th>長度</th>
      <th>E1 路緣凹陷深度</th><th>E1 中線活躍密度</th>
      <th>E2 平均多走</th><th>E2 繞路倍率</th><th>E2 &gt;2x 佔比</th>
      <th>E9 斷頭路</th><th>E10 幾何穿越點</th></tr></thead><tbody>` +
    rows.map(k => {
      const isC = k === '市民大道';
      const g = gr[k]; if (!g) return '';
      const dd = isC ? { extra_walk_mean_m: D.detour.summary.extra_walk_mean_m,
        detour_mean: D.detour.summary.detour_mean, share_over_2x: D.detour.summary.share_over_2x,
        length_m: D.meta.axis_length_m } : det[k];
      const sv = isC ? { per_km: D.severed.per_km } : sev[k];
      const cr = isC ? { walkable_per_km: D.crossings.per_km } : crs[k];
      return `<tr class="${isC ? 'hi' : ''}"><td><b>${k}</b></td>` +
        `<td class="n">${Math.round(dd.length_m).toLocaleString()} m</td>` +
        `<td class="n" style="color:${g.trough_active > 0 ? css('--accent') : css('--ink-2')};font-weight:600">` +
        `${(g.trough_active * 100).toFixed(0)}%</td>` +
        `<td class="n">${g.inner_active.toFixed(2)} /ha</td>` +
        `<td class="n">${Math.round(dd.extra_walk_mean_m)} m</td>` +
        `<td class="n">${dd.detour_mean.toFixed(2)}x</td>` +
        `<td class="n">${(dd.share_over_2x * 100).toFixed(0)}%</td>` +
        `<td class="n">${sv ? sv.per_km + ' /km' : '—'}</td>` +
        `<td class="n">${cr ? cr.walkable_per_km + ' /km' : '—'}</td></tr>`;
    }).join('') + '</tbody>';
})();

/* ------------------------------------------------------ method & caveats -- */
(function () {
  document.getElementById('method').innerHTML = `
  <p style="margin:0 0 9px"><b>軸線</b>：從 OSM 取出 30 條 <code class="mono">市民大道高架道路</code>
  橋面 way，以 20 m 經度分箱取緯度中位數，剔除偏離 9 箱滾動中位數 60 m 以上的箱
  （這一步剔掉了平面五段在光復南路一帶北偏 300 m 的污染），再做 5 箱移動平均。
  結果 6,533 m、彎曲率 1.030，與設計論述所載「全長 6.4 公里」independently 吻合。</p>
  <p style="margin:0 0 9px"><b>繞路係數</b>：以 34,545 條可步行 way 建成 116,736 節點的人行網路圖
  （97.7% 在同一連通分量）。吸附一律限制在最大連通分量內——不這麼做的話，
  台北 OSM 裡數百個 2–30 節點的孤立人行道碎片會產生假的「無路徑」，被誤讀成障礙。
  修正前有 3 組假缺口，修正後全部消失。</p>
  <p style="margin:0 0 9px"><b>Blender 基地模型套疊</b>：模型是公尺制但原點是本地偏移，
  所以先把模型內的 <code class="mono">OSM_Major_Roads</code> 點雲對 OSM 真實路網做配準
  （最近鄰中位距離的 Nelder-Mead 平移擬合），得 tx=301,499.60、ty=2,770,462.78。
  再回頭驗證 scale=0.9998、rotation=+0.07°，證明只用平移是足夠的；
  內點殘差中位數 7.0 m（線段取樣密度不同造成，不影響 ±150 m 的南北判別）。</p>
  <p style="margin:0"><b>對照組</b>：八德路、忠孝東路、南京東路、長安東路、民生東路，
  裁切到與市民大道相同的經度窗口，套用完全相同的程式路徑。</p>`;

  const cav = [
    `<b>樹冠資料不可用。</b>模型內 10,000 個樹冠網格是完全一致的佔位幾何
     （每個都是 ${D.canopy.canopy_w_m} × ${D.canopy.canopy_d_m} m、z ${D.canopy.canopy_z[0]}–${D.canopy.canopy_z[1]} m，
     各維度標準差 &lt; 1e-4），因此<b>沒有</b>計算樹冠面積或體積，也不報這個數字。
     可用的只有 ${D.canopy.n_tree_positions_300m.toLocaleString()} 個樹木<b>位置</b>。`,
    `<b>建物高度是推算值，不是實測。</b>${(D.massing.default_height_share * 100).toFixed(1)}% 的量體高度剛好是 12.0 m，
     其餘集中在 3.2 m 的倍數 → 高度來自 <code class="mono">building:levels</code> × 3.2 m，缺值時填 12 m。
     E6 的所有高度統計都同時報「全部」與「排除預設值」兩組；兩側缺值率相近（北 30.4%、南 29.7%），
     所以不是資料涵蓋造成的假訊號。`,
    `<b>護欄與隔音牆在模型裡是同一段幾何。</b>兩者的長度與頂點數完全相同，
     判定為同一條產生線的兩個高度版本（設計選項），不是兩個各自實測的物件。`,
    `<b>1 組取樣點無法計算</b>（里程 6,100 m）：該處軸線北側 90 m 內完全沒有已繪製的人行網路。
     這是 OSM 資料缺口，已如實標為缺口，未當作障礙計入。`,
    `<b>OSM 是志工地圖。</b>辦公室（office tag）普遍標記不全，商辦數字很可能低估；
     所有 POI 計數都不是官方商業登記統計。`,
    `<b>E9 斷頭路與 E10 幾何穿越點皆未支持假設，一併列出。</b>
     E10 的計數被捷運與縱貫線隧道、以及被平滑中線切到的人行道碎片污染，
     這正是改用網路繞路係數的原因。`,
    `<b>市民大道全段 13.6 km，本分析只涵蓋高架段 6.53 km。</b>
     六～八段（南港方向）無高架，不在同一個障礙假設之內。`,
  ];
  document.getElementById('caveats').innerHTML = cav.map(c => `<li>${c}</li>`).join('');

  document.getElementById('foot').innerHTML =
    `資料來源：${D.meta.sources.map(s => `<code>${s}</code>`).join(' · ')}<br>` +
    `全部量測在 <code>${D.meta.crs_compute}</code>（TWD97 TM2，公尺）進行，` +
    `顯示與原始資料為 <code>${D.meta.crs_display}</code>。` +
    `幾何以 1e-5 度（約 1 m）整數差分編碼，精度細於套疊配準殘差（7 m），編碼未損失實質資訊。<br>` +
    `管線：<code>01_extract_osm</code> → <code>02_build_axis</code> → <code>03_permeability</code> → ` +
    `<code>04_detour</code> → <code>05_structure</code> → <code>06_industry</code> → ` +
    `<code>07_gradient</code> → <code>08_register_blend</code> → <code>09_blend_analysis</code> → ` +
    `<code>10_verdict</code> → <code>11_bundle</code>。每支腳本可獨立重跑驗證。`;
})();

/* ------------------------------------------------------------- boot ------ */
buildLegend();
new ResizeObserver(() => resize()).observe(cv);
resize();
window.addEventListener('resize', () => { resize(); });
matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => { draw(); buildLegend(); });
