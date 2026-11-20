// Hava durumu kartındaki 3D sahne: canvas 2D ile derinlik sıralı sahte 3D (kütüphane yok) + WebAudio sesleri.
// Dış API: window.weatherScene.mount(host, kind) / destroy(). Sayfa kapanınca kendini temizler.
(function () {
  const KINDS = [["clear", "GÜNEŞLİ"], ["cloud", "BULUTLU"], ["rain", "YAĞMUR"], ["storm", "FIRTINA"], ["snow", "KAR"], ["fog", "SİS"], ["night", "GECE"]];
  const reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const rnd = (a, b) => a + Math.random() * (b - a);
  let live = null;

  // ---------- Ses ----------
  function makeAudio() {
    const Ctx = window.AudioContext || window.webkitAudioContext;
    if (!Ctx) return null;
    const ctx = new Ctx();
    const master = ctx.createGain();
    master.gain.value = 0.0;
    master.connect(ctx.destination);
    const noise = ctx.createBuffer(1, ctx.sampleRate * 2, ctx.sampleRate);
    const data = noise.getChannelData(0);
    let last = 0;
    for (let i = 0; i < data.length; i++) { last = (last + 0.02 * (Math.random() * 2 - 1)) / 1.02; data[i] = last * 3.5; }
    const layer = (type, freq, q) => {
      const src = ctx.createBufferSource();
      src.buffer = noise; src.loop = true;
      const filter = ctx.createBiquadFilter();
      filter.type = type; filter.frequency.value = freq; filter.Q.value = q || 0.7;
      const gain = ctx.createGain(); gain.gain.value = 0;
      src.connect(filter); filter.connect(gain); gain.connect(master); src.start();
      return gain;
    };
    const bed = { rain: layer("bandpass", 1500, 0.5), hiss: layer("highpass", 4500, 0.7), wind: layer("lowpass", 420, 0.9) };
    // Rüzgâr yavaşça dalgalanır
    const lfo = ctx.createOscillator(); const lfoGain = ctx.createGain();
    lfo.frequency.value = 0.18; lfoGain.gain.value = 0.05; lfo.connect(lfoGain); lfoGain.connect(bed.wind.gain); lfo.start();
    const blip = (freq, dur, vol, glide) => {
      const osc = ctx.createOscillator(); const g = ctx.createGain(); const t = ctx.currentTime;
      osc.type = "sine"; osc.frequency.setValueAtTime(freq, t); osc.frequency.exponentialRampToValueAtTime(Math.max(60, freq * glide), t + dur);
      g.gain.setValueAtTime(0, t); g.gain.linearRampToValueAtTime(vol, t + dur * 0.15); g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
      osc.connect(g); g.connect(master); osc.start(t); osc.stop(t + dur + 0.05);
    };
    const thunder = () => {
      const t = ctx.currentTime + rnd(0.3, 1.4);
      const src = ctx.createBufferSource(); src.buffer = noise;
      const f = ctx.createBiquadFilter(); f.type = "lowpass"; f.frequency.value = 220;
      const g = ctx.createGain();
      g.gain.setValueAtTime(0.0001, t); g.gain.exponentialRampToValueAtTime(1.4, t + 0.15); g.gain.exponentialRampToValueAtTime(0.0001, t + 2.6);
      src.connect(f); f.connect(g); g.connect(master); src.start(t, rnd(0, 0.8), 3);
    };
    return { ctx, master, bed, blip, thunder, timer: 0 };
  }

  // Hava türüne göre ses karışımı; yoğunluk 0..1
  function mixFor(kind, k) {
    const m = {
      clear: { rain: 0, hiss: 0, wind: 0.05 },
      cloud: { rain: 0, hiss: 0, wind: 0.12 },
      rain: { rain: 0.55 * k + 0.1, hiss: 0.25 * k, wind: 0.08 },
      storm: { rain: 0.8 * k + 0.1, hiss: 0.35 * k, wind: 0.3 },
      snow: { rain: 0, hiss: 0, wind: 0.2 },
      fog: { rain: 0, hiss: 0, wind: 0.07 },
      night: { rain: 0, hiss: 0, wind: 0.04 },
    };
    return m[kind] || m.clear;
  }

  function tuneAudio(scene) {
    const a = scene.audio;
    if (!a) return;
    const t = a.ctx.currentTime;
    a.master.gain.cancelScheduledValues(t);
    a.master.gain.linearRampToValueAtTime(scene.sound ? 0.45 : 0, t + 0.4);
    const mix = mixFor(scene.kind, scene.k);
    for (const name of Object.keys(a.bed)) a.bed[name].gain.linearRampToValueAtTime(mix[name], t + 0.8);
    clearInterval(a.timer);
    // Seyrek sesler: kuş cıvıltısı (gündüz), cırcır böceği (gece)
    a.timer = setInterval(() => {
      if (!scene.sound) return;
      if (scene.kind === "clear" && Math.random() < 0.6) { const f = rnd(2200, 3600); a.blip(f, 0.12, 0.18, 1.5); setTimeout(() => a.blip(f * 1.15, 0.1, 0.14, 1.3), 140); }
      if (scene.kind === "night" && Math.random() < 0.8) for (let i = 0; i < 4; i++) setTimeout(() => a.blip(4300, 0.05, 0.05, 1.02), i * 70);
    }, 1400);
  }

  // ---------- Sahne ----------
  function mount(host, kind) {
    destroy();
    const box = document.createElement("div");
    box.className = "wx3d";
    const canvas = document.createElement("canvas");
    const bar = document.createElement("div");
    bar.className = "wx3dbar";
    const chips = document.createElement("div");
    chips.className = "wx3dchips";
    const slider = document.createElement("input");
    slider.type = "range"; slider.min = "10"; slider.max = "100"; slider.value = "70"; slider.title = "Yoğunluk";
    const snd = document.createElement("button");
    snd.type = "button"; snd.className = "wx3dsnd";
    bar.append(chips, slider, snd);
    box.append(canvas, bar);
    const head = host.querySelector(".wxhead");
    if (head) head.after(box); else host.prepend(box);

    const scene = { kind, k: 0.7, sound: true, yaw: 0.35, pitch: 0.18, zoom: 1, audio: null, raf: 0, parts: [], flash: 0, bolt: null, next: 3, t0: performance.now() };
    const g = canvas.getContext("2d");
    const dpr = Math.min(2, window.devicePixelRatio || 1);
    let W = 0, H = 0;
    const resize = () => {
      W = Math.max(280, box.clientWidth); H = 230;
      canvas.width = W * dpr; canvas.height = H * dpr; canvas.style.height = H + "px";
      g.setTransform(dpr, 0, 0, dpr, 0, 0);
    };
    resize();

    const chipEls = {};
    for (const [id, label] of KINDS) {
      const chip = document.createElement("button");
      chip.type = "button"; chip.textContent = label;
      chip.addEventListener("click", () => setKind(id));
      chips.appendChild(chip); chipEls[id] = chip;
    }
    const paintSnd = () => { snd.textContent = scene.sound ? "♪ SES AÇIK" : "♪ SES KAPALI"; snd.classList.toggle("off", !scene.sound); };
    const ensureAudio = () => {
      if (!scene.audio) { try { scene.audio = makeAudio(); } catch (e) { scene.audio = null; } }
      if (scene.audio && scene.audio.ctx.state === "suspended") scene.audio.ctx.resume().catch(() => {});
      tuneAudio(scene);
    };
    snd.addEventListener("click", () => { scene.sound = !scene.sound; paintSnd(); ensureAudio(); });
    slider.addEventListener("input", () => { scene.k = Number(slider.value) / 100; seed(); tuneAudio(scene); });

    // Fare/parmakla döndür, tekerlekle yakınlaştır
    let drag = null;
    canvas.addEventListener("pointerdown", (e) => { drag = {x: e.clientX, y: e.clientY}; canvas.setPointerCapture(e.pointerId); ensureAudio(); });
    canvas.addEventListener("pointermove", (e) => {
      if (!drag) return;
      scene.yaw += (e.clientX - drag.x) * 0.008;
      scene.pitch = Math.max(-0.1, Math.min(0.7, scene.pitch + (e.clientY - drag.y) * 0.006));
      drag = {x: e.clientX, y: e.clientY};
    });
    canvas.addEventListener("pointerup", () => { drag = null; });
    canvas.addEventListener("wheel", (e) => { e.preventDefault(); scene.zoom = Math.max(0.6, Math.min(1.8, scene.zoom * (e.deltaY < 0 ? 1.08 : 0.93))); }, {passive: false});

    // Dünya → ekran: yaw (Y ekseni), pitch (X ekseni), perspektif
    const proj = (x, y, z) => {
      const cy = Math.cos(scene.yaw), sy = Math.sin(scene.yaw), cp = Math.cos(scene.pitch), sp = Math.sin(scene.pitch);
      const x1 = x * cy - z * sy, z1 = x * sy + z * cy;
      const y1 = y * cp - z1 * sp, z2 = y * sp + z1 * cp + 520;
      const s = (380 * scene.zoom) / Math.max(60, z2);
      return {x: W / 2 + x1 * s, y: H * 0.74 - y1 * s, s, d: z2};
    };

    function seed() {
      const k = scene.k, kd = scene.kind, parts = [];
      const wet = kd === "rain" || kd === "storm", count = wet ? Math.round(60 + 220 * k) : kd === "snow" ? Math.round(40 + 160 * k) : 0;
      for (let i = 0; i < count; i++) parts.push({x: rnd(-260, 260), y: rnd(-20, 240), z: rnd(-260, 260), v: wet ? rnd(380, 560) : rnd(22, 55), ph: rnd(0, 6.28)});
      scene.parts = parts;
      const n = kd === "clear" ? 2 : kd === "cloud" ? 9 : kd === "night" ? 2 : kd === "fog" ? 0 : wet ? 7 : 6;
      scene.clouds = [];
      for (let i = 0; i < n; i++) {
        const puffs = [];
        for (let j = 0; j < 5; j++) puffs.push({dx: rnd(-46, 46), dy: rnd(-8, 12), dz: rnd(-20, 20), r: rnd(26, 46)});
        scene.clouds.push({x: rnd(-220, 220), y: rnd(95, 150), z: rnd(-200, 200), sp: rnd(4, 11), puffs});
      }
      scene.stars = kd === "night" ? Array.from({length: 70}, () => ({x: rnd(0, 1), y: rnd(0, 0.55), a: rnd(0.3, 1), p: rnd(0, 6)})) : [];
      scene.mist = kd === "fog" ? Array.from({length: 7}, (_, i) => ({x: rnd(-200, 200), y: 10 + i * 18, z: rnd(-220, 220), r: rnd(120, 190), sp: rnd(6, 14)})) : [];
    }

    function setKind(id) {
      scene.kind = id;
      for (const key of Object.keys(chipEls)) chipEls[key].classList.toggle("on", key === id);
      const wx = document.getElementById("ov-weather");
      if (wx) wx.dataset.wx = id;
      seed();
      ensureAudioIfRunning();
    }
    const ensureAudioIfRunning = () => { if (scene.audio) tuneAudio(scene); };

    function sky() {
      const kd = scene.kind;
      const top = {clear: "#2e7fc9", cloud: "#5a6f86", rain: "#3a4a5e", storm: "#1d2433", snow: "#7c8ea3", fog: "#8c98a3", night: "#050b1c"}[kd];
      const bot = {clear: "#a9dcff", cloud: "#a8b8c8", rain: "#6b7d90", storm: "#3a4560", snow: "#d4e0ec", fog: "#c7ced5", night: "#1a2548"}[kd];
      const grad = g.createLinearGradient(0, 0, 0, H);
      grad.addColorStop(0, top); grad.addColorStop(1, bot);
      g.fillStyle = grad; g.fillRect(0, 0, W, H);
    }

    function ball(p, r, inner, outer, alpha) {
      const rr = Math.max(1, r * p.s);
      const rg = g.createRadialGradient(p.x - rr * 0.25, p.y - rr * 0.3, rr * 0.1, p.x, p.y, rr);
      rg.addColorStop(0, inner); rg.addColorStop(1, outer);
      g.globalAlpha = alpha; g.fillStyle = rg;
      g.beginPath(); g.arc(p.x, p.y, rr, 0, 6.2832); g.fill(); g.globalAlpha = 1;
    }

    function draw(now) {
      const t = (now - scene.t0) / 1000, kd = scene.kind, dt = Math.min(0.05, scene.dt || 0.016);
      sky();
      // Gök cisimleri
      if (kd === "clear") {
        const p = proj(-90, 150, 120);
        const glow = g.createRadialGradient(p.x, p.y, 4, p.x, p.y, 120 * p.s);
        glow.addColorStop(0, "rgba(255,240,170,.95)"); glow.addColorStop(1, "rgba(255,240,170,0)");
        g.fillStyle = glow; g.fillRect(0, 0, W, H);
        g.strokeStyle = "rgba(255,236,150,.55)"; g.lineWidth = 2;
        for (let i = 0; i < 14; i++) { const a = i / 14 * 6.2832 + t * 0.2; g.beginPath(); g.moveTo(p.x + Math.cos(a) * 34 * p.s, p.y + Math.sin(a) * 34 * p.s); g.lineTo(p.x + Math.cos(a) * (52 + 8 * Math.sin(t * 2 + i)) * p.s, p.y + Math.sin(a) * (52 + 8 * Math.sin(t * 2 + i)) * p.s); g.stroke(); }
        ball(p, 28, "#fff6c2", "#ffc83d", 1);
      }
      if (kd === "night") {
        for (const s of scene.stars) { g.globalAlpha = s.a * (0.6 + 0.4 * Math.sin(t * 2 + s.p)); g.fillStyle = "#fff"; g.fillRect(s.x * W, s.y * H, 1.6, 1.6); }
        g.globalAlpha = 1;
        const p = proj(100, 150, 120);
        ball(p, 24, "#fffde8", "#c9d2e6", 1);
        g.globalAlpha = 0.25; g.fillStyle = "#050b1c"; g.beginPath(); g.arc(p.x + 8 * p.s, p.y - 3 * p.s, 20 * p.s, 0, 6.2832); g.fill(); g.globalAlpha = 1;
      }
      // Zemin ızgarası (derinlik hissi)
      g.strokeStyle = kd === "night" ? "rgba(120,160,255,.18)" : "rgba(255,255,255,.22)"; g.lineWidth = 1;
      for (let i = -4; i <= 4; i++) {
        const a = proj(i * 70, 0, -280), b = proj(i * 70, 0, 280); g.beginPath(); g.moveTo(a.x, a.y); g.lineTo(b.x, b.y); g.stroke();
        const c = proj(-280, 0, i * 70), d = proj(280, 0, i * 70); g.beginPath(); g.moveTo(c.x, c.y); g.lineTo(d.x, d.y); g.stroke();
      }
      // Sis katmanları (arkadan öne)
      const mist = scene.mist.map((m) => ({m, p: proj(m.x, m.y, m.z)})).sort((a, b) => b.p.d - a.p.d);
      for (const {m, p} of mist) {
        m.x += m.sp * dt; if (m.x > 260) m.x = -260;
        const rg = g.createRadialGradient(p.x, p.y, 4, p.x, p.y, m.r * p.s);
        rg.addColorStop(0, `rgba(235,240,245,${0.35 + 0.35 * scene.k})`); rg.addColorStop(1, "rgba(235,240,245,0)");
        g.fillStyle = rg; g.fillRect(0, 0, W, H);
      }
      // Bulutlar: puf'lar derinliğe göre sıralanır
      const dark = kd === "storm" ? ["#6c768c", "#2d3345"] : kd === "rain" ? ["#aab4c2", "#59677a"] : kd === "night" ? ["#46506e", "#1c2240"] : kd === "snow" ? ["#f4f8fc", "#b9c7d6"] : ["#ffffff", "#c9d6e4"];
      const list = [];
      for (const c of scene.clouds) {
        c.x += c.sp * dt * (0.5 + scene.k); if (c.x > 260) c.x = -260;
        for (const pf of c.puffs) { const p = proj(c.x + pf.dx, c.y + pf.dy + Math.sin(t + c.x) * 2, c.z + pf.dz); list.push({p, r: pf.r}); }
      }
      list.sort((a, b) => b.p.d - a.p.d);
      for (const it of list) ball(it.p, it.r, dark[0], dark[1], 0.92);
      // Yağmur / kar
      const wet = kd === "rain" || kd === "storm";
      if (wet) {
        g.strokeStyle = "rgba(190,215,245,.75)"; g.lineWidth = 1.2; g.beginPath();
        for (const d of scene.parts) {
          d.y -= d.v * dt; d.x -= 30 * dt;
          if (d.y < 0) { d.y = rnd(180, 240); d.x = rnd(-260, 260); d.z = rnd(-260, 260); }
          const a = proj(d.x, d.y, d.z), b = proj(d.x + 3, d.y + 16, d.z);
          g.moveTo(a.x, a.y); g.lineTo(b.x, b.y);
        }
        g.stroke();
        // Yerde halka sıçramaları
        g.strokeStyle = "rgba(210,230,255,.35)";
        for (let i = 0; i < 14; i++) { const ph = (t * 1.4 + i * 0.37) % 1, x = Math.sin(i * 12.9) * 220, z = Math.cos(i * 7.7) * 220, p = proj(x, 0, z); g.globalAlpha = (1 - ph) * 0.8; g.beginPath(); g.ellipse(p.x, p.y, 16 * ph * p.s * 2, 5 * ph * p.s * 2, 0, 0, 6.2832); g.stroke(); }
        g.globalAlpha = 1;
      } else if (kd === "snow") {
        g.fillStyle = "#fff";
        for (const f of scene.parts) {
          f.y -= f.v * dt; f.x += Math.sin(t + f.ph) * 14 * dt;
          if (f.y < 0) { f.y = rnd(180, 240); f.x = rnd(-260, 260); f.z = rnd(-260, 260); }
          const p = proj(f.x, f.y, f.z); g.globalAlpha = 0.9; g.beginPath(); g.arc(p.x, p.y, Math.max(1, 3.2 * p.s), 0, 6.2832); g.fill();
        }
        g.globalAlpha = 1;
      }
      // Şimşek
      if (kd === "storm") {
        scene.next -= dt;
        if (scene.next <= 0) {
          scene.next = rnd(2.5, 7) / (0.4 + scene.k);
          scene.flash = 1;
          let x = rnd(-120, 120), y = 130; const z = rnd(-100, 100), pts = [[x, y, z]];
          while (y > 0) { y -= rnd(18, 34); x += rnd(-22, 22); pts.push([x, Math.max(0, y), z]); }
          scene.bolt = pts;
          if (scene.audio && scene.sound) scene.audio.thunder();
        }
        if (scene.bolt && scene.flash > 0.05) {
          g.strokeStyle = `rgba(240,245,255,${scene.flash})`; g.lineWidth = 2.5; g.shadowColor = "#bcd4ff"; g.shadowBlur = 14; g.beginPath();
          scene.bolt.forEach(([x, y, z], i) => { const p = proj(x, y, z); i ? g.lineTo(p.x, p.y) : g.moveTo(p.x, p.y); });
          g.stroke(); g.shadowBlur = 0;
        }
        if (scene.flash > 0) { g.fillStyle = `rgba(255,255,255,${scene.flash * 0.35})`; g.fillRect(0, 0, W, H); scene.flash = Math.max(0, scene.flash - dt * 3.5); }
      }
    }

    let prev = performance.now();
    const loop = (now) => {
      const wx = document.getElementById("ov-weather");
      if (!document.body.contains(box) || (wx && wx.hidden)) { destroy(); return; }
      scene.dt = (now - prev) / 1000; prev = now;
      draw(now);
      scene.raf = requestAnimationFrame(loop);
    };

    scene.destroy = () => {
      cancelAnimationFrame(scene.raf);
      if (scene.audio) { clearInterval(scene.audio.timer); try { scene.audio.ctx.close(); } catch (e) { /* kapalı */ } scene.audio = null; }
      window.removeEventListener("resize", resize);
      box.remove();
    };
    window.addEventListener("resize", resize);
    live = scene;
    paintSnd();
    setKind(kind || "clear");
    ensureAudio();
    if (reduce) draw(performance.now()); else scene.raf = requestAnimationFrame(loop);
  }

  function destroy() {
    if (live) { const s = live; live = null; s.destroy(); }
  }

  window.weatherScene = {mount, destroy, kinds: KINDS.map((k) => k[0])};
})();
