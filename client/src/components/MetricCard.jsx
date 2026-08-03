import { motion } from 'framer-motion';

export const MetricCard = ({ title, value, unit, trend, isCharging, icon: Icon, gradient, accentColor }) => {
  return (
    <motion.div
      whileHover={{ y: -4, boxShadow: '0 12px 24px -10px rgba(0, 0, 0, 0.08)' }}
      transition={{ duration: 0.2 }}
      className="bg-white rounded-2xl p-5 border border-slate-200/80 shadow-sm relative overflow-hidden flex flex-col justify-between"
    >
      {/* Background soft accent gradient glow */}
      <div
        className={`absolute -right-6 -bottom-6 w-28 h-28 rounded-full blur-2xl opacity-15 pointer-events-none ${gradient}`}
      />

      <div className="flex items-center justify-between mb-3">
        <span className="text-sm font-medium text-slate-500">{title}</span>
        <div className={`p-2.5 rounded-xl ${accentColor}`}>
          <Icon className="w-5 h-5" />
        </div>
      </div>

      <div className="flex items-baseline justify-between mt-1">
        <div className="flex items-baseline space-x-1">
          <span className="text-3xl font-bold tracking-tight text-slate-900">{value}</span>
          {unit && <span className="text-base font-semibold text-slate-500">{unit}</span>}
        </div>

        {trend && (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-100">
            {trend}
          </span>
        )}

        {isCharging && (
          <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-50 text-amber-700 border border-amber-100">
            <span className="w-1.5 h-1.5 rounded-full bg-amber-500 animate-pulse"></span>
            <span>Charging</span>
          </span>
        )}
      </div>
    </motion.div>
  );
};
