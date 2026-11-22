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
    $("cam-pip").hidden = !on;  // kendi görüntünü küçük pencerede göster
    if (!on) $("cam-pip-img").removeAttribute("src");
    if (!on) paintHand("kapalı");
  },
  handStatus(text) { paintHand(text); },
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
    if (window.fxWeather) window.fxWeather(data.desc || "");
    if (!$("ov-weather").hidden) openWeather();  // sayfa açıkken yenileme yerinde görünsün
    $("wx-detail").textContent = data.detail || "";
    $("map-cap").textContent = data.city ? `${data.city} · ${(data.card && data.card.source) === "elle" ? "AYARLARDAN" : "OTOMATİK KONUM"} · küçük görüntü © Esri` : "";
  },
  place(spot) {
    window.__spot = spot || null;
    if (window.fxMiniMap) window.fxMiniMap(spot);
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
    if (src) { $("map-img").src = src; $("cam-pip-img").src = src; }
  },
  mailTest(result) {
    $("mail-test").disabled = false;
    const out = $("mail-test-out");
    out.textContent = result;
    out.classList.toggle("ok", /gönderildi/.test(result));
    out.classList.toggle("bad", !/gönderildi/.test(result));
  },
  discordTest(result) {
    $("discord-test").disabled = false;
    const out = $("discord-test-out");
    out.textContent = result;
    out.classList.toggle("ok", /gönderildi/.test(result));
    out.classList.toggle("bad", !/gönderildi/.test(result));
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
  patchNotes(raw, auto) {
    let data;
    try { data = JSON.parse(raw); } catch { return; }
    const list = $("notes-list");
    list.textContent = "";
    const parts = (v) => String(v).split(".").map(n => parseInt(n, 10) || 0);
    const newer = (a, b) => { const x = parts(a), y = parts(b); for (let i = 0; i < 3; i++) { if ((x[i] || 0) !== (y[i] || 0)) return (x[i] || 0) > (y[i] || 0); } return false; };
    const card = (entry, index) => {
      const node = document.createElement("article");
      node.className = "note-card" + (entry.surum === data.current ? " current" : "");
      node.style.setProperty("--n", index);
      const head = document.createElement("header");
      const tag = document.createElement("b");
      tag.textContent = "v" + entry.surum;
      const title = document.createElement("span");
      title.textContent = entry.baslik || "";
      const date = document.createElement("time");
      date.textContent = entry.tarih || "";
      head.append(tag, title, date);
      const ul = document.createElement("ul");
      (entry.maddeler || []).forEach(line => { const li = document.createElement("li"); li.textContent = line; ul.append(li); });
      node.append(head, ul);
      return node;
    };
    // Önce bu sürüm (ve varsa daha yeniler); eskiler kapalı bir bölümde
    const entries = data.entries || [];
    const fresh = entries.filter(entry => entry.surum === data.current || newer(entry.surum, data.current));
    const older = entries.filter(entry => !fresh.includes(entry));
    fresh.forEach((entry, index) => list.append(card(entry, index)));
    if (older.length) {
      const toggle = document.createElement("button");
      toggle.type = "button";
      toggle.className = "notes-more";
      toggle.textContent = `ÖNCEKİ SÜRÜMLER (${older.length}) ▾`;
      const rest = document.createElement("div");
      rest.className = "notes-rest";
      rest.hidden = true;
      older.forEach((entry, index) => rest.append(card(entry, index)));
      toggle.addEventListener("click", () => {
        rest.hidden = !rest.hidden;
        toggle.textContent = `ÖNCEKİ SÜRÜMLER (${older.length}) ${rest.hidden ? "▾" : "▴"}`;
      });
      list.append(toggle, rest);
    }
    $("notes-sub").textContent = data.update ? "Yeni sürüm hazır: " + data.update : "Şu an sürüm " + data.current;
    $("notes-update").hidden = !data.update;
    $("ov-notes").hidden = false;
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
    for (const key of ["gemini_api_key", "tavily_api_key", "youtube_api_key", "youtube_channel_handle", "weather_location", "voice", "assistant_name", "address_as", "ui_color", "live_model", "language", "quiet_minutes", "mail_web", "outlook_web_host", "gmail_address", "gmail_app_password", "discord_owner_id", "discord_username"]) {
      if (form[key]) form[key].value = data.config[key] || "";
    }
    if (form.voice_volume) {
      form.voice_volume.value = String(data.config.voice_volume ?? 100);
      $("vol-label").textContent = "%" + form.voice_volume.value;
    }
    $("set-sfx").setAttribute("aria-checked", data.config.effects === false ? "false" : "true");
    $("mute-sfx").setAttribute("aria-pressed", data.config.effects === false ? "false" : "true");
    $("mute-music").setAttribute("aria-pressed", data.config.music === true ? "true" : "false");
    $("set-music").setAttribute("aria-checked", data.config.music === true ? "true" : "false");
    $("set-patient").setAttribute("aria-checked", data.config.patient_listening === false ? "false" : "true");
    setSwitch("set-proactive", data.config.proactive_enabled);
    setSwitch("set-water", data.config.water_enabled);
    setSwitch("set-break", data.config.break_enabled);
    setSwitch("set-events", data.config.event_alerts);
    setSwitch("set-phone-auto", data.config.phone_autostart);
    setSwitch("set-windows", data.config.start_with_windows);
    setSwitch("set-clap", data.config.clap_wake);
    for (const name of ["move", "resize", "maximize", "minimize"]) setSwitch("set-hand-" + name, data.config["hand_" + name] !== false);
    $("set-hand-speed").value = data.config.hand_speed || 100;
    $("hand-speed-label").textContent = `%${data.config.hand_speed || 100}`;
    setSwitch("set-files", data.config.file_access);
    document.querySelectorAll("#quiet-seg button").forEach(node => node.setAttribute("aria-checked", node.dataset.min === String(data.config.quiet_minutes || 20) ? "true" : "false"));
    window.__liveModel = data.config.live_model;
    window.__dataDir = data.dataDir || "";
    window.__appVersion = data.version || "";
    showPhone(data.phone);
    paintGate(data.gateKeyQr, data.pairCode);
    paintGateState(data.gateState);
    paintHome(data.homeDevices);
    paintSiteQr(data.siteQr, data.siteUrl);
    $("set-mic").setAttribute("aria-checked", $("t-mic").dataset.on === "1" ? "true" : "false");
    paintPanels(data.panels);
    paintMemory(data.memories);
    paintIdentity(data.name);
    paintPalette(data.palette);
    if (data.needKey) openOnboard();
  },
  homeMsg(text) {
    const line = $("home-msg");
    if (line) line.textContent = String(text || "");
  },
  phone(data) {
    showPhone(data);
  },
};

// El kontrolü durumu: görüntü penceresinde ve ayarlar sayfasında.
function paintHand(text) {
  const on = text && !["kapalı", "model indirilemedi", "başlatılamadı", "kamera açılamadı"].includes(text);
  $("cam-pip-note").textContent = text || "kamera";
  $("hand-out").textContent = "El kontrolü: " + (text || "kapalı");
  $("hand-toggle").dataset.on = on ? "1" : "0";
  $("hand-toggle").textContent = on ? "DURDUR" : "BAŞLAT";
}
