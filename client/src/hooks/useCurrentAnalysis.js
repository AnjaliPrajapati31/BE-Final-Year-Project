import { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useApp } from '../contexts/AppContext';
import { ApiError, getAnalysis } from '../services/api';

export const useCurrentAnalysis = () => {
  const [searchParams] = useSearchParams();
  const {
    latestRequestId, latestAnalysisSummary, setLatestAnalysisSummary, setLatestRequestId,
    setFieldId, setActiveField,
  } = useApp();
  const requestId = searchParams.get('requestId') || latestRequestId || latestAnalysisSummary?.request_id;
  const [analysis, setAnalysis] = useState(latestAnalysisSummary || null);
  const [loading, setLoading] = useState(Boolean(requestId && !latestAnalysisSummary));
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!requestId || analysis?.request_id === requestId) return;
    let cancelled = false;
    getAnalysis(requestId)
      .then((result) => {
        if (cancelled) return;
        setAnalysis(result);
        setLatestAnalysisSummary(result);
        setLatestRequestId(result.request_id);
        if (result.field_id) {
          setFieldId(result.field_id);
          setActiveField({ id: result.field_id, name: result.field_id.replaceAll('_', ' ') });
        }
      })
      .catch((loadError) => {
        if (!cancelled) setError(loadError instanceof ApiError ? loadError : new ApiError(loadError.message));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => { cancelled = true; };
  }, [analysis?.request_id, requestId, setActiveField, setFieldId, setLatestAnalysisSummary, setLatestRequestId]);

  const switchingAnalysis = Boolean(requestId && analysis?.request_id !== requestId);
  return { analysis, requestId, loading: loading || switchingAnalysis, error };
};
