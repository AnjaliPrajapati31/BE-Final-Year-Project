import { useEffect, useMemo, useState } from 'react';
import { Link, useLocation, useSearchParams } from 'react-router-dom';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
} from 'recharts';
import {
  MapPin,
  Maximize2,
  Sprout,
  TrendingUp,
  Droplets,
  Calendar,
  CheckCircle,
  Activity,
  Award,
  Info,
  AlertTriangle,
  Database,
} from 'lucide-react';
import { EmptyState, LoadingSpinner, SectionHeader } from '../components/UIHelpers';
import { useApp } from '../contexts/AppContext';
import { ApiError, extractBoundaryPoints, getAnalysis } from '../services/api';

const formatDate = (value) => {
  if (!value) return 'Not available';
  return new Date(value).toLocaleDateString('en-IN', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  });
};

const formatDateTime = (value) => {
  if (!value) return 'Not available';
  return new Date(value).toLocaleString('en-IN', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
};

const formatPercent = (value) => {
  if (value === null || value === undefined) return 'Not available';
  return `${(Number(value) * 100).toFixed(1)}%`;
};

const formatArea = (value) => {
  if (value === null || value === undefined) return 'Not available';
  const hectares = Number(value) / 10000;
  const acres = Number(value) * 0.000247105;
  return {
    sqMeters: `${Number(value).toLocaleString('en-IN', { maximumFractionDigits: 0 })} m²`,
    hectares: `${hectares.toFixed(2)} ha`,
    acres: `${acres.toFixed(2)} acres`,
  };
};

export const Dashboard = () => {
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const { fieldBoundaryPoints, latestAnalysisSummary, setLatestAnalysisSummary } = useApp();
  const requestId = searchParams.get('requestId');
  const fieldId = searchParams.get('fieldId');
  const [analysis, setAnalysis] = useState(location.state?.analysis || latestAnalysisSummary || null);
  const [loading, setLoading] = useState(Boolean(requestId));
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!requestId) {
      return;
    }
    let cancelled = false;
    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        const result = await getAnalysis(requestId);
        if (!cancelled) {
          setAnalysis(result);
          setLatestAnalysisSummary(result);
        }
      } catch (loadError) {
        if (!cancelled) {
          setError(loadError instanceof ApiError ? loadError : new ApiError(loadError.message));
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };
    load();
    return () => {
      cancelled = true;
    };
  }, [requestId, setLatestAnalysisSummary]);

  const coordinatesToDisplay = useMemo(() => {
    const geometryPoints = extractBoundaryPoints(analysis?.geometry?.geojson);
    const sourcePoints = geometryPoints.length > 0 ? geometryPoints : fieldBoundaryPoints;
    return sourcePoints.map((point, index) => ({
      id: index + 1,
      label: `Point ${index + 1}`,
      lat: point.lat,
      lng: point.lng,
    }));
  }, [analysis?.geometry?.geojson, fieldBoundaryPoints]);

  const area = formatArea(analysis?.geometry?.area_m2);
  const chartData = analysis?.charts?.stage_timeline || [];
  const crop = analysis?.crop;
  const stage = analysis?.growth_stage;
  const warnings = analysis?.warnings || [];

  if (!requestId && !analysis) {
    return (
      <EmptyState
        title="No analysis selected"
        description="Draw a Cauvery field polygon and submit it from My Fields to load a stored crop analysis."
        icon={Info}
      />
    );
  }

  if (loading && !analysis) {
    return <LoadingSpinner />;
  }

  if (error && !analysis) {
    return (
      <EmptyState
        title={error.code || 'Analysis load failed'}
        description={`${error.message}${error.requestId ? ` Request ID: ${error.requestId}` : ''}`}
        icon={AlertTriangle}
      />
    );
  }

  return (
    <div className="space-y-6 font-sans text-slate-800 pb-12">
      <SectionHeader
        title="Crop Analytics Overview"
        subtitle={`Stored FastAPI analysis for ${analysis?.field_id || fieldId || 'selected field'}`}
        action={
          <div className="flex items-center space-x-2 bg-emerald-50 border border-emerald-200 text-emerald-800 px-3.5 py-1.5 rounded-full text-xs font-bold shadow-2xs">
            <Database className="w-4 h-4 text-emerald-700" />
            <span>{analysis?.provider?.live_data ? 'Live Earth Engine Data' : 'Stored Analysis'}</span>
          </div>
        }
      />

      {error && (
        <div className="flex items-start gap-3 rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
          <div>
            <div className="font-semibold">{error.message}</div>
            <div className="text-xs text-amber-700">
              {error.code}
              {error.requestId ? ` · Request ID ${error.requestId}` : ''}
            </div>
          </div>
        </div>
      )}

      {warnings.length > 0 && (
        <div className="rounded-2xl border border-amber-200 bg-amber-50 px-5 py-4">
          <div className="mb-2 text-sm font-bold text-amber-900">Warnings</div>
          <ul className="space-y-1 text-sm text-amber-900">
            {warnings.map((warning) => (
              <li key={warning}>• {warning}</li>
            ))}
          </ul>
        </div>
      )}

      <div>
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center space-x-2 text-xs font-bold uppercase tracking-wider text-emerald-800">
            <MapPin className="w-4 h-4 text-emerald-600" />
            <span>Field Boundary Coordinates ({coordinatesToDisplay.length} Vertices)</span>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {coordinatesToDisplay.map((pt) => (
            <div
              key={pt.id}
              className="bg-white rounded-2xl p-5 border border-emerald-200/80 shadow-xs hover:shadow-md transition-all hover:border-emerald-400 group"
            >
              <div className="flex items-center justify-between mb-3">
                <span className="w-8 h-8 rounded-xl bg-emerald-100 text-emerald-800 font-extrabold text-xs flex items-center justify-center group-hover:bg-emerald-700 group-hover:text-white transition-colors">
                  P{pt.id}
                </span>
                <span className="text-[11px] font-bold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-md border border-emerald-200/60">
                  {pt.label}
                </span>
              </div>

              <div className="space-y-1.5">
                <div>
                  <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Latitude</p>
                  <p className="text-sm font-extrabold text-slate-900 font-mono">{pt.lat.toFixed(5)}° N</p>
                </div>
                <div>
                  <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Longitude</p>
                  <p className="text-sm font-extrabold text-slate-900 font-mono">{pt.lng.toFixed(5)}° E</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <div className="bg-white rounded-2xl p-6 border border-emerald-200/80 shadow-xs flex flex-col justify-between hover:shadow-md transition-all">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center space-x-3">
              <div className="w-12 h-12 rounded-2xl bg-emerald-100 text-emerald-800 flex items-center justify-center shadow-xs">
                <Maximize2 className="w-6 h-6" />
              </div>
              <div>
                <h3 className="text-base font-bold text-slate-900 font-serif">Total Field Area</h3>
                <p className="text-xs text-slate-500">Calculated GIS surface area</p>
              </div>
            </div>
            <span className="px-3 py-1 bg-emerald-50 text-emerald-700 rounded-full text-xs font-bold border border-emerald-200">
              {area.sqMeters}
            </span>
          </div>

          <div className="flex items-baseline space-x-4 pt-2">
            <div>
              <p className="text-3xl font-extrabold text-slate-900 font-serif">{area.hectares}</p>
              <p className="text-xs font-semibold text-emerald-700">Metric Hectares</p>
            </div>
            <div className="h-10 w-[1px] bg-emerald-100" />
            <div>
              <p className="text-2xl font-bold text-slate-700 font-serif">{area.acres}</p>
              <p className="text-xs font-medium text-slate-500">Imperial Acres</p>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-2xl p-6 border border-emerald-200/80 shadow-xs flex flex-col justify-between hover:shadow-md transition-all">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center space-x-3">
              <div className="w-12 h-12 rounded-2xl bg-emerald-100 text-emerald-800 flex items-center justify-center shadow-xs">
                <Sprout className="w-6 h-6" />
              </div>
              <div>
                <h3 className="text-base font-bold text-slate-900 font-serif">Crop Type Identification</h3>
                <p className="text-xs text-slate-500">
                  {analysis?.provider?.name || 'Unknown provider'} · {analysis?.status || 'unknown'}
                </p>
              </div>
            </div>
            <span className="px-3 py-1 bg-emerald-50 text-emerald-700 rounded-full text-xs font-bold border border-emerald-200 flex items-center space-x-1">
              <CheckCircle className="w-3.5 h-3.5 text-emerald-600" />
              <span>{formatPercent(crop?.confidence)}</span>
            </span>
          </div>

          <div className="flex items-center justify-between pt-2">
            <div>
              <p className="text-2xl font-extrabold text-slate-900 font-serif">{crop?.class_label || 'Not available'}</p>
              <p className="text-xs font-semibold text-emerald-700">
                Paddy {formatPercent(crop?.paddy_probability)} · Non-Paddy {formatPercent(crop?.non_paddy_probability)}
              </p>
            </div>
            <div className="flex items-center space-x-1.5 text-xs text-emerald-800 font-semibold bg-emerald-50 px-3 py-1.5 rounded-xl border border-emerald-200">
              <CheckCircle className="w-4 h-4 text-emerald-600" />
              <span>{analysis?.provider?.cached ? 'Cached Real Data' : 'Fresh Analysis'}</span>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        <div className="lg:col-span-5 bg-white rounded-2xl p-6 border border-emerald-200/80 shadow-xs flex flex-col justify-between space-y-5">
          <div>
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center space-x-3">
                <div className="w-12 h-12 rounded-2xl bg-emerald-100 text-emerald-800 flex items-center justify-center shadow-xs">
                  <TrendingUp className="w-6 h-6" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-slate-900 font-serif">Crop Growth Stage</h3>
                  <p className="text-xs text-slate-500">{stage?.status || 'not_available'}</p>
                </div>
              </div>
              <span className="px-2.5 py-1 bg-emerald-100 text-emerald-800 rounded-full text-xs font-bold">
                {stage?.evidence || 'No stage evidence'}
              </span>
            </div>

            <div className="space-y-3 pt-2">
              <h4 className="text-xl font-extrabold text-slate-900 font-serif">
                {stage?.stage || 'Growth stage not available'}
              </h4>
              <p className="text-xs text-emerald-800 font-semibold">
                Status: {stage?.reason_code || stage?.status || 'Not available'}
              </p>

              <div className="grid grid-cols-2 gap-3 text-xs text-slate-700 pt-1">
                <div>
                  <div className="font-bold text-slate-900">Cycle Start</div>
                  <div>{formatDate(stage?.cycle_start)}</div>
                </div>
                <div>
                  <div className="font-bold text-slate-900">Latest Observation</div>
                  <div>{formatDate(stage?.latest_observation)}</div>
                </div>
                <div>
                  <div className="font-bold text-slate-900">Current Cycle Count</div>
                  <div>{stage?.current_cycle_count ?? 'Not available'}</div>
                </div>
                <div>
                  <div className="font-bold text-slate-900">Peak Confirmed</div>
                  <div>{stage?.peak_confirmed ? 'Yes' : 'No'}</div>
                </div>
              </div>
            </div>
          </div>

          <div className="bg-emerald-50/70 rounded-xl p-3.5 border border-emerald-200/60 flex items-center space-x-3 text-xs text-emerald-900">
            <Info className="w-4 h-4 text-emerald-700 shrink-0" />
            <span>{stage?.warning || analysis?.explanations?.confidence || 'Stored model explanation available.'}</span>
          </div>
        </div>

        <div className="lg:col-span-7 bg-white rounded-2xl p-6 border border-emerald-200/80 shadow-xs flex flex-col justify-between space-y-4">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 rounded-xl bg-emerald-100 text-emerald-800 flex items-center justify-center shrink-0">
                <Droplets className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-base font-bold text-slate-900 font-serif">
                  Stage Timeline
                </h3>
                <p className="text-xs text-slate-500">
                  Clean optical time series returned by the stored analysis
                </p>
              </div>
            </div>
            <span className="text-xs font-extrabold text-emerald-700 bg-emerald-50 px-3 py-1 rounded-full border border-emerald-200">
              {chartData.length} S2 observations
            </span>
          </div>

          <div className="h-64 w-full pt-2">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="ndmiGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#059669" stopOpacity={0.4} />
                    <stop offset="95%" stopColor="#059669" stopOpacity={0.0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
                <XAxis dataKey="date" tick={{ fontSize: 11, fill: '#64748b' }} axisLine={false} tickLine={false} />
                <YAxis domain={[0, 1]} tick={{ fontSize: 11, fill: '#64748b' }} axisLine={false} tickLine={false} />
                <RechartsTooltip
                  contentStyle={{ backgroundColor: '#ffffff', borderRadius: '12px', border: '1px solid #a7f3d0', boxShadow: '0 4px 12px rgba(0,0,0,0.05)' }}
                  labelStyle={{ fontWeight: 'bold', color: '#065f46', fontSize: '12px' }}
                />
                <Area
                  type="monotone"
                  dataKey="ndmi"
                  name="NDMI Index"
                  stroke="#059669"
                  strokeWidth={3}
                  fillOpacity={1}
                  fill="url(#ndmiGradient)"
                />
                <Area
                  type="monotone"
                  dataKey="ndvi"
                  name="NDVI Index"
                  stroke="#10b981"
                  strokeWidth={2}
                  fillOpacity={0}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      <div className="bg-white rounded-2xl p-6 border border-emerald-200/80 shadow-xs space-y-4 hover:shadow-md transition-all">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between border-b border-slate-100 pb-3 gap-2">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-emerald-100 text-emerald-800 flex items-center justify-center shrink-0">
              <Activity className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-slate-900 font-serif">
                Crop Probability Summary
              </h3>
              <p className="text-xs text-slate-500">
                Field-mask means returned by the production SICKLE fusion model
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-3">
            <span className="text-xs font-extrabold text-emerald-700 bg-emerald-50 px-3 py-1 rounded-full border border-emerald-200">
              Provider {analysis?.provider?.name}
            </span>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pt-2">
          <div className="space-y-4">
            <div>
              <div className="mb-1 flex items-center justify-between text-sm font-semibold text-slate-800">
                <span>Paddy Probability</span>
                <span>{formatPercent(crop?.paddy_probability)}</span>
              </div>
              <div className="h-3 overflow-hidden rounded-full bg-slate-100">
                <div className="h-full rounded-full bg-emerald-600" style={{ width: formatPercent(crop?.paddy_probability) }} />
              </div>
            </div>
            <div>
              <div className="mb-1 flex items-center justify-between text-sm font-semibold text-slate-800">
                <span>Non-Paddy Probability</span>
                <span>{formatPercent(crop?.non_paddy_probability)}</span>
              </div>
              <div className="h-3 overflow-hidden rounded-full bg-slate-100">
                <div className="h-full rounded-full bg-slate-700" style={{ width: formatPercent(crop?.non_paddy_probability) }} />
              </div>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3 text-sm text-slate-700">
            <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
              <div className="text-xs font-bold uppercase tracking-wider text-slate-500">Field Pixels</div>
              <div className="mt-1 text-lg font-extrabold text-slate-900">{crop?.field_pixel_count ?? 'Not available'}</div>
            </div>
            <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
              <div className="text-xs font-bold uppercase tracking-wider text-slate-500">S1 / S2 Obs</div>
              <div className="mt-1 text-lg font-extrabold text-slate-900">{crop ? `${crop.s1_observation_count} / ${crop.s2_observation_count}` : 'Not available'}</div>
            </div>
            <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
              <div className="text-xs font-bold uppercase tracking-wider text-slate-500">Paddy Pixel Fraction</div>
              <div className="mt-1 text-lg font-extrabold text-slate-900">{formatPercent(crop?.paddy_pixel_fraction)}</div>
            </div>
            <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
              <div className="text-xs font-bold uppercase tracking-wider text-slate-500">Non-Paddy Pixel Fraction</div>
              <div className="mt-1 text-lg font-extrabold text-slate-900">{formatPercent(crop?.non_paddy_pixel_fraction)}</div>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        <div className="bg-white rounded-2xl p-6 border border-emerald-200/80 shadow-xs flex items-center justify-between hover:shadow-md transition-all">
          <div className="flex items-center space-x-4">
            <div className="w-12 h-12 rounded-2xl bg-emerald-100 text-emerald-800 flex items-center justify-center shrink-0 shadow-xs">
              <Calendar className="w-6 h-6" />
            </div>
            <div>
              <p className="text-xs font-bold uppercase tracking-wider text-slate-400">Analysis Request ID</p>
              <h4 className="text-2xl font-extrabold text-slate-900 font-serif mt-0.5">
                {analysis?.request_id || requestId}
              </h4>
              <p className="text-xs text-emerald-700 font-semibold mt-0.5">
                Field code {analysis?.field_id || fieldId || 'Not available'}
              </p>
            </div>
          </div>

          <span className="hidden sm:block px-3 py-1 bg-emerald-50 text-emerald-700 text-xs font-bold rounded-full border border-emerald-200">
            ROI v{analysis?.provenance?.roi_version ?? 'N/A'}
          </span>
        </div>

        <div className="bg-white rounded-2xl p-6 border border-emerald-200/80 shadow-xs flex items-center justify-between hover:shadow-md transition-all">
          <div className="flex items-center space-x-4">
            <div className="w-12 h-12 rounded-2xl bg-emerald-100 text-emerald-800 flex items-center justify-center shrink-0 shadow-xs">
              <Award className="w-6 h-6" />
            </div>
            <div>
              <p className="text-xs font-bold uppercase tracking-wider text-slate-400">Stored Analysis</p>
              <h4 className="text-2xl font-extrabold text-slate-900 font-serif mt-0.5">
                {formatDateTime(analysis?.data_quality?.analysis_cutoff)}
              </h4>
              <p className="text-xs text-emerald-700 font-semibold mt-0.5">
                Model {analysis?.provenance?.model || 'Not available'}
              </p>
            </div>
          </div>

          <span className="hidden sm:block px-3 py-1 bg-emerald-50 text-emerald-700 text-xs font-bold rounded-full border border-emerald-200">
            <Link to={`/history?fieldId=${encodeURIComponent(analysis?.field_id || fieldId || '')}`}>View History</Link>
          </span>
        </div>
      </div>
    </div>
  );
};
