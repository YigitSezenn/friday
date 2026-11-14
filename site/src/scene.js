import * as THREE from "three";
import { EffectComposer } from "three/addons/postprocessing/EffectComposer.js";
import { RenderPass } from "three/addons/postprocessing/RenderPass.js";
import { UnrealBloomPass } from "three/addons/postprocessing/UnrealBloomPass.js";
import { OutputPass } from "three/addons/postprocessing/OutputPass.js";

export const SCENE_ID = "friday-core-ring";

const DARK_BG = new THREE.Color("#04070c");
const LIGHT_BG = new THREE.Color("#f6f1e8");
const DARK_POINT = new THREE.Color("#7fe7ff");
const LIGHT_POINT = new THREE.Color("#c46212");
const DARK_METAL = new THREE.Color("#f4f7fb");
const LIGHT_METAL = new THREE.Color("#e4b57a");
const DARK_BEAD = new THREE.Color("#7fe7ff").multiplyScalar(3);
const LIGHT_BEAD = new THREE.Color("#ffe08a").multiplyScalar(2.4);

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
  renderer.toneMappingExposure = 1.08;

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(32, 1, 0.1, 80);
  camera.position.set(0, 0, 11);

  const pmrem = new THREE.PMREMGenerator(renderer);
  const studio = (background, lights) => {
    const env = new THREE.Scene();
    env.background = new THREE.Color(background);
    for (const light of lights) {
      const mesh = new THREE.Mesh(
        new THREE.PlaneGeometry(light[0], light[1]),
        new THREE.MeshBasicMaterial({
          color: new THREE.Color(light[2]).multiplyScalar(light[3]),
          side: THREE.DoubleSide,
        }),
      );
      mesh.position.set(light[4], light[5], light[6]);
      mesh.lookAt(0, 0, 0);
      env.add(mesh);
    }
    return pmrem.fromScene(env, 0.04).texture;
  };
  const darkEnv = studio("#05070c", [
    [10, 3, "#ffffff", 3.2, 0, 8, 2],
    [2, 12, "#2f6bff", 4.2, -9, 0, -2],
    [1.4, 10, "#4cc3ff", 2.4, 8, -1, -4],
    [6, 6, "#d5e6ff", 0.28, 6, 2, 8],
  ]);
  const lightEnv = studio("#f3eadc", [
    [10, 3, "#fff1dc", 3.4, 0, 8, 2],
    [2, 12, "#e39a4a", 4.6, -9, 0, -2],
    [1.4, 10, "#9a4d12", 3.2, 8, -1, -4],
    [6, 6, "#fffaf3", 0.9, 6, 2, 8],
  ]);
  pmrem.dispose();
  let themeMix = document.documentElement.dataset.theme === "light" ? 1 : 0;
  let themeTarget = themeMix;
  scene.environment = themeMix === 1 ? lightEnv : darkEnv;
  scene.background = (themeMix === 1 ? LIGHT_BG : DARK_BG).clone();
  renderer.setClearColor(scene.background, 1);

  const world = new THREE.Group();
  scene.add(world);
  const core = new THREE.Group();
  world.add(core);

  const uniforms = {
    uTime: { value: 0 },
    uAmp: { value: 0.12 },
    uTheme: { value: themeMix },
    uBoot: { value: reduce ? 1 : 0 },
    uEnergy: { value: 0 },
  };
  const metal = new THREE.MeshStandardMaterial({
    color: themeMix === 1 ? "#e4b57a" : "#f4f7fb",
    metalness: 1,
    roughness: 0.08,
    envMapIntensity: 1.35,
  });
  metal.onBeforeCompile = (shader) => {
    shader.uniforms.uTime = uniforms.uTime;
    shader.uniforms.uAmp = uniforms.uAmp;
    shader.uniforms.uTheme = uniforms.uTheme;
    shader.vertexShader = shader.vertexShader
      .replace(
        "#include <common>",
        `#include <common>
        uniform float uTime;
        uniform float uAmp;
        varying vec3 vSunPos;`,
      )
      .replace(
        "#include <begin_vertex>",
        `float wave = sin(position.x * 3.1 + uTime) * sin(position.y * 2.4 + uTime * 0.7);
        vec3 transformed = position + normal * wave * uAmp;
        vSunPos = transformed;`,
      );
    shader.fragmentShader = shader.fragmentShader
      .replace(
        "#include <common>",
        `#include <common>
        uniform float uTime;
        uniform float uTheme;
        varying vec3 vSunPos;
        // friday-sun-disk
        float sunHash(vec3 p) {
          p = fract(p * 0.1031);
          p += dot(p, p.zyx + 31.32);
          return fract((p.x + p.y) * p.z);
        }
        float sunNoise(vec3 p) {
          vec3 i = floor(p);
          vec3 f = fract(p);
          f = f * f * (3.0 - 2.0 * f);
          return mix(
            mix(mix(sunHash(i), sunHash(i + vec3(1.0, 0.0, 0.0)), f.x),
                mix(sunHash(i + vec3(0.0, 1.0, 0.0)), sunHash(i + vec3(1.0, 1.0, 0.0)), f.x), f.y),
            mix(mix(sunHash(i + vec3(0.0, 0.0, 1.0)), sunHash(i + vec3(1.0, 0.0, 1.0)), f.x),
                mix(sunHash(i + vec3(0.0, 1.0, 1.0)), sunHash(i + vec3(1.0, 1.0, 1.0)), f.x), f.y),
            f.z);
        }
        float sunSpot(vec3 p, vec3 center, float radius) {
          return smoothstep(radius, radius * 0.35, length(p - normalize(center)));
        }
        vec3 sunDisk(vec3 pos, vec3 nrm, vec3 viewDir) {
          vec3 p = normalize(pos);
          float facing = clamp(dot(normalize(nrm), normalize(viewDir)), 0.0, 1.0);
          float limb = pow(facing, 0.42);
          float boil = sunNoise(p * 7.5 + vec3(uTime * 0.15, uTime * 0.07, 0.0));
          float grain = sunNoise(p * 20.0 + vec3(uTime * 0.05, 0.0, uTime * 0.04));
          float spots = sunSpot(p, vec3(0.45, 0.35, 0.82), 0.20)
            + sunSpot(p, vec3(-0.55, 0.15, 0.62), 0.13)
            + sunSpot(p, vec3(0.15, -0.72, 0.48), 0.09);
          spots = clamp(spots, 0.0, 1.0);
          vec3 edgeCol = vec3(0.95, 0.22, 0.01);
          vec3 midCol = vec3(1.55, 0.62, 0.04);
          vec3 hotCol = vec3(1.95, 1.12, 0.26);
          vec3 color = mix(edgeCol, midCol, smoothstep(0.0, 0.5, limb));
          color = mix(color, hotCol, pow(limb, 2.1) * (0.18 + 0.55 * clamp(grain, 0.0, 1.0)));
          color *= 0.84 + 0.32 * clamp(boil, 0.0, 1.0);
          color = mix(color, vec3(0.32, 0.07, 0.012), spots * 0.88);
          return color;
        }`,
      )
      .replace(
        "#include <opaque_fragment>",
        `outgoingLight = mix(outgoingLight, sunDisk(vSunPos, normal, geometryViewDir), uTheme);
        #include <opaque_fragment>`,
      );
  };
  const blob = new THREE.Mesh(
    new THREE.SphereGeometry(1.15, mobile() ? 40 : 64, mobile() ? 28 : 48),
    metal,
  );
  core.add(blob);

  const glass = new THREE.ShaderMaterial({
    glslVersion: THREE.GLSL3,
    transparent: true,
    depthWrite: false,
    blending: THREE.NormalBlending,
    uniforms: { uTime: { value: 0 }, uTheme: { value: themeMix } },
    vertexShader: `
      out vec3 vN;
      out vec3 vV;
      void main() {
        vec4 mv = modelViewMatrix * vec4(position, 1.0);
        vN = normalize(normalMatrix * normal);
        vV = normalize(-mv.xyz);
        gl_Position = projectionMatrix * mv;
      }`,
    fragmentShader: `
      precision highp float;
      uniform float uTime;
      uniform float uTheme;
      in vec3 vN;
      in vec3 vV;
      out vec4 fragColor;
      void main() {
        float fres = pow(1.0 - abs(dot(normalize(vN), normalize(vV))), 2.1);
        vec3 irid = 0.5 + 0.5 * cos(6.2831 * (fres + vec3(0.55, 0.7, 0.9)) + uTime * 0.25);
        vec3 cool = mix(vec3(0.85, 0.95, 1.0), irid, 0.45) * fres;
        vec3 warm = mix(vec3(0.55, 0.28, 0.1), irid, 0.4) * fres;
        fragColor = vec4(mix(cool, warm, uTheme), fres * (1.0 - uTheme));
      }`,
  });
  const ring = new THREE.Mesh(new THREE.TorusGeometry(1.95, 0.16, 12, 80), glass);
  ring.rotation.set(1.15, 0.25, 0);
  core.add(ring);

  const beadA = new THREE.Mesh(
    new THREE.SphereGeometry(0.055, 16, 16),
    new THREE.MeshBasicMaterial({ color: themeMix === 1 ? LIGHT_BEAD.clone() : DARK_BEAD.clone() }),
  );
  const beadB = new THREE.Mesh(
    new THREE.SphereGeometry(0.035, 16, 16),
    new THREE.MeshBasicMaterial({ color: new THREE.Color("#ffffff").multiplyScalar(2.4) }),
  );
  if (themeMix > 0.001) {
    for (const bead of [beadA, beadB]) {
      bead.material.transparent = true;
      bead.material.depthWrite = false;
      bead.material.opacity = 1 - themeMix;
    }
  }
  core.add(beadA, beadB);

  const count = mobile() ? 280 : 900;
  const positions = new Float32Array(count * 3);
  for (let i = 0; i < count; i += 1) {
    const radius = 2.2 + Math.random() * 1.8;
    const theta = Math.random() * Math.PI * 2;
    const phi = Math.acos(2 * Math.random() - 1);
    positions[i * 3] = radius * Math.sin(phi) * Math.cos(theta);
    positions[i * 3 + 1] = radius * Math.sin(phi) * Math.sin(theta) * 0.72;
    positions[i * 3 + 2] = radius * Math.cos(phi);
  }
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
  const points = new THREE.Points(
    geometry,
    new THREE.PointsMaterial({
      color: themeMix === 1 ? LIGHT_POINT.clone() : DARK_POINT.clone(),
      size: mobile() ? 0.025 : 0.018,
      transparent: true,
      opacity: 0.85,
      depthWrite: false,
      blending: themeMix === 1 ? THREE.NormalBlending : THREE.AdditiveBlending,
    }),
  );
  world.add(points);

  const rays = new THREE.Mesh(
    new THREE.PlaneGeometry(7.6, 7.6),
    new THREE.ShaderMaterial({
      glslVersion: THREE.GLSL3,
      transparent: true,
      depthWrite: false,
      blending: THREE.NormalBlending,
      uniforms: { uTime: uniforms.uTime, uTheme: uniforms.uTheme },
      vertexShader: `
        out vec2 vUv;
        void main() {
          vUv = uv;
          gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
        }`,
      fragmentShader: `
        precision highp float;
        uniform float uTime;
        uniform float uTheme;
        in vec2 vUv;
        out vec4 fragColor;
        void main() {
          vec2 p = vUv * 2.0 - 1.0;
          float r = length(p);
          float ang = atan(p.y, p.x);
          float fine = pow(abs(cos(ang * 8.0 + uTime * 0.12)), 12.0);
          float bold = pow(abs(cos(ang * 4.0 - 0.2)), 5.0);
          float spokes = max(fine * 0.55, bold);
          float outside = smoothstep(0.30, 0.40, r) * smoothstep(1.0, 0.42, r);
          float corona = smoothstep(0.70, 0.30, r) * smoothstep(0.28, 0.38, r);
          float alpha = (spokes * outside * 0.95 + corona * 0.9) * uTheme;
          if (alpha < 0.004) discard;
          vec3 fire = vec3(0.95, 0.34, 0.02);
          vec3 hot = vec3(1.0, 0.82, 0.32);
          fragColor = vec4(mix(fire, hot, smoothstep(0.72, 0.32, r)), alpha);
        }`,
    }),
  );
  rays.position.z = -0.15;
  rays.renderOrder = 2;
  world.add(rays);

  const reticle = new THREE.Mesh(
    new THREE.PlaneGeometry(6.8, 6.8),
    new THREE.ShaderMaterial({
      glslVersion: THREE.GLSL3,
      transparent: true,
      depthWrite: false,
      blending: THREE.NormalBlending,
      uniforms: {
        uTime: uniforms.uTime,
        uTheme: uniforms.uTheme,
        uBoot: uniforms.uBoot,
        uEnergy: uniforms.uEnergy,
      },
      vertexShader: `
        out vec2 vUv;
        void main() {
          vUv = uv;
          gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
        }`,
      fragmentShader: `
        precision highp float;
        uniform float uTime;
        uniform float uTheme;
        uniform float uBoot;
        uniform float uEnergy;
        in vec2 vUv;
        out vec4 fragColor;
        const float TAU = 6.28318530718;
        // friday-hud-reticle
        float band(float r, float center, float halfWidth, float aa) {
          return 1.0 - smoothstep(halfWidth - aa, halfWidth + aa, abs(r - center));
        }
        float span(float r, float from, float to, float aa) {
          return smoothstep(from - aa, from + aa, r) * (1.0 - smoothstep(to - aa, to + aa, r));
        }
        float arc(float d, float len, float aa) {
          return smoothstep(0.0, aa, d) * (1.0 - smoothstep(len - aa, len, d));
        }
        void main() {
          vec2 p = (vUv * 2.0 - 1.0) * 3.4;
          float r = length(p);
          float a = atan(p.y, p.x) / TAU + 0.5;
          float aa = fwidth(r) * 1.1;
          float turn = aa / (TAU * max(r, 0.2));
          float t = uTime;
          float line = 0.0;
          float hot = 0.0;

          float wobble = sin(a * TAU * 11.0 + t * 2.6) * sin(a * TAU * 5.0 - t * 1.7);
          line += band(r, 1.47 + wobble * (0.012 + 0.06 * uEnergy), 0.007, aa) * 0.9;

          float cells = fract(a + t * 0.006) * 72.0;
          float arcLen = TAU * r / 72.0;
          float tick = 1.0 - smoothstep(0.007 - aa, 0.007 + aa, abs(fract(cells) - 0.5) * arcLen);
          float major = step(mod(floor(cells), 6.0), 0.5);
          float sweep = smoothstep(0.0, 0.03, uBoot * 1.08 - fract(a + 0.25));
          line += tick * span(r, 1.68, mix(1.75, 1.84, major), aa) * mix(0.55, 1.0, major) * sweep;

          float thirds = fract(fract(a - t * 0.03) * 3.0);
          line += band(r, 2.3, 0.02, aa) * arc(thirds, 0.64 * uBoot, turn * 3.0) * 0.85;

          float halves = fract(fract(a + t * 0.018) * 2.0);
          line += band(r, 2.56, 0.005, aa) * arc(halves, 0.9, turn * 2.0) * 0.7 * uBoot;
          hot += band(r, 2.56, 0.022, aa) * arc(fract(a - t * 0.05), 0.03, turn) * uBoot;

          float dashes = abs(fract(fract(a + t * 0.004) * 150.0) - 0.5);
          line += band(r, 2.9, 0.005, aa) * smoothstep(0.2, 0.28, dashes) * 0.4 * uBoot;

          float pair = fract(fract(a + t * 0.011) * 2.0);
          line += band(r, 3.16, 0.008, aa) * arc(pair, 0.36 * uBoot, turn * 2.0) * 0.6;

          float notch = abs(fract(a * 4.0 + 0.5) - 0.5) * TAU * r / 4.0;
          line += (1.0 - smoothstep(0.008 - aa, 0.008 + aa, notch)) * span(r, 3.22, 3.36, aa) * 0.8 * uBoot;

          line *= smoothstep(0.0, 0.3, uBoot);
          vec3 cool = vec3(0.42, 0.9, 1.0) * 1.35;
          vec3 warm = vec3(0.5, 0.22, 0.04);
          vec3 emberCool = vec3(1.0, 0.64, 0.24) * 1.6;
          vec3 emberWarm = vec3(0.05, 0.36, 0.45);
          float alpha = clamp(line + hot, 0.0, 1.0) * mix(0.92, 0.42, uTheme);
          if (alpha < 0.004) discard;
          vec3 color = mix(mix(cool, warm, uTheme), mix(emberCool, emberWarm, uTheme), clamp(hot, 0.0, 1.0));
          fragColor = vec4(color, alpha);
        }`,
    }),
  );
  reticle.position.z = -0.2;
  reticle.renderOrder = 1;
  world.add(reticle);

  const composer = new EffectComposer(renderer);
  composer.addPass(new RenderPass(scene, camera));
  const bloom = new UnrealBloomPass(new THREE.Vector2(640, 360), 0.45, 0.55, 0.86);
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
    const ratio = 1;
    renderer.setPixelRatio(ratio);
    renderer.setSize(innerWidth, innerHeight, false);
    const drawW = Math.max(2, Math.floor(innerWidth * ratio));
    const drawH = Math.max(2, Math.floor(innerHeight * ratio));
    composer.setPixelRatio(1);
    composer.setSize(drawW, drawH);
    bloom.setSize(Math.max(2, Math.floor(drawW * 0.35)), Math.max(2, Math.floor(drawH * 0.35)));
    camera.aspect = innerWidth / innerHeight;
    camera.fov = camera.aspect < 0.8 ? 48 : 32;
    camera.updateProjectionMatrix();
  };
  addEventListener("resize", resize);
  resize();

  const clock = new THREE.Clock();
  let time = 0;
  const pose = { x: 0, y: 0, s: reduce ? 1 : 0.2 };
  let bootClock = 0;
  let energyTarget = 0;
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
    if (!reduce && uniforms.uBoot.value < 1) {
      bootClock += delta;
      const progress = Math.min(1, Math.max(0, (bootClock - 0.25) / 2.2));
      uniforms.uBoot.value = 1 - (1 - progress) ** 3;
    }
    uniforms.uEnergy.value += (energyTarget - uniforms.uEnergy.value) * 0.08;
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
    scene.background.copy(DARK_BG).lerp(LIGHT_BG, themeMix);
    renderer.setClearColor(scene.background, 1);
    points.material.color.copy(DARK_POINT).lerp(LIGHT_POINT, themeMix);
    points.material.opacity = 0.85 - themeMix * 0.45;
    beadA.material.color.copy(DARK_BEAD).lerp(LIGHT_BEAD, themeMix);
    const beadAlpha = 1 - themeMix;
    const beadTransparent = beadAlpha < 0.999;
    if (beadA.material.transparent !== beadTransparent) {
      for (const bead of [beadA, beadB]) {
        bead.material.transparent = beadTransparent;
        bead.material.depthWrite = !beadTransparent;
        bead.material.needsUpdate = true;
      }
    }
    beadA.material.opacity = beadAlpha;
    beadB.material.opacity = beadAlpha;
    metal.color.copy(DARK_METAL).lerp(LIGHT_METAL, themeMix);
    metal.roughness = 0.08 + themeMix * 0.38;
    metal.envMapIntensity = 1.35 - themeMix * 0.35;
    renderer.toneMappingExposure = 1.08 - themeMix * 0.16;
    glass.uniforms.uTheme.value = themeMix;
    uniforms.uTheme.value = themeMix;
    bloom.threshold = 0.78 + themeMix * 0.2;
    bloom.strength = (0.62 - themeMix * 0.4) * (1 - away * 0.72);
    pose.x += (targetX - pose.x) * 0.06;
    pose.y += (targetY - pose.y) * 0.06;
    pose.s += (targetS - pose.s) * 0.06;
    world.position.set(pose.x, pose.y, 0);
    world.scale.setScalar(pose.s);
    core.rotation.y = time * 0.22 + mouse.sx * 0.4 + scroll * 1.2;
    core.rotation.x = mouse.sy * 0.28 + Math.sin(time * 0.35) * 0.08;
    ring.rotation.z = time * 0.16;
    glass.uniforms.uTime.value = time;
    uniforms.uTime.value = time;
    uniforms.uAmp.value = (0.1 + scroll * 0.08) * (1 - themeMix * 0.72);
    const angle = time * 0.7;
    beadA.position.set(Math.cos(angle) * 2.55, Math.sin(angle) * 0.35, Math.sin(angle) * 2.55);
    beadB.position.set(Math.cos(-angle * 0.7) * 2.95, 0, Math.sin(-angle * 0.7) * 2.95);
    points.rotation.y = time * 0.05 + mouse.sx * 0.15;
    points.rotation.x = mouse.sy * 0.08;
    camera.position.x = mouse.sx * 0.28;
    camera.position.y = -mouse.sy * 0.18;
    camera.lookAt(0, 0, 0);
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
      const light = mode === "light";
      themeTarget = light ? 1 : 0;
      scene.environment = light ? lightEnv : darkEnv;
      const blending = light ? THREE.NormalBlending : THREE.AdditiveBlending;
      if (points.material.blending !== blending) {
        points.material.blending = blending;
        points.material.needsUpdate = true;
      }
      if (reduce) themeMix = themeTarget;
    },
  };
}
