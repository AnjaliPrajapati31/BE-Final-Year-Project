import { Outlet, useLocation } from 'react-router-dom';
import { Navbar } from '../components/Navbar';
import { RouteTransition } from '../components/RouteTransition';
import { ResultsShell } from '../components/ResultsShell';
import '../styles/journey.css';
const resultRoutes = new Set(['/dashboard', '/analytics', '/water-stress', '/weather', '/recommendations', '/settings', '/history']);
export const DashboardLayout = () => {
  const { pathname } = useLocation();
  return <RouteTransition><div className="workspace"><Navbar/>
    <main>{resultRoutes.has(pathname) ? <ResultsShell><Outlet/></ResultsShell> : <Outlet/>}</main>
  </div></RouteTransition>;
};
