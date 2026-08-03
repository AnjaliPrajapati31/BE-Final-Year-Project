import { CloudSun, Droplets, Wind, Thermometer, CloudRain } from 'lucide-react';

export const WeatherCard = ({ weather }) => {
  if (!weather) return null;

  return (
    <div className="bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 text-white rounded-2xl p-6 shadow-sm border border-slate-800 relative overflow-hidden flex flex-col justify-between">
      <div className="flex items-start justify-between">
        <div>
          <span className="text-xs font-semibold tracking-wider text-emerald-400 uppercase">
            Field Micro-Climate
          </span>
          <h3 className="text-3xl font-bold mt-1 tracking-tight">{weather.temp}</h3>
          <p className="text-sm text-slate-300 font-medium mt-0.5">{weather.condition}</p>
        </div>
        <div className="p-3 bg-slate-800/80 rounded-xl border border-slate-700/50 text-emerald-400">
          <CloudSun className="w-8 h-8" />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 mt-6 pt-4 border-t border-slate-700/60">
        <div className="flex items-center space-x-2.5">
          <div className="p-1.5 bg-blue-500/10 text-blue-400 rounded-lg">
            <Droplets className="w-4 h-4" />
          </div>
          <div>
            <p className="text-xs text-slate-400">Humidity</p>
            <p className="text-sm font-semibold text-slate-100">{weather.humidity}</p>
          </div>
        </div>

        <div className="flex items-center space-x-2.5">
          <div className="p-1.5 bg-indigo-500/10 text-indigo-400 rounded-lg">
            <CloudRain className="w-4 h-4" />
          </div>
          <div>
            <p className="text-xs text-slate-400">Rainfall</p>
            <p className="text-sm font-semibold text-slate-100">{weather.rainfall}</p>
          </div>
        </div>

        <div className="flex items-center space-x-2.5">
          <div className="p-1.5 bg-teal-500/10 text-teal-400 rounded-lg">
            <Wind className="w-4 h-4" />
          </div>
          <div>
            <p className="text-xs text-slate-400">Wind Speed</p>
            <p className="text-sm font-semibold text-slate-100">{weather.windSpeed}</p>
          </div>
        </div>

        <div className="flex items-center space-x-2.5">
          <div className="p-1.5 bg-amber-500/10 text-amber-400 rounded-lg">
            <Thermometer className="w-4 h-4" />
          </div>
          <div>
            <p className="text-xs text-slate-400">High / Low</p>
            <p className="text-sm font-semibold text-slate-100">{weather.high} / {weather.low}</p>
          </div>
        </div>
      </div>
    </div>
  );
};
