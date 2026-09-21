import { Link, useLocation, useSearchParams } from 'react-router-dom';
import { useApp } from '../contexts/AppContext';
const tabs = [['Overview','/dashboard'],['Crop & stress','/water-stress'],['Water & irrigation','/recommendations'],['Weather','/weather'],['Field records','/settings'],['History','/history']];
export function ResultsShell({ children }) {
  const { pathname } = useLocation(), [params] = useSearchParams();
  const { fieldId, activeField, latestRequestId, latestAnalysisSummary } = useApp();
  const explicitRequest = params.get('requestId');
  const summary = latestAnalysisSummary?.request_id === (explicitRequest || latestRequestId) ? latestAnalysisSummary : null;
  const selected = params.get('fieldId') || summary?.field_id || (!explicitRequest || explicitRequest === latestRequestId ? fieldId : '');
  const requestId = explicitRequest || (selected === fieldId ? latestRequestId : '');
  const query = new URLSearchParams();
  if (selected) query.set('fieldId', selected);
  if (requestId) query.set('requestId', requestId);
  const analysis = latestAnalysisSummary?.request_id === requestId && latestAnalysisSummary?.field_id === selected ? latestAnalysisSummary : null;
  return <section className="results-workspace">
    <header className="results-heading"><div><p className="step-label">03 / RESULTS</p>
      <h1>{selected ? (activeField?.id === selected ? activeField.name : selected.replaceAll('_',' ')) : 'Your field results'}</h1>
      <p>{analysis?.data_quality?.analysis_cutoff ? 'Analysis through ' + analysis.data_quality.analysis_cutoff : 'Choose a stored analysis to inspect its evidence.'}{analysis ? ' · June–October seasonal window' : ''}</p>
    </div><Link className="quiet-button" to="/fields">Change field ↗</Link></header>
    <nav className="result-tabs" aria-label="Field results">{tabs.map(([name,path]) => <Link key={path} aria-current={pathname === path || (pathname === '/analytics' && path === '/dashboard') ? 'page' : undefined} to={path === '/history' ? path : path + '?' + query.toString()}>{name}</Link>)}</nav>
    <div className="result-content" key={selected + ':' + requestId}>{children}</div>
  </section>;
}
