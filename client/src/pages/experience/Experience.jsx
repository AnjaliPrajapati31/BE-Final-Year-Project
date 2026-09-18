import { useCallback, useEffect, useRef, useState } from 'react';
import { onScroll } from 'animejs';
import { ArrowDown, ArrowRight, ArrowUpRight, Maximize2, Pause, Play, RotateCcw, Wind } from 'lucide-react';
import { Link } from 'react-router-dom';
import { STORY_CHAPTERS } from './story';
import './Experience.css';

const clamp = value => Math.min(1, Math.max(0, value));

function ChapterGraphic({ id }) {
  const content = {
    crop: <><i className="scan scan-a" /><i className="scan scan-b" /><b className="parcel-shape" /><small>S1</small><small>S2</small></>,
    growth: <><i className="season-line" />{[.28,.48,.72,1].map((scale, index) => <b key={index} className="plant-mark" style={{ '--plant': scale, left: `${18 + index * 21}%` }} />)}</>,
    stress: <><b className="parcel-shape" /><i className="evidence-patch" /><small>OPTICAL</small><small>RADAR</small></>,
    weather: <><i className="cloud-mark" />{[0,1,2,3].map(index => <b key={index} className="rain-mark" />)}<i className="et-mark">ET₀ ↑</i></>,
    balance: <><b className="soil-profile"><i /><i /><i /></b><span className="balance-arrow in">+ rain</span><span className="balance-arrow out">− crop use</span></>,
    irrigation: <><span className="decision-step">deficit</span><i>→</i><span className="decision-step">efficiency</span><i>→</i><span className="decision-step">mm · m³</span></>,
    evidence: <><i className="timeline" />{[0,1,2,3,4].map(index => <b key={index} className="timeline-point" />)}<small>SOURCE</small><small>ASSUMPTION</small></>,
    field: <><b className="parcel-shape hero-shape" /><i className="pin-mark" /><span>your boundary</span></>,
  }[id];
  return (
    <div className={`delta-graphic delta-graphic--${id}`} aria-hidden="true">
      {content}
    </div>
  );
}

export default function Experience() {
  const rootRef = useRef(null);
  const stageRef = useRef(null);
  const worldRef = useRef(null);
  const observerRef = useRef(null);
  const sectionRefs = useRef([]);
  const progressRef = useRef(null);
  const [ready, setReady] = useState(false);
  const [issue, setIssue] = useState(false);
  const [retry, setRetry] = useState(0);
  const [active, setActive] = useState(-1);
  const [calm, setCalm] = useState(false);
  const [reducedMotion, setReducedMotion] = useState(() => matchMedia('(prefers-reduced-motion: reduce)').matches);

  const syncProgress = useCallback((rawProgress) => {
    const progress = clamp(Number(rawProgress) || 0);
    worldRef.current?.setStoryProgress(progress);
    if (progressRef.current) progressRef.current.style.setProperty('--progress', progress);
    const next = progress < .055 ? -1 : Math.min(7, Math.max(0, Math.round(progress * 8) - 1));
    setActive(previous => previous === next ? previous : next);
  }, []);

  useEffect(() => {
    let cancelled = false;
    const media = matchMedia('(prefers-reduced-motion: reduce)');
    const mediaChange = () => {
      setReducedMotion(media.matches);
      worldRef.current?.setReducedMotion(media.matches);
    };
    media.addEventListener('change', mediaChange);
    import('./world/renderer').then(({ createLandscape }) => {
      if (cancelled || !stageRef.current) return;
      worldRef.current = createLandscape(stageRef.current, {
        reducedMotion: media.matches,
        onReady: () => { if (!cancelled) setReady(true); },
        onProgress: value => progressRef.current?.style.setProperty('--progress', value),
        onError: () => { if (!cancelled) setIssue(true); },
      });
      if (new URLSearchParams(window.location.search).get('inspection') === 'overhead') {
        worldRef.current.setInspectionView('overhead');
      }
    }).catch(() => { if (!cancelled) setIssue(true); });
    return () => {
      cancelled = true;
      media.removeEventListener('change', mediaChange);
      observerRef.current?.revert?.();
      worldRef.current?.dispose();
      worldRef.current = null;
    };
  }, [retry]);

  useEffect(() => {
    if (!ready || !rootRef.current) return undefined;
    const root = rootRef.current;
    let frame = 0;
    const readDocumentProgress = () => {
      frame = 0;
      const start = window.scrollY + root.getBoundingClientRect().top;
      const distance = Math.max(1, root.offsetHeight - window.innerHeight);
      syncProgress((window.scrollY - start) / distance);
    };
    const handleScroll = () => {
      if (!frame) frame = requestAnimationFrame(readDocumentProgress);
    };
    observerRef.current?.revert?.();
    observerRef.current = onScroll({
      target: root,
      enter: 'top top',
      leave: 'bottom bottom',
      sync: true,
      onUpdate: observer => syncProgress(observer.progress),
    });
    window.addEventListener('scroll', handleScroll, { passive: true });
    window.addEventListener('resize', handleScroll);
    readDocumentProgress();
    return () => {
      cancelAnimationFrame(frame);
      window.removeEventListener('scroll', handleScroll);
      window.removeEventListener('resize', handleScroll);
      observerRef.current?.revert?.();
    };
  }, [ready, syncProgress]);

  const goTo = (index, focus = false) => {
    const element = sectionRefs.current[index + 1];
    element?.scrollIntoView({ behavior: reducedMotion ? 'auto' : 'smooth', block: 'start' });
    if (focus) window.setTimeout(() => element?.querySelector('h2')?.focus(), reducedMotion ? 0 : 650);
  };

  const toggleMotion = () => {
    const next = !calm;
    setCalm(next);
    worldRef.current?.setAmbientMotion(!next && !reducedMotion);
  };

  const enterFullScreen = () => {
    if (document.fullscreenElement) document.exitFullscreen?.().catch(() => {});
    else rootRef.current?.requestFullscreen?.().catch(() => {});
  };

  return (
    <main ref={rootRef} className="delta-experience" data-ready={ready} data-issue={issue}>
      <div className="delta-viewport">
        <div ref={stageRef} className="delta-stage" />
        <div className="delta-shade" aria-hidden="true" />
        <div className="delta-topshade" aria-hidden="true" />

        <header className="delta-header">
          <Link to="/" className="delta-brand" aria-label="CropSense home">
            <svg viewBox="0 0 36 36" fill="none" aria-hidden="true"><path d="M7 25V13l11-6 11 6v12l-11 6L7 25Z" stroke="currentColor" strokeWidth="1.1"/><path d="m12 22 6-3 6 3M12 17l6-3 6 3M18 14v11" stroke="currentColor" strokeWidth="1.1"/></svg>
            <span>CropSense<sup>®</sup></span>
          </Link>
          <p className="delta-location">ILLUSTRATIVE AGRICULTURAL VALLEY</p>
          <Link to="/" className="delta-exit">Back to app <ArrowUpRight size={15} /></Link>
        </header>

        <nav className="delta-rail" aria-label="Story chapters">
          {STORY_CHAPTERS.map((chapter, index) => (
            <button key={chapter.id} className={active === index ? 'is-active' : ''} onClick={() => goTo(index, true)} aria-label={`${chapter.number}: ${chapter.heading}`}>
              <span>{chapter.number}</span><i />
            </button>
          ))}
        </nav>

        <div className="delta-progress" ref={progressRef} aria-hidden="true"><span /></div>
        <div className="delta-controls">
          <button onClick={() => goTo(7, true)}>Skip to field view <ArrowDown size={15} /></button>
          <button onClick={toggleMotion} aria-label={calm ? 'Resume environmental motion' : 'Pause environmental motion'} aria-pressed={calm}>{calm ? <Play size={16} /> : <Pause size={16} />}</button>
          <button onClick={enterFullScreen} aria-label="Toggle full screen"><Maximize2 size={16} /></button>
        </div>
        <div className="delta-wind-label" aria-hidden="true"><Wind size={14} /> {calm ? 'Stillness' : 'Valley breeze'}</div>

        {!ready && !issue && <div className="delta-loader" role="status"><span className="delta-loader-line" /><strong>Growing a world.</strong><small>Preparing the living landscape</small></div>}
        {issue && (
          <div className="delta-error" role="alert">
            <p className="delta-eyebrow">LIGHTWEIGHT STORY</p><h1>The landscape could not start.</h1>
            <p>The complete story remains below. You can retry the live view or continue to the field tool.</p>
            <button onClick={() => { setIssue(false); setRetry(value => value + 1); }}>Reload landscape <RotateCcw size={16} /></button>
            <Link to="/fields">Open field tool <ArrowRight size={16} /></Link>
          </div>
        )}
      </div>

      <div className="delta-story">
        <section ref={element => { sectionRefs.current[0] = element; }} className="delta-cover" aria-labelledby="experience-cover-title">
          <div className="delta-cover-copy">
            <p className="delta-eyebrow"><span /> ROOTED IN THE LAND. INFORMED BY SCIENCE.</p>
            <h1 id="experience-cover-title">Understand<br /><em>your field.</em></h1>
            <p>Follow one field from crop recognition to a measured irrigation decision.</p>
            <button onClick={() => goTo(0, true)}>Explore the field <span><ArrowDown size={21} /></span></button>
          </div>
          <p className="delta-scroll-cue"><span /> Scroll to move through the landscape</p>
        </section>

        {STORY_CHAPTERS.map((chapter, index) => (
          <section id={`story-${chapter.id}`} key={chapter.id} ref={element => { sectionRefs.current[index + 1] = element; }} className={`delta-chapter ${active === index ? 'is-active' : ''}`} aria-labelledby={`story-${chapter.id}-title`}>
            <article className="delta-chapter-card">
              <div className="delta-chapter-count"><span>{chapter.number}</span><i /> <b>08</b></div>
              <p className="delta-eyebrow">{chapter.eyebrow}</p>
              <h2 id={`story-${chapter.id}-title`} tabIndex={-1}>{chapter.heading}</h2>
              <p className="delta-chapter-copy">{chapter.copy}</p>
              <div className="delta-tags">{chapter.tags.map(tag => <span key={tag}>{tag}</span>)}</div>
              <p className="delta-qualification">{chapter.qualification}</p>
              {chapter.id === 'field' && <Link className="delta-open" to="/fields">Open existing field tool <ArrowRight size={17} /></Link>}
            </article>
            <ChapterGraphic id={chapter.id} />
          </section>
        ))}
      </div>
    </main>
  );
}
