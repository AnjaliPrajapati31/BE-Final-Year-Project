import { NavLink } from 'react-router-dom';
import {
  Home,
  LayoutDashboard,
  Map,
  Droplets,
  CloudSun,
  Sparkles,
  History,
  Bell,
  Settings,
  LogOut,
  ChevronLeft,
  ChevronRight,
  Sprout,
} from 'lucide-react';
import { useApp } from '../contexts/AppContext';
const navItems = [
  { name: 'Home', path: '/', icon: Home },
  { name: 'Dashboard', path: '/dashboard', icon: LayoutDashboard },
  { name: 'My Fields', path: '/fields', icon: Map },
  { name: 'Water Stress', path: '/water-stress', icon: Droplets },
  { name: 'Weather', path: '/weather', icon: CloudSun },
  { name: 'Recommendations', path: '/recommendations', icon: Sparkles },
  { name: 'History', path: '/history', icon: History },
  { name: 'Notifications', path: '/notifications', icon: Bell },
  { name: 'Settings', path: '/settings', icon: Settings },
];

export const Sidebar = () => {
  const { sidebarOpen, toggleSidebar } = useApp();
  return (
    <aside
      className={`fixed top-0 left-0 z-40 h-screen bg-slate-900 text-white transition-all duration-300 flex flex-col border-r border-slate-800 ${sidebarOpen ? 'w-64' : 'w-20'
        }`}
    >
      {/* Brand Header */}
      <div className="h-16 flex items-center justify-between px-4 border-b border-slate-800">
        <div className="flex items-center space-x-3 overflow-hidden">
          <div className="w-10 h-10 rounded-xl bg-emerald-600 flex items-center justify-center shrink-0 shadow-md">
            <Sprout className="w-6 h-6 text-white" />
          </div>
          {sidebarOpen && (
            <div className="truncate">
              <h1 className="font-bold text-base tracking-tight text-white leading-none">CropSense AI</h1>
              <span className="text-[10px] text-emerald-400 font-semibold uppercase tracking-widest">
                AI Monitor
                Satellite & AI
              </span>
            </div>
          )}
        </div>
        <button
          onClick={toggleSidebar}
          className="hidden md:flex p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white transition-colors cursor-pointer"
          title={sidebarOpen ? 'Collapse Sidebar' : 'Expand Sidebar'}
        >
          {sidebarOpen ? <ChevronLeft className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
        </button>
      </div>
      {/* Navigation Menu */}
      <nav className="flex-1 px-3 py-4 space-y-1.5 overflow-y-auto">
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.name}
              to={item.path}
              className={({ isActive }) =>
                `flex items-center space-x-3 px-3 py-3 rounded-xl text-sm font-medium transition-all ${isActive
                  ? 'bg-emerald-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-white hover:bg-slate-800/70'
                }`
              }
            >
              <Icon className="w-5 h-5 shrink-0" />
              {sidebarOpen && <span className="truncate">{item.name}</span>}
            </NavLink>
          );
        })}
      </nav>
      {/* Logout Footer */}
      <div className="p-3 border-t border-slate-800">
        <button
          onClick={() => alert('Logged out successfully')}
          className="w-full flex items-center space-x-3 px-3 py-3 rounded-xl text-sm font-medium text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 transition-all cursor-pointer"
        >
          <LogOut className="w-5 h-5 shrink-0" />
          {sidebarOpen && <span>Logout</span>}
        </button>
      </div>
    </aside>
  );
};
