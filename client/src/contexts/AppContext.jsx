/* eslint-disable react-refresh/only-export-components */
import { createContext, useContext, useState } from 'react';

const AppContext = createContext();

// Default polygon points (Cauvery Delta sample)
const DEFAULT_BOUNDARY_POINTS = [
  { lat: 10.7850, lng: 79.1350 },
  { lat: 10.7910, lng: 79.1350 },
  { lat: 10.7910, lng: 79.1420 },
  { lat: 10.7850, lng: 79.1420 },
];

export const AppProvider = ({ children }) => {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [activeField, setActiveField] = useState({
    id: 'THANJAVUR_DELTA_SECTOR_A',
    name: 'Thanjavur Delta Sector A',
  });
  const [notificationsCount, setNotificationsCount] = useState(3);
  const [searchQuery, setSearchQuery] = useState('');
  const [fieldBoundaryPoints, setFieldBoundaryPoints] = useState(DEFAULT_BOUNDARY_POINTS);
  const [fieldDisplayName, setFieldDisplayName] = useState('Thanjavur Delta Sector A');
  const [fieldId, setFieldId] = useState('THANJAVUR_DELTA_SECTOR_A');
  const [latestRequestId, setLatestRequestId] = useState(null);
  const [latestAnalysisSummary, setLatestAnalysisSummary] = useState(null);

  const toggleSidebar = () => setSidebarOpen((prev) => !prev);

  return (
    <AppContext.Provider
      value={{
        sidebarOpen,
        setSidebarOpen,
        toggleSidebar,
        activeField,
        setActiveField,
        notificationsCount,
        setNotificationsCount,
        searchQuery,
        setSearchQuery,
        fieldBoundaryPoints,
        setFieldBoundaryPoints,
        fieldDisplayName,
        setFieldDisplayName,
        fieldId,
        setFieldId,
        latestRequestId,
        setLatestRequestId,
        latestAnalysisSummary,
        setLatestAnalysisSummary,
      }}
    >
      {children}
    </AppContext.Provider>
  );
};

export const useApp = () => {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error('useApp must be used within an AppProvider');
  }
  return context;
};
