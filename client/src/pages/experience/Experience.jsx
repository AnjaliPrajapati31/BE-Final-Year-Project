import { useEffect, useRef, useState } from 'react';
import { ArrowUpRight, Pause, Play } from 'lucide-react';
import { preloadFieldMap, useFieldTransition } from '../../components/RouteTransition';
import './Experience.css';
export default function Experience() {
  const host = useRef(null), world = useRef(null);
  const [paused, setPaused] = useState(false), [issue, setIssue] = useState(false), [loading, setLoading] = useState(true);
  const begin = useFieldTransition();
  useEffect(() => {
    let cancelled = false;
    const media = matchMedia('(prefers-reduced-motion: reduce)');
    const change = () => world.current?.setReducedMotion(media.matches);
    import('./world/renderer').then(({ createLandscape }) => {
      if (cancelled) return;
      world.current = createLandscape(host.current, {
        reducedMotion: media.matches,
        onReady: () => { if (!cancelled) setLoading(false); },
        onError: () => { if (!cancelled) { setIssue(true); setLoading(false); } },
      });
    }).catch(() => { if (!cancelled) { setIssue(true); setLoading(false); } });
    media.addEventListener('change', change);
    return () => { cancelled = true; media.removeEventListener('change', change); world.current?.dispose(); world.current = null; };
  }, []);
  const toggle = () => { setPaused(value => !value); world.current?.setAmbientMotion(paused); };
  return <section className="living-home" aria-labelledby="home-title">
    <div className="living-fallback" aria-hidden="true"><i/><i/><i/></div>
    <div className="living-canvas" ref={host} style={issue ? { visibility: 'hidden' } : undefined}/><div className="living-shade" aria-hidden="true"/>
    <div className={'living-loader ' + (loading ? '' : 'living-loader--done')} aria-live="polite" aria-busy={loading}>
      <div className="living-loader__content"><strong>{issue ? 'Showing the lightweight field' : 'Preparing your field view'}</strong><small>{issue ? 'You can continue to field selection.' : 'Loading the landscape and satellite-ready workspace'}</small><span className="living-loader__line" aria-hidden="true"><i/></span></div>
    </div>
    <div className="living-copy"><p className="living-eyebrow">ROOTED IN THE LAND. INFORMED BY SCIENCE.</p>
      <h1 id="home-title">Understand<br/><em>your field.</em></h1>
      <div className="living-action"><p>A closer connection to the land.<br/>A clearer view of what comes next.</p>
        <button onClick={begin} onPointerEnter={() => { void preloadFieldMap().catch(() => {}); }} onFocus={() => { void preloadFieldMap().catch(() => {}); }}>Analyze field <span><ArrowUpRight size={22}/></span></button>
      </div>
    </div>
    <footer className="living-footer"><span>01 &nbsp; Field <i/> 02 &nbsp; Map <i/> 03 &nbsp; Results</span>
      <span>{issue ? 'Showing the lightweight field' : 'Illustrative landscape'}</span>
      <button onClick={toggle} aria-label={paused ? 'Resume environmental motion' : 'Pause environmental motion'} aria-pressed={paused}>{paused ? <Play size={16}/> : <Pause size={16}/>}</button>
    </footer>
  </section>;
}
