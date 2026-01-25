/**
 * Emergency Page
 *
 * Emergency controls and risk limit monitoring.
 */

import React from 'react';
import EmergencyControlPanel from '../components/Emergency/EmergencyControlPanel';
import ErrorBoundary from '../components/Shared/ErrorBoundary';

const Emergency: React.FC = () => {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-3xl font-bold text-white">Emergency Controls</h2>
        <p className="text-gray-400 mt-1">
          Emergency halt controls and risk limit monitoring
        </p>
      </div>

      <ErrorBoundary section="Emergency Controls">
        <EmergencyControlPanel />
      </ErrorBoundary>
    </div>
  );
};

export default Emergency;
