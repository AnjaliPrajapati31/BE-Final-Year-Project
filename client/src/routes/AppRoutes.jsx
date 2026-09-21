import { lazy, Suspense } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { DashboardLayout } from '../layouts/DashboardLayout';
import { Dashboard } from '../pages/Dashboard';
import { WaterStress } from '../pages/WaterStress';
import { Weather } from '../pages/Weather';
import { Recommendations } from '../pages/Recommendations';
import { History } from '../pages/History';
import { Notifications } from '../pages/Notifications';
import { Settings } from '../pages/Settings';
import { CropEvidence } from '../components/CropEvidence';
import { MapBoundary } from '../components/MapBoundary';

const Experience = lazy(() => import('../pages/experience/Experience'));
const MyFields = lazy(() => import('../pages/MyFields').then(module => ({ default: module.MyFields })));

export const AppRoutes = () => {
  return (
    <Routes>
      <Route element={<DashboardLayout />}>
        <Route
          path="/"
          element={(
            <Suspense fallback={<div className="min-h-screen bg-[#637659]" aria-label="Preparing the field" />}><Experience /></Suspense>
          )}
        />
        <Route
          path="/experience"
          element={(
            <Navigate to="/" replace />
          )}
        />


        
        {/* 2. My Fields Page (Interactive GIS Map + Polygon Drawing) */}
        <Route path="fields" element={<MapBoundary><Suspense fallback={<div role="status" className="p-8">Preparing your map…</div>}><MyFields /></Suspense></MapBoundary>} />
        
        {/* 3. Analytics Page (Crop Analytics Overview - Coordinates, NDVI, NDMI, Growth Stage) */}
        <Route path="dashboard" element={<Dashboard />} />
        
        {/* 4. Water Stress Page */}
        <Route path="water-stress" element={<><CropEvidence /><WaterStress /></>} />

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
