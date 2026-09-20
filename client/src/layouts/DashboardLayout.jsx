import { Outlet, useLocation } from 'react-router-dom';
import { Navbar } from '../components/Navbar';

export const DashboardLayout = () => {
  const location = useLocation();
  const isHomePage = location.pathname === '/' || location.pathname === '/experience';

  return (
    <div className={`min-h-screen flex flex-col font-sans antialiased relative ${
      isHomePage ? 'bg-[#17251b] text-white' : 'bg-[#E8F5E9] text-slate-900'
    }`}>
      {!isHomePage && (
        <div
          className="fixed inset-0 z-0 bg-cover bg-center bg-no-repeat pointer-events-none opacity-70"
          style={{ backgroundImage: "url('/fyp-bg.png')" }}
        />
      )}
      <div className="relative z-10 flex-1 flex flex-col w-full">
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
      </div>
    </div>
  );
};
