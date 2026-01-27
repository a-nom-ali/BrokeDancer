/**
 * App Component
 *
 * Main application with routing, layout, and code-splitting.
 */

import { Suspense, lazy } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import DashboardLayout from './components/Layout/DashboardLayout';
import LoadingSpinner from './components/Shared/LoadingSpinner';

// Lazy-loaded pages for code splitting
const Dashboard = lazy(() => import('./pages/Dashboard'));
const Workflows = lazy(() => import('./pages/Workflows'));
const Bots = lazy(() => import('./pages/Bots'));
const Metrics = lazy(() => import('./pages/Metrics'));
const Emergency = lazy(() => import('./pages/Emergency'));
const History = lazy(() => import('./pages/History'));
const Events = lazy(() => import('./pages/Events'));

// Page loading fallback
const PageLoader = () => (
  <div className="flex items-center justify-center h-full min-h-[400px]">
    <LoadingSpinner size="lg" message="Loading..." />
  </div>
);

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<DashboardLayout />}>
          <Route
            index
            element={
              <Suspense fallback={<PageLoader />}>
                <Dashboard />
              </Suspense>
            }
          />
          <Route
            path="workflows"
            element={
              <Suspense fallback={<PageLoader />}>
                <Workflows />
              </Suspense>
            }
          />
          <Route
            path="bots"
            element={
              <Suspense fallback={<PageLoader />}>
                <Bots />
              </Suspense>
            }
          />
          <Route
            path="metrics"
            element={
              <Suspense fallback={<PageLoader />}>
                <Metrics />
              </Suspense>
            }
          />
          <Route
            path="emergency"
            element={
              <Suspense fallback={<PageLoader />}>
                <Emergency />
              </Suspense>
            }
          />
          <Route
            path="history"
            element={
              <Suspense fallback={<PageLoader />}>
                <History />
              </Suspense>
            }
          />
          <Route
            path="events"
            element={
              <Suspense fallback={<PageLoader />}>
                <Events />
              </Suspense>
            }
          />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
