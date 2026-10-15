// The hero's hologram Lumi: a glowing head that talks, built with Three.js.
// Falls back to a static SVG face when WebGL is missing or motion is reduced.
import * as THREE from "../vendor/three/three.module.min.js";

const LINES = [
  "Hi! I'm Lumi. Scan your badge and ask me anything.",
  "Your next session is Voice Interfaces 101, in the Maple Room.",
  "Turn left at the front doors. It's the last door on the right.",
  "I run on the computer you already have.",
];

// A made-up speech envelope: syllable bursts with short gaps, 0..1.
function envelopeAt(t) {
  const syllable = Math.max(0, Math.sin(t * 13.0)) * (0.55 + 0.45 * Math.sin(t * 3.1));
  const word = Math.sin(t * 2.3) > -0.65 ? 1 : 0.15;
  return Math.min(1, syllable * word * 1.15);
}

function svgFallback(stage) {
  stage.insertAdjacentHTML("afterbegin", `
    <svg viewBox="0 0 200 200" role="img" aria-label="Lumi, a glowing round hologram face">
      <defs>
        <radialGradient id="fh" cx="50%" cy="40%" r="60%"><stop offset="0" stop-color="#1b3462"/><stop offset="1" stop-color="#070d1c"/></radialGradient>
        <linearGradient id="fr" x1="0" x2="1"><stop offset="0" stop-color="#3ef0ff"/><stop offset="1" stop-color="#9a6bff"/></linearGradient>
      </defs>
      <circle cx="100" cy="96" r="70" fill="url(#fh)" stroke="url(#fr)" stroke-width="3"/>
      <rect x="70" y="72" width="12" height="22" rx="6" fill="#3ef0ff"/>
      <rect x="118" y="72" width="12" height="22" rx="6" fill="#3ef0ff"/>
      <rect x="78" y="118" width="44" height="7" rx="3.5" fill="url(#fr)"/>
    </svg>`);
}

function captions(el, talking) {
  // Types each line while the avatar "talks", then pauses.
  let line = 0, chars = 0, pause = 0;
  return (dt) => {
    if (!el) return true;
    if (pause > 0) { pause -= dt; return false; }
    const text = LINES[line];
    chars = Math.min(text.length, chars + dt * 34);
    el.textContent = text.slice(0, Math.floor(chars));
    if (chars >= text.length) { pause = 1.6; chars = 0; line = (line + 1) % LINES.length; return false; }
    return talking;
  };
}

export function mountAvatar(stage, caption) {
  const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const probe = document.createElement("canvas");
  const gl = probe.getContext("webgl2") || probe.getContext("webgl");
  if (reduced || !gl) {
    svgFallback(stage);
    if (caption) caption.textContent = LINES[0];
    return;
  }

  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
  stage.prepend(renderer.domElement);
  renderer.domElement.setAttribute("aria-label", "Lumi, a glowing hologram head that talks");
  renderer.domElement.setAttribute("role", "img");

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(32, 1, 0.1, 100);
  camera.position.set(0, 0, 7.2);

  const rig = new THREE.Group();
  scene.add(rig);

  // Head: a fresnel-lit shell with moving scanlines, cyan at the top fading to violet below.
  const shell = new THREE.ShaderMaterial({
    transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
    uniforms: { uTime: { value: 0 }, uA: { value: new THREE.Color("#3ef0ff") }, uB: { value: new THREE.Color("#9a6bff") } },
    vertexShader: `
      varying vec3 vN; varying vec3 vV; varying vec3 vP;
      void main() {
        vec4 wp = modelMatrix * vec4(position, 1.0);
        vP = position; vN = normalize(normalMatrix * normal);
        vV = normalize(-(viewMatrix * wp).xyz);
        gl_Position = projectionMatrix * viewMatrix * wp;
      }`,
    fragmentShader: `
      uniform float uTime; uniform vec3 uA; uniform vec3 uB;
      varying vec3 vN; varying vec3 vV; varying vec3 vP;
      void main() {
        float fres = pow(1.0 - abs(dot(vN, vV)), 2.4);
        float scan = 0.55 + 0.45 * sin(vP.y * 70.0 - uTime * 3.0);
        float sweep = smoothstep(0.0, 0.06, 0.06 - abs(fract(vP.y * 0.35 - uTime * 0.18) - 0.5));
        vec3 col = mix(uB, uA, smoothstep(-1.0, 1.0, vP.y));
        float a = fres * 0.95 + 0.06 * scan + sweep * 0.5;
        gl_FragColor = vec4(col * (0.6 + 0.6 * fres), a);
      }`,
  });
  const head = new THREE.Mesh(new THREE.SphereGeometry(1.45, 96, 96), shell);
  head.scale.set(1, 1.04, 0.96);
  rig.add(head);

  const core = new THREE.Mesh(new THREE.SphereGeometry(1.32, 64, 64),
    new THREE.MeshBasicMaterial({ color: "#0a1630", transparent: true, opacity: 0.55 }));
  rig.add(core);

  const glow = (color) => new THREE.MeshBasicMaterial({ color, transparent: true, opacity: 0.95, blending: THREE.AdditiveBlending });
  const eyeGeo = new THREE.CapsuleGeometry(0.11, 0.26, 8, 16);
  const eyes = [-0.48, 0.48].map((x) => {
    const eye = new THREE.Mesh(eyeGeo, glow("#7ff7ff"));
    eye.position.set(x, 0.28, 1.36);
    rig.add(eye);
    return eye;
  });
  const mouth = new THREE.Mesh(new THREE.CapsuleGeometry(0.07, 0.62, 8, 16), glow("#b38cff"));
  mouth.rotation.z = Math.PI / 2;
  mouth.position.set(0, -0.48, 1.36);
  rig.add(mouth);

  const rings = [[2.05, 0.012, "#3ef0ff", 1.2], [2.35, 0.008, "#9a6bff", -0.8]].map(([r, t, c, s]) => {
    const ring = new THREE.Mesh(new THREE.TorusGeometry(r, t, 8, 160),
      new THREE.MeshBasicMaterial({ color: c, transparent: true, opacity: 0.55, blending: THREE.AdditiveBlending }));
    ring.rotation.x = Math.PI / 2.25;
    ring.userData.speed = s;
    scene.add(ring);
    return ring;
  });

  const count = 700, pos = new Float32Array(count * 3);
  for (let i = 0; i < count; i++) {
    const r = 2.4 + Math.random() * 1.8, a = Math.random() * Math.PI * 2, y = (Math.random() - 0.5) * 3.2;
    pos.set([Math.cos(a) * r, y, Math.sin(a) * r], i * 3);
  }
  const dust = new THREE.Points(new THREE.BufferGeometry().setAttribute("position", new THREE.BufferAttribute(pos, 3)),
    new THREE.PointsMaterial({ color: "#7ff7ff", size: 0.025, transparent: true, opacity: 0.7, blending: THREE.AdditiveBlending }));
  scene.add(dust);

  let pointerX = 0, pointerY = 0;
  addEventListener("pointermove", (e) => {
    pointerX = (e.clientX / innerWidth - 0.5) * 2;
    pointerY = (e.clientY / innerHeight - 0.5) * 2;
  }, { passive: true });

  function resize() {
    const { width, height } = stage.getBoundingClientRect();
    renderer.setSize(width, height, false);
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
  }
  new ResizeObserver(resize).observe(stage);
  resize();

  const step = captions(caption, true);
  let visible = true;
  new IntersectionObserver(([e]) => { visible = e.isIntersecting; }).observe(stage);

  const clock = new THREE.Clock();
  let blink = 0, nextBlink = 2.5, open = 0;
  renderer.setAnimationLoop(() => {
    const dt = Math.min(clock.getDelta(), 0.05), t = clock.elapsedTime;
    if (!visible) return;
    const talking = step(dt);
    const target = talking ? envelopeAt(t) : 0;
    open += (target - open) * Math.min(1, dt * 22);
    mouth.scale.set(1 + open * 0.15, 1 + open * 2.6, 1);
    nextBlink -= dt;
    if (nextBlink < 0) { blink = 0.14; nextBlink = 2 + Math.random() * 3; }
    blink = Math.max(0, blink - dt);
    eyes.forEach((e) => { e.scale.y = blink > 0 ? 0.12 : 1; });
    shell.uniforms.uTime.value = t;
    rig.rotation.y += ((pointerX * 0.35 + Math.sin(t * 0.4) * 0.12) - rig.rotation.y) * 0.05;
    rig.rotation.x += ((pointerY * 0.18) - rig.rotation.x) * 0.05;
    rig.position.y = Math.sin(t * 1.1) * 0.06;
    rings.forEach((r) => { r.rotation.z += dt * 0.25 * r.userData.speed; });
    dust.rotation.y += dt * 0.04;
    renderer.render(scene, camera);
  });
}
