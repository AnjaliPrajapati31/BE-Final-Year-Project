import { NavLink, useLocation } from 'react-router-dom';
import { Sprout } from 'lucide-react';
import { useApp } from '../contexts/AppContext';
export const Navbar = () => {
  const { pathname } = useLocation();
  const { latestRequestId, fieldId } = useApp();
  const home = pathname === '/';
  const query = new URLSearchParams();
  if (latestRequestId) query.set('requestId', latestRequestId);
  if (fieldId) query.set('fieldId', fieldId);
  return <header className={'workspace-nav ' + (home ? 'workspace-nav--home' : '')}>
    <NavLink className="workspace-brand" to="/"><Sprout size={26}/><span>CropSense</span></NavLink>
    <nav aria-label="Main navigation">{home ? <NavLink to="/fields">My fields ↗</NavLink> : <>
      <NavLink to="/">Home</NavLink><NavLink to="/fields">My fields</NavLink>
      <NavLink to={'/dashboard?' + query.toString()}>Results</NavLink>
    </>}</nav>
  </header>;
};
