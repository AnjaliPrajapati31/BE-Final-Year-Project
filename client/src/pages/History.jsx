import { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { AlertTriangle, Calendar, CheckCircle2, Database, ArrowRight } from 'lucide-react';
import { EmptyState, LoadingSpinner, SectionHeader } from '../components/UIHelpers';
import { useApp } from '../contexts/AppContext';
import { ApiError, getFieldHistory } from '../services/api';
import { presentError, presentOverallStatus } from '../lib/presentation';

const formatDateTime = (value) => {
  if (!value) return 'Not available';
  return new Date(value).toLocaleString('en-IN', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
};

export const History = () => {
  const [searchParams] = useSearchParams();
  const { fieldId: contextFieldId } = useApp();
  const fieldId = searchParams.get('fieldId') || contextFieldId;
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(Boolean(fieldId));
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!fieldId) {
      return;
    }
    let cancelled = false;
    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        const result = await getFieldHistory(fieldId);
        if (!cancelled) {
          setHistory(result.items || []);
        }
      } catch (loadError) {
        if (!cancelled) {
          setError(loadError instanceof ApiError ? loadError : new ApiError(loadError.message));
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };
    load();
    return () => {
      cancelled = true;
    };
  }, [fieldId]);

  if (!fieldId) {
    return (
      <EmptyState
        title="No field selected"
        description="Run an analysis first so the dashboard can load analysis history for a field code."
        icon={Database}
      />
    );
  }

  if (loading) {
    return <LoadingSpinner />;
  }

  if (error) {
    const message = presentError(error);
    return (
      <EmptyState
        title={message.title}
        description={message.message}
        icon={AlertTriangle}
      />
    );
  }

  return (
    <div className="space-y-6">
      <SectionHeader
        title="Field Analysis History"
        subtitle={`Stored completed and partial analyses for ${fieldId}`}
        action={
          history.length > 0 ? (
            <div className="rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs font-bold text-slate-700">
              {history.length} stored run{history.length === 1 ? '' : 's'}
            </div>
          ) : null
        }
      />

      <div className="bg-white rounded-2xl border border-slate-200/80 shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-200/80 text-slate-500 text-xs font-semibold uppercase tracking-wider">
                <th className="py-3.5 px-4">Started</th>
                <th className="py-3.5 px-4">Request ID</th>
                <th className="py-3.5 px-4">Revision</th>
                <th className="py-3.5 px-4">Crop</th>
                <th className="py-3.5 px-4">Stage</th>
                <th className="py-3.5 px-4">Status</th>
                <th className="py-3.5 px-4">Open</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-sm text-slate-700">
              {history.map((item) => (
                <tr key={item.request_id} className="hover:bg-slate-50/60 transition-colors">
                  <td className="py-3.5 px-4 font-mono text-xs text-slate-600">{formatDateTime(item.started_at)}</td>
                  <td className="py-3.5 px-4 text-xs font-semibold text-slate-900">
                    <Link
                      to={`/dashboard?requestId=${encodeURIComponent(item.request_id)}&fieldId=${encodeURIComponent(fieldId)}`}
                      className="text-emerald-700 hover:text-emerald-800"
                    >
                      {item.request_id}
                    </Link>
                  </td>
                  <td className="py-3.5 px-4 font-medium text-slate-700">v{item.revision_number}</td>
                  <td className="py-3.5 px-4 font-medium text-slate-900">
                    {item.class_label || 'Not available'}
                    {typeof item.confidence === 'number' ? ` (${(item.confidence * 100).toFixed(1)}%)` : ''}
                  </td>
                  <td className="py-3.5 px-4 text-xs font-medium text-slate-600">{item.stage || item.evidence || 'Not available'}</td>
                  <td className="py-3.5 px-4">
                    <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-50 text-emerald-700 border border-emerald-100">
                      <CheckCircle2 className="w-3 h-3" />
                      <span>{presentOverallStatus(item.status)}</span>
                    </span>
                  </td>
                  <td className="py-3.5 px-4">
                    <Link
                      to={`/dashboard?requestId=${encodeURIComponent(item.request_id)}&fieldId=${encodeURIComponent(fieldId)}`}
                      className="inline-flex items-center gap-1 rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-xs font-bold text-emerald-700 transition hover:border-emerald-400"
                    >
                      <span>Full Analysis</span>
                      <ArrowRight className="w-3 h-3" />
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {!loading && history.length === 0 && (
        <EmptyState
          title="No stored analyses yet"
          description="This field code has no completed or partial analyses in PostgreSQL yet."
          icon={Calendar}
        />
      )}
    </div>
  );
};
