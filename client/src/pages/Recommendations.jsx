import { AlertTriangle, CalendarClock, Droplets, Gauge, MapPin, ShieldCheck } from 'lucide-react';
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { EmptyState, InlineNotice, LoadingSpinner, SectionHeader, StatusPill } from '../components/UIHelpers';
import { useCurrentAnalysis } from '../hooks/useCurrentAnalysis';
import { formatNumber, presentAdvisoryAction, presentError, presentModuleStatus } from '../lib/presentation';

export const Recommendations = () => {
  const { analysis, loading, error } = useCurrentAnalysis();
  if (loading) return <LoadingSpinner />;
  if (error) {
    const message = presentError(error);
    return <EmptyState title={message.title} description={message.message} icon={AlertTriangle} />;
  }
  if (!analysis) {
    return <EmptyState title="No irrigation analysis selected" description="Run or open a Paddy field analysis to calculate water deficit and irrigation advice." icon={Droplets} />;
  }

  const balance = analysis.water_balance;
  const advisory = analysis.irrigation_advisory;
  const module = analysis.modules?.irrigation_advisory;
  const daily = analysis.charts?.water_balance || [];
  if (!advisory || advisory.action === 'unavailable') {
    const nonPaddy = analysis.crop?.class_label === 'Non-Paddy';
    return (
      <div className="space-y-6">
        <SectionHeader title="Irrigation advisory" subtitle={`Field ${analysis.field_id}`} action={<StatusPill status={presentModuleStatus(module?.status)} />} />
        <EmptyState title={nonPaddy ? 'Not needed for this crop result' : 'Advice needs more data'} description={nonPaddy ? 'This first water model supports Paddy only.' : 'A current water balance, field area, and usable weather are required before irrigation advice can be issued.'} icon={Droplets} />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <SectionHeader
        title="Irrigation Advisory"
        subtitle={`Deterministic recommendation for ${analysis.field_id}`}
        action={<StatusPill status={presentModuleStatus(module?.status)} />}
      />
      <InlineNotice title="Provisional field decision support" description="Confirm field conditions before applying water. Satellite stress does not determine irrigation quantity." tone="warning" />

      <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-6">
        <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-start">
          <div>
            <div className="text-xs font-bold uppercase tracking-wider text-emerald-700">Recommended action</div>
            <h2 className="mt-1 text-2xl font-bold text-emerald-950">{presentAdvisoryAction(advisory.action)}</h2>
            <p className="mt-2 max-w-2xl text-sm text-emerald-900">{advisory.reason}</p>
          </div>
          <div className="rounded-xl bg-white px-4 py-3 text-center shadow-sm">
            <div className="text-xs text-slate-500">Timing</div>
            <div className="mt-1 font-bold text-slate-900">{friendlyTiming(advisory.recommended_timing)}</div>
          </div>
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Metric icon={Droplets} label="Net water needed" value={formatNumber(advisory.net_depth_mm, 1, ' mm')} />
        <Metric icon={Gauge} label="Water to apply" value={formatNumber(advisory.gross_depth_mm, 1, ' mm')} />
        <Metric icon={MapPin} label="Approximate field volume" value={formatNumber(advisory.volume_m3, 1, ' m³')} />
        <Metric icon={CalendarClock} label="Forecast rain credited" value={formatNumber(advisory.forecast_rainfall_credited_mm, 1, ' mm')} />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <div className="rounded-2xl border border-slate-200 bg-white p-5">
          <h3 className="font-bold text-slate-900">Current water state</h3>
          <dl className="mt-4 grid grid-cols-2 gap-4 text-sm">
            <Value label="Water deficit" value={formatNumber(balance?.water_deficit_mm, 1, ' mm')} />
            <Value label="Estimated ponded water" value={formatNumber(balance?.ponded_water_mm, 1, ' mm')} />
            <Value label="Root-zone depletion" value={formatNumber(balance?.root_depletion_mm, 1, ' mm')} />
            <Value label="Balance date" value={balance?.as_of_date || 'Not available'} />
          </dl>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-white p-5">
          <div className="flex items-center gap-2"><ShieldCheck className="h-4 w-4 text-emerald-600" /><h3 className="font-bold text-slate-900">Evidence and cautions</h3></div>
          <p className="mt-3 text-sm text-slate-700">Evidence level: <strong className="capitalize">{advisory.evidence_level || 'low'}</strong></p>
          <p className="mt-1 text-sm text-slate-700">Application efficiency: <strong>{formatNumber((advisory.irrigation_efficiency || 0) * 100, 0, '%')}</strong></p>
          {advisory.warnings?.length > 0 && <ul className="mt-3 space-y-1 text-xs text-amber-800">{advisory.warnings.map((warning) => <li key={warning}>• {warning}</li>)}</ul>}
        </div>
      </div>

      {daily.length > 0 && (
        <div className="rounded-2xl border border-slate-200 bg-white p-5">
          <h3 className="font-bold text-slate-900">Daily water deficit</h3>
          <p className="text-xs text-slate-500">Calculated deficit in millimetres; this is separate from satellite stress evidence.</p>
          <div className="mt-4 h-72">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={daily.slice(-45)} margin={{ top: 8, right: 8, left: -18, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
                <XAxis dataKey="date" tick={{ fontSize: 10 }} tickFormatter={(value) => value.slice(5)} />
                <YAxis tick={{ fontSize: 10 }} unit=" mm" />
                <Tooltip formatter={(value) => [`${Number(value).toFixed(1)} mm`, 'Water deficit']} />
                <Area type="monotone" dataKey="water_deficit_mm" stroke="#0284c7" fill="#bae6fd" strokeWidth={2.5} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}
    </div>
  );
};

const friendlyTiming = (value) => ({ now: 'Now', within_2_days: 'Within 2 days', recheck_daily: 'Recheck daily', recheck_after_forecast_rain: 'After forecast rain', none_within_5_days: 'No action in 5 days' }[value] || 'Check field conditions');
const Metric = ({ icon: Icon, label, value }) => <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"><Icon className="h-5 w-5 text-emerald-600" /><div className="mt-3 text-xs font-semibold text-slate-500">{label}</div><div className="mt-1 text-xl font-bold text-slate-900">{value}</div></div>;
const Value = ({ label, value }) => <div><dt className="text-xs text-slate-500">{label}</dt><dd className="mt-1 font-semibold text-slate-900">{value}</dd></div>;
