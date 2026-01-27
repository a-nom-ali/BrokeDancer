/**
 * DashboardLayout Component
 *
 * Main layout wrapper for the dashboard with header, sidebar, and content area.
 */

import React from 'react';
import { Outlet } from 'react-router-dom';
import Navigation from './Navigation';
import { useWebSocket } from '../../hooks/useWebSocket';
import ErrorBoundary from '../Shared/ErrorBoundary';
import ConnectionStatus from '../Shared/ConnectionStatus';

export interface DashboardLayoutProps {
  children?: React.ReactNode;
}

const DashboardLayout: React.FC<DashboardLayoutProps> = ({ children }) => {
  const { connectionStatus, connect } = useWebSocket(true);

  return (
    <div className="flex h-screen bg-gray-900 text-gray-100">
      {/* Sidebar Navigation */}
      <Navigation />

      {/* Main Content Area */}
      <div className="flex flex-col flex-1 overflow-hidden">
        {/* Header */}
        <header className="flex items-center justify-between px-6 py-4 bg-gray-800 border-b border-gray-700">
          <div className="flex items-center space-x-4">
            <h1 className="text-2xl font-bold text-white">
              BrokeDancer
            </h1>
            <span className="text-sm text-gray-400">Dashboard</span>
          </div>

          {/* Connection Status */}
          <div className="flex items-center space-x-3">
            <ConnectionStatus
              status={connectionStatus}
              onReconnect={connect}
            />

            {/* Emergency Status - Will be populated later */}
            <div className="flex items-center space-x-2 px-3 py-1 bg-gray-700 rounded-md">
              <span className="text-xs font-medium text-green-400">NORMAL</span>
            </div>
          </div>
        </header>

        {/* Main Content */}
        <main className="flex-1 overflow-y-auto bg-gray-900 p-6">
          <ErrorBoundary section="Dashboard">
            {children || <Outlet />}
          </ErrorBoundary>
        </main>
      </div>
    </div>
  );
};

export default DashboardLayout;
