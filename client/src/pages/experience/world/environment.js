import * as THREE from 'three';
import { Water } from 'three/addons/objects/Water.js';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';
import { PARCELS, SUN, VALLEY, canalCenter, randomSequence, terrainHeight } from './landscape';
import { skyVertex, skyFragment, groundVertex, groundFragment, parcelVertex, parcelFragment } from './shaders';

function waterNormals() {
  const size = 128, pixels = new Uint8Array(size * size * 4);
  for (let y = 0; y < size; y++) for (let x = 0; x < size; x++) {
    const u = x / size * Math.PI * 2, v = y / size * Math.PI * 2;
    const n = new THREE.Vector3(Math.cos(u * 4 + v * 2) * .16, Math.sin(v * 6 + u) * .14, 1).normalize();
    const i = (y * size + x) * 4;
    pixels[i] = (n.x * .5 + .5) * 255; pixels[i + 1] = (n.y * .5 + .5) * 255;
    pixels[i + 2] = (n.z * .5 + .5) * 255; pixels[i + 3] = 255;
  }
  const texture = new THREE.DataTexture(pixels, size, size);
  texture.wrapS = texture.wrapT = THREE.RepeatWrapping;
  texture.magFilter = texture.minFilter = THREE.LinearFilter; texture.needsUpdate = true;
  return texture;
}

function parcelSurface(parcel) {
  const shape = new THREE.Shape();
  parcel.polygon.forEach(([x, z], index) => index ? shape.lineTo(x, -z) : shape.moveTo(x, -z));
  shape.closePath();
  const geometry = new THREE.ShapeGeometry(shape);
  geometry.rotateX(-Math.PI / 2);
  const position = geometry.attributes.position;
  for (let i = 0; i < position.count; i++) {
    position.setY(i, terrainHeight(position.getX(i), position.getZ(i)) + .012);
  }
  geometry.computeVertexNormals();
  return geometry;
}

function edgeGeometries(a, b) {
  const dx = b[0] - a[0], dz = b[1] - a[1], length = Math.hypot(dx, dz);
  const angle = Math.atan2(dz, dx);
  const bottom = .82, top = .46, height = .16, half = length * .5;
  const vertices = new Float32Array([
    -half, 0, -bottom / 2, half, 0, -bottom / 2, half, 0, bottom / 2, -half, 0, bottom / 2,
    -half, height, -top / 2, half, height, -top / 2, half, height, top / 2, -half, height, top / 2,
  ]);
  const indices = [0,1,2,0,2,3,4,6,5,4,7,6,0,4,5,0,5,1,1,5,6,1,6,2,2,6,7,2,7,3,3,7,4,3,4,0];
  const bund = new THREE.BufferGeometry();
  bund.setAttribute('position', new THREE.BufferAttribute(vertices, 3));
  bund.setIndex(indices); bund.computeVertexNormals();
  const matrix = new THREE.Matrix4().compose(
    new THREE.Vector3((a[0] + b[0]) / 2, terrainHeight((a[0] + b[0]) / 2, (a[1] + b[1]) / 2), (a[1] + b[1]) / 2),
    new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 1, 0), -angle),
    new THREE.Vector3(1, 1, 1),
  );
  bund.applyMatrix4(matrix);
  matrix.setPosition((a[0] + b[0]) / 2, terrainHeight((a[0] + b[0]) / 2, (a[1] + b[1]) / 2) + height + .008, (a[1] + b[1]) / 2);
  const cap = new THREE.BoxGeometry(length, .025, top * .88).applyMatrix4(matrix);
  return [bund, cap];
}

function createParcelLandscape(scene, shared) {
  const group = new THREE.Group();
  const edges = new Map();
  const surfaces = [];
  PARCELS.forEach(parcel => {
    const color = new THREE.Color().setHSL(.19 + parcel.variation * .075, .56, .145 + parcel.variation * .095);
    const geometry = parcelSurface(parcel);
    const colors = new Float32Array(geometry.attributes.position.count * 3);
    for (let i = 0; i < geometry.attributes.position.count; i++) color.toArray(colors, i * 3);
    geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));
    surfaces.push(geometry);
    parcel.polygon.forEach((a, index) => {
      const b = parcel.polygon[(index + 1) % parcel.polygon.length];
      const first = `${a[0].toFixed(3)},${a[1].toFixed(3)}`, second = `${b[0].toFixed(3)},${b[1].toFixed(3)}`;
      const key = first < second ? `${first}|${second}` : `${second}|${first}`;
      if (!edges.has(key)) edges.set(key, [a, b]);
    });
  });
  const surfaceGeometry = mergeGeometries(surfaces, false);
  surfaces.forEach(geometry => geometry.dispose());
  const surface = new THREE.Mesh(surfaceGeometry, new THREE.ShaderMaterial({
    uniforms: { uSun: shared.uSun, uFog: shared.uFog, uFogDensity: shared.uFogDensity },
    vertexShader: parcelVertex,
    fragmentShader: parcelFragment,
    polygonOffset: true,
    polygonOffsetFactor: -1,
  }));
  surface.name = 'Connected paddy parcel surfaces'; group.add(surface);
  const earth = new THREE.MeshStandardMaterial({ color: '#756744', roughness: 1 });
  const grass = new THREE.MeshStandardMaterial({ color: '#69743d', roughness: 1 });
  const earthGeometry = [], grassGeometry = [];
  edges.forEach(([a, b]) => {
    const [bund, cap] = edgeGeometries(a, b); earthGeometry.push(bund); grassGeometry.push(cap);
  });
  const mergedEarth = mergeGeometries(earthGeometry, false), mergedGrass = mergeGeometries(grassGeometry, false);
  earthGeometry.forEach(geometry => geometry.dispose()); grassGeometry.forEach(geometry => geometry.dispose());
  group.add(new THREE.Mesh(mergedEarth, earth), new THREE.Mesh(mergedGrass, grass));
  scene.add(group);
  return group;
}

function createTerrain(scene, shared) {
  const geometry = new THREE.PlaneGeometry(1000, 1000, 120, 120);
  const position = geometry.attributes.position;
  for (let i = 0; i < position.count; i++) {
    const x = position.getX(i), z = -position.getY(i);
    position.setZ(i, terrainHeight(x, z));
  }
  geometry.computeVertexNormals();
  const terrain = new THREE.Mesh(geometry, new THREE.ShaderMaterial({ uniforms: shared, vertexShader: groundVertex, fragmentShader: groundFragment }));
  terrain.rotation.x = -Math.PI / 2; terrain.position.y = -.06; scene.add(terrain);
  return terrain;
}

function createCanal(scene, compact) {
  const normalTexture = waterNormals();
  const waterGeometry = new THREE.PlaneGeometry(4.6, 330, 1, 120);
  const positions = waterGeometry.attributes.position;
  for (let i = 0; i < positions.count; i++) {
    const z = -positions.getY(i);
    positions.setX(i, positions.getX(i) + canalCenter(z));
  }
  waterGeometry.computeVertexNormals();
  const water = new Water(waterGeometry, {
    textureWidth: compact ? 256 : 512, textureHeight: compact ? 256 : 512,
    waterNormals: normalTexture, sunDirection: new THREE.Vector3(...SUN).normalize(),
    sunColor: '#f6deb1', waterColor: '#244f43', distortionScale: .18, fog: true,
  });
  water.rotation.x = -Math.PI / 2; water.position.y = -.045;
  water.material.uniforms.size.value = 14; scene.add(water);
  const bankGeometry = [], bankMaterial = new THREE.MeshStandardMaterial({ color: '#766b45', roughness: 1 });
  for (const side of [-1, 1]) {
    const points = [];
    for (let i = 0; i <= 64; i++) {
      const z = -165 + i / 64 * 330;
      points.push(new THREE.Vector3(canalCenter(z) + side * 2.85, .055, z));
    }
    const curve = new THREE.CatmullRomCurve3(points);
    const bank = new THREE.Mesh(new THREE.TubeGeometry(curve, 128, .34, 7, false), bankMaterial);
    bank.scale.y = .62; scene.add(bank); bankGeometry.push(bank);
  }
  return { water, normalTexture, banks: bankGeometry };
}

export function createEnvironment(scene, shared, compact) {
  const sky = new THREE.Mesh(new THREE.SphereGeometry(550, 40, 22), new THREE.ShaderMaterial({
    uniforms: shared, vertexShader: skyVertex, fragmentShader: skyFragment, side: THREE.BackSide, depthWrite: false,
  }));
  sky.frustumCulled = false; sky.renderOrder = -100; scene.add(sky);
  createTerrain(scene, shared);
  const parcels = createParcelLandscape(scene, shared);
  const water = createCanal(scene, compact);
  return { ...water, parcels };
}

function palmGeometry() {
  const positions = [];
  for (let frond = 0; frond < 12; frond++) {
    const angle = frond * 2.399;
    for (let section = 0; section < 10; section++) {
      const a = section / 10, b = (section + 1) / 10;
      const point = t => [Math.cos(angle) * t * 3.15, Math.sin(t * Math.PI) * .68 - t * t * 1.32, Math.sin(angle) * t * 3.15];
      const width = t => .015 + Math.pow(Math.sin(Math.PI * t), .58) * .14;
      const p = point(a), q = point(b), wa = width(a), wb = width(b);
      const px = -Math.sin(angle) * wa, pz = Math.cos(angle) * wa;
      const qx = -Math.sin(angle) * wb, qz = Math.cos(angle) * wb;
      const pl = [p[0] + px, p[1], p[2] + pz], pr = [p[0] - px, p[1], p[2] - pz];
      const ql = [q[0] + qx, q[1], q[2] + qz], qr = [q[0] - qx, q[1], q[2] - qz];
      positions.push(...pl, ...ql, ...pr, ...pr, ...ql, ...qr);
    }
  }
  const geometry = new THREE.BufferGeometry(); geometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
  geometry.computeVertexNormals(); return geometry;
}

export function createTrees(scene, compact) {
  const rng = randomSequence(4141), clusterCount = compact ? 9 : 13, entries = [];
  for (let cluster = 0; cluster < clusterCount; cluster++) {
    const baseZ = THREE.MathUtils.lerp(VALLEY.minZ + 24, -48, cluster / Math.max(1, clusterCount - 1));
    const members = cluster % 3 === 0 ? 2 : 3;
    for (let member = 0; member < members; member++) {
      const bankSide = (cluster + member) % 2 ? -1 : 1;
      const z = baseZ + (rng() - .5) * 19;
      const outerMember = member === 2 && cluster % 2 === 0;
      const x = canalCenter(z) + bankSide * ((outerMember ? 23 : 8.5) + rng() * (outerMember ? 13 : 9));
      entries.push({
        x, z,
        scale: .68 + rng() * .44,
        rotation: rng() * Math.PI * 2,
        phase: rng() * Math.PI * 2,
      });
    }
  }
  const count = entries.length;
  const fronds = palmGeometry(), trunk = new THREE.CylinderGeometry(.09, .22, 6.2, 8);
  const leafMaterial = new THREE.MeshStandardMaterial({ color: '#314922', roughness: .9, side: THREE.DoubleSide });
  const trunkMaterial = new THREE.MeshStandardMaterial({ color: '#5b5035', roughness: 1 });
  const stems = new THREE.InstancedMesh(trunk, trunkMaterial, count);
  const crowns = new THREE.InstancedMesh(fronds, leafMaterial, count);
  const dummy = new THREE.Object3D();
  entries.forEach((entry, index) => {
    dummy.position.set(entry.x, 3.1 * entry.scale, entry.z);
    dummy.rotation.set(0, entry.rotation, 0); dummy.scale.setScalar(entry.scale);
    dummy.updateMatrix(); stems.setMatrixAt(index, dummy.matrix);
  });
  stems.castShadow = false; crowns.castShadow = false;
  scene.add(stems, crowns);
  // Broken, layered foliage along the far field margin restores horizon depth.
  const foliageGeometry = new THREE.IcosahedronGeometry(1, 1);
  const foliageMaterial = new THREE.MeshStandardMaterial({ color: '#526843', roughness: 1, flatShading: false });
  const foliage = new THREE.InstancedMesh(foliageGeometry, foliageMaterial, compact ? 90 : 156);
  for (let i = 0; i < foliage.count; i++) {
    const cluster = Math.floor(i / 3);
    const x = -260 + cluster * (520 / (foliage.count / 3)) + (rng() - .5) * 8;
    const z = -291 - rng() * 24;
    const height = 3.5 + rng() * 4;
    dummy.position.set(x, terrainHeight(x, z) + height * .6, z);
    dummy.rotation.set(rng() * .25, rng() * 6.28, rng() * .2);
    dummy.scale.set(3 + rng() * 3.5, height, 2.5 + rng() * 3);
    dummy.updateMatrix(); foliage.setMatrixAt(i, dummy.matrix);
    foliage.setColorAt(i, new THREE.Color().setHSL(.25, .18 + rng() * .15, .15 + rng() * .09));
  }
  scene.add(foliage);
  const update = (time, still) => {
    entries.forEach((entry, index) => {
      const sway = still ? 0 : Math.sin(time * .6 + entry.phase) * .018;
      dummy.position.set(entry.x, 6.2 * entry.scale, entry.z);
      dummy.rotation.set(0, entry.rotation, sway);
      dummy.scale.setScalar(entry.scale); dummy.updateMatrix(); crowns.setMatrixAt(index, dummy.matrix);
    });
    crowns.instanceMatrix.needsUpdate = true;
  };
  update(0, true);
  return { update };
}
