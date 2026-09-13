import { CloudSun, Droplets, Info } from 'lucide-react';
import { Bar, CartesianGrid, ComposedChart, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { EmptyState, InlineNotice, LoadingSpinner, SectionHeader, StatusPill } from '../components/UIHelpers';
import { useCurrentAnalysis } from '../hooks/useCurrentAnalysis';
import { formatNumber, presentError, presentModuleStatus } from '../lib/presentation';

export const Weather = () => {
  const { analysis, loading, error } = useCurrentAnalysis();
  if (loading) return <LoadingSpinner />;
  if (error) {
    const message = presentError(error);
    return <EmptyState title={message.title} description={message.message} icon={CloudSun} />;
  }
  if (!analysis) {
    return <EmptyState title="No analysis selected" description="Run or open a field analysis to view the weather evidence used for its water balance." icon={CloudSun} />;
  }

  const weather = analysis.weather;
  const module = analysis.modules?.weather;
  if (!weather?.historical?.length) {
    const state = presentModuleStatus(module?.status);
    return (
      <div className="space-y-6">
        <SectionHeader title="Weather evidence" subtitle="Rainfall and reference evapotranspiration used by the water balance" />
        <EmptyState title={state.label} description="Usable weather data was not produced for this analysis. Earlier crop results remain valid." icon={CloudSun} />
      </div>
    );
  }

  const rows = [
    ...weather.historical.slice(-14).map((row) => ({ ...row, period: 'Observed estimate' })),
    ...(weather.forecast || []).map((row) => ({ ...row, period: 'Forecast' })),
  ];
  const latest = weather.historical.at(-1);

  return (
    <div className="space-y-6">
      <SectionHeader
        title="Weather evidence"
        subtitle="GPM rainfall with ERA5-Land and GFS meteorology"
        action={<StatusPill status={presentModuleStatus(module?.status)} />}
      />
      <InlineNotice title="Regional estimates, not a field rain gauge" description="Use recorded field observations whenever available. Forecast values can change between model runs." tone="warning" />

      <div className="grid gap-4 sm:grid-cols-3">
        <Metric label="Latest estimated rain" value={formatNumber(latest?.rainfall_mm, 1, ' mm')} />
        <Metric label="Latest ET₀" value={formatNumber(latest?.et0_mm, 1, ' mm/day')} />
        <Metric label="Forecast available" value={`${weather.forecast_days || 0} day${weather.forecast_days === 1 ? '' : 's'}`} />
      </div>

      <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <div className="mb-4 flex items-start justify-between gap-3">
          <div>
            <h2 className="font-bold text-slate-900">Recent and forecast daily weather</h2>
            <p className="text-xs text-slate-500">Rainfall bars and reference evapotranspiration line, in millimetres</p>
          </div>
          <CloudSun className="h-5 w-5 text-sky-600" />
        </div>
        <div className="h-80">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={rows} margin={{ top: 10, right: 8, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
              <XAxis dataKey="date" tick={{ fontSize: 10 }} tickFormatter={(value) => value.slice(5)} />
              <YAxis tick={{ fontSize: 10 }} unit=" mm" />
              <Tooltip formatter={(value) => [`${Number(value).toFixed(1)} mm`]} />
              <Bar dataKey="rainfall_mm" name="Rainfall" fill="#38bdf8" radius={[4, 4, 0, 0]} />
              <Line dataKey="et0_mm" name="ET₀" stroke="#f59e0b" strokeWidth={2.5} dot={false} />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="rounded-2xl border border-slate-200 bg-white p-5">
        <div className="mb-3 flex items-center gap-2 text-sm font-bold text-slate-900"><Info className="h-4 w-4" /> Data notes</div>
        <div className="grid gap-3 text-xs text-slate-600 sm:grid-cols-3">
          <span>Latest water-balance day: <strong>{weather.historical_as_of_date || 'Not available'}</strong></span>
          <span>Historical days used: <strong>{weather.historical_days}</strong></span>
          <span>Sources: <strong>{weather.input_sources?.join(', ') || 'Not available'}</strong></span>
        </div>
        {weather.warnings?.length > 0 && (
          <ul className="mt-4 space-y-1 text-xs text-amber-800">
            {weather.warnings.map((warning) => <li key={warning}>• {warning}</li>)}
          </ul>
        )}
      </div>
    </div>
  );
};

const Metric = ({ label, value }) => (
  <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
    <div className="flex items-center gap-2 text-xs font-semibold text-slate-500"><Droplets className="h-4 w-4 text-sky-600" />{label}</div>
    <div className="mt-2 text-2xl font-bold text-slate-900">{value}</div>
  </div>
);
