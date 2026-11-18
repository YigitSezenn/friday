"use strict";
// Ayarlar penceresi, mikrofon/kamera/telefon düğmeleri ve ilk kurulum (Gemini anahtarı).
// Klasik betikler: üst düzey const/let/function tüm hud-*.js dosyalarında ortaktır; sıra index.html'deki gibidir.
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
for (const id of ["set-story", "set-proactive", "set-water", "set-break", "set-events", "set-phone-auto", "set-windows"]) {
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
    if (button.dataset.tab === "izinler") send("permissions");
  });
});
$("set-patient").addEventListener("click", () => $("set-patient").setAttribute("aria-checked", $("set-patient").getAttribute("aria-checked") === "true" ? "false" : "true"));
$("set-music").addEventListener("click", () => $("set-music").setAttribute("aria-checked", $("set-music").getAttribute("aria-checked") === "true" ? "false" : "true"));
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
