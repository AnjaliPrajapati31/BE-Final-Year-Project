import { Link } from 'react-router-dom';
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { useCurrentAnalysis } from '../hooks/useCurrentAnalysis';
import { LoadingSpinner } from '../components/UIHelpers';
import { formatNumber, presentAdvisoryAction, presentError, presentModuleStatus } from '../lib/presentation';
export const Recommendations = () => {
  const { analysis, loading, error } = useCurrentAnalysis();
  if (loading) return <LoadingSpinner/>;
  if (error) return <div className="overview-card" role="alert">{presentError(error).message}</div>;
  if (!analysis) return <div className="overview-card">Select a field analysis to review water needs.</div>;
  const balance = analysis.water_balance, advice = analysis.irrigation_advisory;
  const usable = advice && advice.action !== 'unavailable';
  const nonPaddy = analysis.crop?.class_label === 'Non-Paddy';
  const daily = analysis.charts?.water_balance || [];
  return <div className="overview-stack">
    <section className="overview-conclusion"><p className="step-label">WATER & IRRIGATION</p><h2>{nonPaddy ? 'Not applicable to this crop' : usable ? presentAdvisoryAction(advice.action) : 'Advice needs more information'}</h2>
      <p>{usable ? advice.reason : nonPaddy ? 'The water model supports Paddy fields.' : 'Review the available water balance and field records. Completed calculations remain available below.'}</p>
      <p className="text-xs">Provisional decision support. Confirm field conditions before applying water.</p>
      {usable && <p>Recommended timing: {String(advice.recommended_timing || 'Not available').replaceAll('_',' ')} · Urgency: {advice.urgency || 'Not available'}</p>}
    </section>
    {usable && <div className="overview-metrics">{[['Net water needed',advice.net_depth_mm,' mm'],['Water to apply',advice.gross_depth_mm,' mm'],['Approximate volume',advice.volume_m3,' m³'],['Forecast rain credited',advice.forecast_rainfall_credited_mm,' mm']].map(([label,value,unit]) => <article className="overview-card" key={label}><h3>{label}</h3><strong>{formatNumber(value,1,unit)}</strong></article>)}</div>}
    <section className="overview-card"><h2>Current water state · {presentModuleStatus(analysis.modules?.water_balance?.status).label}</h2><dl>
      {[['Water deficit',balance?.water_deficit_mm],['Lower deficit estimate',balance?.water_deficit_low_mm],['Upper deficit estimate',balance?.water_deficit_high_mm],['Ponded water',balance?.ponded_water_mm],['Root-zone depletion',balance?.root_depletion_mm]].map(([label,value]) => <div key={label}><dt>{label}</dt><dd>{formatNumber(value,1,' mm')}</dd></div>)}<div><dt>Balance date</dt><dd>{balance?.as_of_date || 'Not available'}</dd></div>
    </dl></section>
    {!!daily.length && <section className="overview-card"><h2>Daily water deficit</h2><div className="overview-chart"><ResponsiveContainer width="100%" height="100%"><AreaChart data={daily.slice(-45)}><CartesianGrid vertical={false} stroke="#e0e6d9"/><XAxis dataKey="date" tick={{fontSize:10}} tickFormatter={v=>String(v).slice(5)}/><YAxis unit=" mm" tick={{fontSize:10}}/><Tooltip/><Area dataKey="water_deficit_mm" name="Deficit (mm)" stroke="#426a50" fill="#d1e1c4"/></AreaChart></ResponsiveContainer></div>
      <details><summary>Daily accounting ledger</summary><div className="overflow-x-auto"><table className="w-full text-xs mt-4"><thead><tr>{['Date','Rain (mm)','Actual ETc (mm)','Irrigation (mm)','Losses (mm)','Overflow (mm)','Deficit (mm)'].map(v=><th className="p-2 text-left" key={v}>{v}</th>)}</tr></thead><tbody>{daily.map(row=><tr key={row.date}>{[row.date,formatNumber(row.rainfall_mm),formatNumber(row.actual_etc_mm),formatNumber(row.net_irrigation_mm),formatNumber(row.seepage_percolation_mm),formatNumber(row.runoff_mm),formatNumber(row.water_deficit_mm)].map((v,i)=><td key={i} className="p-2 border-t">{v}</td>)}</tr>)}</tbody></table></div></details>
    </section>}
    <section className="overview-card"><h2>Evidence and assumptions</h2><p className="text-sm">Evidence: {advice?.evidence_level || balance?.evidence_level || 'Not available'}. Application efficiency: {formatNumber(advice?.irrigation_efficiency == null ? null : advice.irrigation_efficiency * 100,0,'%')}.</p>
      <ul>{[...(balance?.warnings || []),...(advice?.warnings || [])].map((w,i)=><li key={i}>{typeof w === 'string' ? w : w.message || 'See analysis limitations'}</li>)}</ul>
      <Link className="quiet-button" to={'/settings?fieldId='+encodeURIComponent(analysis.field_id)+'&requestId='+encodeURIComponent(analysis.request_id)}>Review water records ↗</Link>
    </section>
  </div>;
};
