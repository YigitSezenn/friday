"use strict";
// Kalan düğme/klavye bağlantıları: pencere, Yenile, güncelleme, ayar kaydı, zamanlayıcı, notlar, komut.
// Klasik betikler: üst düzey const/let/function tüm hud-*.js dosyalarında ortaktır; sıra index.html'deki gibidir.
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
$("home-update")?.addEventListener("click", () => send("update"));
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
  values.music = $("set-music").getAttribute("aria-checked") === "true";
  values.patient_listening = $("set-patient").getAttribute("aria-checked") !== "false";
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
  if (event.key === "Escape") { $("ov-settings").hidden = true; $("ov-models").hidden = true; }
});
