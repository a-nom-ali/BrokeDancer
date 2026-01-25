/**
 * ConnectionStatus Component
 *
 * Displays WebSocket connection status with visual feedback.
 */

import React from 'react';
import { SignalIcon, SignalSlashIcon, ArrowPathIcon } from '@heroicons/react/24/outline';
import type { ConnectionStatus as ConnectionStatusType } from '../../hooks/useWebSocket';

interface ConnectionStatusProps {
  status: ConnectionStatusType;
  onReconnect?: () => void;
  showLabel?: boolean;
  size?: 'sm' | 'md';
}

const ConnectionStatus: React.FC<ConnectionStatusProps> = ({
  status,
  onReconnect,
  showLabel = true,
  size = 'md',
}) => {
  const config = {
    connected: {
      icon: SignalIcon,
      color: 'text-green-500',
      bgColor: 'bg-green-500/10',
      borderColor: 'border-green-500/30',
      label: 'Connected',
      pulse: false,
    },
    connecting: {
      icon: ArrowPathIcon,
      color: 'text-yellow-500',
      bgColor: 'bg-yellow-500/10',
      borderColor: 'border-yellow-500/30',
      label: 'Connecting...',
      pulse: true,
    },
    disconnected: {
      icon: SignalSlashIcon,
      color: 'text-gray-500',
      bgColor: 'bg-gray-500/10',
      borderColor: 'border-gray-500/30',
      label: 'Disconnected',
      pulse: false,
    },
    error: {
      icon: SignalSlashIcon,
      color: 'text-red-500',
      bgColor: 'bg-red-500/10',
      borderColor: 'border-red-500/30',
      label: 'Connection Error',
      pulse: false,
    },
  };

  const currentConfig = config[status];
  const Icon = currentConfig.icon;

  const sizeClasses = size === 'sm'
    ? 'px-2 py-1 text-xs gap-1.5'
    : 'px-3 py-1.5 text-sm gap-2';

  const iconSize = size === 'sm' ? 'w-3 h-3' : 'w-4 h-4';

  return (
    <div
      className={`
        inline-flex items-center rounded-full border
        ${currentConfig.bgColor} ${currentConfig.borderColor} ${sizeClasses}
      `}
    >
      <Icon
        className={`
          ${iconSize} ${currentConfig.color}
          ${currentConfig.pulse ? 'animate-spin' : ''}
        `}
      />
      {showLabel && (
        <span className={currentConfig.color}>{currentConfig.label}</span>
      )}
      {status === 'error' && onReconnect && (
        <button
          onClick={onReconnect}
          className="ml-1 text-red-400 hover:text-red-300 underline"
        >
          Retry
        </button>
      )}
    </div>
  );
};

export default ConnectionStatus;
