/**
 * BotCard Component
 *
 * Displays individual bot information with status and controls.
 */

import React from 'react';
import {
  PlayIcon,
  PauseIcon,
  StopIcon,
  CpuChipIcon,
} from '@heroicons/react/24/outline';
import type { BotStatus } from '../../types';

interface BotCardProps {
  botId: string;
  name: string;
  status: BotStatus;
  executions: number;
  successRate: number;
  lastActivity: string;
  onStart?: (botId: string) => void;
  onPause?: (botId: string) => void;
  onStop?: (botId: string) => void;
}

const BotCard: React.FC<BotCardProps> = ({
  botId,
  name,
  status,
  executions,
  successRate,
  lastActivity,
  onStart,
  onPause,
  onStop,
}) => {
  const getStatusConfig = () => {
    switch (status) {
      case 'running':
        return {
          color: 'text-green-400',
          bg: 'bg-green-500/10',
          border: 'border-green-500/30',
          label: 'Running',
          icon: <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />,
        };
      case 'paused':
        return {
          color: 'text-yellow-400',
          bg: 'bg-yellow-500/10',
          border: 'border-yellow-500/30',
          label: 'Paused',
          icon: <div className="w-2 h-2 rounded-full bg-yellow-500" />,
        };
      case 'stopped':
        return {
          color: 'text-gray-400',
          bg: 'bg-gray-500/10',
          border: 'border-gray-500/30',
          label: 'Stopped',
          icon: <div className="w-2 h-2 rounded-full bg-gray-500" />,
        };
      case 'error':
        return {
          color: 'text-red-400',
          bg: 'bg-red-500/10',
          border: 'border-red-500/30',
          label: 'Error',
          icon: <div className="w-2 h-2 rounded-full bg-red-500" />,
        };
      default:
        return {
          color: 'text-gray-400',
          bg: 'bg-gray-500/10',
          border: 'border-gray-500/30',
          label: 'Unknown',
          icon: <div className="w-2 h-2 rounded-full bg-gray-500" />,
        };
    }
  };

  const statusConfig = getStatusConfig();

  return (
    <div className="bg-gray-800 rounded-lg border border-gray-700 p-4 hover:border-gray-600 transition-colors">
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-blue-500/10 rounded-lg">
            <CpuChipIcon className="w-5 h-5 text-blue-400" />
          </div>
          <div>
            <h3 className="text-white font-medium">{name}</h3>
            <p className="text-gray-500 text-xs font-mono">{botId.slice(0, 12)}...</p>
          </div>
        </div>
        <div className={`flex items-center gap-2 px-2 py-1 rounded-full ${statusConfig.bg} ${statusConfig.border} border`}>
          {statusConfig.icon}
          <span className={`text-xs font-medium ${statusConfig.color}`}>
            {statusConfig.label}
          </span>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-3 mb-4">
        <div>
          <p className="text-gray-500 text-xs">Executions</p>
          <p className="text-white font-medium">{executions}</p>
        </div>
        <div>
          <p className="text-gray-500 text-xs">Success Rate</p>
          <p className={`font-medium ${successRate >= 90 ? 'text-green-400' : successRate >= 70 ? 'text-yellow-400' : 'text-red-400'}`}>
            {successRate.toFixed(1)}%
          </p>
        </div>
        <div>
          <p className="text-gray-500 text-xs">Last Activity</p>
          <p className="text-gray-300 text-sm">{lastActivity}</p>
        </div>
      </div>

      {/* Controls */}
      <div className="flex gap-2 pt-3 border-t border-gray-700">
        {status !== 'running' && (
          <button
            onClick={() => onStart?.(botId)}
            className="flex-1 flex items-center justify-center gap-1 px-3 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg text-sm transition-colors"
          >
            <PlayIcon className="w-4 h-4" />
            Start
          </button>
        )}
        {status === 'running' && (
          <button
            onClick={() => onPause?.(botId)}
            className="flex-1 flex items-center justify-center gap-1 px-3 py-2 bg-yellow-600 hover:bg-yellow-700 text-white rounded-lg text-sm transition-colors"
          >
            <PauseIcon className="w-4 h-4" />
            Pause
          </button>
        )}
        {status !== 'stopped' && (
          <button
            onClick={() => onStop?.(botId)}
            className="flex-1 flex items-center justify-center gap-1 px-3 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg text-sm transition-colors"
          >
            <StopIcon className="w-4 h-4" />
            Stop
          </button>
        )}
      </div>
    </div>
  );
};

export default BotCard;
