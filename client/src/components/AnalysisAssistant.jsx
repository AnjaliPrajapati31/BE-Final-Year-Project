import { useEffect, useState } from 'react';
import { Bot, Lock, Sparkles, X } from 'lucide-react';
import { useApp } from '../contexts/AppContext';
import { generateAnalysisExplanation, getReadiness } from '../services/api';
import { presentError } from '../lib/presentation';
import { InlineNotice, LoadingSpinner } from './UIHelpers';

export const AnalysisAssistant = () => {
  const { latestRequestId, latestAnalysisSummary } = useApp();
  const requestId = latestRequestId || latestAnalysisSummary?.request_id;
  const [enabled, setEnabled] = useState(false);
  const [checked, setChecked] = useState(false);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    getReadiness()
      .then((readiness) => {
        if (!cancelled) setEnabled(Boolean(readiness?.dependencies?.ai_explanation?.ready));
      })
      .catch(() => {
        if (!cancelled) setEnabled(false);
      })
      .finally(() => {
        if (!cancelled) setChecked(true);
      });
    return () => { cancelled = true; };
  }, []);

  const explain = async () => {
    if (!enabled || !requestId) return;
    setLoading(true);
    setError(null);
    try {
      const response = await generateAnalysisExplanation(requestId);
      setResult(response.explanation);
    } catch (requestError) {
      setError(presentError(requestError));
    } finally {
      setLoading(false);
    }
  };

  const handleOpen = () => {
    if (!enabled) return;
    setOpen(true);
  };

  return (
    <>
      {open && enabled && (
        <aside className="fixed bottom-28 right-4 z-[70] w-[min(24rem,calc(100vw-2rem))] rounded-2xl border border-slate-200 bg-white shadow-2xl">
          <div className="flex items-center justify-between border-b border-slate-100 p-4">
            <div className="flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-emerald-600" />
              <div>
                <div className="text-sm font-bold text-slate-900">Explain this analysis</div>
                <div className="text-[11px] text-slate-500">Explanation only · calculations stay unchanged</div>
              </div>
            </div>
            <button type="button" onClick={() => setOpen(false)} aria-label="Close assistant" className="rounded-lg p-1.5 text-slate-500 hover:bg-slate-100">
              <X className="h-4 w-4" />
            </button>
          </div>
          <div className="max-h-[60vh] overflow-y-auto p-4">
            {!requestId && <InlineNotice title="No analysis selected" description="Run or open a field analysis first." tone="info" />}
            {error && <InlineNotice title={error.title} description={error.message} tone="danger" />}
            {loading && <LoadingSpinner />}
            {!loading && result && (
              <div className="space-y-3 text-sm text-slate-700">
                <p className="font-semibold text-slate-900">{result.summary}</p>
                <p>{result.crop_and_stage}</p>
                <p>{result.water_status}</p>
                <p>{result.irrigation_guidance}</p>
                {result.cautions?.length > 0 && (
                  <ul className="space-y-1 rounded-xl bg-amber-50 p-3 text-xs text-amber-900">
                    {result.cautions.map((item) => <li key={item}>• {item}</li>)}
                  </ul>
                )}
              </div>
            )}
            {!loading && !result && requestId && (
              <button type="button" onClick={explain} className="w-full rounded-xl bg-[#18392B] px-4 py-3 text-sm font-bold text-white hover:bg-[#10281E]">
                Explain current results
              </button>
            )}
          </div>
        </aside>
      )}

      <div className="fixed bottom-5 right-5 z-[60] flex flex-col items-center gap-1">
        <button
          type="button"
          disabled={!enabled}
          onClick={handleOpen}
          aria-label={enabled ? 'Open analysis assistant' : 'Analysis assistant is disabled'}
          title={enabled ? 'Explain the current analysis' : 'AI explanation is disabled'}
          className={`flex h-12 w-12 items-center justify-center rounded-full shadow-lg transition ${enabled ? 'bg-[#18392B] text-white hover:scale-105' : 'cursor-not-allowed bg-slate-200 text-slate-500'}`}
        >
          <Bot className="h-6 w-6" />
        </button>
        {checked && !enabled && (
          <span className="flex items-center gap-1 rounded-full bg-white px-2 py-0.5 text-[10px] font-semibold text-slate-500 shadow-sm ring-1 ring-slate-200">
            <Lock className="h-2.5 w-2.5" /> AI off
          </span>
        )}
      </div>
    </>
  );
};
