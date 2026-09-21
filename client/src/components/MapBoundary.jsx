import { Component } from 'react';
import { Link } from 'react-router-dom';
export class MapBoundary extends Component {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  render() {
    if (this.state.failed) return <section className="overview-card m-8" role="alert">
      <h1 id="field-map-title" tabIndex={-1}>The map could not load.</h1><p>Reload the map to try again, or return to the field.</p>
      <button className="quiet-button" onClick={() => window.location.reload()}>Retry</button><Link className="quiet-button" to="/">Return home</Link>
    </section>;
    return this.props.children;
  }
}
