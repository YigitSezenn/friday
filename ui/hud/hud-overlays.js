"use strict";
// Hava durumu ve harita katmanları.
// Klasik betikler: üst düzey const/let/function tüm hud-*.js dosyalarında ortaktır; sıra index.html'deki gibidir.
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
  const sourceText = card.source === "elle" ? "KONUM: AYARLARDAN" : "KONUM: OTOMATİK";
  titles.append(el("h2", "", "HAVA DURUMU"), el("p", "", [card.place, card.country, card.observed ? `GÜNCELLENDİ ${card.observed}` : ""].filter(Boolean).join(" · ").toUpperCase()), el("p", "wxsource", sourceText));
  const refresh = el("button", "wxrefresh", "⟳ YENİLE");
  refresh.type = "button";
  refresh.title = "Konumu ve havayı yeniden bul";
  refresh.addEventListener("click", () => {
    refresh.classList.add("spin");
    refresh.disabled = true;
    refresh.textContent = "⟳ BULUNUYOR…";
    send("weather_refresh");
    // Yanıt gelmezse düğme kilitli kalmasın
    setTimeout(() => { refresh.classList.remove("spin"); refresh.disabled = false; refresh.textContent = "⟳ YENİLE"; }, 12000);
  });
  const close = el("button", "", "×");
  close.id = "wx-close";
  close.type = "button";
  head.append(titles, refresh, close);
  host.appendChild(head);

  const hero = el("div", "wxhero");
  const main = el("div", "wxmain");
  const kind = window.fxKind ? window.fxKind(card.desc) : "clear";
  $("ov-weather").dataset.wx = kind;
  const icon = el("i", "wxico big");
  icon.dataset.kind = kind;
  icon.append(document.createElement("u"), document.createElement("u"), document.createElement("u"));
  const temp = el("b", "", "—");
  if (card.temp) window.fxCount ? window.fxCount(temp, card.temp, "°") : (temp.textContent = card.temp + "°");
  main.append(icon, temp, el("div", "wxcopy"));
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
  const fill = {NEM: Number(card.humidity), BULUT: Number(card.cloud), UV: Math.min(100, (Number(card.uv) || 0) * 9), "GÖRÜŞ": Math.min(100, (Number(card.visibility) || 0) * 10), "BASINÇ": Math.max(0, Math.min(100, ((Number(card.pressure) || 1013) - 980) * 1.4))};
  for (const [name, value, note] of items) {
    const box = el("div", "wxstat");
    box.append(el("i", "", name), el("b", "", value));
    if (note) box.append(el("small", "", note));
    if (name === "RÜZGÂR") {
      // Rüzgâr yönünü gösteren dönen ok
      const arrow = el("span", "wxwind", "➤");
      arrow.style.setProperty("--deg", `${(Number(card.windDeg) || 0) + 90}deg`);
      box.append(arrow);
    } else if (Number.isFinite(fill[name])) {
      const bar = el("div", "wxbar");
      const inner = el("i");
      inner.style.setProperty("--v", `${Math.max(3, Math.min(100, fill[name]))}%`);
      bar.append(inner);
      box.append(bar);
    }
    stats.appendChild(box);
  }
  host.appendChild(stats);
  host.appendChild(hourCard(card.hours || []));
  const days = el("div", "wxdays");
  (card.days || []).slice(0, 3).forEach((day, index) => {
    const box = el("div", "wxday");
    box.append(el("i", "", dayName(day.date, index)), el("small", "", dayLabel(day.date)), el("b", "", `${day.hi || "—"}°`), el("span", "", `${day.lo || "—"}°`), el("p", "", day.desc || ""), el("small", "", `↑ %${day.rain || "0"}`));
    const bar = el("div", "wxbar rain");
    const inner = el("i");
    inner.style.setProperty("--v", `${Math.max(2, Math.min(100, Number(day.rain) || 0))}%`);
    bar.append(inner);
    box.append(bar);
    days.appendChild(box);
  });
  host.appendChild(days);
  // Kartlar sırayla içeri girer
  host.querySelectorAll(".wxhero > *, .wxstat, .wxhours, .wxday").forEach((node, index) => node.style.setProperty("--n", index));
  $("ov-weather").hidden = false;
  if (window.weatherScene) window.weatherScene.mount(host, kind);
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
  dot.setAttribute("class", "sundot");
  svg.appendChild(dot);
  const place = (u) => {
    dot.setAttribute("cx", String((1 - u) * (1 - u) * 12 + 2 * (1 - u) * u * 80 + u * u * 148));
    dot.setAttribute("cy", String((1 - u) * (1 - u) * 72 + 2 * (1 - u) * u * 4 + u * u * 72));
  };
  if (!window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
    place(0);
    const started = performance.now();
    requestAnimationFrame(function step(now) {
      const k = Math.min(1, (now - started - 400) / 1500);
      place(Math.max(0, 1 - Math.pow(1 - Math.max(0, k), 3)) * progress);
      if (k < 1) requestAnimationFrame(step);
    });
  }
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
  const NS = "http://www.w3.org/2000/svg";
  const defs = document.createElementNS(NS, "defs");
  defs.innerHTML = '<linearGradient id="wxfill" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="currentColor" stop-opacity=".38"/><stop offset="1" stop-color="currentColor" stop-opacity="0"/></linearGradient>';
  svg.appendChild(defs);
  const area = document.createElementNS(NS, "polygon");
  area.setAttribute("points", `${points[0][0]},128 ${points.map(point => point.join(",")).join(" ")} ${points[points.length - 1][0]},128`);
  area.setAttribute("fill", "url(#wxfill)");
  area.setAttribute("class", "wxarea");
  svg.appendChild(area);
  hours.forEach((hour, index) => {
    const chance = Math.max(0, Math.min(100, Number(hour.rain) || 0));
    const bar = document.createElementNS(NS, "rect");
    bar.setAttribute("x", String(points[index][0] - 7));
    bar.setAttribute("width", "14");
    bar.setAttribute("rx", "3");
    bar.setAttribute("y", String(128 - chance * 0.22));
    bar.setAttribute("height", String(Math.max(2, chance * 0.22)));
    bar.setAttribute("fill", "#5fb3ff");
    bar.setAttribute("class", "wxrainbar");
    bar.style.animationDelay = (0.6 + index * 0.1) + "s";
    svg.appendChild(bar);
  });
  // Çizgi boyunca süzülen ışık
  const trail = document.createElementNS(NS, "circle");
  trail.setAttribute("r", "5");
  trail.setAttribute("fill", "var(--accent)");
  trail.setAttribute("class", "wxtrail");
  const path = "M" + points.map(point => point.join(",")).join(" L");
  const motion = document.createElementNS(NS, "animateMotion");
  motion.setAttribute("path", path);
  motion.setAttribute("dur", "7s");
  motion.setAttribute("begin", "2s");
  motion.setAttribute("repeatCount", "indefinite");
  motion.setAttribute("calcMode", "linear");
  trail.appendChild(motion);
  svg.appendChild(trail);
  const now = document.createElementNS(NS, "circle");
  now.setAttribute("cx", String(points[0][0]));
  now.setAttribute("cy", String(points[0][1]));
  now.setAttribute("r", "6");
  now.setAttribute("fill", "none");
  now.setAttribute("stroke", "var(--accent)");
  now.setAttribute("stroke-width", "2");
  now.setAttribute("class", "wxnow");
  svg.appendChild(now);
  const line = document.createElementNS("http://www.w3.org/2000/svg", "polyline");
  line.setAttribute("points", points.map(point => point.join(",")).join(" "));
  line.setAttribute("fill", "none");
  line.setAttribute("stroke", "currentColor");
  line.setAttribute("stroke-width", "3");
  line.setAttribute("class", "wxline");
  line.setAttribute("pathLength", "1");
  svg.appendChild(line);
  points.forEach((point, index) => {
    const dot = document.createElementNS("http://www.w3.org/2000/svg", "circle");
    dot.setAttribute("cx", String(point[0]));
    dot.setAttribute("cy", String(point[1]));
    dot.setAttribute("r", "4");
    dot.setAttribute("fill", "#fff");
    dot.setAttribute("class", "wxdot");
    dot.style.animationDelay = (0.5 + index * 0.12) + "s";
    svg.appendChild(dot);
    const label = document.createElementNS("http://www.w3.org/2000/svg", "text");
    label.setAttribute("x", String(point[0]));
    label.setAttribute("y", String(point[1] - 10));
    label.setAttribute("text-anchor", "middle");
    label.setAttribute("fill", "var(--ink)");
    label.setAttribute("font-size", "14");
    label.textContent = `${temps[index]}°`;
    label.setAttribute("class", "wxdot");
    label.style.animationDelay = (0.5 + index * 0.12) + "s";
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
let bigMarker = null;
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
    const target = [Number(spot.lon), Number(spot.lat)];
    if (bigMarker) bigMarker.remove();
    const pin = document.createElement("div");
    pin.className = "mappin";
    bigMarker = new maplibregl.Marker({element: pin}).setLngLat(target).addTo(bigMap);
    setTimeout(() => {
      bigMap.resize();
      const calm = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      if (calm) { bigMap.jumpTo({center: target, zoom: 11}); return; }
      // Dünyadan şehre süzülen açılış: uzaktan başlar, eğilir, hafifçe döner
      bigMap.jumpTo({center: target, zoom: 2.2, pitch: 0, bearing: 0});
      bigMap.flyTo({center: target, zoom: 11.6, pitch: 52, bearing: -24, duration: 3800, essential: true, curve: 1.6});
    }, 60);
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
