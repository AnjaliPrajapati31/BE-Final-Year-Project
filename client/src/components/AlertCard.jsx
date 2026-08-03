import { AlertTriangle, CheckCircle2, Info } from 'lucide-react';

export const AlertCard = ({ alert }) => {
  const getIcon = () => {
    switch (alert.type) {
      case 'warning':
        return <AlertTriangle className="w-5 h-5 text-amber-600" />;
      case 'success':
        return <CheckCircle2 className="w-5 h-5 text-emerald-600" />;
      case 'info':
      default:
        return <Info className="w-5 h-5 text-sky-600" />;
    }
  };

  const getBgClass = () => {
    switch (alert.type) {
      case 'warning':
        return 'bg-amber-50/70 border-amber-200/80';
      case 'success':
        return 'bg-emerald-50/70 border-emerald-200/80';
      case 'info':
      default:
        return 'bg-sky-50/70 border-sky-200/80';
    }
  };

  return (
    <div className={`p-4 rounded-xl border ${getBgClass()} transition-all hover:shadow-xs`}>
      <div className="flex items-start space-x-3">
        <div className="mt-0.5 shrink-0">{getIcon()}</div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between">
            <h4 className="text-sm font-semibold text-slate-900 truncate">{alert.title}</h4>
            <span className="text-xs text-slate-500 shrink-0">{alert.timestamp}</span>
          </div>
          <p className="text-xs text-slate-600 mt-1 leading-relaxed">{alert.description}</p>
        </div>
      </div>
    </div>
  );
};
