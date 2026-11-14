import Lenis from "lenis";
import "lenis/dist/lenis.css";
import "./style.css";

window.__fridayUp = true;

const fromApk = navigator.userAgent.includes("FRIDAYAndroid");
if (fromApk) document.documentElement.dataset.app = "apk";

function pairCode(key) {
  let total = 0;
  for (let i = 0; i < key.length; i += 1) {
    total = (total * 131 + key.charCodeAt(i) + i) % 1000000;
  }
  return String(total).padStart(6, "0");
}

let gateKey = "";
function keyFromHash() {
  const body = location.hash.replace(/^#/, "");
  const match = body.match(/(?:^|&)k=([^&]*)/);
  if (!match) return "";
  try { return decodeURIComponent(match[1].replace(/\+/g, "%2B")); }
  catch { return ""; }
}
function applyKey(key) {
  const text = String(key || "").trim();
  if (!text) return;
  gateKey = text;
  const pairInput = document.querySelector("#komut-form [name=pair]");
  if (pairInput) pairInput.value = pairCode(gateKey);
  document.documentElement.dataset.pair = "1";
  const bridge = window.FridayKey;
  if (bridge && typeof bridge.store === "function") bridge.store(gateKey);
  const scanNote = document.querySelector("#apk-scan-note");
  if (scanNote) scanNote.textContent = "QR okundu.";
}
window.__fridayTakeKey = applyKey;
const hashKey = keyFromHash();
if (hashKey) {
  applyKey(hashKey);
  history.replaceState(null, "", `${location.pathname}${location.search}#yaz`);
} else if (window.__fridayKey) {
  applyKey(window.__fridayKey);
} else if (fromApk && window.FridayKey && typeof window.FridayKey.current === "function") {
  const saved = window.FridayKey.current();
  if (saved) applyKey(saved);
}

const note = document.querySelector("#note");
if (note && new URLSearchParams(location.search).get("iletildi") === "1") {
  note.textContent = "Komut bilgisayara iletildi.";
}

const canvas = document.querySelector("#gl");
let scene = null;
if (canvas && !fromApk) {
  // three.js yalnız sahne gösterilecekse iner; telefon sayfası onu hiç yüklemez.
  import("./scene.js").then((module) => {
    document.documentElement.dataset.scene = module.SCENE_ID;
    scene = module.startScene(canvas);
    scene.setTheme(document.documentElement.dataset.theme === "light" ? "light" : "dark");
    update();
  }).catch(() => {});
}
const themeMedia = window.matchMedia("(prefers-color-scheme: light)");
const themeButtons = document.querySelectorAll("#theme button");
const paintTheme = (mode, persist) => {
  if (mode === "light") document.documentElement.dataset.theme = "light";
  else delete document.documentElement.dataset.theme;
  const themeColor = document.querySelector('meta[name="theme-color"]');
  if (themeColor) themeColor.setAttribute("content", mode === "light" ? "#f6f1e8" : "#04070c");
  themeButtons.forEach((button) => {
    button.setAttribute("aria-pressed", String(button.dataset.side === mode));
  });
  scene?.setTheme(mode);
  if (persist) localStorage.setItem("friday-theme", mode);
};
paintTheme(document.documentElement.dataset.theme === "light" ? "light" : "dark", false);
themeButtons.forEach((button) => {
  button.addEventListener("click", () => paintTheme(button.dataset.side, true));
});
themeMedia.addEventListener("change", () => {
  const saved = localStorage.getItem("friday-theme");
  if (saved === "light" || saved === "dark") return;
  paintTheme(themeMedia.matches ? "light" : "dark", false);
});
const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
let lenis = null;

if (!reduce && !fromApk) {
  lenis = new Lenis({ autoRaf: true, duration: 1.4, respectReducedMotion: false });
}

const revealNodes = document.querySelectorAll("[data-reveal]");
if (!reduce && "IntersectionObserver" in window) {
  const settle = (event) => {
    if (event.propertyName === "clip-path") event.currentTarget.classList.add("done");
  };
  const watcher = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (!entry.isIntersecting) return;
      entry.target.classList.add("in");
      watcher.unobserve(entry.target);
    });
  }, { rootMargin: "0px 0px -12% 0px" });
  revealNodes.forEach((node) => {
    const index = Array.prototype.indexOf.call(node.parentElement.children, node);
    node.style.setProperty("--i", String(index));
    node.addEventListener("transitionend", settle);
    watcher.observe(node);
  });
} else {
  document.documentElement.classList.remove("motion");
}

const header = document.querySelector("header");
const navLinks = new Map();
document.querySelectorAll('nav a[href^="#"]').forEach((link) => {
  navLinks.set(link.getAttribute("href").slice(1), link);
});
if ("IntersectionObserver" in window) {
  const spy = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      const link = navLinks.get(entry.target.id);
      if (!link) return;
      if (entry.isIntersecting) link.setAttribute("aria-current", "true");
      else link.removeAttribute("aria-current");
    });
  }, { rootMargin: "-45% 0px -50% 0px" });
  navLinks.forEach((_link, id) => {
    const target = document.getElementById(id);
    if (target) spy.observe(target);
  });
}

const clock = document.querySelector("#clock");
if (clock) {
  const tick = () => {
    const now = new Date();
    clock.dateTime = now.toISOString();
    clock.textContent = now.toLocaleTimeString("tr-TR", { hour: "2-digit", minute: "2-digit" });
  };
  tick();
  setInterval(tick, 15000);
}

if (window.matchMedia("(hover: hover)").matches) {
  document.querySelectorAll(".panel").forEach((panel) => {
    panel.addEventListener("pointermove", (event) => {
      const box = panel.getBoundingClientRect();
      panel.style.setProperty("--mx", `${event.clientX - box.left}px`);
      panel.style.setProperty("--my", `${event.clientY - box.top}px`);
    }, { passive: true });
  });
  document.querySelectorAll(".hero .btn").forEach((button) => {
    button.addEventListener("pointerenter", () => scene?.setEnergy(1));
    button.addEventListener("pointerleave", () => scene?.setEnergy(0));
  });
}

document.querySelectorAll('a[href^="#"]').forEach((link) => {
  link.addEventListener("click", (event) => {
    const id = link.getAttribute("href");
    const target = id ? document.querySelector(id) : null;
    if (!target) return;
    event.preventDefault();
    const offset = header ? header.offsetHeight : 0;
    const top = Math.max(0, target.getBoundingClientRect().top + window.scrollY - offset);
    const start = window.scrollY;
    const change = top - start;
    const began = performance.now();
    const frame = (now) => {
      const progress = Math.min(1, (now - began) / 1400);
      const eased = 1 - (1 - progress) ** 3;
      const y = start + change * eased;
      if (lenis) lenis.scrollTo(y, { immediate: true, force: true });
      else window.scrollTo(0, y);
      if (progress < 1) requestAnimationFrame(frame);
    };
    requestAnimationFrame(frame);
    history.replaceState(null, "", id);
  });
});

const update = () => {
  const height = document.documentElement.scrollHeight - innerHeight;
  const progress = height > 0 ? Math.min(1, Math.max(0, scrollY / height)) : 0;
  if (header) header.style.setProperty("--p", progress.toFixed(4));
  if (canvas) {
    const ghost = Math.min(1, Math.max(0, (scrollY / innerHeight - 0.2) / 0.6));
    canvas.style.setProperty("--gl", (1 - ghost * 0.8).toFixed(3));
  }
  if (scene) scene.setScroll(progress);
};
addEventListener("scroll", update, { passive: true });
update();

const form = document.querySelector("#komut-form");
if (form && note) {
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const pairInput = form.querySelector("[name=pair]");
    const entered = pairInput ? pairInput.value.trim() : "";
    if (!gateKey) {
      note.textContent = "Önce QR okutun.";
      return;
    }
    if (pairCode(gateKey) !== entered) {
      note.textContent = "Kod tutmadı.";
      return;
    }
    const command = (form.querySelector("textarea")?.value || "").trim();
    if (!command) {
      note.textContent = "Bağlandı.";
      return;
    }
    const button = form.querySelector("button[type=submit]");
    button.disabled = true;
    note.textContent = "Gönderiliyor.";
    try {
      const body = new URLSearchParams();
      body.set("key", gateKey);
      body.set("text", command);
      const response = await fetch("/komut", {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8" },
        body,
      });
      const page = await response.text();
      const landed = response.url || "";
      if (landed.includes("iletildi=1")) {
        note.textContent = "Bağlandı. Komut bilgisayara iletildi.";
        form.querySelector("textarea").value = "";
      } else if (page.includes("Komut boş")) {
        note.textContent = "Bağlandı.";
      } else if (page.includes("Anahtar olmadı")) {
        note.textContent = "QR eski. FRIDAY ekranındaki QR kodu yeniden okutun.";
      } else {
        note.textContent = "Bağlandı. Komut iletilemedi.";
      }
    } catch {
      note.textContent = "Bağlandı. Bağlantı kurulamadı.";
    } finally {
      button.disabled = false;
    }
  });
}

const scanNote = document.querySelector("#apk-scan-note");
window.__fridayKeyReady = () => {
  if (scanNote && !gateKey) scanNote.textContent = "QR okutunca kod kutuya yazılır.";
};
document.querySelector("#apk-scan")?.addEventListener("click", () => {
  const bridge = window.FridayKey;
  if (!bridge || typeof bridge.scan !== "function") {
    if (scanNote) scanNote.textContent = "QR oku yalnız FRIDAY uygulamasında çalışır.";
    return;
  }
  bridge.scan();
});
if (fromApk) window.__fridayKeyReady();
window.__fridayHeard = (text) => {
  const said = String(text || "").trim();
  const box = form ? form.querySelector("textarea") : null;
  if (!said || !box) {
    if (note) note.textContent = "Ses alınamadı.";
    return;
  }
  box.value = said;
  if (form.requestSubmit) form.requestSubmit();
  else form.dispatchEvent(new Event("submit", {cancelable: true}));
};
window.__fridayVoiceError = () => {
  if (note) note.textContent = "Mikrofon izni gerekli.";
};
document.querySelector("#apk-mic")?.addEventListener("click", () => {
  const bridge = window.FridaySpeech;
  if (!bridge || typeof bridge.listen !== "function") {
    if (note) note.textContent = "Konuş yalnız FRIDAY uygulamasında çalışır.";
    return;
  }
  if (note) note.textContent = "Dinleniyor.";
  bridge.listen();
});

const wakeForm = document.querySelector("#wake-form");
const wakeNote = document.querySelector("#wake-note");
if (wakeForm && wakeNote) {
  const macInput = wakeForm.querySelector("[name=mac]");
  const ipInput = wakeForm.querySelector("[name=ip]");
  const portInput = wakeForm.querySelector("[name=port]");
  try {
    macInput.value = localStorage.getItem("friday-wake-mac") || "";
    ipInput.value = localStorage.getItem("friday-wake-ip") || "";
    portInput.value = localStorage.getItem("friday-wake-port") || "9";
  } catch { /* kayıt yok */ }
  if (!portInput.value) portInput.value = "9";
  wakeForm.addEventListener("submit", (event) => {
    event.preventDefault();
    const mac = macInput.value.trim();
    const ip = ipInput.value.trim();
    const port = portInput.value.trim() || "9";
    const bridge = window.FridayWake;
    if (!bridge || typeof bridge.wake !== "function") {
      wakeNote.textContent = "Bilgisayarımı aç yalnız FRIDAY uygulamasında çalışır.";
      return;
    }
    const result = bridge.wake(mac, ip, port);
    if (result === "ok") {
      try {
        localStorage.setItem("friday-wake-mac", mac);
        localStorage.setItem("friday-wake-ip", ip);
        localStorage.setItem("friday-wake-port", port);
      } catch { /* kayıt kapalı */ }
      wakeNote.textContent = "Uyandırma paketi gönderildi.";
    } else if (result === "mac") {
      wakeNote.textContent = "MAC adresi olmadı.";
    } else if (result === "ip") {
      wakeNote.textContent = "IP adresi olmadı.";
    } else if (result === "port") {
      wakeNote.textContent = "Port olmadı.";
    } else {
      wakeNote.textContent = "Paket gönderilemedi.";
    }
  });
}

const noteTone = (text) => {
  if (!text || text === "QR okutunca kod kutuya yazılır.") return "";
  if (text === "Gönderiliyor." || text === "Dinleniyor.") return "busy";
  if (/(iletildi|gönderildi|Bağlandı|QR okundu)\.$/.test(text)) return "ok";
  return "warn";
};
let linkTimer = 0;
const paintNote = (node) => {
  const tone = noteTone(node.textContent.trim());
  if (tone) node.dataset.tone = tone;
  else delete node.dataset.tone;
  clearTimeout(linkTimer);
  if (tone) document.documentElement.dataset.link = tone;
  else delete document.documentElement.dataset.link;
  if (tone === "ok") {
    linkTimer = setTimeout(() => delete document.documentElement.dataset.link, 2600);
  }
};
if ("MutationObserver" in window) {
  document.querySelectorAll(".note").forEach((node) => {
    new MutationObserver(() => paintNote(node)).observe(node, { childList: true, characterData: true, subtree: true });
    if (node.textContent.trim()) paintNote(node);
  });
}
