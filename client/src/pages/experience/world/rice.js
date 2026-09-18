import * as THREE from 'three';
import { distanceToParcelBoundary, isCanal, parcelAt, randomSequence, VALLEY } from './landscape';
import { riceVertex, riceFragment } from './shaders';

// Curved, tapered ribbons form individual rice leaves. Grain heads are small
// ellipsoids along a drooping panicle, not billboard textures or flat cards.
function plantGeometry(detailed) {
  const points = [], texcoords = [], parts = [];
  function triangle(a, b, c, ua, ub, uc, part = 0) {
    points.push(...a, ...b, ...c);
    texcoords.push(...ua, ...ub, ...uc);
    parts.push(part, part, part);
  }
  const leaves = detailed ? 6 : 3;
  const segments = detailed ? 7 : 3;
  for (let leaf = 0; leaf < leaves; leaf++) {
    const azimuth = leaf * 2.399;
    const height = .72 + (leaf % 3) * .19;
    const lean = .27 + (leaf % 4) * .055;
    const base = (leaf % 3) * .07;
    const sin = Math.sin(azimuth), cos = Math.cos(azimuth);
    function edge(t, side) {
      const width = .027 * Math.pow(Math.sin(Math.PI * Math.pow(t, .72)), .7) + .0001;
      const bend = lean * t * t;
      return [cos * bend - sin * side * width, base + height * t - .2 * t * t * t,
        sin * bend + cos * side * width];
    }
    for (let segment = 0; segment < segments; segment++) {
      const a = segment / segments, b = (segment + 1) / segments;
      triangle(edge(a, -1), edge(b, -1), edge(a, 1), [0, a], [0, b], [1, a]);
      triangle(edge(a, 1), edge(b, -1), edge(b, 1), [1, a], [0, b], [1, b]);
    }
  }
  if (detailed) {
    // A fine central stalk curves under the weight of paired grain branches.
    for (let i = 0; i < 13; i++) {
      const a = i / 13, b = (i + 1) / 13;
      const start = [.17 * a * a, a * 1.3 - a ** 5 * .21, 0];
      const end = [.17 * b * b, b * 1.3 - b ** 5 * .21, 0];
      triangle([start[0] - .004, start[1], 0], end, [start[0] + .004, start[1], 0], [0, a], [.5, b], [1, a], 1);
    }
    for (let grain = 0; grain < 22; grain++) {
      const t = grain / 22;
      const branch = grain % 2 === 0 ? -1 : 1;
      const center = [.105 + t * .12, 1.03 + Math.sin(t * Math.PI) * .12 - t * .095, branch * (.013 + Math.sin(t * Math.PI) * .035)];
      const top = [center[0] - .006, center[1] + .015, center[2]];
      const bottom = [center[0] + .006, center[1] - .015, center[2]];
      const ring = [[.008, 0, 0], [0, 0, .008], [-.008, 0, 0], [0, 0, -.008]]
        .map(p => p.map((v, i) => v + center[i]));
      for (let side = 0; side < 4; side++) {
        triangle(top, ring[side], ring[(side + 1) % 4], [.5, 1], [0, .5], [1, .5], 1);
        triangle(bottom, ring[(side + 1) % 4], ring[side], [.5, 0], [1, .5], [0, .5], 1);
      }
    }
  }
  const geometry = new THREE.InstancedBufferGeometry();
  geometry.setAttribute('position', new THREE.Float32BufferAttribute(points, 3));
  geometry.setAttribute('uv', new THREE.Float32BufferAttribute(texcoords, 2));
  geometry.setAttribute('aPart', new THREE.Float32BufferAttribute(parts, 1));
  geometry.computeVertexNormals();
  return geometry;
}

export function createRice(scene, shared, compact) {
  const rng = randomSequence();
  const near = [], far = [], nearShade = [], farShade = [];
  // A dense foreground reads as individual plants; the remaining fields use a
  // deliberately thinner canopy. This keeps the render responsive rather than
  // turning a beautiful scene into a desktop-only benchmark.
  const step = compact ? 1.05 : .86;
  let row = 0;
  for (let z = VALLEY.minZ + 4; z < VALLEY.maxZ - 4; z += step, row++) {
    let column = 0;
    for (let x = VALLEY.minX + 4; x < VALLEY.maxX - 4; x += step, column++) {
      const px = x + (rng() - .5) * step * .75;
      const pz = z + (rng() - .5) * step * .75;
      const parcel = parcelAt(px, pz);
      if (!parcel || distanceToParcelBoundary(px, pz, parcel) < .82 || isCanal(px, pz, .35)) continue;
      const distance = Math.hypot(px - 3, pz - 10);
      const detailed = distance < (compact ? 15 : 18);
      const variation = parcel.variation;
      // One plant cluster per deterministic stratum keeps aerial canopy coverage
      // spatially even. Jitter changes the silhouette, never the coverage map.
      const period = compact ? 27 : 18 + Math.floor(variation * 5);
      const stratum = Math.abs(column * 13 + row * 7 + parcel.row * 5 + parcel.column * 3) % period;
      if (!detailed && stratum !== 0) continue;
      const height = (.74 + rng() * .30) * (.83 + variation * .26);
      (detailed ? near : far).push(px, pz, height, parcel.rowAngle + (rng() - .5) * .18);
      (detailed ? nearShade : farShade).push(.16 + variation * .45 + rng() * .24);
    }
  }
  const material = new THREE.ShaderMaterial({
    uniforms: shared,
    vertexShader: riceVertex,
    fragmentShader: riceFragment,
    side: THREE.DoubleSide,
    transparent: true,
  });
  const meshes = [];
  for (const [data, shade, detail] of [[near, nearShade, true], [far, farShade, false]]) {
    const geometry = plantGeometry(detail);
    geometry.setAttribute('aPlant', new THREE.InstancedBufferAttribute(new Float32Array(data), 4));
    geometry.setAttribute('aShade', new THREE.InstancedBufferAttribute(new Float32Array(shade), 1));
    geometry.instanceCount = shade.length;
    geometry.boundingSphere = new THREE.Sphere(new THREE.Vector3(0, 0, -35), 230);
    const mesh = new THREE.Mesh(geometry, material);
    mesh.name = detail ? 'Near rice: curved blades and grain panicles' : 'Far rice: simplified living canopy';
    scene.add(mesh);
    meshes.push(mesh);
  }
  return { meshes, plantCount: nearShade.length + farShade.length };
}
