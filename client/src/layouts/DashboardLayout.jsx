import { Outlet, useLocation } from 'react-router-dom';
import { Navbar } from '../components/Navbar';
import { AnalysisAssistant } from '../components/AnalysisAssistant';

export const DashboardLayout = () => {
  const location = useLocation();
  const isHomePage = location.pathname === '/';

  return (
    <div className="min-h-screen bg-[#F9FAF7] flex flex-col font-sans antialiased text-slate-900">
      {/* Top Navigation Bar with Home, My Field, Analytics, Water Stress */}
      <Navbar />

      {/* Page Content — Home page handles its own full-bleed layout; inner pages get padding */}
      <main className="flex-1 w-full">
        {isHomePage ? (
          <Outlet />
        ) : (
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
            <Outlet />
          </div>
        )}
      </main>
      <AnalysisAssistant />
    </div>
  );
};
