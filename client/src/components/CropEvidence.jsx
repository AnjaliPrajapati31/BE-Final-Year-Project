import { useCurrentAnalysis } from '../hooks/useCurrentAnalysis';
import { formatNumber } from '../lib/presentation';
export function CropEvidence() {
  const { analysis } = useCurrentAnalysis();
  if (!analysis) return null;
  const crop = analysis.crop, stage = analysis.growth_stage;
  return <section className="overview-card mb-6"><h2>Crop and season context</h2><dl>
    <div><dt>Crop classification</dt><dd>{crop?.class_label || 'Not available'}</dd></div>
    <div><dt>Estimated growth stage</dt><dd>{stage?.stage || 'Not available'}</dd></div>
    <div><dt>Paddy probability</dt><dd>{formatNumber(crop?.paddy_probability == null ? null : crop.paddy_probability * 100, 1, '%')}</dd></div>
    <div><dt>Non-Paddy probability</dt><dd>{formatNumber(crop?.non_paddy_probability == null ? null : crop.non_paddy_probability * 100, 1, '%')}</dd></div>
    <div><dt>Crop-cycle start</dt><dd>{stage?.cycle_start || 'Not available'}</dd></div>
    <div><dt>Latest stage observation</dt><dd>{stage?.latest_observation || 'Not available'}</dd></div>
  </dl><p className="mt-4 text-xs text-slate-600">Growth-stage estimates are provisional. Satellite stress is supporting evidence and does not measure the amount of water missing from the field.</p></section>;
}
