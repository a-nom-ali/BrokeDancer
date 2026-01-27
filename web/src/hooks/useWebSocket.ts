/**
 * useWebSocket Hook
 *
 * React hook for managing WebSocket connection and event subscriptions.
 * Wraps the websocketService singleton with React state and lifecycle.
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { websocketService } from '../services/websocket';

export type ConnectionStatus = 'disconnected' | 'connecting' | 'connected' | 'error';

export interface UseWebSocketReturn {
  isConnected: boolean;
  connectionStatus: ConnectionStatus;
  error: Error | null;
  connect: () => void;
  disconnect: () => void;
  subscribeToWorkflow: (workflowId: string) => void;
  subscribeToBot: (botId: string) => void;
  subscribeToStrategy: (strategyId: string) => void;
  unsubscribeFromWorkflow: (workflowId: string) => void;
  unsubscribeFromBot: (botId: string) => void;
  unsubscribeFromStrategy: (strategyId: string) => void;
}

/**
 * Custom hook for WebSocket connection management
 *
 * @param autoConnect - Whether to connect automatically on mount (default: true)
 * @returns WebSocket connection state and control functions
 */
export function useWebSocket(autoConnect = true): UseWebSocketReturn {
  const [isConnected, setIsConnected] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('disconnected');
  const [error, setError] = useState<Error | null>(null);

  // Handle connection
  const connect = useCallback(() => {
    setConnectionStatus('connecting');
    setError(null);

    websocketService.connect();
  }, []);

  // Handle disconnection
  const disconnect = useCallback(() => {
    websocketService.disconnect();
    setIsConnected(false);
    setConnectionStatus('disconnected');
  }, []);

  // Subscription functions
  const subscribeToWorkflow = useCallback((workflowId: string) => {
    websocketService.send('subscribe_workflow', { workflow_id: workflowId });
  }, []);

  const subscribeToBot = useCallback((botId: string) => {
    websocketService.subscribeToBot(botId);
  }, []);

  const subscribeToStrategy = useCallback((strategyId: string, botId = '') => {
    websocketService.subscribeToStrategy(botId, strategyId);
  }, []);

  const unsubscribeFromWorkflow = useCallback((workflowId: string) => {
    websocketService.send('unsubscribe_workflow', { workflow_id: workflowId });
  }, []);

  const unsubscribeFromBot = useCallback((botId: string) => {
    websocketService.unsubscribeFromBot(botId);
  }, []);

  const unsubscribeFromStrategy = useCallback((strategyId: string, botId = '') => {
    websocketService.unsubscribeFromStrategy(botId, strategyId);
  }, []);

  // Track if we've already connected to avoid re-triggering
  const hasConnectedRef = useRef(false);

  useEffect(() => {
    // Set up event listeners
    const handleConnect = () => {
      setIsConnected(true);
      setConnectionStatus('connected');
      setError(null);
    };

    const handleDisconnect = () => {
      setIsConnected(false);
      setConnectionStatus('disconnected');
    };

    const handleError = (err: Error) => {
      setError(err);
      setConnectionStatus('error');
    };

    // Subscribe to connection events
    websocketService.on('connect', handleConnect);
    websocketService.on('disconnect', handleDisconnect);
    websocketService.on('connect_error', handleError);

    // Auto-connect if enabled (only once)
    if (autoConnect && !hasConnectedRef.current) {
      hasConnectedRef.current = true;
      // Defer connection to avoid setState during render
      queueMicrotask(() => {
        websocketService.connect();
        setConnectionStatus('connecting');
      });
    }

    // Cleanup on unmount
    return () => {
      websocketService.off('connect', handleConnect);
      websocketService.off('disconnect', handleDisconnect);
      websocketService.off('connect_error', handleError);

      if (autoConnect) {
        disconnect();
      }
    };
  }, [autoConnect, disconnect]);

  return {
    isConnected,
    connectionStatus,
    error,
    connect,
    disconnect,
    subscribeToWorkflow,
    subscribeToBot,
    subscribeToStrategy,
    unsubscribeFromWorkflow,
    unsubscribeFromBot,
    unsubscribeFromStrategy,
  };
}

export default useWebSocket;
