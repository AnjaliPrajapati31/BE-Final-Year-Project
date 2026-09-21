import * as THREE from 'three';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';
import { ShaderPass } from 'three/addons/postprocessing/ShaderPass.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';
import { FXAAShader } from 'three/addons/shaders/FXAAShader.js';
import { HOME_CAMERA, SUN } from './landscape';
import { createEnvironment, createTrees } from './environment';
import { createRice } from './rice';
import { createFarmer, createBirds } from './life';
import { gradeShader } from './shaders';

export function createLandscape(host, { reducedMotion, onReady, onError, onQuality }) {
  let disposed = false, frame = 0, running = true;
  let lastTime = 0, elapsed = 0, sampleTime = 0, sampleFrames = 0, warmed = 0;
  let quality = 'high', waterPhase = 0;
  let ambientEnabled = true;
  const compact = matchMedia('(max-width: 760px), (pointer: coarse)').matches;
  const motion = { wind: 1 };
  const pointer = new THREE.Vector2(), pointerTarget = new THREE.Vector2();
  const scene = new THREE.Scene();
  const fogColor = new THREE.Color(.42, .49, .40);
  scene.fog = new THREE.FogExp2(fogColor, .0031);
  const camera = new THREE.PerspectiveCamera(HOME_CAMERA.fov, 1, .06, 1100);
  camera.position.set(...HOME_CAMERA.position);
  const renderer = new THREE.WebGLRenderer({ antialias: false, alpha: false, powerPreference: 'high-performance' });
  renderer.setClearColor('#788577');
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.02;
  renderer.setPixelRatio(Math.min(devicePixelRatio, compact ? 1 : 1.5));
  renderer.info.autoReset = false;
  host.appendChild(renderer.domElement);
  renderer.domElement.setAttribute('aria-label', 'Illustrative living paddy field');
  renderer.domElement.setAttribute('role', 'img');

  const shared = {
    uTime: { value: 0 }, uWind: { value: 1 }, uFade: { value: 1 },
    uSun: { value: new THREE.Vector3(...SUN).normalize() },
    uFog: { value: fogColor }, uFogDensity: { value: .0031 },
  };
  const hemisphere = new THREE.HemisphereLight('#cad8d4', '#4d5030', 1.15);
  const sun = new THREE.DirectionalLight('#ffe5b2', 2.05);
  sun.position.copy(shared.uSun.value).multiplyScalar(70);
  scene.add(hemisphere, sun);

  const environment = createEnvironment(scene, shared, compact);
  const rice = createRice(scene, shared, compact);
  const trees = createTrees(scene, compact);
  const life = createFarmer(scene);
  const birds = createBirds(scene);



  const composer = new EffectComposer(renderer);
  const renderPass = new RenderPass(scene, camera);
  const bloom = new UnrealBloomPass(new THREE.Vector2(1, 1), .07, .42, 1.3);
  const output = new OutputPass();
  const fxaa = new ShaderPass(FXAAShader);
  const grade = new ShaderPass(gradeShader);
  composer.addPass(renderPass); composer.addPass(bloom); composer.addPass(grade);
  composer.addPass(fxaa); composer.addPass(output);
  if (compact) bloom.enabled = false;

  function resize() {
    if (disposed) return;
    const { width, height } = host.getBoundingClientRect();
    if (!width || !height) return;
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
    renderer.setSize(width, height, false);
    composer.setSize(width, height);
    const ratio = renderer.getPixelRatio();
    fxaa.material.uniforms.resolution.value.set(1 / (width * ratio), 1 / (height * ratio));
  }
  const observer = new ResizeObserver(resize); observer.observe(host); resize();

  function updateCamera() {
    pointer.lerp(pointerTarget, .035);
    camera.position.set(...HOME_CAMERA.position);
    if (!reducedMotion && ambientEnabled) { camera.position.x += pointer.x * .12; camera.position.y += pointer.y * .035; }
    camera.lookAt(...HOME_CAMERA.target);
  }

  function lowerQuality(fps) {
    if (quality === 'high') {
      quality = 'balanced'; bloom.enabled = false;
      renderer.setPixelRatio(1); composer.setPixelRatio(1); resize();
    } else if (quality === 'balanced') {
      quality = 'light';
      rice.meshes.forEach(mesh => { mesh.geometry.instanceCount = Math.floor(mesh.geometry.instanceCount * .68); });
      renderer.setPixelRatio(.8); composer.setPixelRatio(.8); resize();
    }
    onQuality?.({ quality, fps: Math.round(fps), plants: rice.plantCount });
  }

  function render(now) {
    if (disposed || !running) return;
    const sampleDelta = lastTime ? (now - lastTime) / 1000 : 0;
    const delta = Math.min(sampleDelta, .1);
    lastTime = now; warmed += delta;
    if (!reducedMotion && ambientEnabled) elapsed += delta;
    shared.uTime.value = elapsed;
    shared.uWind.value = reducedMotion ? 0 : motion.wind;
    environment.water.material.uniforms.time.value = elapsed * .27;
    life.farmer.rotation.z = reducedMotion ? 0 : Math.sin(elapsed * .8) * .008;
    life.towel.rotation.x = reducedMotion ? 0 : Math.sin(elapsed * 1.6) * .06;
    trees.update(elapsed, reducedMotion);
    birds.forEach(({ bird, left, right, x, y, z, phase }) => {
      bird.position.set(x + Math.sin(elapsed * .032 + phase) * 14, y + Math.sin(elapsed * .32 + phase) * .5, z);
      left.rotation.z = reducedMotion ? .12 : Math.sin(elapsed * 3 + phase) * .38;
      right.rotation.z = -left.rotation.z;
    });
    updateCamera();
    grade.uniforms.uTime.value = elapsed * .07;
    renderer.info.reset();
    // Reflection is refreshed every other frame; the water's own ripple stays smooth.
    waterPhase++;
    const reflectedRender = environment.water.onBeforeRender;
    if (waterPhase % 2) environment.water.onBeforeRender = () => {};
    try {
      composer.render(delta);
    } catch (error) {
      onError?.(error); running = false; return;
    } finally {
      environment.water.onBeforeRender = reflectedRender;
    }
    if (warmed > 2) {
      sampleFrames++; sampleTime += sampleDelta;
      if (sampleTime > 4) {
        const fps = sampleFrames / sampleTime;
        host.dataset.fps = fps.toFixed(1);
        host.dataset.triangles = String(renderer.info.render.triangles);
        host.dataset.drawCalls = String(renderer.info.render.calls);
        if (fps < 29 && quality !== 'light') lowerQuality(fps);
        sampleTime = 0; sampleFrames = 0;
      }
    }
    frame = requestAnimationFrame(render);
  }

  function pointerMove(event) {
    if (event.pointerType !== 'mouse' || reducedMotion) return;
    const bounds = host.getBoundingClientRect();
    pointerTarget.set((event.clientX - bounds.left) / bounds.width * 2 - 1, -((event.clientY - bounds.top) / bounds.height * 2 - 1));
  }
  function visibility() {
    running = !document.hidden;
    if (running) { lastTime = 0; frame = requestAnimationFrame(render); }
    else cancelAnimationFrame(frame);
  }
  function contextLost(event) {
    event.preventDefault(); running = false; cancelAnimationFrame(frame);
    onError?.(new Error('Graphics context lost'));
  }
  window.addEventListener('pointermove', pointerMove, { passive: true });
  document.addEventListener('visibilitychange', visibility);
  renderer.domElement.addEventListener('webglcontextlost', contextLost);

  const controller = {

    setQuality(value) { if (value === 'light') lowerQuality(24); },
    setAmbientMotion(value) { ambientEnabled = value; motion.wind = value ? 1 : 0; },
    resize,
    setWind(value) { motion.wind = value; },
    setReducedMotion(value) { reducedMotion = value; },
    dispose() {
      disposed = true; cancelAnimationFrame(frame);
      observer.disconnect();
      window.removeEventListener('pointermove', pointerMove);
      document.removeEventListener('visibilitychange', visibility);
      renderer.domElement.removeEventListener('webglcontextlost', contextLost);
      const geometries = new Set(), materials = new Set(), textures = new Set();
      scene.traverse(object => {
        if (object.geometry) geometries.add(object.geometry);
        if (object.material) {
          (Array.isArray(object.material) ? object.material : [object.material]).forEach(material => {
            materials.add(material);
            Object.values(material.uniforms || {}).forEach(uniform => { if (uniform.value?.isTexture) textures.add(uniform.value); });
          });
        }
      });
      geometries.forEach(g => g.dispose()); materials.forEach(m => m.dispose()); textures.forEach(t => t.dispose());
      composer.passes.forEach(pass => pass.dispose?.()); composer.dispose();
      environment.normalTexture.dispose();
      renderer.dispose(); renderer.forceContextLoss(); renderer.domElement.remove();
    },
  };
  frame = requestAnimationFrame((now) => {
    if (disposed) return;
    render(now); host.dataset.plants = String(rice.plantCount);
    onReady?.();
  });
  return controller;
}
