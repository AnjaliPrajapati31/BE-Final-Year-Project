import { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useApp } from '../contexts/AppContext';
import { ApiError, getAnalysis } from '../services/api';
import { matchingAnalysis } from '../lib/journey';
const pending = new Map();
function retrieve(id) {
  if (!pending.has(id)) pending.set(id, getAnalysis(id).finally(() => pending.delete(id)));
  return pending.get(id);
}
export const useCurrentAnalysis = () => {
  const [params] = useSearchParams();
  const { fieldId, latestRequestId, latestAnalysisSummary, setLatestAnalysisSummary, setLatestRequestId, setFieldId, setActiveField } = useApp();
  const selectedField = params.get('fieldId') || '';
  const requestId = params.get('requestId') || (!selectedField || selectedField === fieldId ? latestRequestId : null);
  const cached = matchingAnalysis(latestAnalysisSummary, requestId, selectedField);
  const [state, setState] = useState({ id: null, analysis: null, error: null });
  useEffect(() => {
    if (!requestId || cached) return;
    let cancelled = false;
    retrieve(requestId).then(result => {
      if (cancelled) return;
      if (selectedField && result.field_id !== selectedField) throw new ApiError('This analysis belongs to a different field.', 'ANALYSIS_FIELD_MISMATCH');
      setState({ id: requestId, analysis: result, error: null });
      setLatestAnalysisSummary(result); setLatestRequestId(result.request_id); setFieldId(result.field_id);
      setActiveField(previous => previous?.id === result.field_id ? previous : { id: result.field_id, name: result.field_id.replaceAll('_', ' ') });
    }).catch(error => { if (!cancelled) setState({ id: requestId, analysis: null, error }); });
    return () => { cancelled = true; };
  }, [requestId, selectedField, cached, setLatestAnalysisSummary, setLatestRequestId, setFieldId, setActiveField]);
  const analysis = cached || (state.id === requestId ? matchingAnalysis(state.analysis, requestId, selectedField) : null);
  const error = state.id === requestId ? state.error : null;
  return { requestId, analysis, error, loading: Boolean(requestId && !analysis && !error) };
};
