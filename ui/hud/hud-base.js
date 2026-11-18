"use strict";
// Ortak yardımcılar: $, dil paketi, Python'a istek (send), SVG.
// Klasik betikler: üst düzey const/let/function tüm hud-*.js dosyalarında ortaktır; sıra index.html'deki gibidir.
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

