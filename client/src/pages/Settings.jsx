import { SectionHeader } from '../components/UIHelpers';
import { Sliders } from 'lucide-react';

export const Settings = () => {
  return (
    <div className="space-y-6">
      <SectionHeader
        title="System Settings"
        subtitle="Manage sensor polling frequency, automated threshold triggers, and account security"
      />

      <div className="bg-white rounded-2xl p-6 border border-slate-200/80 shadow-sm space-y-6">
        <div>
          <h3 className="text-base font-bold text-slate-900 mb-4 flex items-center space-x-2">
            <Sliders className="w-5 h-5 text-emerald-600" />
            <span>Telemetry & Sensor Thresholds</span>
          </h3>

          <div className="space-y-4 max-w-xl">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Minimum Moisture Threshold (%)
              </label>
              <input
                type="number"
                defaultValue={45}
                className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm"
              />
              <p className="text-[11px] text-slate-400 mt-1">Triggers automated alert when soil moisture drops below this level.</p>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Sensor Polling Interval
              </label>
              <select defaultValue="15" className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm">
                <option value="5">Every 5 Minutes</option>
                <option value="15">Every 15 Minutes</option>
                <option value="60">Every 1 Hour</option>
              </select>
            </div>
          </div>
        </div>

        <div className="pt-6 border-t border-slate-100">
          <button
            onClick={() => alert('Settings Saved!')}
            className="px-5 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white font-medium text-xs rounded-xl shadow-xs transition-all cursor-pointer"
          >
            Save Preferences
          </button>
        </div>
      </div>
    </div>
  );
};
