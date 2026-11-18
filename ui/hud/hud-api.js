"use strict";
// window.hud: Python'un (bridge) çağırdığı arayüz fonksiyonları.
// Klasik betikler: üst düzey const/let/function tüm hud-*.js dosyalarında ortaktır; sıra index.html'deki gibidir.
window.hud = {
  permissions(data) { paintPermissions(data); },
  // Sesli komutla uyutma: FRIDAY "iyi geceler" desin diye kısa gecikme.
  sleep(asleep, delayMs) {
    // Uyurken önce vedanın bitmesini bekle (en çok 10 sn), sonra uyu.
    const started = Date.now();
    const tick = () => {
      const talking = document.body.dataset.state === "speaking";
      if (asleep && talking && Date.now() - started < 10000) return setTimeout(tick, 300);
      setSleep(asleep);
    };
    setTimeout(tick, Math.max(0, Number(delayMs) || 0));
  },
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
  timer(state) {
    const s = state || {};
    const newEnd = Number(s.end) || 0;
    if (newEnd && newEnd !== timerEnd) timerSpan = Math.max(1, Math.round((newEnd - Date.now()) / 1000));
    timerEnd = newEnd;
    timerLabel = s.label || "";
    stopwatch = !!s.watchRunning;
    stopwatchStart = Number(s.watchStart) || 0;
    watchTotal = Number(s.watchTotal) || 0;
    $("timer-live").hidden = !timerEnd;
    $("timer-hint").hidden = !!timerEnd;
    $("timer-pick").hidden = !!timerEnd;
    $("t-stop").textContent = stopwatch ? "⏸ KRONOMETREYİ DURDUR" : (watchTotal ? "▶ KRONOMETRE DEVAM" : "⏱ KRONOMETRE");
  },
  timerDone(label) {
    $("td-label").textContent = label || "";
    $("timer-done").hidden = false;
    $("td-close").focus();
    clearTimeout(window.__tdHide);
    window.__tdHide = setTimeout(() => { $("timer-done").hidden = true; }, 60000);
  },
  updateOffer(version) {
    if (!version) return;
    for (const id of ["home-update", "app-update"]) {
      const button = $(id);
      if (!button) continue;
      button.hidden = false;
      button.textContent = "Güncelle " + version;
    }
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
      button.setAttribute("aria-checked", item.id === (data.config.ui_color || "teal") ? "true" : "false");
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
    for (const key of ["gemini_api_key", "youtube_api_key", "youtube_channel_handle", "weather_location", "voice", "assistant_name", "address_as", "ui_color", "live_model", "language", "quiet_minutes", "mail_web", "outlook_web_host", "gmail_address", "gmail_app_password"]) {
      if (form[key]) form[key].value = data.config[key] || "";
    }
    if (form.voice_volume) {
      form.voice_volume.value = String(data.config.voice_volume ?? 100);
      $("vol-label").textContent = "%" + form.voice_volume.value;
    }
    $("set-sfx").setAttribute("aria-checked", data.config.effects === false ? "false" : "true");
    $("set-music").setAttribute("aria-checked", data.config.music === true ? "true" : "false");
    $("set-patient").setAttribute("aria-checked", data.config.patient_listening === false ? "false" : "true");
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
    paintSiteQr(data.siteQr, data.siteUrl);
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

