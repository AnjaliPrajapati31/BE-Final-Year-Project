import { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { gsap } from 'gsap';
import { revealRadius } from '../lib/journey';
/* eslint-disable react-refresh/only-export-components */
const TransitionContext = createContext(null);
export const preloadFieldMap = () => import('../pages/MyFields');
export const useFieldTransition = () => useContext(TransitionContext);

export function RouteTransition({ children }) {
  const navigate = useNavigate();
  const location = useLocation();
  const overlay = useRef(null);
  const busy = useRef(false);
  const animation = useRef(null);
  const originKey = useRef(null);
  const timeout = useRef(null);
  const operation = useRef(0);
  const [failure, setFailure] = useState(false);
  const [transitioning, setTransitioning] = useState(false);
  const begin = useCallback(async event => {
    if (busy.current) return;
    const rect = event.currentTarget.getBoundingClientRect();
    const x = event.detail ? event.clientX : rect.left + rect.width / 2;
    const y = event.detail ? event.clientY : rect.top + rect.height / 2;
    busy.current = true;
    const currentOperation = ++operation.current;
    originKey.current = location.key;
    setTransitioning(true);
    setFailure(false);
    const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
    const mapReady = Promise.race([
      preloadFieldMap().then(() => true, () => false),
      new Promise(resolve => { timeout.current = setTimeout(() => resolve(false), 15000); }),
    ]);
    animation.current?.revert();
    animation.current = gsap.context(() => {
      gsap.set(overlay.current, { display: 'grid', opacity: 1, clipPath: 'circle(0px at ' + x + 'px ' + y + 'px)' });
      gsap.to(overlay.current, {
        clipPath: 'circle(' + revealRadius(x, y, innerWidth, innerHeight) + 'px at ' + x + 'px ' + y + 'px)',
        duration: reduced ? 0 : .65, ease: 'power3.inOut',
        onComplete: async () => {
          const loaded = await mapReady;
          clearTimeout(timeout.current);
          if (!busy.current || currentOperation !== operation.current) return;
          gsap.set(overlay.current, { clipPath: 'none' });
          if (loaded) navigate('/fields'); else setFailure(true);
        },
      });
    });
  }, [navigate, location.key]);

  useEffect(() => {
    if (!busy.current) return;
    if (location.key !== originKey.current && location.pathname !== '/fields') {
      operation.current++; busy.current = false; clearTimeout(timeout.current); gsap.killTweensOf(overlay.current); animation.current?.revert();
      // Reset the transition after navigation interrupted it.
      setTransitioning(false);
      return;
    }
    if (location.pathname !== '/fields') return;
    const frame = requestAnimationFrame(() => {
      gsap.to(overlay.current, { opacity: 0, duration: matchMedia('(prefers-reduced-motion: reduce)').matches ? 0 : .3,
        onComplete: () => { gsap.set(overlay.current, { display: 'none' }); busy.current = false; setTransitioning(false); requestAnimationFrame(() => document.getElementById('field-map-title')?.focus()); } });
    });
    return () => cancelAnimationFrame(frame);
  }, [location.pathname, location.key]);
  useEffect(() => () => { busy.current = false; operation.current++; clearTimeout(timeout.current); animation.current?.revert(); gsap.killTweensOf(overlay.current); }, []);
  const dismiss = () => { operation.current++; busy.current = false; clearTimeout(timeout.current); gsap.killTweensOf(overlay.current); gsap.set(overlay.current, { display: 'none' }); setFailure(false); setTransitioning(false); };
  return <TransitionContext.Provider value={begin}><div inert={transitioning ? true : undefined}>{children}</div>
    <div ref={overlay} className="journey-transition" role="status" aria-live="polite">
      {failure ? <div><h2>The map could not load.</h2><p>Check your connection, then try again.</p><button onClick={() => window.location.assign('/fields')}>Retry</button><button onClick={dismiss}>Return home</button></div> : <span>Bringing your field into view.</span>}
    </div>
  </TransitionContext.Provider>;
}
