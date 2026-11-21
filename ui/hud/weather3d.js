// Hava durumu kartındaki 3D sahne: Three.js (vendor/three.min.js) low-poly tepe, ağaç, bulut, güneş/ay, yağmur, kar, şimşek + WebAudio sesleri.
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
  function mixFor(kind, k, windy) {
    const m = {
      clear: { rain: 0, hiss: 0, wind: 0.05 },
      cloud: { rain: 0, hiss: 0, wind: 0.12 },
      rain: { rain: 0.55 * k + 0.1, hiss: 0.25 * k, wind: 0.08 },
      storm: { rain: 0.8 * k + 0.1, hiss: 0.35 * k, wind: 0.3 },
      snow: { rain: 0, hiss: 0, wind: 0.2 },
      fog: { rain: 0, hiss: 0, wind: 0.07 },
      night: { rain: 0, hiss: 0, wind: 0.04 },
    };
    const mix = Object.assign({}, m[kind] || m.clear);
    mix.wind = Math.min(0.6, mix.wind + 0.4 * (windy || 0)); // gerçek rüzgâr hızı sesi güçlendirir
    return mix;
  }

  function tuneAudio(scene) {
    const a = scene.audio;
    if (!a) return;
    const t = a.ctx.currentTime;
    a.master.gain.cancelScheduledValues(t);
    a.master.gain.linearRampToValueAtTime(scene.sound ? 0.45 : 0, t + 0.4);
    const mix = mixFor(scene.kind, scene.k, scene.windy);
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
  // Hava türüne göre hedef değerler; sahne bunlara yumuşakça geçer.
  const CFG = {
    clear: {top: 0x2e86d6, bot: 0xbfe6ff, cloud: 0xffffff, ground: 0x5a9b4e, clouds: 3, sun: 1, moon: 0, stars: 0, rain: 0, snow: 0, fog: 0.004, amb: 0.75, sunI: 1.3},
    cloud: {top: 0x6f8aa6, bot: 0xc3d0dc, cloud: 0xeef2f6, ground: 0x5a8f52, clouds: 10, sun: 0.25, moon: 0, stars: 0, rain: 0, snow: 0, fog: 0.007, amb: 0.7, sunI: 0.5},
    rain: {top: 0x3d4c5f, bot: 0x7d8ea0, cloud: 0x7c8898, ground: 0x3f7048, clouds: 11, sun: 0, moon: 0, stars: 0, rain: 1, snow: 0, fog: 0.012, amb: 0.55, sunI: 0.2},
    storm: {top: 0x161c29, bot: 0x434f66, cloud: 0x434a5a, ground: 0x2f4f3c, clouds: 12, sun: 0, moon: 0, stars: 0, rain: 1.3, snow: 0, fog: 0.014, amb: 0.4, sunI: 0.1},
    snow: {top: 0x8fa3b8, bot: 0xe4edf5, cloud: 0xdde4ec, ground: 0xf1f5fa, clouds: 8, sun: 0.1, moon: 0, stars: 0, rain: 0, snow: 1, fog: 0.012, amb: 0.85, sunI: 0.4},
    fog: {top: 0xa6b0b9, bot: 0xd9dee2, cloud: 0xe4e8eb, ground: 0x7d9a80, clouds: 3, sun: 0.1, moon: 0, stars: 0, rain: 0, snow: 0, fog: 0.032, amb: 0.8, sunI: 0.3},
    night: {top: 0x040a1c, bot: 0x1a2650, cloud: 0x2a3354, ground: 0x1f3a2e, clouds: 3, sun: 0, moon: 1, stars: 1, rain: 0, snow: 0, fog: 0.006, amb: 0.3, sunI: 0},
  };
  const MAX_RAIN = 900, MAX_SNOW = 700, MAX_CLOUDS = 12;

  function glowTexture(T, inner, outer) {
    const c = document.createElement("canvas"); c.width = c.height = 128;
    const x = c.getContext("2d"), g = x.createRadialGradient(64, 64, 2, 64, 64, 64);
    g.addColorStop(0, inner); g.addColorStop(1, outer);
    x.fillStyle = g; x.fillRect(0, 0, 128, 128);
    return new T.CanvasTexture(c);
  }

  function mount(host, kind, data) {
    destroy();
    const T = window.THREE;
    if (!T) return;
    const box = document.createElement("div");
    box.className = "wx3d";
    const canvas = document.createElement("canvas");
    let renderer;
    try { renderer = new T.WebGLRenderer({canvas, antialias: true}); } catch (e) { return; }
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

    // Gerçek veriden başlangıç: rüzgâr hızı sesi, yağış miktarı yoğunluğu belirler.
    const info = data || {};
    const windy = Math.max(0, Math.min(1, (Number(info.wind) || 0) / 40));
    const wetness = Math.max(0, Math.min(1, 0.35 + (Number(info.precip) || 0) / 4));
    const scene = {kind, k: (kind === "rain" || kind === "storm") ? wetness : 0.7, windy, sound: true, audio: null, raf: 0};
    slider.value = String(Math.round(scene.k * 100));
    const H = 260;
    let W = Math.max(280, box.clientWidth);
    renderer.setPixelRatio(Math.min(2, window.devicePixelRatio || 1));
    renderer.setSize(W, H, false);
    canvas.style.height = H + "px";

    // ----- Sahne nesneleri -----
    const world = new T.Scene();
    world.fog = new T.FogExp2(0xbfe6ff, 0.004);
    const camera = new T.PerspectiveCamera(50, W / H, 0.1, 500);
    const cam = {yaw: 0.25, pitch: 0.2, dist: 46, touched: false};
    const hemi = new T.HemisphereLight(0xffffff, 0x446655, 0.7); world.add(hemi);
    const sunLight = new T.DirectionalLight(0xfff2d0, 1.2); sunLight.position.set(-30, 40, 20); world.add(sunLight);
    const flash = new T.PointLight(0xaaccff, 0, 260); flash.position.set(0, 30, -15); world.add(flash);

    const skyMat = new T.ShaderMaterial({
      side: T.BackSide, depthWrite: false, fog: false,
      uniforms: {top: {value: new T.Color(CFG.clear.top)}, bot: {value: new T.Color(CFG.clear.bot)}},
      vertexShader: "varying float h; void main(){ vec4 w = modelMatrix * vec4(position,1.0); h = normalize(w.xyz).y; gl_Position = projectionMatrix * viewMatrix * w; }",
      fragmentShader: "uniform vec3 top; uniform vec3 bot; varying float h; void main(){ gl_FragColor = vec4(mix(bot, top, smoothstep(0.0, 0.55, h)), 1.0); }",
    });
    world.add(new T.Mesh(new T.SphereGeometry(300, 24, 16), skyMat));

    const sun = new T.Group();
    sun.add(new T.Mesh(new T.SphereGeometry(3.2, 20, 14), new T.MeshBasicMaterial({color: 0xfff1b0, fog: false})));
    const sunGlow = new T.Sprite(new T.SpriteMaterial({map: glowTexture(T, "rgba(255,240,170,.95)", "rgba(255,240,170,0)"), blending: T.AdditiveBlending, depthWrite: false, fog: false}));
    sunGlow.scale.set(40, 40, 1); sun.add(sunGlow); sun.position.set(-34, 30, -80); world.add(sun);
    const moon = new T.Group();
    moon.add(new T.Mesh(new T.SphereGeometry(2.6, 20, 14), new T.MeshBasicMaterial({color: 0xf4f1dc, fog: false})));
    const moonGlow = new T.Sprite(new T.SpriteMaterial({map: glowTexture(T, "rgba(200,215,255,.5)", "rgba(200,215,255,0)"), blending: T.AdditiveBlending, depthWrite: false, fog: false}));
    moonGlow.scale.set(22, 22, 1); moon.add(moonGlow); moon.position.set(34, 28, -80); world.add(moon);
    const starGeo = new T.BufferGeometry(), starPos = new Float32Array(240 * 3);
    for (let i = 0; i < 240; i++) { const a = rnd(0, 6.283), e = rnd(0.12, 1.2), r = 250; starPos.set([Math.cos(a) * Math.cos(e) * r, Math.sin(e) * r, Math.sin(a) * Math.cos(e) * r], i * 3); }
    starGeo.setAttribute("position", new T.BufferAttribute(starPos, 3));
    const stars = new T.Points(starGeo, new T.PointsMaterial({color: 0xffffff, size: 1.6, sizeAttenuation: false, transparent: true, opacity: 0, fog: false}));
    world.add(stars);

    // Low-poly tepeler
    const gGeo = new T.PlaneGeometry(220, 220, 44, 44); gGeo.rotateX(-Math.PI / 2);
    const gp = gGeo.attributes.position;
    for (let i = 0; i < gp.count; i++) {
      const x = gp.getX(i), z = gp.getZ(i), d = Math.hypot(x, z), edge = Math.min(1, Math.max(0, (d - 12) / 40));
      gp.setY(i, ((Math.sin(x * 0.08) + Math.cos(z * 0.07)) * 2.4 + Math.sin(x * 0.21 + z * 0.15) * 0.8) * edge);
    }
    gGeo.computeVertexNormals();
    const groundMat = new T.MeshStandardMaterial({color: CFG.clear.ground, flatShading: true, roughness: 1});
    world.add(new T.Mesh(gGeo, groundMat));
    const leaf = new T.MeshStandardMaterial({color: 0x2f6b3f, flatShading: true}), bark = new T.MeshStandardMaterial({color: 0x5b4030, flatShading: true});
    const trees = [];
    for (let i = 0; i < 18; i++) {
      const a = rnd(0, 6.283), r = rnd(13, 52), t = new T.Group(), s = rnd(0.8, 1.6);
      const trunk = new T.Mesh(new T.CylinderGeometry(0.25, 0.35, 1.6, 6), bark); trunk.position.y = 0.8; t.add(trunk);
      for (let j = 0; j < 3; j++) { const cone = new T.Mesh(new T.ConeGeometry(1.7 - j * 0.35, 2.4, 7), leaf); cone.position.y = 2 + j * 1.2; t.add(cone); }
      const x = Math.cos(a) * r, z = Math.sin(a) * r, edge = Math.min(1, Math.max(0, (r - 12) / 40));
      t.position.set(x, ((Math.sin(x * 0.08) + Math.cos(z * 0.07)) * 2.4 + Math.sin(x * 0.21 + z * 0.15) * 0.8) * edge, z);
      t.scale.setScalar(s); t.userData.ph = rnd(0, 6.28); world.add(t); trees.push(t);
    }

    // Bulutlar: düz gölgeli, birleşik küreler
    const cloudMat = new T.MeshStandardMaterial({color: 0xffffff, flatShading: true, roughness: 1});
    const cloudGeo = new T.IcosahedronGeometry(1, 1), clouds = [];
    for (let i = 0; i < MAX_CLOUDS; i++) {
      const g = new T.Group(), n = 5 + Math.floor(rnd(0, 3));
      for (let j = 0; j < n; j++) { const m = new T.Mesh(cloudGeo, cloudMat); m.position.set((j - n / 2) * 2.6 + rnd(-0.6, 0.6), rnd(-0.5, 1), rnd(-1.4, 1.4)); m.scale.set(rnd(2.4, 4), rnd(1.8, 3), rnd(2.2, 3.4)); g.add(m); }
      g.position.set(rnd(-70, 70), rnd(20, 30), rnd(-50, 6)); g.userData = {sp: rnd(1.2, 3), ph: rnd(0, 6.28), sc: 0}; g.scale.setScalar(0.001);
      world.add(g); clouds.push(g);
    }

    // Yağmur çizgileri ve kar taneleri
    const rainGeo = new T.BufferGeometry(), rainPos = new Float32Array(MAX_RAIN * 6), rain = [];
    for (let i = 0; i < MAX_RAIN; i++) rain.push({x: rnd(-45, 45), y: rnd(0, 34), z: rnd(-50, 25), v: rnd(26, 40)});
    rainGeo.setAttribute("position", new T.BufferAttribute(rainPos, 3));
    const rainLines = new T.LineSegments(rainGeo, new T.LineBasicMaterial({color: 0xbcd4f2, transparent: true, opacity: 0.7, fog: false})); rainLines.frustumCulled = false; world.add(rainLines);
    const snowGeo = new T.BufferGeometry(), snowPos = new Float32Array(MAX_SNOW * 3), snow = [];
    for (let i = 0; i < MAX_SNOW; i++) snow.push({x: rnd(-45, 45), y: rnd(0, 34), z: rnd(-50, 25), v: rnd(2, 5), ph: rnd(0, 6.28)});
    snowGeo.setAttribute("position", new T.BufferAttribute(snowPos, 3));
    const flakes = new T.Points(snowGeo, new T.PointsMaterial({color: 0xffffff, size: 0.8, map: glowTexture(T, "rgba(255,255,255,1)", "rgba(255,255,255,0)"), transparent: true, depthWrite: false})); flakes.frustumCulled = false; world.add(flakes);
    const bolt = new T.Line(new T.BufferGeometry(), new T.LineBasicMaterial({color: 0xeaf2ff, fog: false})); bolt.visible = false; world.add(bolt);

    // Şu anki değerler hedeflere yaklaşır
    const cur = {top: new T.Color(), bot: new T.Color(), cloud: new T.Color(), ground: new T.Color(), clouds: 0, sun: 0, moon: 0, stars: 0, rain: 0, snow: 0, fog: 0.004, amb: 0.7, sunI: 1};
    let tgt = CFG[kind] || CFG.clear, flashV = 0, nextBolt = 3, boltT = 0, t = 0;
    const snap = () => { cur.top.setHex(tgt.top); cur.bot.setHex(tgt.bot); cur.cloud.setHex(tgt.cloud); cur.ground.setHex(tgt.ground); for (const k of ["clouds", "sun", "moon", "stars", "rain", "snow", "fog", "amb", "sunI"]) cur[k] = tgt[k]; };
    snap();
    const ease = (a, b, f) => a + (b - a) * f;

    function frame(dt) {
      t += dt;
      const f = 1 - Math.exp(-dt * 2.6), spd = 0.35 + scene.k + scene.windy * 2;
      cur.top.lerp(new T.Color(tgt.top), f); cur.bot.lerp(new T.Color(tgt.bot), f); cur.cloud.lerp(new T.Color(tgt.cloud), f); cur.ground.lerp(new T.Color(tgt.ground), f);
      for (const k of ["clouds", "sun", "moon", "stars", "rain", "snow", "fog", "amb", "sunI"]) cur[k] = ease(cur[k], tgt[k], f);
      skyMat.uniforms.top.value.copy(cur.top); skyMat.uniforms.bot.value.copy(cur.bot);
      world.fog.color.copy(cur.bot); world.fog.density = cur.fog;
      groundMat.color.copy(cur.ground); cloudMat.color.copy(cur.cloud); cloudMat.emissive.copy(cur.cloud).multiplyScalar(0.5);
      hemi.intensity = cur.amb; sunLight.intensity = cur.sunI;
      sun.visible = cur.sun > 0.03; sunGlow.material.opacity = cur.sun; sun.children[0].material.opacity = 1;
      moon.visible = cur.moon > 0.03; moonGlow.material.opacity = cur.moon; stars.material.opacity = cur.stars;
      sun.rotation.z += dt;

      const want = Math.round(cur.clouds);
      clouds.forEach((c, i) => {
        c.userData.sc = ease(c.userData.sc, i < want ? 1 : 0, f * 1.4);
        c.scale.setScalar(Math.max(0.001, c.userData.sc));
        c.position.x += c.userData.sp * dt * spd; if (c.position.x > 80) c.position.x = -80;
        c.position.y += Math.sin(t * 0.6 + c.userData.ph) * dt * 0.4;
      });
      trees.forEach((tr) => { tr.rotation.z = Math.sin(t * (1 + (tgt === CFG.storm ? 2 : 0)) + tr.userData.ph) * (tgt === CFG.storm ? 0.06 : 0.015); });

      const nRain = Math.round(MAX_RAIN * Math.min(1, cur.rain * 0.5) * (0.15 + 0.85 * scene.k));
      for (let i = 0; i < nRain; i++) {
        const d = rain[i]; d.y -= d.v * dt; d.x -= 4 * dt;
        if (d.y < 0) { d.y = rnd(26, 34); d.x = rnd(-45, 45); d.z = rnd(-50, 25); }
        rainPos.set([d.x, d.y, d.z, d.x + 0.35, d.y + 1.7, d.z], i * 6);
      }
      rainGeo.setDrawRange(0, nRain * 2); rainGeo.attributes.position.needsUpdate = true;
      const nSnow = Math.round(MAX_SNOW * Math.min(1, cur.snow) * (0.15 + 0.85 * scene.k));
      for (let i = 0; i < nSnow; i++) {
        const d = snow[i]; d.y -= d.v * dt; d.x += Math.sin(t + d.ph) * dt * 2;
        if (d.y < 0) { d.y = rnd(26, 34); d.x = rnd(-45, 45); d.z = rnd(-50, 25); }
        snowPos.set([d.x, d.y, d.z], i * 3);
      }
      snowGeo.setDrawRange(0, nSnow); snowGeo.attributes.position.needsUpdate = true;

      if (tgt === CFG.storm) {
        nextBolt -= dt;
        if (nextBolt <= 0) {
          nextBolt = rnd(2.5, 7) / (0.4 + scene.k); flashV = 1; boltT = 0.18;
          let x = rnd(-18, 18), y = 26; const z = rnd(-30, -6), pts = [];
          while (y > 0) { pts.push(x, Math.max(0, y), z); y -= rnd(3, 6); x += rnd(-2.5, 2.5); }
          pts.push(x, 0, z); bolt.geometry.setAttribute("position", new T.Float32BufferAttribute(pts, 3)); bolt.visible = true;
          if (scene.audio && scene.sound) scene.audio.thunder();
        }
      }
      boltT -= dt; if (boltT <= 0) bolt.visible = false;
      flashV = Math.max(0, flashV - dt * 3.2); flash.intensity = flashV * 3.2;

      if (!cam.touched) cam.yaw = 0.25 + Math.sin(t * 0.12) * 0.28;
      const cp = Math.cos(cam.pitch);
      camera.position.set(Math.sin(cam.yaw) * cp * cam.dist, 9 + Math.sin(cam.pitch) * cam.dist * 0.7, Math.cos(cam.yaw) * cp * cam.dist);
      camera.lookAt(0, 14, 0);
      renderer.render(world, camera);
    }

    // ----- Kontroller -----
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
    function setKind(id) {
      scene.kind = id; tgt = CFG[id] || CFG.clear;
      for (const key of Object.keys(chipEls)) chipEls[key].classList.toggle("on", key === id);
      const wx = document.getElementById("ov-weather");
      if (wx) wx.dataset.wx = id;
      if (scene.audio) tuneAudio(scene);
      if (reduce) { snap(); frame(0); }
    }
    snd.addEventListener("click", () => { scene.sound = !scene.sound; paintSnd(); ensureAudio(); });
    slider.addEventListener("input", () => { scene.k = Number(slider.value) / 100; tuneAudio(scene); });
    let drag = null;
    canvas.addEventListener("pointerdown", (e) => { drag = {x: e.clientX, y: e.clientY}; cam.touched = true; canvas.setPointerCapture(e.pointerId); ensureAudio(); });
    canvas.addEventListener("pointermove", (e) => {
      if (!drag) return;
      cam.yaw += (e.clientX - drag.x) * 0.008;
      cam.pitch = Math.max(0.02, Math.min(0.75, cam.pitch + (e.clientY - drag.y) * 0.006));
      drag = {x: e.clientX, y: e.clientY};
    });
    canvas.addEventListener("pointerup", () => { drag = null; });
    canvas.addEventListener("wheel", (e) => { e.preventDefault(); cam.dist = Math.max(26, Math.min(80, cam.dist * (e.deltaY < 0 ? 0.93 : 1.08))); }, {passive: false});
    const resize = () => { W = Math.max(280, box.clientWidth); renderer.setSize(W, H, false); camera.aspect = W / H; camera.updateProjectionMatrix(); };
    window.addEventListener("resize", resize);

    let prev = performance.now();
    const loop = (now) => {
      const wx = document.getElementById("ov-weather");
      if (!document.body.contains(box) || (wx && wx.hidden)) { destroy(); return; }
      const dt = Math.min(0.05, (now - prev) / 1000); prev = now;
      frame(dt);
      scene.raf = requestAnimationFrame(loop);
    };
    scene.destroy = () => {
      cancelAnimationFrame(scene.raf);
      if (scene.audio) { clearInterval(scene.audio.timer); try { scene.audio.ctx.close(); } catch (e) { /* kapalı */ } scene.audio = null; }
      window.removeEventListener("resize", resize);
      try { renderer.dispose(); renderer.forceContextLoss(); } catch (e) { /* kapalı */ }
      box.remove();
    };
    live = scene;
    camera.aspect = W / H; camera.updateProjectionMatrix();
    paintSnd();
    setKind(kind || "clear");
    ensureAudio();
    if (reduce) { snap(); frame(0); } else scene.raf = requestAnimationFrame(loop);
  }

  function destroy() {
    if (live) { const s = live; live = null; s.destroy(); }
  }

  window.weatherScene = {mount, destroy, kinds: KINDS.map((k) => k[0])};
})();
