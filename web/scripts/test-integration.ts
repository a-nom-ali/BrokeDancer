/**
 * Integration Test Script
 *
 * Tests connectivity between React dashboard and backend servers.
 * Run with: npx tsx scripts/test-integration.ts
 */

import { io } from 'socket.io-client';

const API_URL = process.env.VITE_API_URL || 'http://localhost:8080/api';
const WS_URL = process.env.VITE_WEBSOCKET_URL || 'http://localhost:8001';

interface TestResult {
  name: string;
  success: boolean;
  message: string;
  duration: number;
}

const results: TestResult[] = [];

async function testAPIEndpoint(name: string, endpoint: string): Promise<TestResult> {
  const start = Date.now();
  try {
    const response = await fetch(`${API_URL}${endpoint}`);
    const duration = Date.now() - start;

    if (response.ok) {
      const data = await response.json();
      return {
        name,
        success: true,
        message: `OK (${response.status}) - ${JSON.stringify(data).slice(0, 100)}...`,
        duration,
      };
    } else {
      return {
        name,
        success: false,
        message: `HTTP ${response.status}: ${response.statusText}`,
        duration,
      };
    }
  } catch (error) {
    return {
      name,
      success: false,
      message: error instanceof Error ? error.message : 'Unknown error',
      duration: Date.now() - start,
    };
  }
}

async function testWebSocketConnection(): Promise<TestResult> {
  const start = Date.now();

  return new Promise((resolve) => {
    const timeout = setTimeout(() => {
      resolve({
        name: 'WebSocket Connection',
        success: false,
        message: 'Connection timeout (5s)',
        duration: Date.now() - start,
      });
    }, 5000);

    const socket = io(WS_URL, {
      transports: ['websocket', 'polling'],
      reconnection: false,
      timeout: 5000,
    });

    socket.on('connect', () => {
      clearTimeout(timeout);
      const duration = Date.now() - start;
      socket.disconnect();
      resolve({
        name: 'WebSocket Connection',
        success: true,
        message: `Connected to ${WS_URL}`,
        duration,
      });
    });

    socket.on('connect_error', (error) => {
      clearTimeout(timeout);
      socket.disconnect();
      resolve({
        name: 'WebSocket Connection',
        success: false,
        message: error.message,
        duration: Date.now() - start,
      });
    });
  });
}

async function runTests() {
  console.log('\n🧪 Integration Tests\n');
  console.log(`API URL: ${API_URL}`);
  console.log(`WebSocket URL: ${WS_URL}\n`);
  console.log('─'.repeat(60));

  // Test API endpoints
  const apiTests = [
    { name: 'API Status', endpoint: '/status' },
    { name: 'API Bots List', endpoint: '/bots' },
    { name: 'API Stats', endpoint: '/stats' },
    { name: 'API Providers', endpoint: '/providers' },
    { name: 'API Strategies', endpoint: '/strategies' },
  ];

  for (const test of apiTests) {
    const result = await testAPIEndpoint(test.name, test.endpoint);
    results.push(result);
    const icon = result.success ? '✅' : '❌';
    console.log(`${icon} ${result.name} (${result.duration}ms)`);
    if (!result.success) {
      console.log(`   └─ ${result.message}`);
    }
  }

  // Test WebSocket
  console.log('─'.repeat(60));
  const wsResult = await testWebSocketConnection();
  results.push(wsResult);
  const wsIcon = wsResult.success ? '✅' : '❌';
  console.log(`${wsIcon} ${wsResult.name} (${wsResult.duration}ms)`);
  if (!wsResult.success) {
    console.log(`   └─ ${wsResult.message}`);
  }

  // Summary
  console.log('\n' + '═'.repeat(60));
  const passed = results.filter((r) => r.success).length;
  const total = results.length;
  const allPassed = passed === total;

  console.log(`\n${allPassed ? '✅' : '⚠️'} ${passed}/${total} tests passed\n`);

  if (!allPassed) {
    console.log('Failed tests:');
    results
      .filter((r) => !r.success)
      .forEach((r) => console.log(`  - ${r.name}: ${r.message}`));
    console.log('\nMake sure the backend servers are running:');
    console.log('  1. Flask server: python -m src.web.server --port 8080');
    console.log('  2. WebSocket server: python src/web/run_websocket_server.py --port 8001');
  }

  process.exit(allPassed ? 0 : 1);
}

runTests().catch(console.error);
