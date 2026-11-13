"use strict";

const $ = id => document.getElementById(id);
const NS = "http://www.w3.org/2000/svg";
const DAYS = ["PAZARTESİ", "SALI", "ÇARŞAMBA", "PERŞEMBE", "CUMA", "CUMARTESİ", "PAZAR"];
const MONTHS = ["", "OCAK", "ŞUBAT", "MART", "NİSAN", "MAYIS", "HAZİRAN", "TEMMUZ", "AĞUSTOS", "EYLÜL", "EKİM", "KASIM", "ARALIK"];
const LABEL = {connecting: "BAĞLANIYOR", listening: "DİNLİYOR", thinking: "DÜŞÜNÜYOR", speaking: "KONUŞUYOR", idle: "BEKLEMEDE", paused: "SESSİZ", error: "HATA"};
let uiPack = (window.FRIDAY_I18N && window.FRIDAY_I18N.tr) || {};

function applyLanguage(code) {
  const table = window.FRIDAY_I18N || {};
  uiPack = table[code] || table.tr || uiPack;
  if (!uiPack) return;
  document.documentElement.lang = uiPack.htmlLang || "tr";
  Object.assign(LABEL, uiPack.states || {});
  if (uiPack.days) DAYS.splice(0, DAYS.length, ...uiPack.days);
  if (uiPack.months) MONTHS.splice(0, MONTHS.length, ...uiPack.months);
  if (typeof PANEL_LABELS !== "undefined" && uiPack.panels) Object.assign(PANEL_LABELS, uiPack.panels);
  document.querySelectorAll("[data-i18n]").forEach((node) => {
    const value = uiPack[node.dataset.i18n];
    if (typeof value !== "string") return;
    const text = [...node.childNodes].find((child) => child.nodeType === 3 && child.textContent.trim());
    if (text && node.childElementCount) text.textContent = value;
    else node.textContent = value;
  });
  document.querySelectorAll("[data-i18n-ph]").forEach((node) => {
    const value = uiPack[node.dataset.i18nPh];
    if (typeof value === "string") node.placeholder = value;
  });
  const state = document.body.dataset.state;
  if ($("t-state") && LABEL[state]) $("t-state").textContent = LABEL[state];
  if ($("t-mic-state")) $("t-mic-state").textContent = $("t-mic").dataset.on === "0" ? uiPack.micOff : uiPack.micOn;
  if ($("t-cam-state")) $("t-cam-state").textContent = $("t-cam").dataset.on === "1" ? uiPack.camOn : uiPack.camOff;
  if ($("hint")) $("hint").textContent = $("t-mic").dataset.on === "0" ? uiPack.hintOff : uiPack.hintOn;
}

function send(kind, data) {
  const payload = data || {};
  try {
    if (window.pywebview && window.pywebview.api) return window.pywebview.api.post(kind, payload);
  } catch (err) {
    console.error(err);
  }
  return Promise.resolve();
}

function svg(tag, attrs) {
  const node = document.createElementNS(NS, tag);
  for (const key in attrs || {}) node.setAttribute(key, attrs[key]);
  return node;
}

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
  hit.addEventListener("click", () => {
    const asleep = document.body.dataset.sleep !== "1";
    document.body.dataset.sleep = asleep ? "1" : "0";
    window.hud.state(asleep ? "paused" : "listening");
    $("t-state").textContent = asleep ? "UYKUDA" : LABEL[document.body.dataset.state];
    send("sleep", {asleep});
  });
  host.appendChild(hit);
  return shells;
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

function dial(host, size) {
  host.replaceChildren();
  const node = svg("svg", {viewBox: "0 0 100 100"});
  node.appendChild(svg("circle", {cx: 50, cy: 50, r: 42, fill: "none", stroke: "rgba(var(--rgb),.28)", "stroke-width": 1.4}));
  const arc = svg("path", {id: "arc", fill: "none", stroke: "var(--accent)", "stroke-width": 2.2, "stroke-linecap": "round"});
  const label = svg("text", {x: 50, y: 50, "text-anchor": "middle", "dominant-baseline": "middle", fill: "#fff", "font-size": size, "font-family": "Segoe UI"});
  const sub = svg("text", {x: 50, y: 66, "text-anchor": "middle", fill: "var(--dim)", "font-size": 8, "font-family": "Segoe UI"});
  node.append(arc, label, sub);
  host.appendChild(node);
  return {arc, label, sub};
}

const clock = dial($("clock-dial"), 16);
const gauge = dial($("sys-dial"), 18);
const timerFace = dial($("timer-dial"), 13);
gauge.sub.textContent = "";

function arcPath(fraction) {
  const span = Math.max(0.02, Math.min(0.999, fraction)) * Math.PI * 2;
  const start = -Math.PI / 2;
  const end = start + span;
  const r = 42;
  const large = span > Math.PI ? 1 : 0;
  return `M${50 + Math.cos(start) * r},${50 + Math.sin(start) * r} A${r},${r} 0 ${large} 1 ${50 + Math.cos(end) * r},${50 + Math.sin(end) * r}`;
}

let timerEnd = 0;
let stopwatch = false;
let stopwatchStart = 0;
let cpu = 0;

function paintDials() {
  const now = new Date();
  $("t-clock").textContent = now.toLocaleTimeString("tr-TR", {hour: "2-digit", minute: "2-digit"});
  $("when").textContent = `${DAYS[now.getDay() === 0 ? 6 : now.getDay() - 1]} · ${now.getDate()} ${MONTHS[now.getMonth() + 1]}`;
  clock.label.textContent = now.toLocaleTimeString("tr-TR", {hour: "2-digit", minute: "2-digit"});
  clock.arc.setAttribute("d", arcPath(now.getSeconds() / 60));
  gauge.label.textContent = String(Math.round(cpu));
  gauge.arc.setAttribute("d", arcPath(Math.max(0.04, cpu / 100)));
  let text = "--:--";
  let sub = "HAZIR";
  if (timerEnd) {
    const left = Math.max(0, Math.ceil((timerEnd - Date.now()) / 1000));
    text = `${String(Math.floor(left / 60)).padStart(2, "0")}:${String(left % 60).padStart(2, "0")}`;
    sub = left ? "" : "BİTTİ";
    if (!left) {
      timerEnd = 0;
      send("beep");
    }
  } else if (stopwatch) {
    const elapsed = Math.floor((Date.now() - stopwatchStart) / 1000);
    text = `${String(Math.floor(elapsed / 60)).padStart(2, "0")}:${String(elapsed % 60).padStart(2, "0")}`;
    sub = "";
  }
  timerFace.label.textContent = text;
  timerFace.sub.textContent = sub;
}
setInterval(paintDials, 200);
paintDials();

let notes = [];
let assistantName = "FRIDAY";

function paintIdentity(name) {
  assistantName = name || "FRIDAY";
  $("mark").textContent = assistantName;
  document.title = assistantName;
  const model = window.__liveModel || "models/gemini-2.5-flash-native-audio-latest";
  $("model-blurb").textContent = `${assistantName} arayüzü açık. Ses: Gemini Live, ${model}.`;
  const about = $("about-blurb");
  if (about) {
    const bits = [`Ses: Gemini Live, ${model}.`];
    if (window.__appVersion) bits.push(window.__appVersion);
    if (window.__dataDir) bits.push("Kayıtlar: " + window.__dataDir);
    about.textContent = bits.join(" ");
  }
}

function paintPalette(palette) {
  if (!palette) return;
  const root = document.documentElement.style;
  for (const key of ["c", "rgb", "accent", "arg", "ink", "dim", "faint"]) {
    if (palette[key]) root.setProperty("--" + key, palette[key]);
  }
}
function renderNotes() {
  $("note-count").textContent = String(notes.length);
  $("note-hint").textContent = notes.length ? notes.slice(-2).join("\n") : (uiPack.noteEmpty || "");
}

function addLine(text, kind) {
  const line = document.createElement("div");
  line.className = "sub" + (kind ? " " + kind : "");
  line.textContent = text;
  const log = $("chat-log");
  log.appendChild(line);
  while (log.children.length > 4) log.removeChild(log.firstChild);
}

window.hud = {
  state(name) {
    document.body.dataset.state = name || "idle";
    $("t-state").textContent = LABEL[name] || name;
  },
  muted(on) {
    $("t-mic").dataset.on = on ? "0" : "1";
    $("t-mic-state").textContent = on ? uiPack.micOff : uiPack.micOn;
    $("hint").textContent = on ? uiPack.hintOff : uiPack.hintOn;
    if (on && document.body.dataset.state === "listening") document.body.dataset.state = "paused";
  },
  camera(on) {
    $("t-cam").dataset.on = on ? "1" : "0";
    $("t-cam-state").textContent = on ? uiPack.camOn : uiPack.camOff;
  },
  log(text) {
    text = String(text == null ? "" : text);
    if (text.startsWith("JARVIS:")) addLine(text.slice(7).trim(), "");
    else if (text.startsWith("Siz:")) addLine(text.slice(4).trim(), "you");
    else if (text.startsWith("ERR:")) {
      addLine(text.slice(4).trim(), "err");
      if (document.body.classList.contains("onboard") && !/anahtari yok|anahtar yok/i.test(text) && /anahtar|baglanti|bağlantı|api|internet/i.test(text)) {
        keyBusy = false;
        const input = $("ob-key");
        if (input) input.disabled = false;
        onboardNote(text.slice(4).trim(), "bad");
        const help = $("ob-khelp");
        if (help) help.classList.add("loud");
      }
    }
    else if (text.includes("FRIDAY ayakta")) {
      addLine("Her şey çalıştı. FRIDAY ayakta.", "");
      closeOnboard();
    }
  },
  stats(data) {
    cpu = Number(data.cpu) || 0;
    $("sys-rows").textContent = `CPU  %${Math.round(cpu)}\nRAM  %${Math.round(data.ram || 0)}\nDİSK %${Math.round(data.disk || 0)} dolu`;
  },
  weather(data) {
    window.__weather = data || {};
    $("wx-temp").textContent = data.temp || "--°";
    $("wx-city").textContent = data.city || "KONUM";
    $("wx-desc").textContent = data.desc || "";
    $("wx-detail").textContent = data.detail || "";
    $("map-cap").textContent = data.city ? `${data.city} · SABİT KONUM · küçük görüntü © Esri` : "";
  },
  place(spot) {
    window.__spot = spot || null;
  },
  agenda(data) {
    $("cal-count").textContent = String(data.calendarCount || 0);
    $("rem-count").textContent = String(data.reminderCount || 0);
    $("cal-text").textContent = data.calendar || "Bugün takviminde etkinlik yok.";
    $("rem-text").textContent = data.reminders || "Bekleyen anımsatıcı yok.";
  },
  map(src) {
    if (src) $("map-img").src = src;
  },
  preview(src) {
    if (src) $("map-img").src = src;
  },
  notes(lines) {
    notes = lines || [];
    renderNotes();
  },
  updateOffer(version) {
    const button = $("app-update");
    if (!button || !version) return;
    button.hidden = false;
    button.textContent = "Güncelle " + version;
  },
  focus(name) {
    document.querySelectorAll(".mod").forEach(node => node.classList.toggle("lit", node.dataset.key === name));
    setTimeout(() => document.querySelectorAll(".mod.lit").forEach(node => node.classList.remove("lit")), 5000);
  },
  settings(data) {
    const form = $("settings-form");
    const shown = data.config && data.config.language && data.config.language !== "auto" ? data.config.language : (data.uiLanguage || "tr");
    window.__uiLanguage = shown;
    applyLanguage(shown);
    const voice = form.voice;
    voice.replaceChildren();
    for (const name of data.voices || []) {
      const option = document.createElement("option");
      option.value = name;
      option.textContent = name;
      voice.appendChild(option);
    }
    const colors = $("color-seg");
    colors.replaceChildren();
    for (const item of data.colors || []) {
      const button = document.createElement("button");
      button.type = "button";
      button.textContent = (uiPack.colors && uiPack.colors[item.id]) || item.label;
      button.dataset.color = item.id;
      button.setAttribute("aria-checked", item.id === (data.config.ui_color || "gold") ? "true" : "false");
      button.addEventListener("click", () => {
        form.ui_color.value = item.id;
        colors.querySelectorAll("button").forEach(node => node.setAttribute("aria-checked", node === button ? "true" : "false"));
      });
      colors.appendChild(button);
    }
    const list = $("address-list");
    list.replaceChildren();
    for (const phrase of data.addresses || []) {
      const option = document.createElement("option");
      option.value = phrase;
      list.appendChild(option);
    }
    paintChoice($("model-seg"), data.models || [], data.config.live_model, value => { form.live_model.value = value; });
    paintChoice($("lang-seg"), (data.languages || []).map(item => item.key), data.config.language || "auto", value => {
      form.language.value = value;
      const next = value === "auto" ? "tr" : value;
      window.__uiLanguage = next;
      applyLanguage(next);
      send("settings", {values: {language: value}});
    }, uiPack.langNames || {});
    for (const key of ["gemini_api_key", "youtube_api_key", "youtube_channel_handle", "weather_location", "voice", "assistant_name", "address_as", "ui_color", "live_model", "language", "quiet_minutes"]) {
      if (form[key]) form[key].value = data.config[key] || "";
    }
    if (form.voice_volume) {
      form.voice_volume.value = String(data.config.voice_volume ?? 100);
      $("vol-label").textContent = "%" + form.voice_volume.value;
    }
    $("set-sfx").setAttribute("aria-checked", data.config.effects === false ? "false" : "true");
    setSwitch("set-aec", data.config.aec_enabled !== false);
    setSwitch("set-story", data.config.story_enabled);
    setSwitch("set-proactive", data.config.proactive_enabled);
    setSwitch("set-water", data.config.water_enabled);
    setSwitch("set-break", data.config.break_enabled);
    setSwitch("set-events", data.config.event_alerts);
    setSwitch("set-phone-auto", data.config.phone_autostart);
    setSwitch("set-windows", data.config.start_with_windows);
    document.querySelectorAll("#quiet-seg button").forEach(node => node.setAttribute("aria-checked", node.dataset.min === String(data.config.quiet_minutes || 20) ? "true" : "false"));
    window.__liveModel = data.config.live_model;
    window.__dataDir = data.dataDir || "";
    window.__appVersion = data.version || "";
    paintStory(data.story);
    showPhone(data.phone);
    paintGate(data.gateKeyQr, data.pairCode);
    $("set-mic").setAttribute("aria-checked", $("t-mic").dataset.on === "1" ? "true" : "false");
    paintPanels(data.panels);
    paintMemory(data.memories);
    paintIdentity(data.name);
    paintPalette(data.palette);
    if (data.needKey) openOnboard();
  },
  phone(data) {
    showPhone(data);
  },
  story(data) {
    paintStory(data);
  },
};

const PANEL_LABELS = {time: "Zaman", system: "Sistem", timer: "Zamanlayıcı", notes: "Notlar", weather: "Hava", calendar: "Takvim", reminders: "Anımsatıcılar", map: "Harita"};

function setSwitch(id, on) {
  const node = $(id);
  if (node) node.setAttribute("aria-checked", on ? "true" : "false");
}
function paintChoice(host, values, current, onPick, labels) {
  if (!host) return;
  host.replaceChildren();
  for (const value of values) {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = labels && labels[value] ? labels[value] : String(value).replace("models/", "");
    button.setAttribute("aria-checked", value === current ? "true" : "false");
    button.addEventListener("click", () => {
      host.querySelectorAll("button").forEach(node => node.setAttribute("aria-checked", node === button ? "true" : "false"));
      onPick(value);
    });
    host.appendChild(button);
  }
}
function paintGate(qr, code) {
  const image = $("gate-qr");
  const digits = $("pair-code");
  if (image) {
    if (qr) {
      image.hidden = false;
      image.src = qr;
    } else {
      image.hidden = true;
      image.removeAttribute("src");
    }
  }
  if (digits) digits.textContent = /^\d{6}$/.test(String(code || "")) ? String(code) : "------";
}
function showPhone(_data) {}
function paintStory(story) {
  const note = $("story-note");
  const list = $("story-list");
  if (!note || !list) return;
  if (!story || !story.enabled) {
    note.textContent = "Hikâye kapalı. Genel sekmesinden açınca ipuçları birikir.";
    list.replaceChildren();
    return;
  }
  const hint = (story.hints || [])[0];
  note.textContent = story.ending === "kapat" ? "Hikâye kapandı. Başarımlar duruyor." : hint ? "İpucu: " + hint : "Açık iz kalmadı.";
  list.replaceChildren();
  for (const row of story.achievements || []) {
    const line = document.createElement("div");
    line.className = "mem-row";
    line.textContent = (row.got ? "açıldı · " : "kapalı · ") + row.title + " — " + row.detail;
    list.appendChild(line);
  }
}
function paintPanels(panels) {
  const box = $("set-panels");
  box.replaceChildren();
  for (const panel of panels || []) {
    const row = document.createElement("div");
    row.className = "row2";
    const text = document.createElement("div");
    text.textContent = PANEL_LABELS[panel.id] || panel.id;
    const toggle = document.createElement("button");
    toggle.type = "button";
    toggle.className = "switch";
    toggle.dataset.panel = panel.id;
    toggle.setAttribute("aria-checked", panel.off ? "false" : "true");
    toggle.addEventListener("click", () => toggle.setAttribute("aria-checked", toggle.getAttribute("aria-checked") === "true" ? "false" : "true"));
    row.append(text, toggle);
    box.appendChild(row);
    const node = document.querySelector(`.mod[data-key="${panel.id}"]`);
    if (node) node.hidden = !!panel.off;
  }
}

function paintMemory(rows) {
  const box = $("mem-list");
  box.replaceChildren();
  if (!rows || !rows.length) {
    box.textContent = "Kayıt yok.";
    return;
  }
  for (const row of rows) {
    const line = document.createElement("div");
    line.className = "mem-row";
    const text = document.createElement("span");
    text.textContent = `${row.category} · ${row.key}: ${row.text}`;
    const button = document.createElement("button");
    button.type = "button";
    button.className = "tbtn";
    button.textContent = "SİL";
    button.addEventListener("click", () => send("forget", {category: row.category, key: row.key}));
    line.append(text, button);
    box.appendChild(line);
  }
}

function toggleMic() {
  const off = $("t-mic").dataset.on === "1";
  window.hud.muted(off);
  if (off) window.hud.state("paused");
  else if (document.body.dataset.state === "paused") window.hud.state("listening");
  send("mute", {muted: off});
}
$("t-mic").addEventListener("click", toggleMic);
$("t-cam").addEventListener("click", () => {
  const on = $("t-cam").dataset.on !== "1";
  window.hud.camera(on);
  send("camera", {on});
});
function openPhone() {
  $("ov-settings").hidden = false;
  document.querySelector('.stab[data-tab="telefon"]').click();
  send("phone");
}
$("t-phone").addEventListener("click", openPhone);
for (const id of ["set-story", "set-proactive", "set-water", "set-break", "set-events", "set-phone-auto", "set-aec", "set-windows"]) {
  $(id).addEventListener("click", () => $(id).setAttribute("aria-checked", $(id).getAttribute("aria-checked") === "true" ? "false" : "true"));
}
document.querySelectorAll("#quiet-seg button").forEach(button => {
  button.addEventListener("click", () => {
    document.querySelectorAll("#quiet-seg button").forEach(node => node.setAttribute("aria-checked", node === button ? "true" : "false"));
    document.querySelector("[name=quiet_minutes]").value = button.dataset.min;
  });
});
$("story-keep").addEventListener("click", () => send("story", {ending: "surdur"}));
$("story-end").addEventListener("click", () => send("story", {ending: "kapat"}));
document.querySelectorAll(".stab").forEach(button => {
  button.addEventListener("click", () => {
    document.querySelectorAll(".stab").forEach(node => node.setAttribute("aria-selected", node === button ? "true" : "false"));
    document.querySelectorAll(".pane").forEach(node => node.classList.toggle("on", node.dataset.pane === button.dataset.tab));
  });
});
$("set-sfx").addEventListener("click", () => $("set-sfx").setAttribute("aria-checked", $("set-sfx").getAttribute("aria-checked") === "true" ? "false" : "true"));
$("set-mic").addEventListener("click", () => { toggleMic(); $("set-mic").setAttribute("aria-checked", $("t-mic").dataset.on === "1" ? "true" : "false"); });
const volume = document.querySelector("[name=voice_volume]");
if (volume) volume.addEventListener("input", () => { $("vol-label").textContent = "%" + volume.value; });
$("t-settings").addEventListener("click", () => { $("ov-settings").hidden = false; });
$("t-persona").addEventListener("click", () => { $("ov-models").hidden = false; });
$("set-close").addEventListener("click", () => { $("ov-settings").hidden = true; });
$("mod-close").addEventListener("click", () => { $("ov-models").hidden = true; });
const AI_STUDIO = "https://aistudio.google.com/apikey";
const KEY_VIDEO = "https://youtu.be/VZl5uBT4a60";
let keyBusy = false;
let keyTimer = 0;
function openOnboard() {
  const board = $("onboard");
  if (!board || document.body.classList.contains("onboard")) return;
  document.body.classList.add("onboard");
  document.body.dataset.ob = "step";
  board.hidden = false;
  setTimeout(() => { const input = $("ob-key"); if (input && !input.disabled) input.focus(); }, 400);
}
function closeOnboard() {
  keyBusy = false;
  clearTimeout(keyTimer);
  document.body.classList.remove("onboard");
  delete document.body.dataset.ob;
  const board = $("onboard");
  if (board) board.hidden = true;
  const help = $("keyhelp");
  if (help) help.hidden = true;
  const input = $("ob-key");
  if (input) { input.value = ""; input.disabled = false; }
}
function onboardNote(text, kind) {
  const note = $("ob-key-note");
  if (!note) return;
  note.textContent = text || "";
  note.classList.toggle("good", kind === "good");
  note.classList.toggle("bad", kind === "bad");
}
function submitKey() {
  if (keyBusy) return;
  const input = $("ob-key");
  if (!input) return;
  const key = input.value.trim();
  if (key.length < 30) {
    onboardNote(key ? "Bu anahtar çok kısa görünüyor; tamamını kopyaladığından emin ol." : "Anahtar girilmedi.", "bad");
    $("ob-khelp").classList.add("loud");
    return;
  }
  keyBusy = true;
  input.value = "";
  input.disabled = true;
  $("ob-khelp").classList.remove("loud");
  onboardNote("Anahtar kaydedildi. Bağlantı kuruluyor.", "good");
  $("ob-sub").textContent = "Bağlantı kuruluyor.";
  send("settings", {values: {gemini_api_key: key}});
}
$("ob-get").addEventListener("click", () => send("open", {url: AI_STUDIO}));
$("ob-video").addEventListener("click", () => send("open", {url: KEY_VIDEO}));
$("kh-studio").addEventListener("click", () => send("open", {url: AI_STUDIO}));
$("kh-video").addEventListener("click", () => send("open", {url: KEY_VIDEO}));
$("ob-key").addEventListener("input", () => {
  onboardNote("", "");
  $("ob-khelp").classList.remove("loud");
  clearTimeout(keyTimer);
  if ($("ob-key").value.trim().length >= 30) keyTimer = setTimeout(submitKey, 400);
});
$("ob-key").addEventListener("keydown", event => { if (event.key === "Enter") submitKey(); });
$("ob-next").addEventListener("click", submitKey);
$("ob-khelp").addEventListener("click", () => { $("keyhelp").hidden = false; });
$("kh-close").addEventListener("click", () => { $("keyhelp").hidden = true; });
$("keyhelp").addEventListener("click", event => { if (event.target.id === "keyhelp") $("keyhelp").hidden = true; });
document.querySelectorAll(".kh-q").forEach(button => {
  button.addEventListener("click", () => button.parentElement.classList.toggle("open"));
});
function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text != null) node.textContent = text;
  return node;
}
function clockMinutes(text) {
  const match = String(text || "").trim().match(/^(\d{1,2}):(\d{2})\s*([AP]M)?$/i);
  if (!match) return null;
  let hour = Number(match[1]);
  const minute = Number(match[2]);
  const mark = (match[3] || "").toUpperCase();
  if (mark === "PM" && hour < 12) hour += 12;
  if (mark === "AM" && hour === 12) hour = 0;
  return hour * 60 + minute;
}
function dayName(date, index) {
  if (index === 0) return "BUGÜN";
  if (index === 1) return "YARIN";
  const parsed = new Date(`${date}T12:00:00`);
  const names = ["PAZAR", "PAZARTESİ", "SALI", "ÇARŞAMBA", "PERŞEMBE", "CUMA", "CUMARTESİ"];
  return Number.isNaN(parsed.getTime()) ? "" : names[parsed.getDay()];
}
function dayLabel(date) {
  const parsed = new Date(`${date}T12:00:00`);
  if (Number.isNaN(parsed.getTime())) return date || "";
  const months = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"];
  return `${parsed.getDate()} ${months[parsed.getMonth()]}`;
}
function wet(desc) {
  return /yağ|çis|kar|sağanak/i.test(desc || "");
}
function openWeather() {
  const card = (window.__weather && window.__weather.card) || {};
  if (!card.temp && !card.place) return;
  const host = $("wx-body");
  host.replaceChildren();
  const head = el("div", "wxhead");
  const titles = el("div");
  titles.append(el("h2", "", "HAVA DURUMU"), el("p", "", [card.place, card.country, card.observed ? `GÜNCELLENDİ ${card.observed}` : ""].filter(Boolean).join(" · ").toUpperCase()));
  head.append(titles, el("button", "", "×"));
  head.lastChild.id = "wx-close";
  head.lastChild.type = "button";
  host.appendChild(head);

  const hero = el("div", "wxhero");
  const main = el("div", "wxmain");
  main.append(el("b", "", card.temp ? `${card.temp}°` : "—"), el("div", "wxcopy"));
  main.lastChild.append(el("strong", "", card.desc || "—"), el("span", "", `Hissedilen ${card.feels || "—"}°`), el("span", "", `En yüksek ${card.high || "—"}° · En düşük ${card.low || "—"}°`));
  hero.append(main, sunCard(card), moonCard(card));
  host.appendChild(hero);

  const stats = el("div", "wxstats");
  const items = [
    ["NEM", card.humidity ? `%${card.humidity}` : "—", ""],
    ["RÜZGÂR", card.wind ? `${card.wind} km/s` : "—", card.windFrom || ""],
    ["BASINÇ", card.pressure ? `${card.pressure} hPa` : "—", "yüksek basınç"],
    ["GÖRÜŞ", card.visibility ? `${card.visibility} km` : "—", Number(card.visibility) >= 10 ? "açık" : ""],
    ["UV", card.uv || "—", card.uvLabel || ""],
    ["BULUT", card.cloud ? `%${card.cloud}` : "—", card.precip ? `${card.precip} mm yağış` : ""],
  ];
  for (const [name, value, note] of items) {
    const box = el("div", "wxstat");
    box.append(el("i", "", name), el("b", "", value));
    if (note) box.append(el("small", "", note));
    stats.appendChild(box);
  }
  host.appendChild(stats);
  host.appendChild(hourCard(card.hours || []));
  const days = el("div", "wxdays");
  (card.days || []).slice(0, 3).forEach((day, index) => {
    const box = el("div", "wxday");
    box.append(el("i", "", dayName(day.date, index)), el("small", "", dayLabel(day.date)), el("b", "", `${day.hi || "—"}°`), el("span", "", `${day.lo || "—"}°`), el("p", "", day.desc || ""), el("small", "", `↑ %${day.rain || "0"}`));
    days.appendChild(box);
  });
  host.appendChild(days);
  $("ov-weather").hidden = false;
}
function sunCard(card) {
  const box = el("div", "wxsun");
  const rise = clockMinutes(card.sunrise);
  const set = clockMinutes(card.sunset);
  const now = clockMinutes(card.observed);
  let progress = 0.35;
  if (rise != null && set != null && set > rise && now != null) progress = Math.min(1, Math.max(0, (now - rise) / (set - rise)));
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("viewBox", "0 0 160 86");
  const arc = document.createElementNS("http://www.w3.org/2000/svg", "path");
  arc.setAttribute("d", "M12 72 Q80 4 148 72");
  arc.setAttribute("fill", "none");
  arc.setAttribute("stroke", "var(--accent)");
  arc.setAttribute("stroke-width", "3");
  svg.appendChild(arc);
  const dot = document.createElementNS("http://www.w3.org/2000/svg", "circle");
  const t = progress;
  const x = (1 - t) * (1 - t) * 12 + 2 * (1 - t) * t * 80 + t * t * 148;
  const y = (1 - t) * (1 - t) * 72 + 2 * (1 - t) * t * 4 + t * t * 72;
  dot.setAttribute("cx", String(x));
  dot.setAttribute("cy", String(y));
  dot.setAttribute("r", "5");
  dot.setAttribute("fill", "var(--accent)");
  svg.appendChild(dot);
  box.appendChild(svg);
  box.append(el("p", "", `${card.sunrise || "—"}  GÜNEŞ  ${card.sunset || "—"}`));
  return box;
}
function moonCard(card) {
  const box = el("div", "wxmoon");
  box.append(el("i", "", "AY"), el("b", "", card.moon || "—"), el("small", "", card.moonLight ? `%${card.moonLight} aydınlık` : ""));
  return box;
}
function hourCard(hours) {
  const box = el("div", "wxhours");
  box.appendChild(el("p", "", "ÖNÜMÜZDEKİ 24 SAAT"));
  if (!hours.length) return box;
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("viewBox", "0 0 800 150");
  const temps = hours.map(hour => Number(hour.temp) || 0);
  const low = Math.min(...temps) - 1;
  const high = Math.max(...temps) + 1;
  const span = Math.max(1, high - low);
  const points = temps.map((temp, index) => {
    const x = 36 + index * (728 / Math.max(1, hours.length - 1));
    const y = 28 + (1 - (temp - low) / span) * 70;
    return [x, y];
  });
  const line = document.createElementNS("http://www.w3.org/2000/svg", "polyline");
  line.setAttribute("points", points.map(point => point.join(",")).join(" "));
  line.setAttribute("fill", "none");
  line.setAttribute("stroke", "currentColor");
  line.setAttribute("stroke-width", "3");
  svg.appendChild(line);
  points.forEach((point, index) => {
    const dot = document.createElementNS("http://www.w3.org/2000/svg", "circle");
    dot.setAttribute("cx", String(point[0]));
    dot.setAttribute("cy", String(point[1]));
    dot.setAttribute("r", "4");
    dot.setAttribute("fill", "#fff");
    svg.appendChild(dot);
    const label = document.createElementNS("http://www.w3.org/2000/svg", "text");
    label.setAttribute("x", String(point[0]));
    label.setAttribute("y", String(point[1] - 10));
    label.setAttribute("text-anchor", "middle");
    label.setAttribute("fill", "var(--ink)");
    label.setAttribute("font-size", "14");
    label.textContent = `${temps[index]}°`;
    svg.appendChild(label);
  });
  box.appendChild(svg);
  const row = el("div", "wxhourrow");
  hours.forEach((hour, index) => {
    const cell = el("div");
    cell.append(el("b", "", index === 0 ? "ŞİMDİ" : hour.time), el("small", "", `%${hour.rain || "0"}`));
    row.appendChild(cell);
  });
  box.appendChild(row);
  return box;
}
let bigMap = null;
function openMap() {
  const spot = window.__spot;
  $("map-title").textContent = (spot && spot.label) || $("wx-city").textContent || "KONUM";
  $("ov-map").hidden = false;
  const frame = $("bigmap");
  const img = $("bigmap-img");
  if (window.maplibregl && spot && spot.lat != null) {
    img.hidden = true;
    frame.hidden = false;
    if (!bigMap) {
      bigMap = new maplibregl.Map({
        container: frame,
        style: "https://tiles.openfreemap.org/styles/dark",
        center: [Number(spot.lon), Number(spot.lat)],
        zoom: 11,
        attributionControl: true,
      });
      bigMap.addControl(new maplibregl.NavigationControl(), "top-left");
    }
    setTimeout(() => {
      bigMap.resize();
      bigMap.jumpTo({center: [Number(spot.lon), Number(spot.lat)], zoom: 11});
    }, 40);
    return;
  }
  frame.hidden = true;
  img.hidden = false;
  img.src = $("map-img").src || "";
}
document.querySelector('[data-key="weather"]').addEventListener("click", openWeather);
document.querySelector('[data-key="map"]').addEventListener("click", openMap);
$("ov-weather").addEventListener("click", event => { if (event.target.id === "wx-close") $("ov-weather").hidden = true; });
$("map-close").addEventListener("click", () => { $("ov-map").hidden = true; });
$("min").addEventListener("click", () => send("minimize"));
$("quit").addEventListener("click", () => send("quit"));
$("app-update")?.addEventListener("click", () => send("update"));
$("uninstall").addEventListener("click", () => {
  const ok = confirm("FRIDAY kaldırılsın mı? Uygulama ve FRIDAY kayıt klasörü silinir. Başka klasörler silinmez.");
  if (ok) send("uninstall");
});
$("open-data").addEventListener("click", () => send("open_data"));
$("settings-form").addEventListener("submit", event => {
  event.preventDefault();
  const form = event.target;
  const values = {};
  for (const key of ["gemini_api_key", "youtube_api_key", "youtube_channel_handle", "weather_location", "voice", "assistant_name", "address_as", "ui_color", "live_model", "language", "quiet_minutes"]) values[key] = form[key].value.trim();
  values.voice_volume = Number(form.voice_volume.value);
  values.effects = $("set-sfx").getAttribute("aria-checked") !== "false";
  values.aec_enabled = $("set-aec").getAttribute("aria-checked") !== "false";
  values.story_enabled = $("set-story").getAttribute("aria-checked") === "true";
  values.proactive_enabled = $("set-proactive").getAttribute("aria-checked") === "true";
  values.water_enabled = $("set-water").getAttribute("aria-checked") === "true";
  values.break_enabled = $("set-break").getAttribute("aria-checked") === "true";
  values.event_alerts = $("set-events").getAttribute("aria-checked") === "true";
  values.phone_autostart = $("set-phone-auto").getAttribute("aria-checked") === "true";
  values.start_with_windows = $("set-windows").getAttribute("aria-checked") === "true";
  values.quiet_minutes = Number(values.quiet_minutes || 20);
  values.panels_off = [...document.querySelectorAll("#set-panels .switch")].filter(node => node.getAttribute("aria-checked") !== "true").map(node => node.dataset.panel);
  send("settings", {values});
  $("ov-settings").hidden = true;
});
document.querySelectorAll(".tbtn[data-min]").forEach(button => {
  button.addEventListener("click", () => {
    stopwatch = false;
    timerEnd = Date.now() + Number(button.dataset.min) * 60000;
  });
});
$("t-stop").addEventListener("click", () => {
  timerEnd = 0;
  stopwatch = !stopwatch;
  if (stopwatch) stopwatchStart = Date.now();
});
$("note-in").addEventListener("keydown", event => {
  if (event.key !== "Enter") return;
  const text = event.target.value.trim();
  if (!text) return;
  notes.push(text);
  renderNotes();
  event.target.value = "";
  send("note", {lines: notes});
});
$("cmd").addEventListener("keydown", event => {
  if (event.key !== "Enter") return;
  const text = event.target.value.trim();
  if (!text) return;
  event.target.value = "";
  if (text.toLowerCase().startsWith("not al:")) {
    const note = text.split(":").slice(1).join(":").trim();
    if (note) {
      notes.push(note);
      renderNotes();
      send("note", {lines: notes});
    }
    return;
  }
  addLine(text, "you");
  send("command", {text});
});
addEventListener("keydown", event => {
  if (event.key === "F4") { event.preventDefault(); toggleMic(); }
  if (event.key === "F6") { event.preventDefault(); $("t-cam").click(); }
  if (event.key === "Escape") { $("ov-settings").hidden = true; $("ov-models").hidden = true; }
});
