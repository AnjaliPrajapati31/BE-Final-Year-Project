import { SectionHeader } from '../components/UIHelpers';
import { CloudSun, Sun, CloudRain, Droplets } from 'lucide-react';

const forecastData = [
  { day: 'Today', temp: '26°C', condition: 'Partly Cloudy', pop: '10%', icon: CloudSun },
  { day: 'Tomorrow', temp: '22°C', condition: 'Heavy Rain', pop: '85%', icon: CloudRain },
  { day: 'Thu', temp: '24°C', condition: 'Sunny', pop: '5%', icon: Sun },
  { day: 'Fri', temp: '27°C', condition: 'Clear', pop: '0%', icon: Sun },
  { day: 'Sat', temp: '25°C', condition: 'Scattered Showers', pop: '40%', icon: CloudRain },
];

export const Weather = () => {
  return (
    <div className="space-y-6">
      <SectionHeader
        title="Agri-Weather Intelligence"
        subtitle="Localized microclimate insights and precipitation forecasts tailored for irrigation efficiency"
      />

      {/* 5-Day Forecast Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        {forecastData.map((item, idx) => {
          const Icon = item.icon;
          return (
            <div
              key={idx}
              className={`p-5 rounded-2xl border text-center transition-all ${
                idx === 0
                  ? 'bg-emerald-900 text-white border-emerald-800 shadow-md'
                  : 'bg-white text-slate-800 border-slate-200/80 shadow-xs'
              }`}
            >
              <p className={`text-xs font-bold uppercase tracking-wider ${idx === 0 ? 'text-emerald-300' : 'text-slate-500'}`}>
                {item.day}
              </p>
              <div className="my-4 flex justify-center">
                <Icon className={`w-8 h-8 ${idx === 0 ? 'text-emerald-400' : 'text-sky-600'}`} />
              </div>
              <h4 className="text-xl font-bold">{item.temp}</h4>
              <p className={`text-xs mt-1 font-medium ${idx === 0 ? 'text-slate-300' : 'text-slate-600'}`}>
                {item.condition}
              </p>
              <div className={`mt-3 pt-3 border-t text-[11px] font-semibold flex items-center justify-center space-x-1 ${
                idx === 0 ? 'border-emerald-800 text-emerald-300' : 'border-slate-100 text-sky-700'
              }`}>
                <Droplets className="w-3 h-3" />
                <span>Rain: {item.pop}</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
