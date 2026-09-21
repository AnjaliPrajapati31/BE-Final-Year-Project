import * as THREE from 'three';
import { randomSequence, canalCenter } from './landscape';

function limb(start, end, radius, material, group) {
  const direction = new THREE.Vector3().subVectors(end, start);
  const mesh = new THREE.Mesh(new THREE.CylinderGeometry(radius * .86, radius, direction.length(), 10), material);
  mesh.position.copy(start).add(end).multiplyScalar(.5);
  mesh.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), direction.normalize());
  group.add(mesh);
}

export function createFarmer(scene) {
  const farmer = new THREE.Group();
  const skin = new THREE.MeshStandardMaterial({ color: '#674731', roughness: .92 });
  const shirt = new THREE.MeshStandardMaterial({ color: '#c8c4ad', roughness: 1 });
  const cloth = new THREE.MeshStandardMaterial({ color: '#aaa68c', roughness: 1, side: THREE.DoubleSide });
  const head = new THREE.Mesh(new THREE.SphereGeometry(.095, 16, 12), skin);
  head.scale.set(.9, 1.16, .98); head.position.y = 1.54; farmer.add(head);
  const hair = new THREE.Mesh(new THREE.SphereGeometry(.096, 16, 8, 0, Math.PI * 2, 0, Math.PI * .52),
    new THREE.MeshStandardMaterial({ color: '#252b20', roughness: 1 }));
  hair.position.y = 1.565; farmer.add(hair);
  const torso = new THREE.Mesh(new THREE.CapsuleGeometry(.135, .29, 6, 12), shirt);
  torso.scale.set(1.12, 1, .72); torso.position.y = 1.17; farmer.add(torso);
  const wrap = new THREE.CylinderGeometry(.17, .205, .59, 32, 12, true);
  const p = wrap.attributes.position;
  for (let i = 0; i < p.count; i++) {
    const a = Math.atan2(p.getZ(i), p.getX(i));
    const fold = Math.sin(a * 13) * .009 + Math.sin(a * 7) * .006;
    p.setX(i, p.getX(i) + Math.cos(a) * fold);
    p.setZ(i, p.getZ(i) + Math.sin(a) * fold);
  }
  wrap.computeVertexNormals();
  const dhoti = new THREE.Mesh(wrap, cloth); dhoti.position.y = .70; farmer.add(dhoti);
  for (const side of [-1, 1]) {
    limb(new THREE.Vector3(side * .085, .47, 0), new THREE.Vector3(side * .09, .075, .02), .032, skin, farmer);
    const foot = new THREE.Mesh(new THREE.CapsuleGeometry(.035, .08, 4, 8), skin);
    foot.rotation.x = Math.PI / 2; foot.position.set(side * .09, .038, -.025); farmer.add(foot);
    limb(new THREE.Vector3(side * .15, 1.34, 0), new THREE.Vector3(side * .21, 1.12, .01), .049, shirt, farmer);
    limb(new THREE.Vector3(side * .21, 1.13, .01), new THREE.Vector3(side * .16, .93, .08), .028, skin, farmer);
  }
  // A folded shoulder towel breaks the silhouette and provides small wind motion.
  const towel = new THREE.Mesh(new THREE.PlaneGeometry(.085, .40, 3, 8), cloth);
  towel.position.set(-.115, 1.23, .115); farmer.add(towel);
  farmer.position.set(canalCenter(-11) - 3.1, .16, -11);
  farmer.rotation.y = -.18;
  scene.add(farmer);
  return { farmer, towel };
}

export function createBirds(scene) {
  const group = new THREE.Group();
  const rng = randomSequence(7878);
  const material = new THREE.MeshBasicMaterial({ color: '#414d40', side: THREE.DoubleSide });
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute('position', new THREE.Float32BufferAttribute([0,0,0, .6,.04,.13, .43,0,-.08], 3));
  geometry.computeVertexNormals();
  const birds = [];
  for (let i = 0; i < 9; i++) {
    const bird = new THREE.Group();
    const left = new THREE.Mesh(geometry, material), right = new THREE.Mesh(geometry, material);
    right.scale.x = -1;
    bird.add(left, right); bird.scale.setScalar(.55 + rng() * .2);
    group.add(bird);
    birds.push({ bird, left, right, x: -45 + rng() * 70, y: 14 + rng() * 8, z: -75 - rng() * 70, phase: rng() * 6.28 });
  }
  scene.add(group);
  return birds;
}
