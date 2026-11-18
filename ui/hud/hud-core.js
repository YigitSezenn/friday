"use strict";
// Çekirdek halkası (SVG), uyku modu ve canlandırma döngüsü.
// Klasik betikler: üst düzey const/let/function tüm hud-*.js dosyalarında ortaktır; sıra index.html'deki gibidir.
function ringPath(cx, cy, radius, amp, harmonics, phase) {
  const count = 120;
  const points = [];
  for (let i = 0; i < count; i++) {
    const angle = i / count * Math.PI * 2;
    let offset = 0;
    for (const harmonic of harmonics) offset += Math.sin(angle * harmonic.k + phase * harmonic.s + harmonic.p) * harmonic.a;
    const rr = radius + offset * amp;
    points.push([cx + Math.cos(angle) * rr, cy + Math.sin(angle) * rr]);
  }
  let path = `M${points[0][0].toFixed(2)},${points[0][1].toFixed(2)}`;
  for (let i = 0; i < count; i++) {
    const p0 = points[(i - 1 + count) % count];
    const p1 = points[i];
    const p2 = points[(i + 1) % count];
    const p3 = points[(i + 2) % count];
    path += `C${(p1[0] + (p2[0] - p0[0]) / 6).toFixed(2)},${(p1[1] + (p2[1] - p0[1]) / 6).toFixed(2)} ${(p2[0] - (p3[0] - p1[0]) / 6).toFixed(2)},${(p2[1] - (p3[1] - p1[1]) / 6).toFixed(2)} ${p2[0].toFixed(2)},${p2[1].toFixed(2)}`;
  }
  return path + "Z";
}

// FRIDAY theme.ring from the installed app (jarvis.personas): style smooth, speed 1.5, core 26.
// Harmonics are _FLUID; each shell is [radius, amplitude, opacity].
const RING_SPEED = 1.5;
const GAIN = {idle: 1, paused: 0.6, connecting: 1.1, listening: 1.35, thinking: 1.15, speaking: 1.6, error: 0.8};
const SHELLS = [
  {r: 326, amp: 22, op: 0.3, h: [{k: 2, a: 1, s: 1.1, p: 0}, {k: 3, a: 0.6, s: -0.8, p: 1.1}, {k: 5, a: 0.25, s: 0.6, p: 2}]},
  {r: 284, amp: 18, op: 0.55, h: [{k: 2, a: 0.9, s: -1, p: 0.6}, {k: 4, a: 0.5, s: 0.9, p: 1.8}, {k: 6, a: 0.2, s: -0.5, p: 0.3}]},
  {r: 238, amp: 13, op: 0.85, h: [{k: 3, a: 1, s: 0.9, p: 2.1}, {k: 4, a: 0.45, s: -0.7, p: 0.7}, {k: 7, a: 0.2, s: 0.8, p: 1.5}]},
];

function buildRing() {
  const host = $("core");
  host.replaceChildren();
  const size = 1000;
  const center = size / 2;
  const orb = document.createElement("div");
  orb.className = "orb";
  host.appendChild(orb);
  const layer = attrs => {
    const node = svg("svg", Object.assign({viewBox: `0 0 ${size} ${size}`}, attrs || {}));
    orb.appendChild(node);
    return node;
  };
  const shellSvg = layer({class: "soft"});
  const shells = SHELLS.map((shell, index) => {
    const node = svg("path", {fill: "none", stroke: "currentColor", "stroke-width": index === 0 ? 1.8 : 1.2, "stroke-opacity": shell.op, "stroke-linejoin": "round"});
    shellSvg.appendChild(node);
    return {node, shell};
  });
  const ticks = layer({class: "spin-s"});
  for (let i = 0; i < 90; i++) {
    const angle = i / 90 * Math.PI * 2;
    const long = i % 5 === 0;
    const inner = 372;
    const outer = inner + (long ? 15 : 7);
    ticks.appendChild(svg("line", {
      x1: center + Math.cos(angle) * inner, y1: center + Math.sin(angle) * inner,
      x2: center + Math.cos(angle) * outer, y2: center + Math.sin(angle) * outer,
      stroke: "currentColor", "stroke-opacity": long ? 0.5 : 0.2, "stroke-width": long ? 1.5 : 1,
    }));
  }
  const arc = (radius, from, length, color, width, cls) => {
    const node = layer({class: cls + " soft"});
    node.style.setProperty("--sd", "8");
    const a0 = from * Math.PI / 180;
    const a1 = (from + length) * Math.PI / 180;
    const d = `M${center + Math.cos(a0) * radius},${center + Math.sin(a0) * radius} A${radius},${radius} 0 ${length > 180 ? 1 : 0} 1 ${center + Math.cos(a1) * radius},${center + Math.sin(a1) * radius}`;
    node.appendChild(svg("path", {d, fill: "none", stroke: color, "stroke-width": width, "stroke-opacity": 0.95, "stroke-linecap": "round"}));
  };
  arc(400, 150, 120, "currentColor", 3, "spin-m");
  arc(418, 20, 62, "var(--accent)", 2, "spin-f");
  const pulse = layer({id: "pulse"});
  const defs = svg("defs");
  const glow = svg("radialGradient", {id: "g-core"});
  const mid = svg("radialGradient", {id: "g-mid"});
  [["0%", "#ffffff", 0.95], ["30%", "var(--c)", 0.85], ["60%", "var(--c)", 0.35], ["100%", "var(--c)", 0]].forEach(([offset, color, opacity]) => {
    glow.appendChild(svg("stop", {offset, "stop-color": color, "stop-opacity": opacity}));
  });
  [["0%", "var(--c)", 0.95], ["45%", "var(--c)", 0.8], ["75%", "var(--c)", 0.3], ["100%", "var(--c)", 0]].forEach(([offset, color, opacity]) => {
    mid.appendChild(svg("stop", {offset, "stop-color": color, "stop-opacity": opacity}));
  });
  defs.append(glow, mid);
  pulse.appendChild(defs);
  pulse.appendChild(svg("circle", {cx: center, cy: center, r: 150, fill: "url(#g-core)"}));
  pulse.appendChild(svg("circle", {cx: center, cy: center, r: 92, fill: "url(#g-mid)"}));
  pulse.appendChild(svg("circle", {cx: center, cy: center, r: 26, fill: "#fff", "fill-opacity": 0.92}));
  const hit = document.createElement("button");
  hit.className = "hit";
  hit.type = "button";
  hit.title = "Uyut / uyandır";
  hit.addEventListener("click", () => setSleep(document.body.dataset.sleep !== "1"));
  host.appendChild(hit);
  return shells;
}

// Uyku: çekirdeğe tıklama, sesli komut (sleep_mode aracı), yazı ya da F4 ile.
function setSleep(asleep) {
  asleep = !!asleep;
  if ((document.body.dataset.sleep === "1") === asleep) return;
  document.body.dataset.sleep = asleep ? "1" : "0";
  window.hud.state(asleep ? "paused" : "listening");
  $("t-state").textContent = asleep ? "UYKUDA" : LABEL[document.body.dataset.state];
  send("sleep", {asleep});
}

const ring = buildRing();
let phase = 0;
let last = performance.now();
function frame(now) {
  const dt = Math.min(0.05, (now - last) / 1000);
  last = now;
  if (document.body.dataset.sleep === "1") {
    requestAnimationFrame(frame);
    return;
  }
  const state = document.body.dataset.state;
  const gain = GAIN[state] || 1;
  phase += dt * RING_SPEED * (state === "speaking" ? 1.8 : 1);
  for (const item of ring) {
    item.node.setAttribute("d", ringPath(500, 500, item.shell.r, item.shell.amp * gain, item.shell.h, phase));
  }
  requestAnimationFrame(frame);
}
requestAnimationFrame(frame);
setTimeout(() => { document.body.dataset.boot = "0"; }, 1600);

