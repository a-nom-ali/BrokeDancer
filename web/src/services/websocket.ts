/**
 * WebSocket Service
 *
 * Handles real-time communication with the backend using Socket.io
 * Provides type-safe event handling and automatic reconnection
 */

import { io, Socket } from 'socket.io-client';
import type {
  WebSocketEvent,
  NodeExecutionEvent,
  BotMetricsEvent,
  StrategyMetricsEvent,
  RiskLimitUpdateEvent,
} from '../types';

// WebSocket configuration
const WEBSOCKET_URL = import.meta.env.VITE_WEBSOCKET_URL || 'http://localhost:8001';
const RECONNECT_DELAY = 1000;
const MAX_RECONNECT_ATTEMPTS = 10;

// Event handler type - using generic function type for flexibility
// eslint-disable-next-line @typescript-eslint/no-explicit-any
type EventHandler = (data: any) => void;

/**
 * WebSocket Manager
 * Singleton class to manage WebSocket connections
 */
class WebSocketService {
  private socket: Socket | null = null;
  private reconnectAttempts = 0;
  private eventHandlers: Map<string, Set<EventHandler>> = new Map();
  private isConnecting = false;

  /**
   * Connect to WebSocket server
   */
  connect(): void {
    if (this.socket?.connected || this.isConnecting) {
      console.log('WebSocket already connected or connecting');
      return;
    }

    this.isConnecting = true;
    console.log('Connecting to WebSocket:', WEBSOCKET_URL);

    this.socket = io(WEBSOCKET_URL, {
      transports: ['websocket', 'polling'],
      reconnection: true,
      reconnectionDelay: RECONNECT_DELAY,
      reconnectionAttempts: MAX_RECONNECT_ATTEMPTS,
    });

    this.setupEventListeners();
  }

  /**
   * Disconnect from WebSocket server
   */
  disconnect(): void {
    if (this.socket) {
      console.log('Disconnecting from WebSocket');
      this.socket.disconnect();
      this.socket = null;
      this.isConnecting = false;
    }
  }

  /**
   * Setup Socket.io event listeners
   */
  private setupEventListeners(): void {
    if (!this.socket) return;

    this.socket.on('connect', () => {
      console.log('WebSocket connected');
      this.isConnecting = false;
      this.reconnectAttempts = 0;
      this.emit('connection_status', { connected: true });
    });

    this.socket.on('disconnect', (reason) => {
      console.log('WebSocket disconnected:', reason);
      this.isConnecting = false;
      this.emit('connection_status', { connected: false, reason });
    });

    this.socket.on('connect_error', (error) => {
      console.error('WebSocket connection error:', error);
      this.reconnectAttempts++;
      this.emit('connection_error', { error: error.message, attempts: this.reconnectAttempts });
    });

    this.socket.on('reconnect', (attemptNumber) => {
      console.log('WebSocket reconnected after', attemptNumber, 'attempts');
      this.reconnectAttempts = 0;
      this.emit('reconnected', { attempts: attemptNumber });
    });

    // Application-specific events from backend
    // Node execution events
    this.socket.on('node_execution', (data: NodeExecutionEvent) => {
      this.emit('node_execution', data);
    });

    // Bot metrics events
    this.socket.on('bot_metrics', (data: BotMetricsEvent) => {
      this.emit('bot_metrics', data);
    });

    // Strategy metrics events
    this.socket.on('strategy_metrics', (data: StrategyMetricsEvent) => {
      this.emit('strategy_metrics', data);
    });

    // Risk limit updates
    this.socket.on('risk_limit_update', (data: RiskLimitUpdateEvent) => {
      this.emit('risk_limit_update', data);
    });

    // Workflow events from backend WebSocket server
    this.socket.on('workflow_event', (data: WebSocketEvent) => {
      this.emit('workflow_event', data);
    });

    // Stats updates from Flask server
    this.socket.on('stats_update', (data: WebSocketEvent) => {
      this.emit('stats_update', data);
    });

    // Trade executed notifications
    this.socket.on('trade_executed', (data: WebSocketEvent) => {
      this.emit('trade_executed', data);
      // Also emit as workflow_event for dashboard compatibility
      this.emit('workflow_event', { ...data, type: 'execution_completed' });
    });

    // Bot lifecycle events
    this.socket.on('bot_started', (data: WebSocketEvent) => {
      this.emit('bot_started', data);
      this.emit('workflow_event', { ...data, type: 'execution_started' });
    });

    this.socket.on('bot_stopped', (data: WebSocketEvent) => {
      this.emit('bot_stopped', data);
      this.emit('workflow_event', { ...data, type: 'execution_halted' });
    });

    this.socket.on('bot_paused', (data: WebSocketEvent) => {
      this.emit('bot_paused', data);
    });

    this.socket.on('bot_resumed', (data: WebSocketEvent) => {
      this.emit('bot_resumed', data);
    });

    // Bot list and health updates
    this.socket.on('bot_list_update', (data: WebSocketEvent) => {
      this.emit('bot_list_update', data);
    });

    this.socket.on('provider_health_update', (data: WebSocketEvent) => {
      this.emit('provider_health_update', data);
    });

    // Recent events replay on connection
    this.socket.on('recent_events', (data: WebSocketEvent[]) => {
      data.forEach(event => this.emit('workflow_event', event));
    });

    // Notifications
    this.socket.on('notification', (data: WebSocketEvent) => {
      this.emit('notification', data);
    });

    // Execution complete (legacy)
    this.socket.on('execution_complete', (data: WebSocketEvent) => {
      this.emit('execution_complete', data);
    });
  }

  /**
   * Subscribe to an event
   */
  on(eventName: string, handler: EventHandler): void {
    if (!this.eventHandlers.has(eventName)) {
      this.eventHandlers.set(eventName, new Set());
    }
    this.eventHandlers.get(eventName)!.add(handler);
  }

  /**
   * Unsubscribe from an event
   */
  off(eventName: string, handler: EventHandler): void {
    const handlers = this.eventHandlers.get(eventName);
    if (handlers) {
      handlers.delete(handler);
    }
  }

  /**
   * Emit an event to all subscribers
   */
  private emit(eventName: string, data: unknown): void {
    const handlers = this.eventHandlers.get(eventName);
    if (handlers) {
      handlers.forEach(handler => handler(data));
    }
  }

  /**
   * Send a message to the server
   */
  send(eventName: string, data: unknown): void {
    if (!this.socket?.connected) {
      console.warn('WebSocket not connected, cannot send:', eventName);
      return;
    }
    this.socket.emit(eventName, data);
  }

  /**
   * Check if connected
   */
  get isConnected(): boolean {
    return this.socket?.connected ?? false;
  }

  /**
   * Subscribe to node execution events for a specific strategy
   */
  subscribeToStrategy(botId: string, strategyId: string): void {
    this.send('subscribe_strategy', { botId, strategyId });
  }

  /**
   * Unsubscribe from node execution events for a specific strategy
   */
  unsubscribeFromStrategy(botId: string, strategyId: string): void {
    this.send('unsubscribe_strategy', { botId, strategyId });
  }

  /**
   * Subscribe to bot metrics
   */
  subscribeToBot(botId: string): void {
    this.send('subscribe_bot', { botId });
  }

  /**
   * Unsubscribe from bot metrics
   */
  unsubscribeFromBot(botId: string): void {
    this.send('unsubscribe_bot', { botId });
  }

  /**
   * Subscribe to all bots (for main dashboard)
   */
  subscribeToAllBots(): void {
    this.send('subscribe_all_bots', {});
  }

  /**
   * Request current state
   */
  requestState(type: 'bot' | 'strategy', id: string): void {
    this.send('request_state', { type, id });
  }
}

// Export singleton instance
export const websocketService = new WebSocketService();

// Export class for testing
export { WebSocketService };
