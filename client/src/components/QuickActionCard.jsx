import { Plus, Sparkles, Droplet } from 'lucide-react';

export const QuickActionCard = ({ onAddField, onCheckRecommendation, onRecordIrrigation }) => {
  return (
    <div className="bg-white rounded-2xl p-5 border border-slate-200/80 shadow-sm">
      <h3 className="text-base font-semibold text-slate-900 mb-4">Quick Actions</h3>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <button
          onClick={onAddField}
          className="flex items-center justify-center space-x-2 py-3 px-4 rounded-xl bg-emerald-700 hover:bg-emerald-800 text-white font-medium text-sm transition-all shadow-xs active:scale-[0.99] cursor-pointer"
        >
          <Plus className="w-4 h-4" />
          <span>Add Field</span>
        </button>

        <button
          onClick={onCheckRecommendation}
          className="flex items-center justify-center space-x-2 py-3 px-4 rounded-xl bg-sky-700 hover:bg-sky-800 text-white font-medium text-sm transition-all shadow-xs active:scale-[0.99] cursor-pointer"
        >
          <Sparkles className="w-4 h-4" />
          <span>Check AI Rec</span>
        </button>

        <button
          onClick={onRecordIrrigation}
          className="flex items-center justify-center space-x-2 py-3 px-4 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-800 font-medium text-sm border border-slate-200 transition-all active:scale-[0.99] cursor-pointer"
        >
          <Droplet className="w-4 h-4 text-sky-600" />
          <span>Record Irrigation</span>
        </button>
      </div>
    </div>
  );
};
