"use strict";
// Kalan düğme/klavye bağlantıları: pencere, Yenile, güncelleme, ayar kaydı, zamanlayıcı, notlar, komut.
// Klasik betikler: üst düzey const/let/function tüm hud-*.js dosyalarında ortaktır; sıra index.html'deki gibidir.
$("app-pw-open")?.addEventListener("click", () => send("open", {url: "https://myaccount.google.com/apppasswords"}));
$("mail-test")?.addEventListener("click", () => {
  const form = $("settings-form");
  $("mail-test").disabled = true;
  $("mail-test-out").textContent = "Gönderiliyor…";
  send("mail_test", {address: form.gmail_address.value.trim(), password: form.gmail_app_password.value});
});
$("discord-test")?.addEventListener("click", () => {
  $("discord-test").disabled = true;
  $("discord-test-out").textContent = "Gönderiliyor…";
  send("discord_test", {username: $("settings-form").discord_username.value.trim()});
});
// Hızlı ses düğmeleri: ayarları kaydedip sesi yeniden bağlamadan anında uygulanır.
for (const [id, key, sw] of [["mute-music", "music", "set-music"], ["mute-sfx", "effects", "set-sfx"]]) {
  $(id).addEventListener("click", () => {
    const on = $(id).getAttribute("aria-pressed") !== "true";
    $(id).setAttribute("aria-pressed", String(on));
    $(sw).setAttribute("aria-checked", String(on));
    send("sound_toggle", {[key]: on});
  });
}
$("settings-form").discord_owner_id?.addEventListener("input", (event) => {
  const clean = event.target.value.replace(/\D/g, "");
  const warn = $("discord-warn");
  if (clean !== event.target.value) {
    event.target.style.outline = "1px solid #ff5c7a";
    warn.textContent = "Yalnızca rakam yazılabilir. Kullanıcı adı değil, Discord Kullanıcı Kimliği (17-19 haneli sayı) gerekir.";
    warn.hidden = false;
  } else if (clean.length && (clean.length < 15 || clean.length > 22)) {
    event.target.style.outline = "1px solid #ff5c7a";
    warn.textContent = "Kimlik 17-19 haneli olmalı; eksik ya da fazla görünüyor.";
    warn.hidden = false;
  } else {
    event.target.style.outline = "";
    warn.hidden = true;
  }
  event.target.value = clean;
});
$("min").addEventListener("click", () => send("minimize"));
$("quit").addEventListener("click", () => send("quit"));
// Yenile: ilk basış uyarır, 4 sn içinde ikinci basış yeni anahtar üretir (eski telefon eşleşmesi bozulur).
(() => {
  const button = $("pair-refresh");
  if (!button) return;
  let armed = null;
  const reset = () => { armed = null; button.textContent = "Yenile"; button.classList.remove("warn"); };
  button.addEventListener("click", () => {
    if (!armed) {
      button.textContent = "Eski telefon eşleşmesi bozulur · onayla";
      button.classList.add("warn");
      armed = setTimeout(reset, 4000);
      return;
    }
    clearTimeout(armed);
    reset();
    button.disabled = true;
    button.textContent = "Yenileniyor…";
    Promise.resolve(send("gate_refresh", {rotate: true})).finally(() => {
      setTimeout(() => { button.disabled = false; reset(); }, 900);
    });
  });
})();
["home-name", "home-host", "home-cmd"].forEach(id => $(id)?.addEventListener("keydown", event => { if (event.key === "Enter") event.preventDefault(); }));
$("home-add")?.addEventListener("click", () => { $("home-msg").textContent = "Aranıyor…"; send("home", {action: "add", device: $("home-name").value, host: $("home-host").value}); });
$("home-learn")?.addEventListener("click", () => { $("home-msg").textContent = "Dinleniyor: 30 saniye içinde kumandayı köprüye doğrultup tuşa bas…"; send("home", {action: "learn", device: $("home-name").value, command: $("home-cmd").value}); });
// Güncelle: üç düğme de aynı kilidi kullanır; ilk tıktan sonra 10 sn boyunca ikinci tık yok sayılır.
let updateLocked = false;
for (const id of ["home-update", "app-update", "notes-update"]) {
  $(id)?.addEventListener("click", () => {
    if (updateLocked) return;
    updateLocked = true;
    const buttons = ["home-update", "app-update", "notes-update"].map($).filter(Boolean);
    const labels = buttons.map((button) => button.textContent);
    buttons.forEach((button) => { button.disabled = true; button.textContent = "Güncelleniyor…"; });
    send("update");
    setTimeout(() => {
      updateLocked = false;
      buttons.forEach((button, index) => { button.disabled = false; button.textContent = labels[index]; });
    }, 10000);
  });
}
$("app-notes")?.addEventListener("click", () => send("notes"));
$("t-ver")?.addEventListener("click", () => send("notes"));
const closeNotes = () => { $("ov-notes").hidden = true; };
$("notes-ok")?.addEventListener("click", closeNotes);
$("notes-close")?.addEventListener("click", closeNotes);
$("uninstall").addEventListener("click", () => {
  const ok = confirm("FRIDAY kaldırılsın mı? Uygulama ve FRIDAY kayıt klasörü silinir. Başka klasörler silinmez.");
  if (ok) send("uninstall");
});
$("open-data").addEventListener("click", () => send("open_data"));
$("settings-form").addEventListener("submit", event => {
  event.preventDefault();
  const form = event.target;
  const values = {};
  for (const key of ["gemini_api_key", "tavily_api_key", "youtube_api_key", "youtube_channel_handle", "weather_location", "voice", "assistant_name", "address_as", "ui_color", "live_model", "language", "quiet_minutes", "mail_web", "outlook_web_host", "gmail_address", "gmail_app_password", "discord_owner_id", "discord_username"]) values[key] = form[key].value.trim();
  values.voice_volume = Number(form.voice_volume.value);
  values.effects = $("set-sfx").getAttribute("aria-checked") !== "false";
  values.music = $("set-music").getAttribute("aria-checked") === "true";
  values.patient_listening = $("set-patient").getAttribute("aria-checked") !== "false";
  values.clap_wake = $("set-clap").getAttribute("aria-checked") === "true";
  values.proactive_enabled = $("set-proactive").getAttribute("aria-checked") === "true";
  values.water_enabled = $("set-water").getAttribute("aria-checked") === "true";
  values.break_enabled = $("set-break").getAttribute("aria-checked") === "true";
  values.event_alerts = $("set-events").getAttribute("aria-checked") === "true";
  values.phone_autostart = $("set-phone-auto").getAttribute("aria-checked") === "true";
  values.file_access = $("set-files").getAttribute("aria-checked") === "true";
  values.start_with_windows = $("set-windows").getAttribute("aria-checked") === "true";
  values.quiet_minutes = Number(values.quiet_minutes || 20);
  values.panels_off = [...document.querySelectorAll("#set-panels .switch")].filter(node => node.getAttribute("aria-checked") !== "true").map(node => node.dataset.panel);
  send("settings", {values});
  $("ov-settings").hidden = true;
});
document.querySelectorAll("#timer-pick .tbtn[data-min]").forEach(button => {
  button.addEventListener("click", () => send("timer", {action: "set", seconds: Number(button.dataset.min) * 60}));
});
document.querySelectorAll("#timer-live .tbtn[data-add]").forEach(button => {
  button.addEventListener("click", () => send("timer", {action: "add", seconds: Number(button.dataset.add)}));
});
$("t-cancel").addEventListener("click", () => send("timer", {action: "cancel"}));
$("t-stop").addEventListener("click", () => send("timer", {action: "watch", watch: "toggle"}));
function closeTimerDone() {
  $("timer-done").hidden = true;
  send("timer", {action: "dismiss"});
}
$("td-close").addEventListener("click", closeTimerDone);
$("td-snooze").addEventListener("click", () => { closeTimerDone(); send("timer", {action: "set", seconds: 300, label: $("td-label").textContent}); });
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
  if (document.body.dataset.sleep === "1") setSleep(false);
  addLine(text, "you");
  send("command", {text});
});
addEventListener("keydown", event => {
  if (event.key === "F4") {
    event.preventDefault();
    if (document.body.dataset.sleep === "1") { setSleep(false); return; }
    toggleMic();
  }
  if (event.key === "F6") { event.preventDefault(); $("t-cam").click(); }
  if (event.key === "Escape") { $("ov-settings").hidden = true; $("ov-models").hidden = true; $("ov-notes").hidden = true; }
});
