import { useEffect, useRef, useState } from 'react';
import { getReadiness, generateAnalysisExplanation } from '../services/api';
import { presentError } from '../lib/presentation';
export function AnalysisExplanation({ requestId }) {
  const [enabled, setEnabled] = useState(false), [pending, setPending] = useState(false);
  const [result, setResult] = useState(null), [error, setError] = useState(null);
  const alive = useRef(false), busy = useRef(false);
  useEffect(() => {
    alive.current = true;
    getReadiness().then(value => { if (alive.current) setEnabled(value.dependencies?.ai_explanation?.ready === true); }).catch(() => {});
    return () => { alive.current = false; };
  }, []);
  if (!enabled) return null;
  const explain = async () => {
    if (busy.current) return;
    busy.current = true; setPending(true); setError(null);
    try {
      const value = await generateAnalysisExplanation(requestId);
      if (alive.current) setResult(value.explanation);
    } catch (problem) { if (alive.current) setError(presentError(problem).message); }
    finally { busy.current = false; if (alive.current) setPending(false); }
  };
  return <section className="overview-card"><h2>Explain this analysis</h2>
    <p className="text-sm mb-3">Optional AI interpretation of this saved result. The water model determines irrigation quantities.</p>
    <button className="quiet-button" disabled={pending} onClick={explain}>{pending ? 'Preparing explanation…' : 'Explain these results'}</button>
    {error && <p role="alert" className="mt-3 text-sm">{error}</p>}
    {result && <div className="mt-4 space-y-3 text-sm">{['summary','crop_and_stage','water_status','irrigation_guidance'].map(key => <p key={key}>{result[key]}</p>)}<ul>{result.cautions?.map((text,index)=><li key={index}>{text}</li>)}</ul></div>}
  </section>;
}
