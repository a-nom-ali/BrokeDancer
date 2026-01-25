/**
 * Events Page
 *
 * Live event stream monitor.
 */

import React from 'react';
import EventStreamMonitor from '../components/Events/EventStreamMonitor';
import ErrorBoundary from '../components/Shared/ErrorBoundary';

const Events: React.FC = () => {
  return (
    <div className="flex flex-col h-full space-y-6">
      <div>
        <h2 className="text-3xl font-bold text-white">Live Events</h2>
        <p className="text-gray-400 mt-1">
          Real-time workflow event stream
        </p>
      </div>

      <div className="flex-1 overflow-hidden">
        <ErrorBoundary section="Event Stream">
          <EventStreamMonitor />
        </ErrorBoundary>
      </div>
    </div>
  );
};

export default Events;
