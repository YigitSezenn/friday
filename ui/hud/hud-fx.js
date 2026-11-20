// 3B eğim, ışık yansıması, basma dalgası ve hava ikonu. Yalnızca görüntü; işlevlere dokunmaz.
(function () {
  const reduce = window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches;
  const root = document.documentElement;

  function tilt(card, event) {
    const box = card.getBoundingClientRect();
    const x = (event.clientX - box.left) / box.width;
    const y = (event.clientY - box.top) / box.height;
    card.style.setProperty("--ry", ((x - 0.5) * 2 * 9).toFixed(2) + "deg");
    card.style.setProperty("--rx", ((0.5 - y) * 2 * 9).toFixed(2) + "deg");
    card.style.setProperty("--gx", (x * 100).toFixed(1) + "%");
    card.style.setProperty("--gy", (y * 100).toFixed(1) + "%");
  }
  function flat(card) {
    card.style.setProperty("--rx", "0deg");
    card.style.setProperty("--ry", "0deg");
  }

  if (!reduce) {
    document.addEventListener("pointermove", (event) => {
      const card = event.target.closest && event.target.closest(".mod");
      if (card) tilt(card, event);
      const nx = event.clientX / window.innerWidth - 0.5;
      const ny = event.clientY / window.innerHeight - 0.5;
      root.style.setProperty("--px", (nx * -14).toFixed(1) + "px");
      root.style.setProperty("--py", (ny * -10).toFixed(1) + "px");
    }, {passive: true});
    document.addEventListener("pointerout", (event) => {
      const card = event.target.closest && event.target.closest(".mod");
      if (card && !card.contains(event.relatedTarget)) flat(card);
    }, {passive: true});
  }

  // Basınca dalga
  document.addEventListener("pointerdown", (event) => {
    if (reduce) return;
    const button = event.target.closest && event.target.closest(".tbtn, .winctl button, #topbar .ctl");
    if (!button) return;
    const box = button.getBoundingClientRect();
    const size = Math.max(box.width, box.height) * 2;
    const wave = document.createElement("span");
    wave.className = "fx-ripple";
    wave.style.width = wave.style.height = size + "px";
    wave.style.left = event.clientX - box.left - size / 2 + "px";
    wave.style.top = event.clientY - box.top - size / 2 + "px";
    button.appendChild(wave);
    setTimeout(() => wave.remove(), 650);
  }, {passive: true});

  // Hava metninden ikon türü
  window.fxKind = function (desc) {
    const text = String(desc || "").toLowerCase();
    let kind = "clear";
    if (/fırtına|gök gürültü|şimşek|thunder|storm/.test(text)) kind = "storm";
    else if (/kar|snow|sleet/.test(text)) kind = "snow";
    else if (/yağmur|sağanak|çise|rain|shower|drizzle/.test(text)) kind = "rain";
    else if (/sis|pus|duman|fog|mist|haze/.test(text)) kind = "fog";
    else if (/bulut|kapalı|cloud|overcast/.test(text)) kind = "cloud";
    else if (/gece|night/.test(text)) kind = "night";
    return kind;
  };
  window.fxWeather = function (desc) {
    const icon = document.getElementById("wx-ico");
    if (icon) icon.dataset.kind = window.fxKind(desc);
  };
  // Sayıyı 0'dan sayarak yükselt
  window.fxCount = function (node, target, suffix) {
    const end = Number(target);
    if (reduce || !Number.isFinite(end)) { node.textContent = target + (suffix || ""); return; }
    const start = performance.now();
    (function step(now) {
      const t = Math.min(1, (now - start) / 900);
      node.textContent = Math.round(end * (1 - Math.pow(1 - t, 3))) + (suffix || "");
      if (t < 1) requestAnimationFrame(step);
    })(start);
  };

  // Zamanlayıcı/kronometre çalışırken kadran ışıldar
  const timer = document.querySelector('.mod[data-key="timer"]');
  const live = document.getElementById("timer-live");
  if (timer && live) {
    const sync = () => timer.classList.toggle("running", !live.hidden);
    new MutationObserver(sync).observe(live, {attributes: true, attributeFilter: ["hidden"]});
    sync();
  }
})();
