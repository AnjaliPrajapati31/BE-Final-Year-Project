export const SEED = 270319;
export const SUN = [0.58, 0.26, -0.78];
export const VALLEY = { minX: -250, maxX: 250, minZ: -285, maxZ: 90 };

export function randomSequence(seed = SEED) {
  let state = seed >>> 0;
  return () => {
    state += 0x6D2B79F5;
    let t = Math.imul(state ^ (state >>> 15), 1 | state);
    t ^= t + Math.imul(t ^ (t >>> 7), 61 | t);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export function canalCenter(z) {
  return 7 + Math.sin(z * .021) * 5.2 + Math.sin(z * .071 + 1.4) * 1.15;
}

export function terrainHeight(x, z) {
  const valleyDistance = Math.max(Math.abs(x) - 265, Math.abs(z + 88) - 235, 0);
  const rise = Math.pow(Math.min(valleyDistance / 210, 1), 1.45) * 78;
  const ridge = Math.sin(x * .013 + z * .009) * 9 + Math.sin(x * .031 - z * .006) * 4;
  return valleyDistance > 0 ? Math.max(0, rise + ridge) : 0;
}

const ROWS = [-280, -218, -158, -101, -44, 15, 78];
const LEFT_BASE = [-248, -188, -126, -64];
const RIGHT_BASE = [0, 64, 128, 190, 248];

function rowPoint(side, rowIndex, columnIndex) {
  const sidePhase = side === 'left' ? .35 : 1.65;
  const edgeWeight = Math.sin(Math.PI * columnIndex / 4);
  const z = ROWS[rowIndex] + Math.sin(rowIndex * 1.37 + columnIndex * 1.91 + sidePhase) * 7.5 * edgeWeight;
  const wobble = Math.sin(rowIndex * 1.71 + columnIndex * 2.13) * 5.2;
  if (side === 'left') {
    if (columnIndex === 4) return [canalCenter(z) - 3.1, z];
    return [LEFT_BASE[columnIndex] + wobble + Math.sin(z * .028) * 2.1, z];
  }
  if (columnIndex === 0) return [canalCenter(z) + 3.1, z];
  return [RIGHT_BASE[columnIndex] + wobble + Math.cos(z * .024) * 2.4, z];
}

function createParcels() {
  const parcels = [];
  for (const side of ['left', 'right']) {
    for (let row = 0; row < ROWS.length - 1; row++) {
      for (let column = 0; column < 4; column++) {
        parcels.push({
          id: `${side}-${row}-${column}`,
          polygon: [rowPoint(side, row, column), rowPoint(side, row, column + 1), rowPoint(side, row + 1, column + 1), rowPoint(side, row + 1, column)],
          row, column, side,
          variation: ((row * 17 + column * 29 + (side === 'right' ? 11 : 0)) % 41) / 40,
          rowAngle: (side === 'left' ? -.08 : .07) + Math.sin(row * 1.3 + column) * .09,
        });
      }
    }
  }
  return parcels;
}

export const PARCELS = createParcels();
export const HERO_PARCEL_ID = 'left-3-3';
export const HERO_PARCEL = PARCELS.find(parcel => parcel.id === HERO_PARCEL_ID);

export function pointInPolygon(x, z, polygon) {
  let inside = false;
  for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
    const [xi, zi] = polygon[i], [xj, zj] = polygon[j];
    if (((zi > z) !== (zj > z)) && (x < (xj - xi) * (z - zi) / ((zj - zi) || 1e-9) + xi)) inside = !inside;
  }
  return inside;
}

function segmentDistance(x, z, a, b) {
  const vx = b[0] - a[0], vz = b[1] - a[1];
  const t = Math.max(0, Math.min(1, ((x - a[0]) * vx + (z - a[1]) * vz) / (vx * vx + vz * vz || 1)));
  return Math.hypot(x - (a[0] + vx * t), z - (a[1] + vz * t));
}

export function distanceToParcelBoundary(x, z, parcel) {
  let distance = Infinity;
  for (let i = 0; i < parcel.polygon.length; i++) distance = Math.min(distance, segmentDistance(x, z, parcel.polygon[i], parcel.polygon[(i + 1) % parcel.polygon.length]));
  return distance;
}

export function parcelAt(x, z) {
  return PARCELS.find(parcel => pointInPolygon(x, z, parcel.polygon));
}

export function isCanal(x, z, margin = 0) {
  return Math.abs(x - canalCenter(z)) < 2.35 + margin;
}

export const CAMERA_KEYS = [
  { position: [2.5, 1.85, 20], target: [-5, 1.1, -25], fov: 53 },
  { position: [0, 3.6, 13], target: [-12, .7, -28], fov: 51 },
  { position: [-7, 7, 13], target: [-17, 0, -33], fov: 50 },
  { position: [-12, 13, 18], target: [-20, 0, -37], fov: 49 },
  { position: [-2, 25, 25], target: [-25, 0, -42], fov: 48 },
  { position: [11, 43, 31], target: [-25, 0, -48], fov: 47 },
  { position: [20, 67, 38], target: [-24, 0, -52], fov: 46 },
  { position: [28, 91, 43], target: [-18, 0, -56], fov: 45 },
  { position: [35, 120, 50], target: [-10, 0, -58], fov: 44 },
];
