import { Link } from 'react-router-dom';
import { ResponsiveContainer, ComposedChart, Line, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend } from 'recharts';
import { useCurrentAnalysis } from '../hooks/useCurrentAnalysis';
import { formatNumber, presentAdvisoryAction, presentError, presentModuleStatus } from '../lib/presentation';
import { LoadingSpinner } from '../components/UIHelpers';
import { AnalysisExplanation } from '../components/AnalysisExplanation';

function Chart({ rows, water = false }) {
  if (!rows.length) return <p className="text-sm text-slate-500">No usable observations for this chart.</p>;
  return <div className="overview-chart"><ResponsiveContainer width="100%" height="100%"><ComposedChart data={rows}>
    <CartesianGrid vertical={false} stroke="#e1e7da"/><XAxis dataKey="date" tick={{ fontSize: 10 }} tickFormatter={v => String(v).slice(5)}/><YAxis tick={{ fontSize: 10 }} width={42}/><Tooltip/><Legend wrapperStyle={{ fontSize: 11 }}/>
    {water ? <><Bar dataKey="rainfall_mm" name="Rainfall (mm)" fill="#a0c4c4"/><Line dataKey="et0_mm" name="ET₀ (mm)" stroke="#ad9252" dot={false}/><Line dataKey="water_deficit_mm" name="Deficit (mm)" stroke="#35624b" dot={false}/></> : <><Line dataKey="ndvi" name="NDVI" stroke="#5b793f" dot={false}/><Line dataKey="ndmi" name="NDMI" stroke="#518d9b" dot={false}/></>}
  </ComposedChart></ResponsiveContainer></div>;
}
function Boundary({ geometry }) {
  const ring = geometry?.type === 'MultiPolygon' ? geometry.coordinates?.[0]?.[0] : geometry?.coordinates?.[0];
  if (!ring?.length) return null;
  const xs = ring.map(p => p[0]), ys = ring.map(p => p[1]);
  const minX = Math.min(...xs), maxY = Math.max(...ys);
  const scale = Math.min(110 / (Math.max(...xs) - minX || 1), 65 / (maxY - Math.min(...ys) || 1));
  return <svg className="field-thumbnail" viewBox="0 0 130 85" role="img" aria-label="Analyzed field boundary"><polygon points={ring.map(p => (10 + (p[0] - minX) * scale) + ',' + (10 + (maxY - p[1]) * scale)).join(' ')}/></svg>;
}
export const Dashboard = () => {
  const { analysis, loading, error } = useCurrentAnalysis();
  if (loading) return <LoadingSpinner/>;
  if (error) return <div className="overview-card" role="alert"><h2>{presentError(error).title}</h2><p>{presentError(error).message}</p><Link to="/fields">Return to your field</Link></div>;
  if (!analysis) return <div className="overview-card"><h2>Start with your field.</h2><p>Select a boundary or open a saved analysis to see your results.</p><Link className="primary-button" to="/fields">Select field →</Link></div>;
  const crop = analysis.crop, stage = analysis.growth_stage, stress = analysis.moisture_stress, balance = analysis.water_balance, advice = analysis.irrigation_advisory;
  const query = new URLSearchParams({ requestId: analysis.request_id, fieldId: analysis.field_id }).toString();
  const nonPaddy = crop?.class_label === 'Non-Paddy';
  const usable = advice && advice.action !== 'unavailable';
  const label = module => presentModuleStatus(analysis.modules?.[module]?.status).label;
  const weather = new Map((analysis.weather?.historical || []).map(row => [row.date, row]));
  const ledger = (analysis.charts?.water_balance || []).map(row => ({ ...weather.get(row.date), ...row }));
  const warnings = [...new Set([...(analysis.warnings || []), ...(balance?.warnings || []), ...(advice?.warnings || [])].map(w => typeof w === 'string' ? w : w.message || w.code || 'Limited evidence'))];
  return <div className="overview-stack">
    <div className="overview-card flex items-center justify-between gap-4"><div><h2>Field at a glance</h2><p>{formatNumber(analysis.geometry?.area_m2 == null ? null : analysis.geometry.area_m2 / 10000, 2, ' ha')} · {analysis.data_quality?.analysis_cutoff || 'Observation date unavailable'}</p><small>Evidence: {advice?.evidence_level || balance?.evidence_level || 'See module details'} · Stage, stress and water estimates are provisional.</small></div><Boundary geometry={analysis.geometry?.geojson}/></div>
    <section className="overview-conclusion"><p className="step-label">YOUR NEXT STEP</p><h2>{nonPaddy ? 'Rice-specific water advice does not apply.' : usable ? presentAdvisoryAction(advice.action) : 'More field information is needed.'}</h2>
      <p>{nonPaddy ? 'The crop result is Non-Paddy. Rice growth, stress and water modules are not applicable to this result.' : usable ? advice.reason : 'Review the module states below. Usable weather and a field water balance are needed before irrigation quantities can be estimated.'}</p>
      {usable && <p>Net depth: <b>{formatNumber(advice.net_depth_mm, 1, ' mm')}</b> · Water to apply: <b>{formatNumber(advice.gross_depth_mm, 1, ' mm')}</b> · Approximate volume: <b>{formatNumber(advice.volume_m3, 1, ' m³')}</b></p>}
      <Link className="quiet-button" to={(usable ? '/recommendations?' : '/settings?') + query}>{usable ? 'Review advice and assumptions' : 'Review field records'} ↗</Link>
    </section>
    <div className="overview-metrics">{[
      ['Crop', crop?.class_label || 'Not available', 'crop'], ['Growth stage', stage?.stage || 'Not available', 'growth_stage'],
      ['Moisture-stress risk', stress?.stress_risk || 'Not available', 'moisture_stress'], ['Water deficit', formatNumber(balance?.water_deficit_mm, 1, ' mm'), 'water_balance'],
    ].map(([title,value,module]) => <article className="overview-card" key={module}><h3>{title}</h3><strong>{value}</strong><small>{label(module)}</small></article>)}</div>
    <div className="overview-chart-grid"><section className="overview-card"><h2>Water arriving, leaving and needed</h2><Chart rows={ledger.slice(-45)} water/></section><section className="overview-card"><h2>Crop observation timeline</h2><Chart rows={analysis.charts?.stage_timeline || []}/></section></div>
    <section className="overview-card"><h2>Evidence and limitations</h2><div className="flex flex-wrap gap-3 text-xs">{Object.entries(analysis.modules || {}).map(([name, module]) => <span key={name}>{name.replaceAll('_',' ')}: {presentModuleStatus(module.status).label}</span>)}</div>
      {warnings.length ? <details className="mt-4" open><summary>{warnings.length} caution{warnings.length === 1 ? '' : 's'} to review</summary><ul>{warnings.map(w => <li key={w}>{w}</li>)}</ul></details> : <p className="mt-3 text-sm">No additional warnings were returned.</p>}
    </section>
    <AnalysisExplanation key={analysis.request_id} requestId={analysis.request_id}/>
    <details className="overview-card"><summary>Technical details and downloads</summary><dl className="mt-5"><div><dt>Paddy probability</dt><dd>{formatNumber(crop?.paddy_probability == null ? null : crop.paddy_probability * 100, 1, '%')}</dd></div><div><dt>Non-Paddy probability</dt><dd>{formatNumber(crop?.non_paddy_probability == null ? null : crop.non_paddy_probability * 100, 1, '%')}</dd></div><div><dt>Radar / optical observations</dt><dd>{crop?.s1_observation_count ?? '—'} / {crop?.s2_observation_count ?? '—'}</dd></div><div><dt>Request</dt><dd>{analysis.request_id}</dd></div>{Object.entries(analysis.provenance || {}).map(([key,value]) => <div key={key}><dt>{key.replaceAll('_',' ')}</dt><dd>{typeof value === 'object' ? JSON.stringify(value) : String(value ?? 'Not available')}</dd></div>)}</dl>
      {(analysis.artifacts || []).filter(a => a.download_url).map((a,i) => <a className="quiet-button mt-3 mr-3" key={i} href={a.download_url} target="_blank" rel="noreferrer">{a.artifact_type || a.type || 'Download'}</a>)}
    </details>
  </div>;
};
