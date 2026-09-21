import { useCallback, useEffect, useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { MapContainer, TileLayer, Polygon, Polyline, GeoJSON, useMap, useMapEvents } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { useApp } from '../contexts/AppContext';
import { analyzeField, deriveFieldId, pointsToPolygonGeoJson, getCoverage, extractBoundaryPoints } from '../services/api';
import { normalizePolygon, areaHectares, readFieldDraft } from '../lib/journey';
import { presentError } from '../lib/presentation';

function MapEvents({ drawing, add }) {
  useMapEvents({ click: event => { if (drawing) add({ lat: event.latlng.lat, lng: event.latlng.lng }); } });
  return null;
}
function FitGeometry({ geometry }) {
  const map = useMap();
  useEffect(() => {
    if (!geometry) return;
    const bounds = L.geoJSON(geometry).getBounds();
    if (bounds.isValid()) map.fitBounds(bounds, { padding: [35, 35], maxZoom: 17 });
    map.invalidateSize();
  }, [geometry, map]);
  return null;
}
const layers = {
  satellite: { url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', attribution: '&copy; Esri and imagery contributors' },
  street: { url: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', attribution: '&copy; OpenStreetMap contributors' },
};
export function MyFields() {
  const navigate = useNavigate();
  const { fieldBoundaryPoints, setFieldBoundaryPoints, fieldDisplayName, setFieldDisplayName, fieldId, setFieldId, latestAnalysisSummary, setLatestRequestId, setLatestAnalysisSummary, setActiveField } = useApp();
  const [draft] = useState(readFieldDraft);
  const [points, setPoints] = useState(draft.points || fieldBoundaryPoints || []);
  const [closed, setClosed] = useState(Boolean(draft.closed && draft.points?.length >= 3));
  const [drawing, setDrawing] = useState(false);
  const [coverage, setCoverage] = useState(null), [coverageError, setCoverageError] = useState(false);
  const [layer, setLayer] = useState('satellite'), [tiles, setTiles] = useState('loading');
  const [year, setYear] = useState(draft.year || new Date().getFullYear());
  const [sowing, setSowing] = useState(draft.sowing || ''), [transplanting, setTransplanting] = useState(draft.transplanting || '');
  const [artifacts, setArtifacts] = useState(false), [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null), [fit, setFit] = useState(null);
  const [panelOpen, setPanelOpen] = useState(true);
  const submission = useRef(false), alive = useRef(true), coverageAttempt = useRef(0);
  const upload = useRef(null);
  const loadCoverage = useCallback(async () => {
    const attempt = ++coverageAttempt.current;
    try {
      const result = await getCoverage();
      if (!alive.current || attempt !== coverageAttempt.current) return;
      if (!result?.geometry) throw new Error('Missing coverage geometry');
      setCoverage(result); setFit(result);
    } catch { if (alive.current && attempt === coverageAttempt.current) setCoverageError(true); }
  }, []);
  useEffect(() => {
    alive.current = true;
    // External request; state updates occur in its completion handlers.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void loadCoverage();
    return () => { alive.current = false; };
  }, [loadCoverage]);
  useEffect(() => { setFieldBoundaryPoints(points); }, [points, setFieldBoundaryPoints]);
  useEffect(() => {
    try { sessionStorage.setItem('cropsense.fieldDraft', JSON.stringify({ points, closed, name: fieldDisplayName, year, sowing, transplanting })); } catch { /* Draft remains in memory if storage is unavailable. */ }
  }, [points, closed, fieldDisplayName, year, sowing, transplanting]);
  const add = point => setPoints(previous => [...previous, point]);
  const clear = () => { setPoints([]); setClosed(false); setDrawing(false); setError(null); };
  const uploadFile = async event => {
    const file = event.target.files?.[0];
    event.target.value = '';
    if (!file) return;
    try {
      if (file.size > 2 * 1024 * 1024) throw new Error('Use a GeoJSON file smaller than 2 MB.');
      const selected = normalizePolygon(JSON.parse(await file.text()));
      setPoints(selected); setClosed(true); setDrawing(false); setError(null);
      setFit(pointsToPolygonGeoJson(selected));
    } catch (problem) { setError({ message: problem instanceof SyntaxError ? 'This file is not valid GeoJSON.' : problem.message }); }
  };
  const restoreField = () => {
    const selected = extractBoundaryPoints(latestAnalysisSummary?.geometry?.geojson);
    if (!selected.length) return;
    setPoints(selected); setClosed(true); setDrawing(false); setFit(pointsToPolygonGeoJson(selected));
    setFieldDisplayName(latestAnalysisSummary.field_id.replaceAll('_', ' '));
  };
  const submit = async event => {
    event.preventDefault();
    if (submission.current || !coverage) return;
    const code = deriveFieldId(fieldDisplayName);
    if (!code || !closed || points.length < 3 || areaHectares(points) <= 0) {
      setError({ message: 'Enter a field name and finish a boundary with at least three different corners.' }); return;
    }
    if ([sowing, transplanting].filter(Boolean).some(date => Number(date.slice(0, 4)) !== year) || (sowing && transplanting && transplanting < sowing)) {
      setError({ message: 'Planting dates must match the analysis year, with transplanting on or after sowing.' }); return;
    }
    submission.current = true; setSubmitting(true); setError(null);
    try {
      const result = await analyzeField({ field_id: code, geometry: pointsToPolygonGeoJson(points), year, season: 'june_october',
        sowing_date_hint: sowing || null, transplanting_date_hint: transplanting || null, generate_artifacts: artifacts });
      setFieldId(code); setLatestRequestId(result.request_id); setLatestAnalysisSummary(result);
      setActiveField({ id: code, name: fieldDisplayName.trim() });
      if (alive.current) navigate('/dashboard?requestId=' + encodeURIComponent(result.request_id) + '&fieldId=' + encodeURIComponent(code));
    } catch (problem) { if (alive.current) setError(problem); }
    finally { submission.current = false; if (alive.current) setSubmitting(false); }
  };
  const coordinates = points.map(p => [p.lat, p.lng]);
  const errorText = error?.code ? presentError(error).message : error?.message;
  const local = new Date();
  const today = new Date(local.getTime() - local.getTimezoneOffset() * 60000).toISOString().slice(0,10);
  return <section className="field-workspace">
    <div className="field-map">
      <MapContainer center={[0, 0]} zoom={2} scrollWheelZoom>
        <TileLayer key={layer} {...layers[layer]} eventHandlers={{ loading: () => setTiles('loading'), load: () => setTiles('ready'), tileerror: () => setTiles('error') }}/>
        {coverage && <GeoJSON data={coverage} style={{ color: '#5f873f', weight: 2, fillOpacity: .055 }}/>}
        <FitGeometry geometry={fit}/>
        <MapEvents drawing={drawing && !submitting} add={add}/>
        {closed ? <Polygon positions={coordinates} pathOptions={{ color: '#e3b854', fillColor: '#aace77', fillOpacity: .25 }}/> : <Polyline positions={coordinates} pathOptions={{ color: '#e3b854' }}/>}
      </MapContainer>
      <div className="field-map-notice">{tiles === 'loading' ? 'Loading map imagery. ' : tiles === 'error' ? 'Some map tiles could not load. Try the other basemap. ' : ''}
        {drawing ? 'Click around your field, then choose Finish boundary.' : 'Green outline: approved coverage. Field shape, patch fit, and satellite availability are checked when you run analysis.'}</div>
    </div>
    <aside className="field-panel"><p className="step-label">02 / SELECT YOUR FIELD</p><h1 id="field-map-title" tabIndex={-1}>Bring your field into view.</h1>
      <button className="quiet-button panel-toggle" onClick={() => setPanelOpen(v => !v)} aria-expanded={panelOpen}>{panelOpen ? 'Hide' : 'Show'} field controls</button>
      {panelOpen && <>
      <p>Draw or upload the real boundary. Your selected field stays here while the analysis runs.</p>
      {coverageError ? <div className="form-error" role="alert">Coverage information is unavailable. <button type="button" className="quiet-button" onClick={() => { setCoverageError(false); setCoverage(null); void loadCoverage(); }}>Retry</button></div> : !coverage && <p role="status">Loading approved coverage…</p>}
      <fieldset disabled={submitting} style={{ border: 0, padding: 0 }}>
      <div className="tool-grid">
        <button className="quiet-button" onClick={() => { clear(); setDrawing(true); }}>Draw boundary</button>
        <button className="quiet-button" onClick={() => upload.current?.click()}>Upload GeoJSON</button>
        <input ref={upload} hidden type="file" accept=".json,.geojson,application/geo+json" onChange={uploadFile}/>
        {drawing && <><button className="quiet-button" disabled={!points.length} onClick={() => setPoints(p => p.slice(0, -1))}>Undo point</button><button className="quiet-button" disabled={points.length < 3} onClick={() => { setClosed(true); setDrawing(false); }}>Finish boundary</button></>}
        {!!points.length && <button className="quiet-button" onClick={clear}>Clear</button>}
        {latestAnalysisSummary?.geometry?.geojson && <button className="quiet-button" onClick={restoreField}>Return to saved boundary</button>}
      </div>
      <label>Basemap<select value={layer} onChange={e => { setLayer(e.target.value); setTiles('loading'); }}><option value="satellite">Satellite imagery</option><option value="street">Street map</option></select></label>
      <div className="selection-summary"><span>{closed ? 'Boundary finished' : points.length ? 'Drawing boundary' : 'No field selected'}</span><span>{points.length > 2 ? areaHectares(points).toFixed(2) + ' ha (estimate)' : '—'}</span></div>
      <form onSubmit={submit}>
        <label>Field name<input required value={fieldDisplayName} onChange={e => setFieldDisplayName(e.target.value)} placeholder="e.g. North paddy field" maxLength={100}/></label>
        <label>Analysis year<select value={year} onChange={e => setYear(Number(e.target.value))}>{Array.from({ length: new Date().getFullYear() - 2024 }, (_, i) => new Date().getFullYear() - i).map(y => <option key={y}>{y}</option>)}</select></label>
        <p>Supported seasonal window: June–October. Current-season data may be incomplete.</p>
        <details><summary>Planting dates (optional)</summary><label>Sowing date<input type="date" max={today} value={sowing} onChange={e => setSowing(e.target.value)}/></label><label>Transplanting date<input type="date" max={today} value={transplanting} onChange={e => setTransplanting(e.target.value)}/></label></details>
        <details><summary>Advanced options & boundary coordinates</summary><label><input type="checkbox" checked={artifacts} onChange={e => setArtifacts(e.target.checked)}/>Generate downloadable artifacts</label><p>{points.map(p => p.lat.toFixed(5) + ', ' + p.lng.toFixed(5)).join(' · ') || 'No boundary yet.'}</p></details>
        {error && <div className="form-error" role="alert">{errorText}<p>Your boundary is preserved. Check saved history before retrying a timed-out request.</p>{error.requestId && <details><summary>Technical details</summary>{error.requestId}</details>}</div>}
        <button className="primary-button" disabled={!coverage || !closed || submitting} type="submit">{submitting ? 'Analyzing…' : 'Run analysis →'}</button>
      </form></fieldset>
      {submitting && <div className="analysis-wait" role="status"><progress aria-label="Analysis in progress"/><p>Analyzing your field. This may take a few minutes.</p></div>}
      {fieldId && <p><Link to={'/history?fieldId=' + encodeURIComponent(fieldId)}>Open saved field history ↗</Link></p>}
      </>}
    </aside>
  </section>;
}
