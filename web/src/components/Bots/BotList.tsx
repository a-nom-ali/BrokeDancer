/**
 * BotList Component
 *
 * Displays a grid of bots derived from WebSocket workflow events.
 */

import React, { useMemo, useState } from 'react';
import BotCard from './BotCard';
import { useWorkflowEvents } from '../../hooks/useWorkflowEvents';
import EmptyState from '../Shared/EmptyState';
import { CpuChipIcon, FunnelIcon } from '@heroicons/react/24/outline';
import type { BotStatus } from '../../types';

interface BotData {
  botId: string;
  name: string;
  status: BotStatus;
  executions: number;
  successes: number;
  failures: number;
  lastActivity: string;
}

interface BotListProps {
  onBotAction?: (action: 'start' | 'pause' | 'stop', botId: string) => void;
}

const BotList: React.FC<BotListProps> = ({ onBotAction }) => {
  const { events } = useWorkflowEvents({ maxEvents: 1000 });
  const [statusFilter, setStatusFilter] = useState<BotStatus | 'all'>('all');

  // Derive bot data from events
  const bots = useMemo((): BotData[] => {
    const botMap = new Map<string, BotData>();

    events.forEach((event) => {
      const botId = event.bot_id;
      if (!botId) return;

      if (!botMap.has(botId)) {
        botMap.set(botId, {
          botId,
          name: `Bot ${botId.slice(0, 6)}`,
          status: 'running',
          executions: 0,
          successes: 0,
          failures: 0,
          lastActivity: 'Never',
        });
      }

      const bot = botMap.get(botId)!;

      if (event.type === 'execution_started') {
        bot.executions++;
        bot.status = 'running';
      } else if (event.type === 'execution_completed') {
        bot.successes++;
        bot.status = 'running';
      } else if (event.type === 'execution_failed') {
        bot.failures++;
        bot.status = 'error';
      } else if (event.type === 'execution_halted') {
        bot.status = 'paused';
      }

      // Update last activity
      const date = new Date(event.timestamp);
      if (!isNaN(date.getTime())) {
        bot.lastActivity = date.toLocaleTimeString('en-US', {
          hour: '2-digit',
          minute: '2-digit',
        });
      }
    });

    return Array.from(botMap.values());
  }, [events]);

  // Filter bots by status
  const filteredBots = useMemo(() => {
    if (statusFilter === 'all') return bots;
    return bots.filter(bot => bot.status === statusFilter);
  }, [bots, statusFilter]);

  // Calculate stats
  const stats = useMemo(() => ({
    total: bots.length,
    running: bots.filter(b => b.status === 'running').length,
    paused: bots.filter(b => b.status === 'paused').length,
    error: bots.filter(b => b.status === 'error').length,
  }), [bots]);

  const handleStart = (botId: string) => {
    console.log('Start bot:', botId);
    onBotAction?.('start', botId);
  };

  const handlePause = (botId: string) => {
    console.log('Pause bot:', botId);
    onBotAction?.('pause', botId);
  };

  const handleStop = (botId: string) => {
    console.log('Stop bot:', botId);
    onBotAction?.('stop', botId);
  };

  if (bots.length === 0) {
    return (
      <EmptyState
        title="No bots detected"
        message="Run a workflow to see bots appear here. Bots are detected from workflow execution events."
        icon={<CpuChipIcon className="w-12 h-12" />}
      />
    );
  }

  return (
    <div className="space-y-4">
      {/* Stats Bar */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4 text-sm">
          <span className="text-gray-400">
            <span className="text-white font-medium">{stats.total}</span> bots
          </span>
          <span className="text-gray-400">
            <span className="text-green-400 font-medium">{stats.running}</span> running
          </span>
          <span className="text-gray-400">
            <span className="text-yellow-400 font-medium">{stats.paused}</span> paused
          </span>
          {stats.error > 0 && (
            <span className="text-gray-400">
              <span className="text-red-400 font-medium">{stats.error}</span> error
            </span>
          )}
        </div>

        {/* Filter */}
        <div className="flex items-center gap-2">
          <FunnelIcon className="w-4 h-4 text-gray-500" />
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value as BotStatus | 'all')}
            className="bg-gray-700 text-white text-sm rounded-lg px-3 py-1.5 border border-gray-600 focus:border-blue-500 focus:outline-none"
          >
            <option value="all">All Status</option>
            <option value="running">Running</option>
            <option value="paused">Paused</option>
            <option value="stopped">Stopped</option>
            <option value="error">Error</option>
          </select>
        </div>
      </div>

      {/* Bot Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filteredBots.map((bot) => (
          <BotCard
            key={bot.botId}
            botId={bot.botId}
            name={bot.name}
            status={bot.status}
            executions={bot.executions}
            successRate={
              bot.executions > 0
                ? (bot.successes / bot.executions) * 100
                : 0
            }
            lastActivity={bot.lastActivity}
            onStart={handleStart}
            onPause={handlePause}
            onStop={handleStop}
          />
        ))}
      </div>

      {filteredBots.length === 0 && (
        <div className="text-center py-8">
          <p className="text-gray-500">No bots match the selected filter</p>
        </div>
      )}
    </div>
  );
};

export default BotList;
