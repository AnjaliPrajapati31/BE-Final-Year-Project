import { SectionHeader } from '../components/UIHelpers';
import { AlertCard } from '../components/AlertCard';

const alerts = [
  {
    id: 'placeholder-1',
    title: 'No live notifications endpoint connected',
    description: 'The current FastAPI service exposes field analysis, stored retrieval, and history. Notification streaming is still a client placeholder.',
    type: 'info',
    timestamp: 'Awaiting backend support',
  },
];

export const Notifications = () => {
  return (
    <div className="space-y-6">
      <SectionHeader
        title="Notifications & Alerts"
        subtitle="Real-time alert dispatch log from sensor telemetry and rain predictions"
      />

      <div className="bg-white rounded-2xl p-6 border border-slate-200/80 shadow-sm space-y-3">
        {alerts.map((alert) => (
          <AlertCard key={alert.id} alert={alert} />
        ))}
      </div>
    </div>
  );
};
