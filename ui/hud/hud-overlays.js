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
