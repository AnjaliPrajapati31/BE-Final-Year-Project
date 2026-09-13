import { useMemo } from 'react';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  ReferenceLine,
  Legend,
} from 'recharts';
import {
  Droplets,
  AlertTriangle,
  CheckCircle,
  Info,
  Activity,
  Radio,
  ShieldAlert,
  Leaf,
  TrendingDown,
  TrendingUp,
} from 'lucide-react';
import { EmptyState, LoadingSpinner, SectionHeader } from '../components/UIHelpers';
import { useApp } from '../contexts/AppContext';
import { useCurrentAnalysis } from '../hooks/useCurrentAnalysis';
import { presentError } from '../lib/presentation';

// ─── helpers ──────────────────────────────────────────────────────────────────

const fmtDate = (d) => {
  if (!d) return '';
  return new Date(d).toLocaleDateString('en-IN', {
    day: '2-digit',
    month: 'short',
    year: '2-digit',
  });
};

const RISK_CONFIG = {
  'No stress evidence': {
    color: '#16a34a',
    bg: 'bg-emerald-50',
    border: 'border-emerald-200',
    text: 'text-emerald-800',
    badge: 'bg-emerald-100 text-emerald-800',
    icon: CheckCircle,
    dot: '#16a34a',
  },
  'Possible stress': {
    color: '#d97706',
    bg: 'bg-amber-50',
    border: 'border-amber-200',
    text: 'text-amber-800',
    badge: 'bg-amber-100 text-amber-800',
    icon: AlertTriangle,
    dot: '#d97706',
  },
  'Moderate stress risk': {
    color: '#ea580c',
    bg: 'bg-orange-50',
    border: 'border-orange-200',
    text: 'text-orange-800',
    badge: 'bg-orange-100 text-orange-800',
    icon: TrendingDown,
    dot: '#ea580c',
  },
  'High stress risk': {
    color: '#dc2626',
    bg: 'bg-red-50',
    border: 'border-red-200',
    text: 'text-red-800',
    badge: 'bg-red-100 text-red-800',
    icon: ShieldAlert,
    dot: '#dc2626',
  },
  'Insufficient data': {
    color: '#64748b',
    bg: 'bg-slate-50',
    border: 'border-slate-200',
    text: 'text-slate-700',
    badge: 'bg-slate-100 text-slate-700',
    icon: Info,
    dot: '#94a3b8',
  },
};

const getRiskConfig = (risk) => RISK_CONFIG[risk] || RISK_CONFIG['Insufficient data'];

const ScoreBar = ({ score }) => {
  if (score == null) return null;
  const pct = Math.round(score * 100);
  const color =
    pct >= 60 ? '#dc2626' : pct >= 40 ? '#ea580c' : pct >= 20 ? '#d97706' : '#16a34a';
  return (
    <div className="mt-3">
      <div className="flex justify-between text-xs text-slate-500 mb-1">
        <span>Evidence score</span>
        <span className="font-semibold" style={{ color }}>{pct} / 100</span>
      </div>
      <div className="h-2 rounded-full bg-slate-100 overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-700"
          style={{ width: `${pct}%`, backgroundColor: color }}
        />
      </div>
      <div className="flex justify-between text-[10px] text-slate-400 mt-0.5">
        <span>No evidence</span>
        <span>Possible</span>
        <span>Moderate</span>
        <span>High</span>
      </div>
    </div>
  );
};

const CustomTooltipOptical = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-white border border-slate-200 rounded-xl shadow-lg p-3 text-xs">
      <p className="font-semibold text-slate-700 mb-1">{fmtDate(label)}</p>
      {payload.map((p) => (
        <p key={p.dataKey} style={{ color: p.color }}>
          {p.name}: {p.value != null ? p.value.toFixed(3) : '—'}
        </p>
      ))}
    </div>
  );
};

const CustomTooltipRadar = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-white border border-slate-200 rounded-xl shadow-lg p-3 text-xs">
      <p className="font-semibold text-slate-700 mb-1">{fmtDate(label)}</p>
      {payload.map((p) => (
        <p key={p.dataKey} style={{ color: p.color }}>
          {p.name}: {p.value != null ? `${p.value.toFixed(2)} dB` : '—'}
        </p>
      ))}
    </div>
  );
};

// ─── Explanation pills ────────────────────────────────────────────────────────
const Pill = ({ label, desc }) => (
  <div className="flex items-start gap-2 rounded-xl border border-slate-100 bg-slate-50 px-3 py-2">
    <Info className="mt-0.5 h-3.5 w-3.5 shrink-0 text-slate-400" />
    <div>
      <span className="text-xs font-semibold text-slate-700">{label}</span>
      <span className="text-xs text-slate-500 ml-1">— {desc}</span>
    </div>
  </div>
);

// ─── Main component ────────────────────────────────────────────────────────────
export const WaterStress = () => {
  const { activeField } = useApp();
  const { analysis: latestAnalysis, loading, error } = useCurrentAnalysis();

  const stress = latestAnalysis?.moisture_stress ?? null;
  const crop = latestAnalysis?.crop ?? null;
  const stage = latestAnalysis?.growth_stage ?? null;
  const charts = useMemo(() => latestAnalysis?.charts ?? {}, [latestAnalysis?.charts]);

  const optical = useMemo(() => {
    const raw = stress?.chart_data?.optical ?? charts?.stress_optical ?? [];
    return raw.map((r) => ({ ...r, dateLabel: r.date }));
  }, [stress, charts]);

  const radar = useMemo(() => {
    const raw = stress?.chart_data?.radar ?? charts?.stress_radar ?? [];
    return raw.map((r) => ({ ...r, dateLabel: r.date }));
  }, [stress, charts]);

  // Stress markers (dates with anomalies) for optical chart reference lines
  const markerDates = useMemo(
    () => optical.filter((r) => r.stress_marker).map((r) => r.date),
    [optical]
  );

  if (loading) return <LoadingSpinner />;
  if (error && !latestAnalysis) {
    const message = presentError(error);
    return <EmptyState title={message.title} description={message.message} icon={AlertTriangle} />;
  }

  // Non-Paddy skip
  if (crop && crop.class_label !== 'Paddy') {
    return (
      <div className="space-y-6 font-sans text-slate-800 pb-12">
        <SectionHeader
          title="Moisture-Stress Risk"
          subtitle={`Not available for ${activeField?.name}`}
        />
        <EmptyState
          title="Only available for Paddy fields"
          description="Moisture-stress analysis is currently supported only for Paddy crops. This field is classified as Non-Paddy."
          icon={Leaf}
        />
      </div>
    );
  }

  // No analysis yet
  if (!latestAnalysis) {
    return (
      <div className="space-y-6 font-sans text-slate-800 pb-12">
        <SectionHeader
          title="Moisture-Stress Risk"
          subtitle={activeField ? `No analysis found for ${activeField.name}` : 'No field selected'}
        />
        <EmptyState
          title="Run an analysis first"
          description="Submit a field analysis in My Fields to see moisture-stress diagnostics."
          icon={Droplets}
        />
      </div>
    );
  }

  // Paddy but no stress (shouldn't normally happen — gate failure logged as warning)
  if (!stress) {
    return (
      <div className="space-y-6 font-sans text-slate-800 pb-12">
        <SectionHeader
          title="Moisture-Stress Risk"
          subtitle={`${activeField?.name ?? 'Field'} — data not available`}
        />
        <EmptyState
          title="Stress data not available"
          description="The moisture-stress module did not produce a result for this analysis. Check the analysis warnings."
          icon={Info}
        />
      </div>
    );
  }

  const riskLabel =
    stress.status === 'insufficient_data' ? 'Insufficient data' : (stress.stress_risk ?? 'Insufficient data');
  const cfg = getRiskConfig(riskLabel);
  const RiskIcon = cfg.icon;

  return (
    <div className="space-y-6 font-sans text-slate-800 pb-12">
      {/* ── Header ── */}
      <SectionHeader
        title="Moisture-Stress Risk"
        subtitle={`${activeField?.name ?? 'Field'} · Satellite-based provisional assessment`}
        action={
          <div
            className={`flex items-center space-x-2 border px-3.5 py-1.5 rounded-full text-xs font-bold shadow-sm ${cfg.badge} ${cfg.border}`}
          >
            <RiskIcon className="w-4 h-4" />
            <span>{riskLabel}</span>
          </div>
        }
      />

      {/* ── Provisional warning banner ── */}
      <div className="rounded-2xl border border-amber-200 bg-amber-50 px-5 py-4 flex items-start gap-3">
        <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-600" />
        <p className="text-sm text-amber-800 leading-relaxed">
          <strong>Provisional only.</strong>{' '}
          {stress.warning ??
            'Satellite signals may be affected by clouds, crop senescence, harvest, or sensor artefacts. This is not a confirmed water-shortage diagnosis.'}
        </p>
      </div>

      {/* ── Risk summary card ── */}
      <div className={`rounded-2xl border p-6 ${cfg.bg} ${cfg.border}`}>
        <div className="flex items-center gap-3 mb-2">
          <RiskIcon className="h-6 w-6" style={{ color: cfg.color }} />
          <h2 className={`text-xl font-bold ${cfg.text}`}>{riskLabel}</h2>
          {stress.provisional && (
            <span className="text-[10px] font-bold uppercase tracking-wider bg-white/60 border border-current/20 rounded px-2 py-0.5 text-slate-500">
              Provisional
            </span>
          )}
        </div>
        <div className="flex flex-wrap gap-4 text-sm text-slate-600 mt-1">
          {stress.latest_observation_date && (
            <span>
              <span className="font-medium">Latest obs:</span>{' '}
              {fmtDate(stress.latest_observation_date)}
            </span>
          )}
          {stage?.stage && (
            <span>
              <span className="font-medium">Stage:</span> {stage.stage}
            </span>
          )}
          {stress.persistence_observations != null && (
            <span>
              <span className="font-medium">Consecutive anomalies:</span>{' '}
              {stress.persistence_observations}
            </span>
          )}
        </div>
        <ScoreBar score={stress.stress_score} />
      </div>

      {/* ── Evidence / Counter-evidence ── */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        {/* Evidence */}
        <div className="rounded-2xl border border-slate-200 bg-white p-5">
          <div className="flex items-center gap-2 mb-3">
            <TrendingDown className="h-4 w-4 text-orange-500" />
            <h3 className="font-semibold text-slate-900 text-sm">Supporting evidence</h3>
          </div>
          {stress.evidence?.length > 0 ? (
            <ul className="space-y-2">
              {stress.evidence.map((e, i) => (
                <li key={i} className="flex items-start gap-2 text-sm text-slate-700">
                  <span className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-orange-400" />
                  {e}
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-slate-500 italic">No stress evidence found.</p>
          )}
        </div>

        {/* Counter-evidence */}
        <div className="rounded-2xl border border-slate-200 bg-white p-5">
          <div className="flex items-center gap-2 mb-3">
            <TrendingUp className="h-4 w-4 text-emerald-500" />
            <h3 className="font-semibold text-slate-900 text-sm">Counter-evidence</h3>
          </div>
          {stress.counter_evidence?.length > 0 ? (
            <ul className="space-y-2">
              {stress.counter_evidence.map((e, i) => (
                <li key={i} className="flex items-start gap-2 text-sm text-slate-700">
                  <span className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-emerald-400" />
                  {e}
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-slate-500 italic">No counter-evidence.</p>
          )}
        </div>
      </div>

      {/* ── Vegetation & Moisture chart ── */}
      <div className="rounded-2xl border border-slate-200 bg-white p-5">
        <div className="flex items-center gap-2 mb-1">
          <Activity className="h-4 w-4 text-indigo-500" />
          <h3 className="font-semibold text-slate-900 text-sm">Vegetation &amp; moisture timeline</h3>
        </div>
        <p className="text-xs text-slate-400 mb-4">
          Orange vertical lines mark dates where NDMI fell below the field baseline.
        </p>
        {optical.length > 0 ? (
          <ResponsiveContainer width="100%" height={280}>
            <LineChart data={optical} margin={{ top: 4, right: 12, left: -10, bottom: 4 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
              <XAxis
                dataKey="dateLabel"
                tickFormatter={fmtDate}
                tick={{ fontSize: 10, fill: '#94a3b8' }}
                tickLine={false}
              />
              <YAxis
                domain={[-0.3, 1]}
                tick={{ fontSize: 10, fill: '#94a3b8' }}
                tickLine={false}
                axisLine={false}
              />
              <RechartsTooltip content={<CustomTooltipOptical />} />
              <Legend
                iconType="circle"
                iconSize={8}
                wrapperStyle={{ fontSize: 11, paddingTop: 8 }}
              />
              {markerDates.map((d) => (
                <ReferenceLine key={d} x={d} stroke="#ea580c" strokeDasharray="4 3" strokeWidth={1.5} />
              ))}
              <Line
                type="monotone"
                dataKey="ndvi"
                name="NDVI"
                stroke="#16a34a"
                strokeWidth={2}
                dot={{ r: 3, fill: '#16a34a' }}
                activeDot={{ r: 5 }}
                connectNulls
              />
              <Line
                type="monotone"
                dataKey="ndmi"
                name="NDMI"
                stroke="#0284c7"
                strokeWidth={2}
                dot={{ r: 3, fill: '#0284c7' }}
                activeDot={{ r: 5 }}
                connectNulls
              />
              <Line
                type="monotone"
                dataKey="ndwi"
                name="NDWI"
                stroke="#7c3aed"
                strokeWidth={1.5}
                strokeDasharray="5 3"
                dot={false}
                connectNulls
              />
            </LineChart>
          </ResponsiveContainer>
        ) : (
          <div className="h-40 flex items-center justify-center text-sm text-slate-400">
            No optical time-series data available.
          </div>
        )}
      </div>

      {/* ── Radar chart ── */}
      <div className="rounded-2xl border border-slate-200 bg-white p-5">
        <div className="flex items-center gap-2 mb-1">
          <Radio className="h-4 w-4 text-violet-500" />
          <h3 className="font-semibold text-slate-900 text-sm">Sentinel-1 radar timeline</h3>
        </div>
        <p className="text-xs text-slate-400 mb-4">
          SAR backscatter values in dB. Lower values may indicate reduced canopy or surface moisture.
        </p>
        {radar.length > 0 ? (
          <ResponsiveContainer width="100%" height={240}>
            <LineChart data={radar} margin={{ top: 4, right: 12, left: -10, bottom: 4 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
              <XAxis
                dataKey="dateLabel"
                tickFormatter={fmtDate}
                tick={{ fontSize: 10, fill: '#94a3b8' }}
                tickLine={false}
              />
              <YAxis
                tick={{ fontSize: 10, fill: '#94a3b8' }}
                tickLine={false}
                axisLine={false}
                tickFormatter={(v) => `${v} dB`}
              />
              <RechartsTooltip content={<CustomTooltipRadar />} />
              <Legend
                iconType="circle"
                iconSize={8}
                wrapperStyle={{ fontSize: 11, paddingTop: 8 }}
              />
              <Line
                type="monotone"
                dataKey="vv"
                name="VV"
                stroke="#7c3aed"
                strokeWidth={2}
                dot={{ r: 3, fill: '#7c3aed' }}
                activeDot={{ r: 5 }}
                connectNulls
              />
              <Line
                type="monotone"
                dataKey="vh"
                name="VH"
                stroke="#c026d3"
                strokeWidth={2}
                dot={{ r: 3, fill: '#c026d3' }}
                activeDot={{ r: 5 }}
                connectNulls
              />
              <Line
                type="monotone"
                dataKey="vv_minus_vh"
                name="VV − VH"
                stroke="#0ea5e9"
                strokeWidth={1.5}
                strokeDasharray="5 3"
                dot={false}
                connectNulls
              />
            </LineChart>
          </ResponsiveContainer>
        ) : (
          <div className="h-36 flex items-center justify-center text-sm text-slate-400">
            No radar time-series data available.
          </div>
        )}
      </div>

      {/* ── Indicator explanations ── */}
      <div className="rounded-2xl border border-slate-200 bg-white p-5">
        <div className="flex items-center gap-2 mb-3">
          <Info className="h-4 w-4 text-slate-400" />
          <h3 className="font-semibold text-slate-900 text-sm">What these indicators mean</h3>
        </div>
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
          <Pill label="NDVI" desc="Crop greenness and canopy condition. Derived from Sentinel-2 near-infrared and red bands." />
          <Pill label="NDMI" desc="Vegetation moisture-related signal. Sensitive to canopy water content." />
          <Pill label="NDWI" desc="Water body and surface moisture indicator. Lower values may suggest drier conditions." />
          <Pill label="VV / VH" desc="Sentinel-1 radar backscatter (dB). Responds to field structure and surface roughness." />
          <Pill label="VV − VH" desc="Cross-polarisation difference. Can indicate changes in canopy volume." />
          <Pill label="Stress score" desc="Rule-based evidence accumulation score (0–1). Not a probability. Provisional only." />
        </div>
      </div>

      {/* ── Provenance ── */}
      <div className="rounded-xl border border-slate-100 bg-slate-50 px-4 py-3 flex flex-wrap gap-x-6 gap-y-1 text-xs text-slate-500">
        <span><strong>Rule version:</strong> {stress.stress_rule_version ?? '—'}</span>
        <span><strong>Stage context:</strong> {stress.stage_context ?? '—'}</span>
        <span><strong>Stage evidence:</strong> {stress.stage_evidence ?? '—'}</span>
      </div>
    </div>
  );
};
