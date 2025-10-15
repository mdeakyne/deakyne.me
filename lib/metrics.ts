const BOX_WIDTH = 59;
const NUMBER_FORMAT = new Intl.NumberFormat('en-US');
const PERCENT_FORMAT = new Intl.NumberFormat('en-US', {
  style: 'percent',
  minimumFractionDigits: 1,
  maximumFractionDigits: 1,
});
const SPARKLINE_CHARS = ['▁', '▂', '▃', '▄', '▅', '▆', '▇', '█'];

export interface MetricsOverview {
  totalCalls: number;
  uniqueUsers: number;
  avgResponseTimeMs: number;
  errorRate: number;
  activeUsers?: number;
  uptime?: number;
  lastRefreshed?: string;
}

export interface MetricsEndpointStat {
  endpoint: string;
  totalCalls: number;
  avgResponseTimeMs: number;
  errorRate: number;
  remoteTotal?: number | null;
}

export interface MetricsTimelinePoint {
  label: string;
  totalCalls: number;
}

export type TrendDirection = 'up' | 'down' | 'flat';

export interface MetricsDashboardPayload {
  overview: MetricsOverview;
  endpoints: MetricsEndpointStat[];
  timeline: MetricsTimelinePoint[];
  responseTimes?: {
    p50: number;
    p95: number;
    p99: number;
    trend: TrendDirection;
  };
}

function pad(content = ''): string {
  const safe = content.length > BOX_WIDTH - 4 ? content.slice(0, BOX_WIDTH - 7) + '...' : content;
  const padded = safe.padEnd(BOX_WIDTH - 4, ' ');
  return `║ ${padded} ║`;
}

function blankLine(): string {
  return `║ ${' '.repeat(BOX_WIDTH - 4)} ║`;
}

function formatNumber(value: number): string {
  return NUMBER_FORMAT.format(Math.round(value));
}

function formatMs(value: number): string {
  return `${Math.round(value)}ms`;
}

function formatPercent(value: number): string {
  const normalized = Math.max(0, Math.min(1, value));
  return PERCENT_FORMAT.format(normalized);
}

function formatOverview(overview: MetricsOverview): string[] {
  const uptime = overview.uptime ?? (1 - overview.errorRate);
  const lines: string[] = [];
  lines.push(pad('📊 OVERVIEW (Last 30 Days)'));
  lines.push(blankLine());
  lines.push(pad(`Total API Calls:`.padEnd(24) + ` ${formatNumber(overview.totalCalls)}`));
  lines.push(pad(`Unique Developers:`.padEnd(24) + ` ${formatNumber(overview.uniqueUsers)}`));
  lines.push(pad(`Avg Response Time:`.padEnd(24) + ` ${formatMs(overview.avgResponseTimeMs)}`));
  lines.push(pad(`Uptime:`.padEnd(24) + ` ${formatPercent(uptime)}`));
  if (overview.activeUsers !== undefined) {
    lines.push(pad(`Active Users (7d):`.padEnd(24) + ` ${formatNumber(overview.activeUsers)}`));
  }
  if (overview.lastRefreshed) {
    lines.push(pad(`Refreshed:`.padEnd(24) + ` ${overview.lastRefreshed}`));
  }
  return lines;
}

function generateBar(value: number, max: number, width = 24): string {
  if (max <= 0) {
    return '░'.repeat(width);
  }
  const ratio = Math.max(0, Math.min(1, value / max));
  const filled = Math.max(1, Math.round(ratio * width));
  return '█'.repeat(filled).padEnd(width, '░');
}

function formatEndpoints(endpoints: MetricsEndpointStat[]): string[] {
  if (!endpoints.length) {
    return [pad('No endpoint traffic recorded yet.')];
  }

  const total = endpoints.reduce((acc, item) => acc + item.totalCalls, 0);
  const max = Math.max(...endpoints.map((item) => item.totalCalls));
  const lines: string[] = [];
  lines.push(pad('📈 TOP ENDPOINTS'));
  lines.push(blankLine());

  endpoints.slice(0, 10).forEach((endpoint) => {
    const percentage = total ? (endpoint.totalCalls / total) : 0;
    const bar = generateBar(endpoint.totalCalls, max);
    const label = endpoint.endpoint.padEnd(18);
    const remoteTag = endpoint.remoteTotal ? ` | PostHog: ${formatNumber(endpoint.remoteTotal)}` : '';
    const meta = `${formatNumber(endpoint.totalCalls)} (${formatPercent(percentage)})${remoteTag}`;
    lines.push(pad(`${label}${bar}  ${meta}`));
  });

  return lines;
}

function sparkline(values: number[]): string {
  if (!values.length) {
    return ''.padEnd(10, '▁');
  }
  const min = Math.min(...values);
  const max = Math.max(...values);
  if (min === max) {
    return SPARKLINE_CHARS[0].repeat(values.length);
  }
  return values
    .map((value) => {
      const ratio = (value - min) / (max - min || 1);
      const index = Math.min(SPARKLINE_CHARS.length - 1, Math.round(ratio * (SPARKLINE_CHARS.length - 1)));
      return SPARKLINE_CHARS[index];
    })
    .join('');
}

function formatTimeline(points: MetricsTimelinePoint[]): string[] {
  if (!points.length) {
    return [pad('No timeline data available.')];
  }
  const values = points.map((point) => point.totalCalls);
  const spark = sparkline(values);
  const start = points[0]?.label ?? '';
  const end = points[points.length - 1]?.label ?? '';
  return [
    pad('⚡ ACTIVITY'),
    blankLine(),
    pad(`Volume: ${spark}`),
    pad(`Range: ${start} → ${end}`),
  ];
}

function formatResponseTimes(trends?: { p50: number; p95: number; p99: number; trend: TrendDirection }): string[] {
  if (!trends) {
    return [pad('⏱ RESPONSE TIMES'), blankLine(), pad('No percentile data available.')];
  }
  const trendSymbol = trends.trend === 'up' ? '↑' : trends.trend === 'down' ? '↓' : '→';
  return [
    pad('⏱ RESPONSE TIMES'),
    blankLine(),
    pad(`P50 / P95 / P99:`.padEnd(24) + ` ${formatMs(trends.p50)} / ${formatMs(trends.p95)} / ${formatMs(trends.p99)}`),
    pad(`Trend:`.padEnd(24) + ` ${trendSymbol}`),
  ];
}

export function renderDashboard(payload: MetricsDashboardPayload): string {
  const lines: string[] = [];
  lines.push('');
  lines.push('╔═══════════════════════════════════════════════════════════╗');
  lines.push('║              DEAKYNE.ME API METRICS DASHBOARD             ║');
  lines.push('╠═══════════════════════════════════════════════════════════╣');
  lines.push(blankLine());
  lines.push(...formatOverview(payload.overview));
  lines.push(blankLine());
  lines.push(...formatEndpoints(payload.endpoints));
  lines.push(blankLine());
  lines.push(...formatTimeline(payload.timeline));
  lines.push(blankLine());
  lines.push(...formatResponseTimes(payload.responseTimes));
  lines.push(blankLine());
  lines.push('╚═══════════════════════════════════════════════════════════╝');
  lines.push('');
  return lines.join('\r\n');
}
