"use strict";
/* FRIDAY çekirdeği: bağımlılıksız canvas 2D ile sahte-3D reaktör.
   Perspektif izdüşümü, dönen gyro halkaları, derinlik gölgeli parçacık küresi,
   yörünge boncukları, fare paralaksı ve duruma göre tepki. */
(function () {
  const host = document.getElementById("core");
  if (!host) return;
  const canvas = document.createElement("canvas");
  canvas.id = "core3d";
  canvas.setAttribute("aria-hidden", "true");
  host.insertBefore(canvas, host.querySelector(".hit"));
  const ctx = canvas.getContext("2d");
  if (!ctx) return;

  const reduce = window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches;
  const STATE = {
    idle: {spin: 0.35, glow: 0.55, jit: 0.0},
    paused: {spin: 0.12, glow: 0.3, jit: 0.0},
    connecting: {spin: 0.9, glow: 0.7, jit: 0.02},
    listening: {spin: 0.6, glow: 0.85, jit: 0.015},
    thinking: {spin: 1.5, glow: 1.0, jit: 0.04},
    speaking: {spin: 1.0, glow: 1.2, jit: 0.07},
    error: {spin: 0.2, glow: 0.7, jit: 0.1},
  };
  const TAU = Math.PI * 2;
  const rings = [
    {r: 0.92, tilt: 1.15, spin: 0.55, axis: 0.0, w: 1.6, beads: 3, dash: null},
    {r: 0.78, tilt: 0.35, spin: -0.8, axis: 1.1, w: 1.2, beads: 2, dash: [10, 6]},
    {r: 0.64, tilt: 1.9, spin: 1.1, axis: 2.2, w: 1.4, beads: 4, dash: null},
    {r: 0.50, tilt: 0.9, spin: -1.4, axis: 0.6, w: 1.0, beads: 1, dash: [3, 5]},
  ];
  const dots = [];
  const N = 260;
  for (let i = 0; i < N; i++) {
    const y = 1 - (i / (N - 1)) * 2;
    const rad = Math.sqrt(1 - y * y);
    const th = i * 2.399963229728653;
    dots.push({x: Math.cos(th) * rad, y, z: Math.sin(th) * rad, s: 0.6 + Math.random() * 0.9});
  }
  const sparks = Array.from({length: 46}, () => ({a: Math.random() * TAU, e: Math.random() * TAU, r: 0.35 + Math.random() * 0.75, v: 0.2 + Math.random() * 0.7}));

  let size = 0;
  let dpr = 1;
  let rgb = "0,212,196";
  let accent = "255,77,77";
  let colorAt = 0;
  let rx = 0;
  let ry = 0;
  let tx = 0;
  let ty = 0;
  let t = 0;
  let spin = 0.35;
  let glow = 0.55;
  let last = performance.now();

  function resize() {
    size = Math.max(200, host.clientWidth || 540);
    dpr = Math.min(2, window.devicePixelRatio || 1);
    canvas.width = Math.round(size * dpr);
    canvas.height = Math.round(size * dpr);
  }
  new ResizeObserver(resize).observe(host);
  resize();
  window.addEventListener("pointermove", (e) => {
    tx = (e.clientX / innerWidth - 0.5) * 2;
    ty = (e.clientY / innerHeight - 0.5) * 2;
  }, {passive: true});

  function readColor(now) {
    if (now - colorAt < 600) return;
    colorAt = now;
    const cs = getComputedStyle(document.documentElement);
    rgb = (cs.getPropertyValue("--rgb") || rgb).trim() || rgb;
    accent = (cs.getPropertyValue("--arg") || accent).trim() || accent;
  }

  // 3B nokta: önce Y, sonra X ekseninde döndür, perspektifle izdüşür.
  function project(x, y, z, cy, sy, cx, sx, R) {
    const x1 = x * cy + z * sy;
    const z1 = -x * sy + z * cy;
    const y2 = y * cx - z1 * sx;
    const z2 = y * sx + z1 * cx;
    const f = 2.6 / (2.6 - z2 * 0.9);
    return {x: size / 2 + x1 * R * f, y: size / 2 + y2 * R * f, z: z2, f};
  }

  function ringPoint(ring, a, k) {
    // halka düzlemi: tilt ile eğik, axis ile döndürülmüş
    let x = Math.cos(a) * ring.r;
    let y = Math.sin(a) * ring.r;
    let z = 0;
    const ct = Math.cos(ring.tilt), st = Math.sin(ring.tilt);
    let y2 = y * ct - z * st;
    let z2 = y * st + z * ct;
    const ca = Math.cos(ring.axis + k), sa = Math.sin(ring.axis + k);
    const x3 = x * ca + z2 * sa;
    const z3 = -x * sa + z2 * ca;
    return [x3, y2, z3];
  }

  function frame(now) {
    requestAnimationFrame(frame);
    const dt = Math.min(0.05, (now - last) / 1000);
    last = now;
    const body = document.body;
    if (body.dataset.sleep === "1") return;
    readColor(now);
    const st = STATE[body.dataset.state] || STATE.idle;
    const k = reduce ? 0.25 : 1;
    spin += (st.spin * k - spin) * Math.min(1, dt * 2.2);
    glow += (st.glow - glow) * Math.min(1, dt * 2.5);
    t += dt * spin;
    rx += ((ty * 0.35) - rx) * Math.min(1, dt * 3);
    ry += ((tx * 0.5) - ry) * Math.min(1, dt * 3);
    const baseY = t * 0.5 + ry;
    const baseX = 0.28 + rx;
    const cy = Math.cos(baseY), sy = Math.sin(baseY), cx = Math.cos(baseX), sx = Math.sin(baseX);
    const R = size * 0.36;
    const pulse = 1 + Math.sin(now / 480) * 0.02 * glow + (body.dataset.state === "speaking" ? Math.sin(now / 90) * 0.012 : 0);

    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, size, size);
    ctx.globalCompositeOperation = "lighter";
    ctx.lineCap = "round";

    // derinlik gölgeli parçacık küresi
    const sph = R * 0.34 * pulse;
    for (const d of dots) {
      const p = project(d.x * 0.34, d.y * 0.34, d.z * 0.34, cy, sy, cx, sx, R);
      const depth = (p.z / 0.34 + 1) / 2;
      const a = (0.1 + depth * 0.6) * (0.55 + glow * 0.4);
      ctx.fillStyle = `rgba(${rgb},${a.toFixed(3)})`;
      const rad = (0.7 + depth * 1.4) * d.s * (size / 700);
      ctx.beginPath();
      ctx.arc(p.x, p.y, rad, 0, TAU);
      ctx.fill();
    }

    // gyro halkaları + boncuklar
    rings.forEach((ring, i) => {
      const spinK = t * ring.spin * 0.9;
      const seg = 140;
      let prev = null;
      for (let s = 0; s <= seg; s++) {
        const a = (s / seg) * TAU;
        const [x, y, z] = ringPoint(ring, a, spinK * 0.25);
        const p = project(x, y, z, cy, sy, cx, sx, R * pulse);
        if (prev) {
          const depth = (p.z + 1) / 2;
          ctx.strokeStyle = `rgba(${rgb},${(0.12 + depth * 0.62) * Math.min(1, 0.55 + glow * 0.45)})`;
          ctx.lineWidth = ring.w * (0.6 + depth * 1.1) * (size / 640);
          if (ring.dash && s % 2) { prev = p; continue; }
          ctx.beginPath();
          ctx.moveTo(prev.x, prev.y);
          ctx.lineTo(p.x, p.y);
          ctx.stroke();
        }
        prev = p;
      }
      for (let b = 0; b < ring.beads; b++) {
        const a = spinK + (b / ring.beads) * TAU + i;
        const [x, y, z] = ringPoint(ring, a, spinK * 0.25);
        const p = project(x, y, z, cy, sy, cx, sx, R * pulse);
        const depth = (p.z + 1) / 2;
        const rad = (2.6 + depth * 3.6) * (size / 640);
        const g = ctx.createRadialGradient(p.x, p.y, 0, p.x, p.y, rad * 3.4);
        g.addColorStop(0, `rgba(255,255,255,${0.5 + depth * 0.45})`);
        g.addColorStop(0.25, `rgba(${i % 2 ? accent : rgb},${0.55 + depth * 0.4})`);
        g.addColorStop(1, `rgba(${i % 2 ? accent : rgb},0)`);
        ctx.fillStyle = g;
        ctx.beginPath();
        ctx.arc(p.x, p.y, rad * 3.4, 0, TAU);
        ctx.fill();
      }
    });

    // dışa saçılan kıvılcımlar (düşünme/konuşma sırasında artar)
    const energy = Math.max(0, glow - 0.7);
    for (const sp of sparks) {
      sp.a += dt * sp.v * (0.4 + spin);
      const rr = (sp.r + Math.sin(now / 700 + sp.e) * 0.06 + st.jit * Math.sin(now / 60 + sp.e)) * pulse;
      const x = Math.cos(sp.a) * Math.cos(sp.e) * rr;
      const y = Math.sin(sp.e) * rr * 0.9;
      const z = Math.sin(sp.a) * Math.cos(sp.e) * rr;
      const p = project(x, y, z, cy, sy, cx, sx, R);
      const depth = (p.z / 1.2 + 1) / 2;
      ctx.fillStyle = `rgba(${rgb},${((0.15 + depth * 0.5) * (0.35 + energy * 1.6)).toFixed(3)})`;
      ctx.beginPath();
      ctx.arc(p.x, p.y, (0.8 + depth * 1.4) * (size / 700), 0, TAU);
      ctx.fill();
    }

    // merkez parlaması
    const cg = ctx.createRadialGradient(size / 2, size / 2, 0, size / 2, size / 2, sph * 1.9);
    cg.addColorStop(0, `rgba(255,255,255,${0.35 * glow})`);
    cg.addColorStop(0.35, `rgba(${rgb},${0.3 * glow})`);
    cg.addColorStop(1, `rgba(${rgb},0)`);
    ctx.fillStyle = cg;
    ctx.beginPath();
    ctx.arc(size / 2, size / 2, sph * 1.9, 0, TAU);
    ctx.fill();
    ctx.globalCompositeOperation = "source-over";
  }
  requestAnimationFrame(frame);
})();
