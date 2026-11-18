"use strict";
// Sol/sağ paneller: saat, sistem, zamanlayıcı göstergesi, notlar, kimlik, izinler, konuşma satırları.
// Klasik betikler: üst düzey const/let/function tüm hud-*.js dosyalarında ortaktır; sıra index.html'deki gibidir.
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
let timerLabel = "";
let timerSpan = 0;
let stopwatch = false;
let stopwatchStart = 0;
let watchTotal = 0;
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
    // Sayaç Python'da; burada yalnızca gösterilir (bitiş alarmı da oradan gelir).
    const left = Math.max(0, Math.ceil((timerEnd - Date.now()) / 1000));
    const h = Math.floor(left / 3600);
    const m = Math.floor((left % 3600) / 60);
    text = h ? `${h}:${String(m).padStart(2, "0")}:${String(left % 60).padStart(2, "0")}` : `${String(m).padStart(2, "0")}:${String(left % 60).padStart(2, "0")}`;
    sub = timerLabel ? timerLabel.toUpperCase().slice(0, 10) : (left ? "" : "BİTTİ");
    timerFace.arc && timerSpan && timerFace.arc.setAttribute("d", arcPath(Math.max(0.02, left / timerSpan)));
  } else if (stopwatch || watchTotal) {
    const elapsed = Math.floor((stopwatch ? Date.now() - stopwatchStart : watchTotal) / 1000);
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
  const model = window.__liveModel || "models/gemini-3.8-live";
  $("model-blurb").textContent = `${assistantName} arayüzü açık. Ses: Gemini Live, ${model}.`;
  const about = $("about-blurb");
  if (about) {
    const bits = [`Ses: Gemini Live, ${model}.`];
    if (window.__appVersion) bits.push(window.__appVersion);
    const ver = $("t-ver");
    if (ver) ver.textContent = window.__appVersion ? window.__appVersion : "";
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
// Notlar: liste, çift tıkla düzenle, × ile sil (kalıcı kayıt Python'da: jarvis/notes.py).
function renderNotes() {
  $("note-count").textContent = String(notes.length);
  const hint = $("note-hint");
  hint.textContent = uiPack.noteEmpty || "Henüz not yok. “Not al: …” de ya da aşağıya yaz.";
  hint.hidden = notes.length > 0;
  const list = $("note-list");
  list.replaceChildren();
  notes.forEach((note, index) => {
    const item = document.createElement("li");
    const text = document.createElement("span");
    text.className = "note-text";
    text.textContent = note;
    text.title = "Düzenlemek için çift tıkla";
    text.addEventListener("dblclick", () => editNote(item, index));
    const remove = document.createElement("button");
    remove.type = "button";
    remove.className = "note-x";
    remove.title = "Notu sil";
    remove.setAttribute("aria-label", "Notu sil: " + note);
    remove.textContent = "×";
    remove.addEventListener("click", () => {
      item.classList.add("leaving");
      setTimeout(() => send("note_delete", {index}), 180);
    });
    item.append(text, remove);
    list.appendChild(item);
  });
}

function editNote(item, index) {
  const input = document.createElement("input");
  input.className = "note-in note-edit";
  input.value = notes[index] || "";
  item.replaceChildren(input);
  input.focus();
  input.select();
  let done = false;
  const finish = save => {
    if (done) return;
    done = true;
    const value = input.value.trim();
    if (save && value && value !== notes[index]) send("note_edit", {index, text: value});
    else renderNotes();
  };
  input.addEventListener("keydown", event => {
    if (event.key === "Enter") finish(true);
    if (event.key === "Escape") finish(false);
  });
  input.addEventListener("blur", () => finish(true));
}

function addLine(text, kind) {
  const line = document.createElement("div");
  line.className = "sub" + (kind ? " " + kind : "");
  line.textContent = text;
  const log = $("chat-log");
  log.appendChild(line);
  while (log.children.length > 4) log.removeChild(log.firstChild);
}

const PERM_TEXT = {granted: "✓ VERİLDİ", denied: "✕ KAPALI", unknown: "— BİLİNMİYOR"};
function paintPermissions(data) {
  document.querySelectorAll(".perm").forEach(row => {
    const state = (data && data[row.dataset.perm]) || "unknown";
    const badge = row.querySelector(".perm-state");
    badge.dataset.state = state;
    badge.textContent = PERM_TEXT[state] || PERM_TEXT.unknown;
    row.querySelector(".perm-open").hidden = state === "granted";
  });
}
document.querySelectorAll(".perm-open").forEach(button => {
  button.addEventListener("click", () => send("open_privacy", {kind: button.closest(".perm").dataset.perm}));
});

