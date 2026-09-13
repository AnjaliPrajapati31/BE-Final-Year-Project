import { useCallback, useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { ClipboardCheck, Droplets, Gauge, Sliders } from 'lucide-react';
import { EmptyState, InlineNotice, LoadingSpinner, SectionHeader } from '../components/UIHelpers';
import { useApp } from '../contexts/AppContext';
import { presentError } from '../lib/presentation';
import {
  createIrrigationEvent,
  createWaterObservation,
  getIrrigationEvents,
  getIrrigationHistoryCoverage,
  getWaterObservations,
  getWaterProfile,
  updateIrrigationHistoryCoverage,
  updateWaterProfile,
} from '../services/api';

const localToday = () => {
  const now = new Date();
  return new Date(now.getTime() - now.getTimezoneOffset() * 60000).toISOString().slice(0, 10);
};

export const Settings = () => {
  const { fieldId: contextFieldId } = useApp();
  const [searchParams] = useSearchParams();
  const fieldId = searchParams.get('fieldId') || contextFieldId;
  const [profile, setProfile] = useState({});
  const [events, setEvents] = useState([]);
  const [observations, setObservations] = useState([]);
  const [coverage, setCoverage] = useState({ coverage_status: 'unknown', coverage_start: '', coverage_end: '' });
  const [event, setEvent] = useState({ event_date: localToday(), amount: '', unit: 'mm', application_efficiency: '0.60' });
  const [observation, setObservation] = useState({ observed_at: `${localToday()}T08:00`, observation_type: 'ponded_depth', value: '', measurement_depth_m: '0.5', reliability: 'medium', method: 'field ruler' });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState('');
  const [notice, setNotice] = useState(null);

  const load = useCallback(async () => {
    if (!fieldId) return;
    setLoading(true);
    try {
      const [profileResult, eventResult, observationResult, coverageResult] = await Promise.all([
        getWaterProfile(fieldId), getIrrigationEvents(fieldId), getWaterObservations(fieldId), getIrrigationHistoryCoverage(fieldId),
      ]);
      setProfile(profileResult?.overrides || {});
      setEvents(eventResult || []);
      setObservations(observationResult || []);
      setCoverage({
        coverage_status: coverageResult?.coverage_status || 'unknown',
        coverage_start: coverageResult?.coverage_start || '',
        coverage_end: coverageResult?.coverage_end || '',
      });
    } catch (error) {
      setNotice({ ...presentError(error), tone: 'danger' });
    } finally {
      setLoading(false);
    }
  }, [fieldId]);

  useEffect(() => {
    if (!fieldId) return undefined;
    let cancelled = false;
    Promise.all([
      getWaterProfile(fieldId), getIrrigationEvents(fieldId), getWaterObservations(fieldId), getIrrigationHistoryCoverage(fieldId),
    ]).then(([profileResult, eventResult, observationResult, coverageResult]) => {
      if (cancelled) return;
      setProfile(profileResult?.overrides || {});
      setEvents(eventResult || []);
      setObservations(observationResult || []);
      setCoverage({ coverage_status: coverageResult?.coverage_status || 'unknown', coverage_start: coverageResult?.coverage_start || '', coverage_end: coverageResult?.coverage_end || '' });
    }).catch((error) => {
      if (!cancelled) setNotice({ ...presentError(error), tone: 'danger' });
    }).finally(() => {
      if (!cancelled) setLoading(false);
    });
    return () => { cancelled = true; };
  }, [fieldId]);

  const saveProfile = async (submitEvent) => {
    submitEvent.preventDefault();
    setSaving('profile');
    setNotice(null);
    try {
      const values = Object.fromEntries(Object.entries(profile).filter(([, value]) => value !== '').map(([key, value]) => [key, Number(value)]));
      await updateWaterProfile(fieldId, { profile_version: 'cauvery-paddy-v1', source: 'user', ...values });
      setNotice({ title: 'Water profile saved', message: 'These values will be used by the next field analysis.', tone: 'success' });
    } catch (error) {
      setNotice({ ...presentError(error), tone: 'danger' });
    } finally { setSaving(''); }
  };

  const addEvent = async (submitEvent) => {
    submitEvent.preventDefault();
    setSaving('event');
    setNotice(null);
    try {
      await createIrrigationEvent(fieldId, {
        event_date: event.event_date, amount: Number(event.amount), unit: event.unit,
        irrigation_method: 'surface', application_efficiency: Number(event.application_efficiency), source: 'user',
        client_event_id: crypto.randomUUID(),
      });
      setEvent((current) => ({ ...current, amount: '' }));
      setNotice({ title: 'Irrigation recorded', message: 'The next analysis will include this event.', tone: 'success' });
      await load();
    } catch (error) { setNotice({ ...presentError(error), tone: 'danger' }); }
    finally { setSaving(''); }
  };

  const addObservation = async (submitEvent) => {
    submitEvent.preventDefault();
    setSaving('observation');
    setNotice(null);
    try {
      const isSoil = observation.observation_type === 'volumetric_soil_water';
      await createWaterObservation(fieldId, {
        observed_at: new Date(observation.observed_at).toISOString(), observation_type: observation.observation_type,
        value: Number(observation.value), unit: isSoil ? 'm3/m3' : 'mm', method: observation.method,
        measurement_depth_m: isSoil ? Number(observation.measurement_depth_m) : null, source: 'user', reliability: observation.reliability,
        client_observation_id: crypto.randomUUID(),
      });
      setObservation((current) => ({ ...current, value: '' }));
      setNotice({ title: 'Field observation recorded', message: 'The measurement is stored with this field revision.', tone: 'success' });
      await load();
    } catch (error) { setNotice({ ...presentError(error), tone: 'danger' }); }
    finally { setSaving(''); }
  };

  const saveCoverage = async (submitEvent) => {
    submitEvent.preventDefault();
    setSaving('coverage');
    setNotice(null);
    try {
      const unknown = coverage.coverage_status === 'unknown';
      await updateIrrigationHistoryCoverage(fieldId, {
        coverage_status: coverage.coverage_status,
        coverage_start: unknown ? null : coverage.coverage_start,
        coverage_end: unknown ? null : coverage.coverage_end,
        source: 'user', notes: null,
      });
      setNotice({ title: 'History coverage saved', message: unknown ? 'Irrigation history remains marked as unknown.' : 'The model can now distinguish recorded history from missing history.', tone: 'success' });
    } catch (error) { setNotice({ ...presentError(error), tone: 'danger' }); }
    finally { setSaving(''); }
  };

  if (!fieldId) return <EmptyState title="No field selected" description="Run or open a field analysis before entering irrigation and water measurements." icon={Droplets} />;
  if (loading) return <LoadingSpinner />;

  return (
    <div className="space-y-6">
      <SectionHeader
        title="Field water data"
        subtitle={`Measured inputs and auditable history for ${fieldId || 'the selected field'}`}
      />
      <InlineNotice title="Why these inputs matter" description="Measured irrigation and water depth improve evidence. Leaving them unknown is safer than entering an estimated zero." tone="info" />
      {notice && <InlineNotice title={notice.title} description={notice.message} tone={notice.tone} />}

      <div className="grid gap-6 lg:grid-cols-2">
        <FormCard icon={Sliders} title="Water profile" description="Optional field-specific values. Blank fields continue using visible versioned defaults.">
          <form onSubmit={saveProfile} className="grid gap-3 sm:grid-cols-2">
            <NumberField label="Field capacity (m³/m³)" value={profile.field_capacity ?? ''} onChange={(value) => setProfile({ ...profile, field_capacity: value })} step="0.01" />
            <NumberField label="Wilting point (m³/m³)" value={profile.wilting_point ?? ''} onChange={(value) => setProfile({ ...profile, wilting_point: value })} step="0.01" />
            <NumberField label="Root depth (m)" value={profile.root_depth_m ?? ''} onChange={(value) => setProfile({ ...profile, root_depth_m: value })} step="0.05" />
            <NumberField label="Seepage/percolation (mm/day)" value={profile.seepage_percolation_mm_day ?? ''} onChange={(value) => setProfile({ ...profile, seepage_percolation_mm_day: value })} step="0.1" />
            <NumberField label="Irrigation efficiency (0–1)" value={profile.irrigation_efficiency ?? ''} onChange={(value) => setProfile({ ...profile, irrigation_efficiency: value })} step="0.05" />
            <NumberField label="Maximum ponding (mm)" value={profile.max_ponding_mm ?? ''} onChange={(value) => setProfile({ ...profile, max_ponding_mm: value })} step="1" />
            <Submit label="Save profile" busy={saving === 'profile'} />
          </form>
        </FormCard>

        <FormCard icon={Droplets} title="Record irrigation" description="Enter either applied depth or total field volume.">
          <form onSubmit={addEvent} className="grid gap-3 sm:grid-cols-2">
            <Input label="Date" type="date" max={localToday()} value={event.event_date} onChange={(value) => setEvent({ ...event, event_date: value })} required />
            <NumberField label={event.unit === 'mm' ? 'Applied depth (mm)' : 'Applied volume (m³)'} value={event.amount} onChange={(value) => setEvent({ ...event, amount: value })} step="0.1" required />
            <Select label="Amount unit" value={event.unit} onChange={(value) => setEvent({ ...event, unit: value })} options={[['mm', 'Depth (mm)'], ['m3', 'Volume (m³)']]} />
            <NumberField label="Application efficiency (0–1)" value={event.application_efficiency} onChange={(value) => setEvent({ ...event, application_efficiency: value })} step="0.05" required />
            <Submit label="Record irrigation" busy={saving === 'event'} />
          </form>
          <HistoryList items={events.slice(-4).reverse()} empty="No irrigation recorded yet." render={(item) => `${item.event_date} · ${item.gross_depth_mm} mm gross · ${item.status === 'active' ? 'Current' : 'Corrected/voided'}`} />
        </FormCard>

        <FormCard icon={Gauge} title="Record field-water observation" description="Ponding, water-table depth, or volumetric soil water.">
          <form onSubmit={addObservation} className="grid gap-3 sm:grid-cols-2">
            <Input label="Observed at" type="datetime-local" max={`${localToday()}T23:59`} value={observation.observed_at} onChange={(value) => setObservation({ ...observation, observed_at: value })} required />
            <Select label="Measurement" value={observation.observation_type} onChange={(value) => setObservation({ ...observation, observation_type: value })} options={[['ponded_depth', 'Ponded-water depth'], ['water_table_depth', 'Water-table depth'], ['volumetric_soil_water', 'Volumetric soil water']]} />
            <NumberField label={observation.observation_type === 'volumetric_soil_water' ? 'Value (m³/m³)' : 'Value (mm)'} value={observation.value} onChange={(value) => setObservation({ ...observation, value })} step="0.01" required />
            {observation.observation_type === 'volumetric_soil_water' && <NumberField label="Measurement depth (m)" value={observation.measurement_depth_m} onChange={(value) => setObservation({ ...observation, measurement_depth_m: value })} step="0.05" required />}
            <Select label="Reliability" value={observation.reliability} onChange={(value) => setObservation({ ...observation, reliability: value })} options={[['high', 'High'], ['medium', 'Medium'], ['low', 'Low']]} />
            <Input label="Method" value={observation.method} onChange={(value) => setObservation({ ...observation, method: value })} required />
            <Submit label="Record observation" busy={saving === 'observation'} />
          </form>
          <HistoryList items={observations.slice(-4).reverse()} empty="No field-water observations recorded." render={(item) => `${new Date(item.observed_at).toLocaleString('en-IN')} · ${item.observation_type.replaceAll('_', ' ')} · ${item.original_value} ${item.original_unit}`} />
        </FormCard>

        <FormCard icon={ClipboardCheck} title="Irrigation-history coverage" description="Tell the model whether the irrigation log is complete for a date range.">
          <form onSubmit={saveCoverage} className="grid gap-3 sm:grid-cols-2">
            <Select label="History quality" value={coverage.coverage_status} onChange={(value) => setCoverage({ ...coverage, coverage_status: value })} options={[['unknown', 'Unknown'], ['partial', 'Partial record'], ['complete', 'Complete record']]} />
            {coverage.coverage_status !== 'unknown' && <>
              <Input label="From" type="date" max={localToday()} value={coverage.coverage_start} onChange={(value) => setCoverage({ ...coverage, coverage_start: value })} required />
              <Input label="To" type="date" max={localToday()} value={coverage.coverage_end} onChange={(value) => setCoverage({ ...coverage, coverage_end: value })} required />
            </>}
            <Submit label="Save coverage" busy={saving === 'coverage'} />
          </form>
        </FormCard>
      </div>
    </div>
  );
};

const FormCard = ({ icon: Icon, title, description, children }) => <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"><div className="mb-4 flex gap-3"><div className="rounded-xl bg-emerald-50 p-2.5 text-emerald-700"><Icon className="h-5 w-5" /></div><div><h2 className="font-bold text-slate-900">{title}</h2><p className="text-xs text-slate-500">{description}</p></div></div>{children}</section>;
const Input = ({ label, onChange, ...props }) => <label className="text-xs font-semibold text-slate-700">{label}<input {...props} onChange={(event) => onChange(event.target.value)} className="mt-1 w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2.5 text-sm font-normal outline-none focus:border-emerald-500" /></label>;
const NumberField = (props) => <Input type="number" min="0" {...props} />;
const Select = ({ label, value, onChange, options }) => <label className="text-xs font-semibold text-slate-700">{label}<select value={value} onChange={(event) => onChange(event.target.value)} className="mt-1 w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2.5 text-sm font-normal">{options.map(([key, text]) => <option key={key} value={key}>{text}</option>)}</select></label>;
const Submit = ({ label, busy }) => <button disabled={busy} className="self-end rounded-xl bg-[#18392B] px-4 py-2.5 text-sm font-bold text-white disabled:cursor-wait disabled:opacity-60">{busy ? 'Saving…' : label}</button>;
const HistoryList = ({ items, empty, render }) => <div className="mt-4 border-t border-slate-100 pt-3 text-xs text-slate-600">{items.length ? <ul className="space-y-1">{items.map((item) => <li key={item.id}>{render(item)}</li>)}</ul> : <p>{empty}</p>}</div>;
