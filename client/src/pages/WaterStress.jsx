import { useState } from 'react';
import {
  Droplets,
  Activity,
  Radio,
  CloudSun,
  Zap,
  CheckCircle,
  RefreshCw,
  Sparkles,
  Gauge,
  Info,
} from 'lucide-react';
import { SectionHeader } from '../components/UIHelpers';
import { useApp } from '../contexts/AppContext';

export const WaterStress = () => {
  const { activeField } = useApp();

  // Interactive state for fetching ET₀ and calculating Water Stress
  const [fetchingET0, setFetchingET0] = useState(false);
  const [et0Data, setEt0Data] = useState(null);

  const [calculatingStress, setCalculatingStress] = useState(false);
  const [waterStressResult, setWaterStressResult] = useState(null);

  // Core metrics requested by user
  const avgNdmi = {
    score: '0.68',
    status: 'Optimal Hydration',
    detail: 'Normalized Difference Moisture Index',
    trend: '+4.2% vs last week',
  };

  const avgNdvi = {
    score: '0.78',
    status: 'High Canopy Density',
    detail: 'Normalized Difference Vegetation Index',
    trend: '+6.1% vs last week',
  };

  const vvScore = {
    score: '-11.4 dB',
    normalized: '0.82',
    status: 'Strong Radar Backscatter',
    detail: 'Sentinel-1 SAR VV (Vertical-Vertical) Polarization',
    trend: 'Stable Soil Roughness',
  };

  // Handler for Fetching ET₀ Data
  const handleFetchET0 = () => {
    setFetchingET0(true);
    setTimeout(() => {
      setEt0Data({
        value: '4.85 mm/day',
        method: 'FAO-56 Penman-Monteith Standard',
        tempMax: '32.4°C',
        tempMin: '23.1°C',
        solarRadiation: '21.8 MJ/m²/day',
        vaporPressureDeficit: '1.42 kPa',
        windSpeed: '2.1 m/s (at 2m height)',
        relativeHumidity: '68%',
        fetchedAt: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      });
      setFetchingET0(false);
    }, 1200);
  };

  // Handler for Calculating Water Stress
  const handleCalculateWaterStress = () => {
    setCalculatingStress(true);
    setTimeout(() => {
      setWaterStressResult({
        cwsi: '0.22', // Crop Water Stress Index (0 = no stress, 1 = maximum stress)
        stressLevel: 'Low Water Deficit',
        statusColor: 'text-emerald-700 bg-emerald-50 border-emerald-200',
        recommendation: 'Field hydration is currently optimal. No immediate emergency irrigation required for the next 48 hours.',
        suggestedIrrigation: 'Maintain regular 12mm scheduled cycle on Wednesday night.',
        calculatedAt: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      });
      setCalculatingStress(false);
    }, 1400);
  };

  return (
    <div className="space-y-6 font-sans text-slate-800 pb-12">
      {/* Top Header */}
      <SectionHeader
        title="Water Stress Analysis & Diagnostics"
        subtitle={`Satellite multispectral & SAR radar water deficit profiling for ${activeField.name}`}
        action={
          <div className="flex items-center space-x-2 bg-emerald-50 border border-emerald-200 text-emerald-800 px-3.5 py-1.5 rounded-full text-xs font-bold shadow-2xs">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-ping"></span>
            <span>Live Satellite Radar Active</span>
          </div>
        }
      />

      {/* ==========================================
          ROW 1: THE THREE CORE METRIC CARDS
          ========================================== */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        {/* Card 1: Avg NDMI Score */}
        <div className="bg-white rounded-2xl p-6 border border-emerald-200/80 shadow-xs hover:shadow-md transition-all space-y-4">
          <div className="flex items-center justify-between">
            <div className="w-12 h-12 rounded-2xl bg-emerald-100 text-emerald-800 flex items-center justify-center shadow-xs">
              <Droplets className="w-6 h-6" />
            </div>
            <span className="px-3 py-1 bg-emerald-50 text-emerald-700 rounded-full text-xs font-bold border border-emerald-200">
              {avgNdmi.status}
            </span>
          </div>

          <div>
            <p className="text-xs font-bold uppercase tracking-wider text-slate-400">Average NDMI Score</p>
            <div className="flex items-baseline space-x-2 mt-1">
              <h3 className="text-3xl font-extrabold text-slate-900 font-serif">{avgNdmi.score}</h3>
              <span className="text-xs font-bold text-emerald-600">{avgNdmi.trend}</span>
            </div>
            <p className="text-xs text-slate-500 mt-1">{avgNdmi.detail}</p>
          </div>
        </div>

        {/* Card 2: Avg NDVI Score */}
        <div className="bg-white rounded-2xl p-6 border border-emerald-200/80 shadow-xs hover:shadow-md transition-all space-y-4">
          <div className="flex items-center justify-between">
            <div className="w-12 h-12 rounded-2xl bg-emerald-100 text-emerald-800 flex items-center justify-center shadow-xs">
              <Activity className="w-6 h-6" />
            </div>
            <span className="px-3 py-1 bg-emerald-50 text-emerald-700 rounded-full text-xs font-bold border border-emerald-200">
              {avgNdvi.status}
            </span>
          </div>

          <div>
            <p className="text-xs font-bold uppercase tracking-wider text-slate-400">Average NDVI Score</p>
            <div className="flex items-baseline space-x-2 mt-1">
              <h3 className="text-3xl font-extrabold text-slate-900 font-serif">{avgNdvi.score}</h3>
              <span className="text-xs font-bold text-emerald-600">{avgNdvi.trend}</span>
            </div>
            <p className="text-xs text-slate-500 mt-1">{avgNdvi.detail}</p>
          </div>
        </div>

        {/* Card 3: VV Score */}
        <div className="bg-white rounded-2xl p-6 border border-emerald-200/80 shadow-xs hover:shadow-md transition-all space-y-4">
          <div className="flex items-center justify-between">
            <div className="w-12 h-12 rounded-2xl bg-emerald-100 text-emerald-800 flex items-center justify-center shadow-xs">
              <Radio className="w-6 h-6" />
            </div>
            <span className="px-3 py-1 bg-emerald-50 text-emerald-700 rounded-full text-xs font-bold border border-emerald-200">
              Index: {vvScore.normalized}
            </span>
          </div>

          <div>
            <p className="text-xs font-bold uppercase tracking-wider text-slate-400">VV Backscatter Score</p>
            <div className="flex items-baseline space-x-2 mt-1">
              <h3 className="text-3xl font-extrabold text-slate-900 font-serif">{vvScore.score}</h3>
              <span className="text-xs font-bold text-slate-500">{vvScore.trend}</span>
            </div>
            <p className="text-xs text-slate-500 mt-1">{vvScore.detail}</p>
          </div>
        </div>
      </div>

      {/* ==========================================
          ROW 2: ACTION BUTTONS & DYNAMIC RESULTS
          ========================================== */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        
        {/* LEFT COLUMN: ET₀ DATA FETCHING BLOCK */}
        <div className="bg-white rounded-2xl p-6 border border-emerald-200/80 shadow-xs space-y-5 flex flex-col justify-between">
          <div className="space-y-3">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 rounded-xl bg-emerald-100 text-emerald-800 flex items-center justify-center shrink-0">
                <CloudSun className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-base font-bold text-slate-900 font-serif">
                  Reference Evapotranspiration (ET₀)
                </h3>
                <p className="text-xs text-slate-500">
                  Atmospheric evaporative demand calculated via FAO-56 Penman-Monteith model
                </p>
              </div>
            </div>

            {/* Fetch Button */}
            <button
              onClick={handleFetchET0}
              disabled={fetchingET0}
              className="w-full flex items-center justify-center space-x-2.5 bg-emerald-700 hover:bg-emerald-800 active:scale-[0.99] text-white font-extrabold text-sm py-3.5 px-6 rounded-xl shadow-md transition-all cursor-pointer disabled:opacity-75"
            >
              {fetchingET0 ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin text-emerald-200" />
                  <span>Fetching ET₀ Satellite Telemetry...</span>
                </>
              ) : (
                <>
                  <CloudSun className="w-4 h-4 text-emerald-300" />
                  <span>Fetch Data of ET₀ (Reference Evapotranspiration)</span>
                </>
              )}
            </button>
          </div>

          {/* ET₀ Result Card (Rendered after fetching) */}
          {et0Data ? (
            <div className="bg-emerald-50/70 rounded-2xl p-5 border border-emerald-200 space-y-4 animate-fadeIn">
              <div className="flex items-center justify-between border-b border-emerald-200/60 pb-3">
                <span className="text-xs font-bold text-emerald-900">ET₀ Value Calculated</span>
                <span className="text-[11px] font-semibold text-emerald-700 bg-white px-2.5 py-0.5 rounded-full border border-emerald-200">
                  Synced at {et0Data.fetchedAt}
                </span>
              </div>

              <div className="flex items-baseline space-x-3">
                <span className="text-3xl font-extrabold text-emerald-950 font-serif">{et0Data.value}</span>
                <span className="text-xs font-medium text-emerald-800">{et0Data.method}</span>
              </div>

              <div className="grid grid-cols-2 gap-3 text-xs pt-1 border-t border-emerald-200/60">
                <div>
                  <p className="text-[10px] uppercase font-bold text-emerald-700">Solar Radiation</p>
                  <p className="font-bold text-slate-800">{et0Data.solarRadiation}</p>
                </div>
                <div>
                  <p className="text-[10px] uppercase font-bold text-emerald-700">Vapor Deficit (VPD)</p>
                  <p className="font-bold text-slate-800">{et0Data.vaporPressureDeficit}</p>
                </div>
                <div>
                  <p className="text-[10px] uppercase font-bold text-emerald-700">Temperature Window</p>
                  <p className="font-bold text-slate-800">{et0Data.tempMin} - {et0Data.tempMax}</p>
                </div>
                <div>
                  <p className="text-[10px] uppercase font-bold text-emerald-700">Wind Speed (2m)</p>
                  <p className="font-bold text-slate-800">{et0Data.windSpeed}</p>
                </div>
              </div>
            </div>
          ) : (
            <div className="bg-slate-50 rounded-2xl p-6 border border-slate-200/80 text-center space-y-2">
              <Info className="w-6 h-6 text-slate-400 mx-auto" />
              <p className="text-xs font-medium text-slate-500">
                Click the button above to fetch real-time ET₀ reference evapotranspiration telemetry.
              </p>
            </div>
          )}
        </div>

        {/* RIGHT COLUMN: WATER STRESS CALCULATION BLOCK */}
        <div className="bg-white rounded-2xl p-6 border border-emerald-200/80 shadow-xs space-y-5 flex flex-col justify-between">
          <div className="space-y-3">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 rounded-xl bg-emerald-100 text-emerald-800 flex items-center justify-center shrink-0">
                <Gauge className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-base font-bold text-slate-900 font-serif">
                  Water Stress Diagnostic Engine
                </h3>
                <p className="text-xs text-slate-500">
                  Combines NDMI, NDVI, VV SAR backscatter & ET₀ to evaluate root-zone stress
                </p>
              </div>
            </div>

            {/* Get Water Stress Button */}
            <button
              onClick={handleCalculateWaterStress}
              disabled={calculatingStress}
              className="w-full flex items-center justify-center space-x-2.5 bg-emerald-700 hover:bg-emerald-800 active:scale-[0.99] text-white font-extrabold text-sm py-3.5 px-6 rounded-xl shadow-md transition-all cursor-pointer disabled:opacity-75"
            >
              {calculatingStress ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin text-emerald-200" />
                  <span>Calculating Crop Water Stress Index...</span>
                </>
              ) : (
                <>
                  <Zap className="w-4 h-4 text-emerald-300" />
                  <span>Get Water Stress</span>
                </>
              )}
            </button>
          </div>

          {/* Water Stress Diagnostic Result Card (Rendered after calculation) */}
          {waterStressResult ? (
            <div className="bg-emerald-50/70 rounded-2xl p-5 border border-emerald-200 space-y-4 animate-fadeIn">
              <div className="flex items-center justify-between border-b border-emerald-200/60 pb-3">
                <span className="text-xs font-bold text-emerald-900">Crop Water Stress Index (CWSI)</span>
                <span className={`text-xs font-bold px-3 py-1 rounded-full border ${waterStressResult.statusColor}`}>
                  {waterStressResult.stressLevel}
                </span>
              </div>

              <div className="flex items-baseline space-x-3">
                <span className="text-4xl font-extrabold text-emerald-950 font-serif">CWSI {waterStressResult.cwsi}</span>
                <span className="text-xs font-semibold text-emerald-700">(Scale 0.00 - 1.00)</span>
              </div>

              <div className="space-y-2 pt-2 border-t border-emerald-200/60 text-xs">
                <div className="flex items-start space-x-2">
                  <CheckCircle className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                  <p className="text-slate-800 font-medium">{waterStressResult.recommendation}</p>
                </div>
                <div className="flex items-start space-x-2 pt-1">
                  <Sparkles className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                  <p className="text-emerald-900 font-bold">Suggested Schedule: {waterStressResult.suggestedIrrigation}</p>
                </div>
              </div>
            </div>
          ) : (
            <div className="bg-slate-50 rounded-2xl p-6 border border-slate-200/80 text-center space-y-2">
              <Info className="w-6 h-6 text-slate-400 mx-auto" />
              <p className="text-xs font-medium text-slate-500">
                Click <em>"Get Water Stress"</em> to run full multispectral diagnostics and view water deficit advisory.
              </p>
            </div>
          )}
        </div>

      </div>
    </div>
  );
};
