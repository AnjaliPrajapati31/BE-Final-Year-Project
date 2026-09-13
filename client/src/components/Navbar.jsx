import { useState } from 'react';
import { NavLink, useNavigate, useLocation } from 'react-router-dom';
import { Sprout, Menu, X, Leaf } from 'lucide-react';
import { useApp } from '../contexts/AppContext';

export const Navbar = () => {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const { latestRequestId, fieldId } = useApp();
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
    <header className="sticky top-0 z-50 bg-[#F9FAF7]/95 backdrop-blur-md border-b border-emerald-900/10 text-slate-900 transition-all shadow-xs">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-20 flex items-center justify-between">
        
        {/* Left: Brand Logo & Tagline */}
        <NavLink to="/" className="flex items-center space-x-3 group">
          <div className="w-10 h-10 rounded-xl bg-[#18392B] flex items-center justify-center text-emerald-400 shadow-md group-hover:scale-105 transition-transform">
            <Sprout className="w-6 h-6 stroke-[2.5]" />
          </div>
          <div>
            <div className="flex items-center space-x-1.5">
              <span className="font-heading font-extrabold text-xl text-[#18392B] tracking-tight">
                CropSense AI
              </span>
            </div>
            <p className="text-[11px] text-emerald-800/80 font-semibold tracking-wide">
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
                    ? 'text-[#18392B]'
                    : 'text-slate-600 hover:text-[#18392B]'
                }`}
              >
                {link.name}
                {isActive && (
                  <span className="absolute bottom-0 left-0 w-full h-[2.5px] bg-[#18392B] rounded-full" />
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
            className="hidden sm:flex items-center space-x-2 bg-[#18392B] hover:bg-[#10281E] text-white px-5 py-2.5 rounded-full font-bold text-sm transition-all shadow-md hover:shadow-lg cursor-pointer group"
          >
            <span>Get Started</span>
            <Leaf className="w-4 h-4 text-emerald-300 group-hover:rotate-12 transition-transform" />
          </button>

          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="md:hidden p-2 rounded-xl text-slate-800 hover:bg-slate-100 transition-colors"
            aria-label="Toggle navigation menu"
          >
            {mobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
          </button>
        </div>
      </div>

      {/* Mobile Menu */}
      {mobileMenuOpen && (
        <div className="md:hidden bg-white border-b border-slate-200 px-4 py-4 space-y-2 shadow-xl">
          {navLinks.map((link) => {
            const matchPath = link.basePath || link.path;
            const isActive = location.pathname === matchPath || (matchPath !== '/' && location.pathname.startsWith(matchPath));
            if (link.locked) {
              return (
                <div
                  key={link.name}
                  className="block px-4 py-3 rounded-xl text-base font-semibold text-slate-400 bg-slate-50 cursor-not-allowed"
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
                    ? 'bg-[#18392B] text-white'
                    : 'text-slate-700 hover:bg-slate-100'
                }`}
              >
                {link.name}
              </NavLink>
            );
          })}
          <div className="pt-3 border-t border-slate-100 space-y-2">
            <button
              onClick={() => {
                setMobileMenuOpen(false);
                navigate('/fields');
              }}
              className="w-full flex items-center justify-center space-x-2 bg-[#18392B] text-white px-5 py-3 rounded-xl font-bold text-sm shadow-md"
            >
              <span>Get Started</span>
              <Leaf className="w-4 h-4 text-emerald-300" />
            </button>
          </div>
        </div>
      )}
    </header>
  );
};
