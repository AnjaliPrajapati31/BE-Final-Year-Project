import {
  Lock,
  Info,
} from 'lucide-react';
import { EmptyState, SectionHeader } from '../components/UIHelpers';
import { useApp } from '../contexts/AppContext';

export const WaterStress = () => {
  const { activeField } = useApp();

  return (
    <div className="space-y-6 font-sans text-slate-800 pb-12">
      <SectionHeader
        title="Water Stress Analysis"
        subtitle={`This feature is not available yet for ${activeField.name}`}
        action={
          <div className="flex items-center space-x-2 bg-slate-100 border border-slate-200 text-slate-700 px-3.5 py-1.5 rounded-full text-xs font-bold shadow-2xs">
            <Lock className="w-4 h-4" />
            <span>Locked</span>
          </div>
        }
      />

      <EmptyState
        title="Water stress diagnostics are locked"
        description="The current production backend only supports crop analysis, stored retrieval, history, and optional artifacts. Water-stress APIs are not available yet, so this page is intentionally read-only."
        icon={Lock}
      />

      <div className="rounded-2xl border border-slate-200 bg-white p-6">
        <div className="mb-3 flex items-center gap-2 text-sm font-bold text-slate-900">
          <Info className="h-4 w-4 text-slate-600" />
          <span>What is available now</span>
        </div>
        <ul className="space-y-2 text-sm text-slate-700">
          <li>• Draw a Cauvery field polygon in My Fields and submit it for live crop analysis.</li>
          <li>• View the full stored analysis in Analytics, including crop result, stage status, warnings, and provenance.</li>
          <li>• Open History to review prior analyses for the same field code and drill back into each run.</li>
        </ul>
      </div>
    </div>
  );
};
