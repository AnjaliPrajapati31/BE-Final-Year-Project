export const SectionHeader = ({ title, subtitle, action }) => {
  return (
    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">{title}</h1>
        {subtitle && <p className="text-sm text-slate-500 mt-0.5">{subtitle}</p>}
      </div>
      {action && <div>{action}</div>}
    </div>
  );
};

export const LoadingSpinner = () => (
  <div className="flex items-center justify-center p-12">
    <div className="w-8 h-8 border-4 border-emerald-200 border-t-emerald-600 rounded-full animate-spin"></div>
  </div>
);

export const SkeletonLoader = () => (
  <div className="animate-pulse space-y-4">
    <div className="h-24 bg-slate-200 rounded-2xl w-full"></div>
    <div className="h-64 bg-slate-200 rounded-2xl w-full"></div>
  </div>
);

export const EmptyState = ({ title, description, icon: Icon }) => (
  <div className="text-center py-12 px-4 bg-white rounded-2xl border border-slate-200/80">
    {Icon && <Icon className="w-12 h-12 text-slate-300 mx-auto mb-3" />}
    <h3 className="text-base font-semibold text-slate-800">{title}</h3>
    <p className="text-sm text-slate-500 mt-1 max-w-sm mx-auto">{description}</p>
  </div>
);

export const StatusPill = ({ status }) => {
  const tones = {
    success: 'border-emerald-200 bg-emerald-50 text-emerald-700',
    warning: 'border-amber-200 bg-amber-50 text-amber-700',
    danger: 'border-red-200 bg-red-50 text-red-700',
    neutral: 'border-slate-200 bg-slate-50 text-slate-600',
  };
  return <span className={`inline-flex rounded-full border px-2.5 py-1 text-xs font-semibold ${tones[status.tone] || tones.neutral}`}>{status.label}</span>;
};

export const InlineNotice = ({ title, description, tone = 'warning' }) => {
  const tones = {
    warning: 'border-amber-200 bg-amber-50 text-amber-900',
    danger: 'border-red-200 bg-red-50 text-red-900',
    info: 'border-sky-200 bg-sky-50 text-sky-900',
    success: 'border-emerald-200 bg-emerald-50 text-emerald-900',
  };
  return (
    <div className={`rounded-xl border px-4 py-3 text-sm ${tones[tone] || tones.warning}`}>
      <div className="font-semibold">{title}</div>
      {description && <div className="mt-0.5 text-xs opacity-80">{description}</div>}
    </div>
  );
};
