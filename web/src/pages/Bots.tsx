/**
 * Bots Page
 *
 * Bot management and monitoring with real-time status from WebSocket events.
 */

import React, { useCallback } from 'react';
import { BotList } from '../components/Bots';
import ErrorBoundary from '../components/Shared/ErrorBoundary';
import MetricCard from '../components/Shared/MetricCard';
import { SkeletonMetricGrid } from '../components/Shared/Skeleton';
import { useWorkflowEvents } from '../hooks/useWorkflowEvents';
import { useWebSocket } from '../hooks/useWebSocket';
import {
  CpuChipIcon,
  PlayCircleIcon,
  PauseCircleIcon,
  ExclamationCircleIcon,
} from '@heroicons/react/24/outline';

const Bots: React.FC = () => {
  const { events } = useWorkflowEvents({ maxEvents: 1000 });
  const { connectionStatus } = useWebSocket(false);

  // Calculate bot stats from events
  const stats = React.useMemo(() => {
    const botSet = new Set<string>();
    const statusMap = new Map<string, string>();

    events.forEach((event) => {
      const botId = event.bot_id;
      if (!botId) return;
      botSet.add(botId);

      if (event.type === 'execution_started' || event.type === 'execution_completed') {
        statusMap.set(botId, 'running');
      } else if (event.type === 'execution_failed') {
        statusMap.set(botId, 'error');
      } else if (event.type === 'execution_halted') {
        statusMap.set(botId, 'paused');
      }
    });

    let running = 0;
    let paused = 0;
    let error = 0;

    statusMap.forEach((status) => {
      if (status === 'running') running++;
      else if (status === 'paused') paused++;
      else if (status === 'error') error++;
    });

    return {
      total: botSet.size,
      running,
      paused,
      error,
    };
  }, [events]);

  const handleBotAction = useCallback((action: 'start' | 'pause' | 'stop', botId: string) => {
    // In a real implementation, this would call the API
    console.log(`Bot action: ${action} on ${botId}`);
    // TODO: Implement API calls when backend is connected
    // botAPI.startBot(botId), botAPI.pauseBot(botId), botAPI.stopBot(botId)
  }, []);

  const isLoading = connectionStatus === 'connecting';

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-3xl font-bold text-white">Bots</h2>
        <p className="text-gray-400 mt-1">
          Manage and monitor your trading bots
        </p>
      </div>

      {/* Stats Summary */}
      {isLoading ? (
        <SkeletonMetricGrid count={4} />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <MetricCard
            title="Total Bots"
            value={stats.total}
            icon={<CpuChipIcon className="w-5 h-5" />}
            color="blue"
          />
          <MetricCard
            title="Running"
            value={stats.running}
            icon={<PlayCircleIcon className="w-5 h-5" />}
            color="green"
          />
          <MetricCard
            title="Paused"
            value={stats.paused}
            icon={<PauseCircleIcon className="w-5 h-5" />}
            color="yellow"
          />
          <MetricCard
            title="Errors"
            value={stats.error}
            icon={<ExclamationCircleIcon className="w-5 h-5" />}
            color={stats.error > 0 ? 'red' : 'gray'}
          />
        </div>
      )}

      {/* Bot List */}
      <ErrorBoundary section="Bot List">
        <BotList onBotAction={handleBotAction} />
      </ErrorBoundary>
    </div>
  );
};

export default Bots;
