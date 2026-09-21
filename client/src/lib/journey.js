export function revealRadius(x, y, width, height) {
  return Math.hypot(Math.max(x, width - x), Math.max(y, height - y)) + 2;
}

export function normalizePolygon(value) {
  let geometry = value;
  if (value?.type === 'FeatureCollection') {
    if (value.features?.length !== 1) throw new Error('Upload exactly one field polygon.');
    geometry = value.features[0]?.geometry;
  } else if (value?.type === 'Feature') geometry = value.geometry;
  if (geometry?.type !== 'Polygon' || geometry.coordinates?.length !== 1) {
    throw new Error('Upload one Polygon without holes.');
  }
  const ring = geometry.coordinates[0];
  if (!Array.isArray(ring) || ring.length < 4 || ring.length > 10000) throw new Error('Use a closed polygon with at least three corners.');
  if (!ring.every(p => Array.isArray(p) && p.length >= 2 && Number.isFinite(p[0]) && Number.isFinite(p[1]) && Math.abs(p[0]) <= 180 && Math.abs(p[1]) <= 90)) throw new Error('Coordinates must be valid longitude and latitude.');
  if (ring[0][0] !== ring.at(-1)[0] || ring[0][1] !== ring.at(-1)[1]) throw new Error('The uploaded polygon must be closed.');
  const points = ring.slice(0, -1).map(([lng, lat]) => ({ lng, lat }));
  if (new Set(points.map(p => p.lng + ',' + p.lat)).size < 3) throw new Error('Choose at least three different corners.');
  return points;
}

export function areaHectares(points) {
  if (points.length < 3) return 0;
  const radians = Math.PI / 180;
  const latitude = points.reduce((sum, p) => sum + p.lat, 0) / points.length * radians;
  const origin = points[0];
  const xy = points.map(p => [(p.lng - origin.lng) * radians * 6371008.8 * Math.cos(latitude), (p.lat - origin.lat) * radians * 6371008.8]);
  return Math.abs(xy.reduce((sum, p, i) => { const q = xy[(i + 1) % xy.length]; return sum + p[0] * q[1] - q[0] * p[1]; }, 0)) / 20000;
}

export function matchingAnalysis(value, requestId, fieldId) {
  return value && value.request_id === requestId && (!fieldId || value.field_id === fieldId) ? value : null;
}

export function fillDailyGaps(rows) {
  const byDate = new Map(rows.filter(row => /^\d{4}-\d{2}-\d{2}$/.test(row.date)).map(row => [row.date, row]));
  const dates = [...byDate.keys()].sort();
  if (!dates.length) return [];
  const start = Date.parse(dates[0]), end = Date.parse(dates.at(-1));
  if (!Number.isFinite(start) || !Number.isFinite(end) || end - start > 366 * 86400000) return rows;
  const result = [];
  for (let time = start; time <= end; time += 86400000) {
    const date = new Date(time).toISOString().slice(0,10);
    result.push(byDate.get(date) || { date, period: 'No data' });
  }
  return result;
}

export function readFieldDraft() {
  try {
    const value = JSON.parse(sessionStorage.getItem('cropsense.fieldDraft') || 'null');
    if (!value || !Array.isArray(value.points) || !value.points.every(p => Number.isFinite(p.lat) && Number.isFinite(p.lng))) return {};
    return value;
  } catch { return {}; }
}
