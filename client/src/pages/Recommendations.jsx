import { SectionHeader } from '../components/UIHelpers';
import { Sparkles, CheckCircle, Clock, ShieldCheck } from 'lucide-react';

const recommendations = [
  {
    id: 'placeholder-1',
    field: 'Not connected to FastAPI yet',
    action: 'Use the field analysis dashboard for live crop classification',
    timing: 'After selecting a field polygon',
    reason: 'The current production backend exposes crop analysis, stage estimation, and history, not irrigation recommendation endpoints.',
    confidence: 'Placeholder',
  },
];

export const Recommendations = () => {
  return (
    <div className="space-y-6">
      <SectionHeader
        title="AI Irrigation Advisory"
        subtitle="Generative AI models analyzing satellite NDVI, soil moisture probes, and weather models"
      />

      <div className="space-y-4">
        {recommendations.map((rec) => (
          <div
            key={rec.id}
            className="bg-white rounded-2xl p-6 border border-slate-200/80 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-6"
          >
            <div className="flex items-start space-x-4">
              <div className="p-3 bg-emerald-100 text-emerald-800 rounded-xl mt-1">
                <Sparkles className="w-6 h-6" />
              </div>
              <div>
                <div className="flex items-center space-x-2">
                  <span className="text-xs font-bold text-emerald-700 bg-emerald-50 px-2.5 py-0.5 rounded-full border border-emerald-100">
                    {rec.field}
                  </span>
                  <span className="text-xs text-slate-400 flex items-center space-x-1">
                    <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
                    <span>AI Confidence: {rec.confidence}</span>
                  </span>
                </div>
                <h3 className="text-lg font-bold text-slate-900 mt-1">{rec.action}</h3>
                <p className="text-xs text-slate-600 mt-1 max-w-xl">{rec.reason}</p>
                <div className="flex items-center space-x-2 text-xs text-slate-500 mt-2 font-medium">
                  <Clock className="w-3.5 h-3.5" />
                  <span>Optimal Execution Window: {rec.timing}</span>
                </div>
              </div>
            </div>

            <div className="flex items-center space-x-3 shrink-0">
              <button
                onClick={() => alert('Recommendation Approved & Scheduled!')}
                className="px-5 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white font-medium text-xs rounded-xl shadow-xs transition-all flex items-center space-x-1.5 cursor-pointer"
              >
                <CheckCircle className="w-4 h-4" />
                <span>Execute Recommendation</span>
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
