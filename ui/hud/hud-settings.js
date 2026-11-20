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
// Telefona indir: sitenin indirme bölümüne giden QR (telefon kamerası okur).
function paintSiteQr(qr, url) {
  const image = $("site-qr");
  if (image) {
    image.hidden = !qr;
    if (qr) image.src = qr;
  }
  const label = $("site-url");
  if (label) label.textContent = url ? url.replace(/^https:\/\//, "").replace(/[?#].*$/, "") : "";
  const copy = $("site-copy");
  if (copy) copy.dataset.url = url || "";
}
$("site-copy")?.addEventListener("click", event => {
  const button = event.currentTarget;
  if (!button.dataset.url) return;
  send("copy", {text: button.dataset.url});
  button.textContent = "Kopyalandı";
  setTimeout(() => { button.textContent = "Bağlantıyı kopyala"; }, 1600);
});
function showPhone(_data) {}
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

let memoryRows = [];
const MEMORY_LABELS = {email_contacts: "E-posta kişileri", whatsapp_contacts: "WhatsApp kişileri", notes: "Notlar", kisisel: "Kişisel", tercih: "Tercihler", preferences: "Tercihler", personal: "Kişisel"};
const memoryLabel = (name) => MEMORY_LABELS[name] || name;
function paintMemory(rows) {
  if (Array.isArray(rows)) memoryRows = rows;
  const box = $("mem-list");
  const query = ($("mem-search")?.value || "").trim().toLowerCase();
  const shown = memoryRows.filter(row => !query || `${row.category} ${row.key} ${row.text}`.toLowerCase().includes(query));
  $("mem-count").textContent = memoryRows.length ? `${shown.length}/${memoryRows.length} kayıt` : "";
  box.replaceChildren();
  if (!shown.length) {
    const empty = document.createElement("p");
    empty.className = "whisper";
    empty.textContent = memoryRows.length ? "Eşleşen kayıt yok." : "Henüz bir şey hatırlamıyorum. “Şunu hatırla: …” diyebilir ya da aşağıdan ekleyebilirsin.";
    box.appendChild(empty);
    return;
  }
  let lastCategory = null;
  shown.forEach((row, index) => {
    if (row.category !== lastCategory) {
      lastCategory = row.category;
      const head = document.createElement("div");
      head.className = "mem-cat";
      head.textContent = memoryLabel(row.category);
      box.appendChild(head);
    }
    const line = document.createElement("div");
    line.className = "mem-row";
    line.style.setProperty("--n", Math.min(index, 12));
    const text = document.createElement("div");
    text.className = "mem-text";
    const key = document.createElement("b");
    key.textContent = row.key || row.category;
    const value = document.createElement("span");
    value.textContent = row.text;
    text.append(key, value);
    text.title = "Düzeltmek için tıkla";
    text.addEventListener("click", () => {
      const input = document.createElement("input");
      input.className = "mem-edit";
      input.value = row.text;
      input.maxLength = 400;
      value.replaceWith(input);
      input.focus();
      input.select();
      const commit = () => {
        const next = input.value.trim();
        if (next && next !== row.text && row.key) send("memory_save", {category: row.category, key: row.key, text: next});
        else paintMemory();
      };
      input.addEventListener("keydown", event => { if (event.key === "Enter") { event.preventDefault(); commit(); } if (event.key === "Escape") paintMemory(); });
      input.addEventListener("blur", commit);
    });
    const button = document.createElement("button");
    button.type = "button";
    button.className = "tbtn danger";
    button.textContent = "SİL";
    let armed = false;
    button.addEventListener("click", () => {
      if (!armed) {
        armed = true;
        button.textContent = "EMİN MİSİN?";
        setTimeout(() => { armed = false; button.textContent = "SİL"; }, 2500);
        return;
      }
      line.classList.add("gone");
      setTimeout(() => send("forget", {category: row.category, key: row.key}), 260);
    });
    line.append(text, button);
    box.appendChild(line);
  });
}
$("mem-search")?.addEventListener("input", () => paintMemory());
$("mem-save")?.addEventListener("click", () => {
  const category = $("mem-cat").value.trim() || "notes";
  const key = $("mem-key").value.trim();
  const text = $("mem-val").value.trim();
  if (!key || !text) { (key ? $("mem-val") : $("mem-key")).focus(); return; }
  send("memory_save", {category, key, text});
  $("mem-key").value = "";
  $("mem-val").value = "";
});

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
for (const id of ["set-proactive", "set-water", "set-break", "set-events", "set-phone-auto", "set-windows"]) {
  $(id).addEventListener("click", () => $(id).setAttribute("aria-checked", $(id).getAttribute("aria-checked") === "true" ? "false" : "true"));
}
document.querySelectorAll("#quiet-seg button").forEach(button => {
  button.addEventListener("click", () => {
    document.querySelectorAll("#quiet-seg button").forEach(node => node.setAttribute("aria-checked", node === button ? "true" : "false"));
    document.querySelector("[name=quiet_minutes]").value = button.dataset.min;
  });
});
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
