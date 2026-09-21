import { test } from 'node:test';
import assert from 'node:assert/strict';
import { revealRadius, normalizePolygon, areaHectares, matchingAnalysis, fillDailyGaps } from './journey.js';
const polygon = { type: 'Polygon', coordinates: [[[79,10],[79.001,10],[79.001,10.001],[79,10.001],[79,10]]] };
test('missing weather days stay empty instead of becoming zero or interpolation', () => {
  const result = fillDailyGaps([{ date:'2025-10-01', rainfall_mm:2 },{ date:'2025-10-03', rainfall_mm:4 }]);
  assert.equal(result.length,3);
  assert.equal(result[1].date,'2025-10-02');
  assert.equal(result[1].rainfall_mm,undefined);
});
test('reveal covers every viewport corner from centre and edge activation', () => {
  for (const [x,y] of [[0,0],[390,844],[120,300],[195,422]]) {
    const radius = revealRadius(x,y,390,844);
    for (const [cx,cy] of [[0,0],[390,0],[0,844],[390,844]]) assert.ok(radius >= Math.hypot(cx-x,cy-y));
  }
});
test('normalizes supported Polygon wrappers and preserves coordinate order', () => {
  const feature = { type: 'Feature', geometry: polygon };
  for (const value of [polygon,feature,{type:'FeatureCollection',features:[feature]}]) {
    const points = normalizePolygon(value);
    assert.deepEqual(points[0],{lng:79,lat:10}); assert.equal(points.length,4);
    assert.ok(areaHectares(points) > 1 && areaHectares(points) < 1.3);
  }
});
test('rejects multiple fields, open rings, non-finite positions, holes and wrong types', () => {
  for (const value of [
    {type:'FeatureCollection',features:[]}, {type:'MultiPolygon',coordinates:[]},
    {type:'Polygon',coordinates:[polygon.coordinates[0],polygon.coordinates[0]]},
    {type:'Polygon',coordinates:[[[0,0],[1,0],[1,1],[0,1]]]},
    {type:'Polygon',coordinates:[[[0,0],[NaN,0],[1,1],[0,0]]]},
  ]) assert.throws(()=>normalizePolygon(value));
});
test('analysis must match both field and selected run', () => {
  const run = { request_id:'run-a',field_id:'field-a' };
  assert.equal(matchingAnalysis(run,'run-a','field-a'),run);
  assert.equal(matchingAnalysis(run,'run-b','field-a'),null);
  assert.equal(matchingAnalysis(run,'run-a','field-b'),null);
  assert.equal(matchingAnalysis(run,null,'field-a'),null);
});
