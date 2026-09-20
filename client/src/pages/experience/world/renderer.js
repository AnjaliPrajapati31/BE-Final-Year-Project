import * as THREE from 'three';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';
import { ShaderPass } from 'three/addons/postprocessing/ShaderPass.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';
import { FXAAShader } from 'three/addons/shaders/FXAAShader.js';
import { CAMERA_KEYS, HERO_PARCEL, SUN } from './landscape';
import { createEnvironment, createTrees } from './environment';
import { createRice } from './rice';
import { createFarmer, createBirds } from './life';
import { gradeShader } from './shaders';

function parcelCenter(parcel) {
  return parcel.polygon.reduce((center, [x, z]) => center.add(new THREE.Vector3(x, 0, z)), new THREE.Vector3()).multiplyScalar(1 / parcel.polygon.length);
}

function createStoryLayers(scene, parcel) {
  const center = parcelCenter(parcel);
  const group = new THREE.Group();
  const materials = [];
  const material = (color, opacity = 0) => {
    const value = new THREE.MeshBasicMaterial({ color, transparent: true, opacity, depthWrite: false, side: THREE.DoubleSide });
    materials.push(value); return value;
  };
  const scan = new THREE.Mesh(new THREE.RingGeometry(4.5, 4.62, 64), material('#dcecc3'));
  scan.rotation.x = -Math.PI / 2; scan.position.copy(center).setY(.52); group.add(scan);

  const growthMaterial = new THREE.LineBasicMaterial({ color: '#d8e5ae', transparent: true, opacity: 0, depthWrite: false });
  const growthPoints = [
    new THREE.Vector3(-8, .45, 3), new THREE.Vector3(-4, 1.15, 1),
    new THREE.Vector3(0, 2.1, 0), new THREE.Vector3(4, 3.25, -1), new THREE.Vector3(8, 4.55, -3),
  ].map(point => point.add(center));
  const growth = new THREE.Line(new THREE.BufferGeometry().setFromPoints(growthPoints), growthMaterial);
  const growthNodes = new THREE.Points(
    new THREE.BufferGeometry().setFromPoints(growthPoints),
    new THREE.PointsMaterial({ color: '#edf0bf', size: .42, transparent: true, opacity: 0, depthWrite: false }),
  );
  group.add(growth, growthNodes);

  const stress = new THREE.Mesh(new THREE.CircleGeometry(5.8, 48), material('#d7a85a'));
  stress.rotation.x = -Math.PI / 2; stress.position.copy(center).add(new THREE.Vector3(-3, .28, 1)); group.add(stress);
  const balance = new THREE.Mesh(new THREE.RingGeometry(7.5, 8.15, 64, 1, 0, Math.PI * 1.55), material('#93c6c0'));
  balance.rotation.x = -Math.PI / 2; balance.position.copy(center).setY(.55); group.add(balance);
  const advice = new THREE.Mesh(new THREE.ConeGeometry(.8, 2.8, 5), material('#f2deb0'));
  advice.position.copy(center).add(new THREE.Vector3(0, 2.1, 0)); group.add(advice);
  const rainGeometry = new THREE.BufferGeometry();
  const rainPositions = [];
  for (let i = 0; i < 72; i++) {
    const a = i * 2.399, radius = 3 + (i % 9) * 1.15;
    rainPositions.push(center.x + Math.cos(a) * radius, 4 + (i % 8) * 1.1, center.z + Math.sin(a) * radius);
  }
  rainGeometry.setAttribute('position', new THREE.Float32BufferAttribute(rainPositions, 3));
  const rainMaterial = new THREE.PointsMaterial({ color: '#c7e5df', size: .16, transparent: true, opacity: 0, depthWrite: false });
  materials.push(rainMaterial); group.add(new THREE.Points(rainGeometry, rainMaterial));

  const evidenceMaterial = new THREE.LineBasicMaterial({ color: '#efe4bd', transparent: true, opacity: 0, depthWrite: false });
  const evidencePoints = Array.from({ length: 6 }, (_, index) => center.clone().add(new THREE.Vector3(-9 + index * 3.6, 2.3 + (index % 2) * .35, -5)));
  const evidence = new THREE.Line(new THREE.BufferGeometry().setFromPoints(evidencePoints), evidenceMaterial);
  const evidenceNodes = new THREE.Points(
    new THREE.BufferGeometry().setFromPoints(evidencePoints),
    new THREE.PointsMaterial({ color: '#f4deb0', size: .34, transparent: true, opacity: 0, depthWrite: false }),
  );
  group.add(evidence, evidenceNodes);
  scene.add(group);
  return { group, materials, scan, growth, growthNodes, stress, balance, advice, rain: group.children[6], evidence, evidenceNodes };
}

function pulse(progress, center, width = .16) {
  return Math.max(0, 1 - Math.abs(progress - center) / width);
}

function updateStoryLayers(layers, progress) {
  layers.scan.material.opacity = pulse(progress, .35, .2) * .78;
  layers.scan.scale.setScalar(.9 + progress * .55);
}


export function createLandscape(host, { reducedMotion, onReady, onError, onQuality, onProgress }) {
  let disposed = false, frame = 0, running = true;
  let lastTime = 0, elapsed = 0, sampleTime = 0, sampleFrames = 0, warmed = 0;
  let quality = 'high', waterPhase = 0;
  let inspectionView = null;
  const compact = matchMedia('(max-width: 760px), (pointer: coarse)').matches;
  const motion = { progress: 0, wind: 1, parallaxX: 0, parallaxY: 0 };
  const pointer = new THREE.Vector2(), pointerTarget = new THREE.Vector2();
  const scene = new THREE.Scene();
  const fogColor = new THREE.Color(.42, .49, .40);
  scene.fog = new THREE.FogExp2(fogColor, .0031);
  const camera = new THREE.PerspectiveCamera(52, 1, .06, 1100);
  camera.position.set(...CAMERA_KEYS[0].position);
  const renderer = new THREE.WebGLRenderer({ antialias: false, alpha: false, powerPreference: 'high-performance' });
  renderer.setClearColor('#788577');
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = .92;
  renderer.setPixelRatio(Math.min(devicePixelRatio, compact ? 1 : 1.5));
  renderer.info.autoReset = false;
  host.appendChild(renderer.domElement);
  renderer.domElement.setAttribute('aria-label', 'Live rendered Cauvery paddy landscape');
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

  const positions = new THREE.CatmullRomCurve3(CAMERA_KEYS.map(k => new THREE.Vector3(...k.position)), false, 'centripetal');
  const targets = new THREE.CatmullRomCurve3(CAMERA_KEYS.map(k => new THREE.Vector3(...k.target)), false, 'centripetal');
  const cameraPoint = new THREE.Vector3(), targetPoint = new THREE.Vector3();
  const heroPoints = HERO_PARCEL.polygon.map(([x, z]) => new THREE.Vector3(x, .34, z));
  const marker = new THREE.LineLoop(new THREE.BufferGeometry().setFromPoints(heroPoints), new THREE.LineBasicMaterial({ color: '#f3e5ad', transparent: true, opacity: 0 }));
  const storyLayers = createStoryLayers(scene, HERO_PARCEL);
  scene.add(marker);

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
    const p = motion.progress;
    // Parameter interpolation deliberately lingers near the ground before climbing.
    positions.getPoint(p, cameraPoint); targets.getPoint(p, targetPoint);
    pointer.lerp(pointerTarget, .035);
    const parallax = reducedMotion ? 0 : (1 - p) * .25;
    cameraPoint.x += pointer.x * parallax;
    cameraPoint.y += pointer.y * parallax * .32;
    camera.position.copy(cameraPoint);
    camera.lookAt(targetPoint);
    if (inspectionView === 'overhead') {
      const center = parcelCenter(HERO_PARCEL);
      camera.position.set(center.x, 175, center.z);
      camera.lookAt(center.x, 0, center.z);
    }
    const fov = 52 - p * 6;
    if (Math.abs(camera.fov - fov) > .01) { camera.fov = fov; camera.updateProjectionMatrix(); }
    shared.uFogDensity.value = .0031 * (1 - p * .62);
    scene.fog.density = shared.uFogDensity.value;
    // At altitude, individual plants resolve into field colour while the real
    // bund and canal geometry stays visible for the selection composition.
    shared.uFade.value = 1 - THREE.MathUtils.smoothstep(p, .64, .93) * .68;
    marker.material.opacity = THREE.MathUtils.smoothstep(p, .035, .15) * (.34 + THREE.MathUtils.smoothstep(p, .84, .98) * .56);
    updateStoryLayers(storyLayers, p);
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
    const delta = lastTime ? Math.min((now - lastTime) / 1000, .1) : 0;
    lastTime = now; warmed += delta;
    if (!reducedMotion) elapsed += delta;
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
    if (waterPhase % 2 || motion.progress > .65) environment.water.onBeforeRender = () => {};
    try {
      composer.render(delta);
    } catch (error) {
      onError?.(error); running = false; return;
    } finally {
      environment.water.onBeforeRender = reflectedRender;
    }
    if (warmed > 2) {
      sampleFrames++; sampleTime += delta;
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
    setStoryProgress(value) {
      motion.progress = THREE.MathUtils.clamp(value, 0, 1);
      onProgress?.(motion.progress);
      updateCamera();
    },
    setQuality(value) { if (value === 'light') lowerQuality(24); },
    setAmbientMotion(value) { motion.wind = value ? 1 : 0; reducedMotion = !value; },
    setInspectionView(value) { inspectionView = value; updateCamera(); },
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
