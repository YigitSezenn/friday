import * as THREE from "three";
import { EffectComposer } from "three/addons/postprocessing/EffectComposer.js";
import { RenderPass } from "three/addons/postprocessing/RenderPass.js";
import { UnrealBloomPass } from "three/addons/postprocessing/UnrealBloomPass.js";
import { OutputPass } from "three/addons/postprocessing/OutputPass.js";

export const SCENE_ID = "friday-hud-reactor";

// Palette taken from the desktop HUD (ui/hud/hud.css): gold #e6c98a, rose accent #e7a0ae.
// Dark values are multiplied so the bloom pass makes them glow; light values stay readable on cream.
const BG = { dark: new THREE.Color("#05060a"), light: new THREE.Color("#f6f1e6") };
const GOLD = { dark: new THREE.Color("#e6c98a").multiplyScalar(1.5), light: new THREE.Color("#8a4b12") };
const ROSE = { dark: new THREE.Color("#e7a0ae").multiplyScalar(1.4), light: new THREE.Color("#9c2a50") };
const CORE = { dark: new THREE.Color("#fff4dc").multiplyScalar(2.6), light: new THREE.Color("#e08a1e").multiplyScalar(1.3) };
// Açık modda derinlik için koyu bakır ve sıcak parıltı (krem zeminde ışıma görünmez; kontrast ve gölgeyle derinlik verilir).
const COPPER = { dark: new THREE.Color("#e6c98a").multiplyScalar(1.2), light: new THREE.Color("#5e2f0a") };
const EMBER = { dark: new THREE.Color("#ffd9a0").multiplyScalar(1.6), light: new THREE.Color("#d9731a") };
const FLOOR = { dark: new THREE.Color("#e6c98a"), light: new THREE.Color("#7a4a1a") };
const DUST = { dark: new THREE.Color("#e6c98a"), light: new THREE.Color("#8a5a2b") };

export function startScene(canvas) {
  const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const mobile = () => innerWidth < 900;
  const renderer = new THREE.WebGLRenderer({
    canvas,
    antialias: false,
    powerPreference: "high-performance",
    stencil: false,
  });
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1;

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(34, 1, 0.1, 80);
  camera.position.set(0, 1.4, 11);

  let themeMix = document.documentElement.dataset.theme === "light" ? 1 : 0;
  let themeTarget = themeMix;
  scene.background = BG.dark.clone().lerp(BG.light, themeMix);
  scene.fog = new THREE.Fog(scene.background.clone(), 9, 27);
  renderer.setClearColor(scene.background, 1);

  // Every material registered here is re-tinted each frame so the theme cross-fades.
  const tinted = [];
  const tint = (material, palette, opacity = 1) => {
    material.opacity = opacity;
    material.color.copy(palette.dark);
    tinted.push({ material, palette });
    return material;
  };
  const basic = (palette, opacity = 1) =>
    tint(new THREE.MeshBasicMaterial({ transparent: true, opacity, side: THREE.DoubleSide, depthWrite: false }), palette, opacity);

  const world = new THREE.Group();
  scene.add(world);
  const reactor = new THREE.Group();
  reactor.scale.setScalar(mobile() ? 0.56 : 0.7);
  world.add(reactor);

  // Spinning parts: { obj, speed } — speed is multiplied by energy when the user hovers a button.
  const spinners = [];

  // Segmented ring. A holder carries the tilt; the inner spin group does the rotation.
  const segRing = ({ radius, width, parts, fill, palette, opacity, speed, tilt = null, parent = reactor }) => {
    const holder = new THREE.Group();
    if (tilt) holder.rotation.set(tilt[0], tilt[1], tilt[2]);
    parent.add(holder);
    const spin = new THREE.Group();
    holder.add(spin);
    const mat = basic(palette, opacity);
    for (let i = 0; i < parts; i++) {
      const start = (i / parts) * Math.PI * 2;
      const geometry = new THREE.RingGeometry(radius, radius + width, 96, 1, start, (Math.PI * 2 / parts) * fill);
      spin.add(new THREE.Mesh(geometry, mat));
    }
    spinners.push({ obj: spin, speed });
    return spin;
  };

  // Core: bright centre, soft halo, then the segmented rings of the reactor.
  reactor.add(new THREE.Mesh(new THREE.SphereGeometry(0.3, 32, 24), basic(CORE, 1)));
  const halo = new THREE.Mesh(new THREE.CircleGeometry(0.95, 64), basic(GOLD, 0.1));
  halo.position.z = -0.05;
  reactor.add(halo);

  segRing({ radius: 0.85, width: 0.035, parts: 3, fill: 0.62, palette: GOLD, opacity: 0.95, speed: 0.6 });
  segRing({ radius: 1.12, width: 0.012, parts: 12, fill: 0.45, palette: GOLD, opacity: 0.8, speed: -0.35 });
  segRing({ radius: 2.2, width: 0.03, parts: 2, fill: 0.88, palette: GOLD, opacity: 0.55, speed: 0.22 });
  segRing({ radius: 2.55, width: 0.05, parts: 36, fill: 0.42, palette: GOLD, opacity: 0.75, speed: -0.5 });

  // Tick scale around the core; every sixth tick is longer, like a HUD gauge.
  const TICKS = 72;
  const ticks = new THREE.InstancedMesh(new THREE.BoxGeometry(0.035, 0.11, 0.01), basic(GOLD, 0.85), TICKS);
  const matrix = new THREE.Matrix4();
  const quat = new THREE.Quaternion();
  const scale = new THREE.Vector3();
  const pos = new THREE.Vector3();
  const zAxis = new THREE.Vector3(0, 0, 1);
  for (let i = 0; i < TICKS; i++) {
    const angle = (i / TICKS) * Math.PI * 2;
    const major = i % 6 === 0;
    pos.set(Math.cos(angle) * 1.66, Math.sin(angle) * 1.66, 0);
    quat.setFromAxisAngle(zAxis, angle - Math.PI / 2);
    scale.set(major ? 1.6 : 1, major ? 1.6 : 1, 1);
    matrix.compose(pos, quat, scale);
    ticks.setMatrixAt(i, matrix);
  }
  reactor.add(ticks);
  spinners.push({ obj: ticks, speed: 0.12 });

  // Two tilted orbit rings in rose; a bead rides each one.
  // Two tilted orbit rings in rose; a bead rides each one.
  const orbitA = segRing({ radius: 2.95, width: 0.012, parts: 1, fill: 1, palette: ROSE, opacity: 0.7, speed: 0.3, tilt: [1.15, 0, 0.25] });
  const orbitB = segRing({ radius: 3.25, width: 0.008, parts: 1, fill: 1, palette: ROSE, opacity: 0.5, speed: -0.2, tilt: [1.15, 0, -0.9] });
  orbitA.add(new THREE.Mesh(new THREE.SphereGeometry(0.07, 16, 16), basic(ROSE, 1)));
  orbitA.children[orbitA.children.length - 1].position.set(2.95, 0, 0);
  orbitB.add(new THREE.Mesh(new THREE.SphereGeometry(0.05, 16, 16), basic(GOLD, 1)));
  orbitB.children[orbitB.children.length - 1].position.set(3.25, 0, 0);

  // Opaklığı temaya göre değişen parçalar: koyu modda ince, açık modda belirgin.
  const themed = [];
  const fade = (material, darkOpacity, lightOpacity) => {
    themed.push({ material, darkOpacity, lightOpacity });
    return material;
  };

  // Radyal doku (parıltı / gölge) — tek kanvastan.
  const radial = (stops) => {
    const size = 256;
    const c = document.createElement("canvas");
    c.width = c.height = size;
    const g = c.getContext("2d");
    const grad = g.createRadialGradient(size / 2, size / 2, 0, size / 2, size / 2, size / 2);
    for (const [at, color] of stops) grad.addColorStop(at, color);
    g.fillStyle = grad;
    g.fillRect(0, 0, size, size);
    const texture = new THREE.CanvasTexture(c);
    texture.colorSpace = THREE.SRGBColorSpace;
    return texture;
  };

  // Çekirdek ışıması: açık modda sıcak turuncu bir hale, koyu modda bloom'a ek yumuşak ışık.
  const glowMat = fade(tint(new THREE.SpriteMaterial({
    map: radial([[0, "rgba(255,255,255,1)"], [0.25, "rgba(255,255,255,.75)"], [0.6, "rgba(255,255,255,.18)"], [1, "rgba(255,255,255,0)"]]),
    transparent: true, depthWrite: false,
  }), EMBER, 0.35), 0.35, 0.85);
  const glow = new THREE.Sprite(glowMat);
  glow.scale.setScalar(2.6);
  reactor.add(glow);

  // Zemine düşen yumuşak gölge: açık modda reaktörü yüzeyden ayırır.
  const shadowMat = fade(new THREE.MeshBasicMaterial({
    map: radial([[0, "rgba(60,30,8,.55)"], [0.5, "rgba(60,30,8,.18)"], [1, "rgba(60,30,8,0)"]]),
    transparent: true, depthWrite: false,
  }), 0, 0.9);
  const shadow = new THREE.Mesh(new THREE.CircleGeometry(3.4, 64), shadowMat);
  shadow.rotation.x = -Math.PI / 2;
  shadow.position.y = -2.9;
  world.add(shadow);

  // Masaüstü uygulamadaki gibi parçacık küresi: dönerken derinlik hissi verir.
  const SPHERE = mobile() ? 260 : 520;
  const spherePos = new Float32Array(SPHERE * 3);
  for (let i = 0; i < SPHERE; i++) {
    const y = 1 - (i / (SPHERE - 1)) * 2;
    const r = Math.sqrt(1 - y * y);
    const th = i * 2.399963229728653;
    spherePos.set([Math.cos(th) * r * 0.62, y * 0.62, Math.sin(th) * r * 0.62], i * 3);
  }
  const sphereGeo = new THREE.BufferGeometry();
  sphereGeo.setAttribute("position", new THREE.BufferAttribute(spherePos, 3));
  const sphere = new THREE.Points(sphereGeo, fade(tint(new THREE.PointsMaterial({ size: 0.028, transparent: true, depthWrite: false }), COPPER, 0.5), 0.45, 0.9));
  reactor.add(sphere);

  // Jiroskop halkaları: üç eğik tam halka, her birinde bir boncuk.
  const gyros = [];
  [[0.98, [1.2, 0.3, 0], 0.7], [1.3, [0.4, 1.1, 0.5], -0.55], [1.86, [1.6, -0.5, 0.9], 0.4]].forEach(([radius, tilt, speed], i) => {
    const holder = new THREE.Group();
    holder.rotation.set(tilt[0], tilt[1], tilt[2]);
    reactor.add(holder);
    const spin = new THREE.Group();
    holder.add(spin);
    const ring = new THREE.Mesh(
      new THREE.TorusGeometry(radius, 0.008 + i * 0.002, 6, 160),
      fade(basic(i === 1 ? ROSE : COPPER, 0.6), 0.35, 0.85),
    );
    spin.add(ring);
    const bead = new THREE.Mesh(new THREE.SphereGeometry(0.05 + i * 0.008, 16, 16), fade(basic(i === 1 ? ROSE : EMBER, 1), 0.9, 1));
    bead.position.set(radius, 0, 0);
    spin.add(bead);
    gyros.push({ spin, speed });
  });

  // Perspective floor grid. It sits below the reactor and fades into the fog.
  const floor = new THREE.GridHelper(44, 44);
  floor.material = tint(new THREE.LineBasicMaterial({ transparent: true, depthWrite: false }), FLOOR, 0.22);
  floor.position.y = -3.4;
  scene.add(floor);

  // Drifting dust in the gold accent.
  const DUST_COUNT = mobile() ? 220 : 480;
  const dustPositions = new Float32Array(DUST_COUNT * 3);
  for (let i = 0; i < DUST_COUNT; i++) {
    dustPositions[i * 3] = (Math.random() - 0.5) * 30;
    dustPositions[i * 3 + 1] = (Math.random() - 0.5) * 16;
    dustPositions[i * 3 + 2] = (Math.random() - 0.5) * 16 - 3;
  }
  const dustGeometry = new THREE.BufferGeometry();
  dustGeometry.setAttribute("position", new THREE.BufferAttribute(dustPositions, 3));
  const dust = new THREE.Points(
    dustGeometry,
    tint(new THREE.PointsMaterial({ size: 0.035, transparent: true, depthWrite: false }), DUST, 0.7),
  );
  world.add(dust);

  const composer = new EffectComposer(renderer);
  composer.addPass(new RenderPass(scene, camera));
  const bloom = new UnrealBloomPass(new THREE.Vector2(640, 360), 0.7, 0.45, 0.6);
  composer.addPass(bloom);
  composer.addPass(new OutputPass());
  const bloomOn = !mobile();

  const mouse = { x: 0, y: 0, sx: 0, sy: 0 };
  const state = { scroll: 0 };
  addEventListener("pointermove", (event) => {
    mouse.x = (event.clientX / innerWidth) * 2 - 1;
    mouse.y = (event.clientY / innerHeight) * 2 - 1;
  }, { passive: true });

  const resize = () => {
    renderer.setPixelRatio(1);
    renderer.setSize(innerWidth, innerHeight, false);
    const drawW = Math.max(2, innerWidth);
    const drawH = Math.max(2, innerHeight);
    composer.setPixelRatio(1);
    composer.setSize(drawW, drawH);
    bloom.setSize(Math.max(2, Math.floor(drawW * 0.35)), Math.max(2, Math.floor(drawH * 0.35)));
    camera.aspect = innerWidth / innerHeight;
    camera.fov = camera.aspect < 0.8 ? 46 : 34;
    camera.updateProjectionMatrix();
  };
  addEventListener("resize", resize);
  resize();

  const clock = new THREE.Clock();
  let time = 0;
  let boot = reduce ? 1 : 0;
  let bootClock = 0;
  let energy = 0;
  let energyTarget = 0;
  const pose = { x: 0, y: 0, s: reduce ? 1 : 0.2 };
  let drawing = !document.hidden;
  document.addEventListener("visibilitychange", () => {
    drawing = !document.hidden;
    if (drawing) clock.getDelta();
  });

  const frame = () => {
    requestAnimationFrame(frame);
    if (!drawing) return;
    const delta = Math.min(clock.getDelta(), 0.05);
    time += reduce ? delta * 0.05 : delta;
    if (!reduce && boot < 1) {
      bootClock += delta;
      const progress = Math.min(1, Math.max(0, (bootClock - 0.2) / 2));
      boot = 1 - (1 - progress) ** 3;
    }
    energy += (energyTarget - energy) * 0.08;
    mouse.sx += (mouse.x - mouse.sx) * 0.06;
    mouse.sy += (mouse.y - mouse.sy) * 0.06;

    const scroll = state.scroll;
    const away = Math.min(1, Math.max(0, (scroll - 0.08) / 0.45));
    const halfWidth = Math.tan(THREE.MathUtils.degToRad(camera.fov / 2)) * 11 * camera.aspect;
    const heroX = mobile() ? 0 : halfWidth * 0.52;
    const heroY = mobile() ? 1.35 : 0;
    const heroS = mobile() ? 0.72 : 1;
    const targetX = heroX + (mobile() ? 0 : away * 1.45);
    const targetY = heroY - scroll * (mobile() ? 0.85 : 0.22);
    const targetS = heroS * (1 - away * (mobile() ? 0.18 : 0.4));

    themeMix += (themeTarget - themeMix) * (reduce ? 1 : 0.08);
    if (Math.abs(themeTarget - themeMix) < 0.004) themeMix = themeTarget;
    scene.background.copy(BG.dark).lerp(BG.light, themeMix);
    scene.fog.color.copy(scene.background);
    renderer.setClearColor(scene.background, 1);
    for (const { material, palette } of tinted) material.color.copy(palette.dark).lerp(palette.light, themeMix);
    for (const { material, darkOpacity, lightOpacity } of themed) material.opacity = darkOpacity + (lightOpacity - darkOpacity) * themeMix;
    // Açık modda ışıma yerine normal karışım: krem zeminde renkler yıkanmaz.
    glowMat.blending = themeMix > 0.5 ? THREE.NormalBlending : THREE.AdditiveBlending;
    bloom.threshold = 0.6 + themeMix * 0.3;
    bloom.strength = (0.7 - themeMix * 0.55) * (1 - away * 0.7) * (0.85 + energy * 0.45);

    pose.x += (targetX - pose.x) * 0.06;
    pose.y += (targetY - pose.y) * 0.06;
    pose.s += (targetS - pose.s) * 0.06;
    const bootScale = boot < 1 ? 0.12 + 0.88 * boot : 1;
    world.position.set(pose.x, pose.y, 0);
    world.scale.setScalar(pose.s * bootScale);

    const speedUp = 1 + energy * 2.2;
    for (const { obj, speed } of spinners) obj.rotation.z = time * speed * speedUp;
    for (const { spin, speed } of gyros) spin.rotation.z = time * speed * speedUp;
    sphere.rotation.y = time * 0.35 * speedUp;
    sphere.rotation.x = time * 0.12;
    glow.scale.setScalar(2.6 * (1 + Math.sin(time * 2.2) * 0.04 + energy * 0.25));
    reactor.rotation.y = Math.sin(time * 0.25) * 0.22 + mouse.sx * 0.4 + scroll * 0.8;
    reactor.rotation.x = -0.18 + mouse.sy * 0.25 + Math.sin(time * 0.3) * 0.05;

    dust.rotation.y = time * 0.03 + mouse.sx * 0.12;
    dust.rotation.x = mouse.sy * 0.06;
    floor.position.y = -3.4 - scroll * 0.6;
    camera.position.x = mouse.sx * 0.3;
    camera.position.y = 1.4 - mouse.sy * 0.2;
    camera.lookAt(0, -0.2, 0);

    if (bloomOn) composer.render();
    else renderer.render(scene, camera);
  };
  frame();
  document.documentElement.classList.add("gl-ready");

  return {
    id: SCENE_ID,
    setScroll(value) {
      state.scroll = Math.min(1, Math.max(0, value));
    },
    setEnergy(value) {
      energyTarget = Math.min(1, Math.max(0, value));
    },
    setTheme(mode) {
      themeTarget = mode === "light" ? 1 : 0;
      if (reduce) themeMix = themeTarget;
    },
  };
}
