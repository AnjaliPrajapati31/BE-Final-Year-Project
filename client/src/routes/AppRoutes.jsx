import { lazy, Suspense } from 'react';
import { Routes, Route } from 'react-router-dom';
import { DashboardLayout } from '../layouts/DashboardLayout';
import { MyFields } from '../pages/MyFields';
import { Dashboard } from '../pages/Dashboard';
import { WaterStress } from '../pages/WaterStress';
import { Weather } from '../pages/Weather';
import { Recommendations } from '../pages/Recommendations';
import { History } from '../pages/History';
import { Notifications } from '../pages/Notifications';
import { Settings } from '../pages/Settings';

const Experience = lazy(() => import('../pages/experience/Experience'));

export const AppRoutes = () => {
  return (
    <Routes>
      <Route element={<DashboardLayout />}>
        <Route
          path="/"
          element={(
            <Suspense fallback={<div className="min-h-screen bg-[#17261e]" aria-label="Preparing the landscape" />}>
              <Experience />
            </Suspense>
          )}
        />
        <Route
          path="/experience"
          element={(
            <Suspense fallback={<div className="min-h-screen bg-[#17261e]" aria-label="Preparing the landscape" />}>
              <Experience />
            </Suspense>
          )}
        />


        
        {/* 2. My Fields Page (Interactive GIS Map + Polygon Drawing) */}
        <Route path="fields" element={<MyFields />} />
        
        {/* 3. Analytics Page (Crop Analytics Overview - Coordinates, NDVI, NDMI, Growth Stage) */}
        <Route path="dashboard" element={<Dashboard />} />
        
        {/* 4. Water Stress Page */}
        <Route path="water-stress" element={<WaterStress />} />

        {/* Legacy route alias for /analytics */}
        <Route path="analytics" element={<Dashboard />} />

        {/* Supplementary Routes */}
        <Route path="weather" element={<Weather />} />
        <Route path="recommendations" element={<Recommendations />} />
        <Route path="history" element={<History />} />
        <Route path="notifications" element={<Notifications />} />
        <Route path="settings" element={<Settings />} />
      </Route>
    </Routes>
  );
};
