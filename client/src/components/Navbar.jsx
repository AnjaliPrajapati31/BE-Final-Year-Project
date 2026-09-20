import { useState } from 'react';
import { NavLink, useNavigate, useLocation } from 'react-router-dom';
import { Sprout, Menu, X, Leaf } from 'lucide-react';
import { useApp } from '../contexts/AppContext';

export const Navbar = () => {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const { latestRequestId, fieldId } = useApp();
  const isHomePage = location.pathname === '/' || location.pathname === '/experience';

  const analysisQuery = latestRequestId
    ? `?requestId=${encodeURIComponent(latestRequestId)}${fieldId ? `&fieldId=${encodeURIComponent(fieldId)}` : ''}`
    : '';

  const navLinks = [
    { name: 'Home', path: '/' },
    { name: 'My Fields', path: '/fields' },
    { name: 'Results', path: `/dashboard${analysisQuery}`, basePath: '/dashboard' },
    { name: 'Water Stress', path: `/water-stress${analysisQuery}`, basePath: '/water-stress' },
    { name: 'Weather', path: `/weather${analysisQuery}`, basePath: '/weather' },
    { name: 'Irrigation', path: `/recommendations${analysisQuery}`, basePath: '/recommendations' },
    { name: 'Field Data', path: `/settings${fieldId ? `?fieldId=${encodeURIComponent(fieldId)}` : ''}`, basePath: '/settings' },
  ];

  return (
    <header className={`z-50 transition-all duration-300 ${
      isHomePage
        ? 'absolute top-0 left-0 right-0 bg-transparent text-white'
        : 'sticky top-0 bg-[#18392B] text-white shadow-md border-b border-emerald-900/30'
    }`}>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-20 flex items-center justify-between">
        
        {/* Left: Brand Logo & Tagline */}
        <NavLink to="/" className="flex items-center space-x-3 group">
          <div className="w-10 h-10 rounded-xl bg-emerald-500/20 border border-emerald-400/30 flex items-center justify-center text-emerald-300 shadow-md group-hover:scale-105 transition-transform">
            <Sprout className="w-6 h-6 stroke-[2.5]" />
          </div>
          <div>
            <div className="flex items-center space-x-1.5">
              <span className="font-heading font-extrabold text-xl text-white tracking-tight">
                CropSense AI
              </span>
            </div>
            <p className="text-[11px] text-emerald-300/90 font-semibold tracking-wide">
              Grow Better. Live Better.
            </p>
          </div>
        </NavLink>

        {/* Center: Navigation Links */}
        <nav className="hidden md:flex items-center space-x-5">
          {navLinks.map((link) => {
            const matchPath = link.basePath || link.path;
            const isActive = location.pathname === matchPath || (matchPath !== '/' && location.pathname.startsWith(matchPath));
            if (link.locked) {
              return (
                <button
                  key={link.name}
                  type="button"
                  title="Coming soon"
                  className="relative py-1 text-sm font-bold text-slate-400 cursor-not-allowed inline-flex items-center gap-1.5"
                >
                  <span>{link.name}</span>
                  <Lock className="w-3.5 h-3.5" />
                </button>
              );
            }
            return (
              <NavLink
                key={link.name}
                to={link.path}
                className={`relative py-1 text-sm font-bold transition-colors duration-200 ${
                  isActive
                    ? 'text-white font-extrabold'
                    : 'text-slate-100/85 hover:text-white'
                }`}
              >
                {link.name}
                {isActive && (
                  <span className="absolute bottom-0 left-0 w-full h-[2.5px] bg-emerald-400 rounded-full" />
                )}
              </NavLink>
            );
          })}
        </nav>

        {/* Right: Login + Get Started */}
        <div className="flex items-center space-x-3">
          {/* Get Started Button */}
          <button
            onClick={() => navigate('/fields')}
            className="hidden sm:flex items-center space-x-2 bg-emerald-600 hover:bg-emerald-500 text-white border border-emerald-400/30 px-5 py-2.5 rounded-full font-bold text-sm transition-all shadow-md hover:shadow-lg cursor-pointer group"
          >
            <span>Get Started</span>
            <Leaf className="w-4 h-4 text-emerald-200 group-hover:rotate-12 transition-transform" />
          </button>

          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="md:hidden p-2 rounded-xl text-white hover:bg-white/10 transition-colors"
            aria-label="Toggle navigation menu"
          >
            {mobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
          </button>
        </div>
      </div>

      {/* Mobile Menu */}
      {mobileMenuOpen && (
        <div className={`md:hidden px-4 py-4 space-y-2 shadow-2xl text-white ${
          isHomePage
            ? 'bg-[#12271c]/95 backdrop-blur-xl border-b border-white/10'
            : 'bg-[#18392B] border-b border-emerald-900/40'
        }`}>
          {navLinks.map((link) => {
            const matchPath = link.basePath || link.path;
            const isActive = location.pathname === matchPath || (matchPath !== '/' && location.pathname.startsWith(matchPath));
            if (link.locked) {
              return (
                <div
                  key={link.name}
                  className="block px-4 py-3 rounded-xl text-base font-semibold text-slate-400 bg-white/5 cursor-not-allowed"
                >
                  <span className="inline-flex items-center gap-2">
                    <span>{link.name}</span>
                    <Lock className="w-4 h-4" />
                  </span>
                </div>
              );
            }
            return (
              <NavLink
                key={link.name}
                to={link.path}
                onClick={() => setMobileMenuOpen(false)}
                className={`block px-4 py-3 rounded-xl text-base font-semibold transition-colors ${
                  isActive
                    ? 'bg-emerald-600 text-white'
                    : 'text-slate-200 hover:bg-white/10'
                }`}
              >
                {link.name}
              </NavLink>
            );
          })}
          <div className="pt-3 border-t border-white/10 space-y-2">
            <button
              onClick={() => {
                setMobileMenuOpen(false);
                navigate('/fields');
              }}
              className="w-full flex items-center justify-center space-x-2 bg-emerald-600 hover:bg-emerald-500 text-white px-5 py-3 rounded-xl font-bold text-sm shadow-md"
            >
              <span>Get Started</span>
              <Leaf className="w-4 h-4 text-emerald-200" />
            </button>
          </div>
        </div>
      )}
    </header>
  );


};
