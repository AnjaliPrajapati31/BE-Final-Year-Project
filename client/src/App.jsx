import { BrowserRouter } from 'react-router-dom';
import { AppProvider } from './contexts/AppContext';
import { AppRoutes } from './routes/AppRoutes';
import './index.css';

export default function App() {
  return (
    <AppProvider>
      <BrowserRouter>
        <AppRoutes />
      </BrowserRouter>
    </AppProvider>
  );
}
