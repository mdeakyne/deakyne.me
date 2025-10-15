import { describe, expect, it } from 'vitest';

import { renderDashboard, type MetricsDashboardPayload } from '@/lib/metrics';

const samplePayload: MetricsDashboardPayload = {
  overview: {
    totalCalls: 1247,
    uniqueUsers: 23,
    avgResponseTimeMs: 45,
    errorRate: 0.002,
    activeUsers: 12,
    lastRefreshed: '2025-10-14T12:00:00Z',
  },
  endpoints: [
    { endpoint: '/api/profile', totalCalls: 342, avgResponseTimeMs: 30, errorRate: 0.01, remoteTotal: 360 },
    { endpoint: '/api/experience', totalCalls: 256, avgResponseTimeMs: 42, errorRate: 0.02 },
    { endpoint: '/api/books', totalCalls: 154, avgResponseTimeMs: 54, errorRate: 0.03 },
  ],
  timeline: [
    { label: 'Mon', totalCalls: 90 },
    { label: 'Tue', totalCalls: 100 },
    { label: 'Wed', totalCalls: 80 },
    { label: 'Thu', totalCalls: 120 },
    { label: 'Fri', totalCalls: 60 },
  ],
  responseTimes: {
    p50: 40,
    p95: 75,
    p99: 110,
    trend: 'down',
  },
};

describe('renderDashboard', () => {
  it('renders key overview metrics', () => {
    const output = renderDashboard(samplePayload);
    expect(output).toContain('Total API Calls');
    expect(output).toContain('1,247');
    expect(output).toContain('Active Users (7d)');
  });

  it('renders endpoint breakdown with percentages', () => {
    const output = renderDashboard(samplePayload);
    expect(output).toContain('/api/profile');
    expect(output).toMatch(/\(\d+(\.\d+)?%/);
  });

  it('renders timeline sparkline', () => {
    const output = renderDashboard(samplePayload);
    expect(output).toContain('Volume:');
    expect(output).toMatch(/[▁▂▃▄▅▆▇█]+/);
  });

  it('renders response time percentiles', () => {
    const output = renderDashboard(samplePayload);
    expect(output).toContain('P50 / P95 / P99');
    expect(output).toContain('40ms');
    expect(output).toContain('↓');
  });
});
