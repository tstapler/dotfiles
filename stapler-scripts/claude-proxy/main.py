"""Claude Proxy - Simple OAuth + Bedrock fallback proxy for Claude Code."""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse, HTMLResponse
from typing import Dict, Any
import asyncio
import json
import logging
from logging.handlers import RotatingFileHandler
import time

from auth import get_auth_from_request
from providers.anthropic import AnthropicProvider
from providers.bedrock import BedrockProvider
from providers import ValidationError, AuthenticationError, RateLimitError
from fallback import FallbackHandler
from metrics import MetricsCollector
from compactor import compress_messages, get_flags, init_compactor
from error_tracker import ErrorTracker, ErrorTrackingHandler
import config

# Configure logging with rotation and separate files
# Keep 10 files of 10MB each (100MB total) per log type

# Application logs (main, fallback, providers) - meaningful logs
app_handler = RotatingFileHandler(
    '/tmp/claude-proxy.app.log',
    maxBytes=10*1024*1024,  # 10MB per file
    backupCount=10
)
app_handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
))

# HTTP request logs (httpx, httpcore) - noisy logs
http_handler = RotatingFileHandler(
    '/tmp/claude-proxy.http.log',
    maxBytes=10*1024*1024,  # 10MB per file
    backupCount=5  # Less history for noisy logs
)
http_handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(name)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
))

# Configure root logger for application logs
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
root_logger.addHandler(app_handler)

# Configure httpx/httpcore to use separate log file
for http_logger_name in ['httpx', 'httpcore']:
    http_logger = logging.getLogger(http_logger_name)
    http_logger.handlers.clear()  # Remove inherited handlers
    http_logger.addHandler(http_handler)
    http_logger.propagate = False  # Don't propagate to root logger

logger = logging.getLogger(__name__)

# Initialize error tracking
error_tracker = ErrorTracker()
error_tracking_handler = ErrorTrackingHandler(error_tracker)
root_logger.addHandler(error_tracking_handler)
logger.info("Error tracking handler attached")


def _msg_type_summary(messages: list) -> tuple[str, dict]:
    """Count content block types across all messages.

    Returns (json_string, raw_dict) where json_string is a compact representation
    suitable for logging and storage, e.g. '{"text":5,"tool_use":3,"tool_result":3}'.
    """
    counts: dict = {}
    for msg in messages:
        content = msg.get("content", "")
        if isinstance(content, str) and content:
            counts["text"] = counts.get("text", 0) + 1
        elif isinstance(content, list):
            for block in content:
                if isinstance(block, dict):
                    t = block.get("type", "unknown")
                    counts[t] = counts.get(t, 0) + 1
    if not counts:
        return "", counts
    return json.dumps(counts, separators=(",", ":")), counts


# Request duration thresholds for monitoring
SLOW_REQUEST_THRESHOLD = 30  # seconds
BLOCKING_REQUEST_THRESHOLD = 60  # seconds


async def _monitor_event_loop_lag():
    """Sample event loop lag every second and record to metrics."""
    while True:
        t = time.perf_counter()
        await asyncio.sleep(1)
        lag_ms = max(0.0, (time.perf_counter() - t - 1.0) * 1000)
        # Use async version to avoid blocking event loop with disk I/O
        await metrics.record_event_loop_lag_async(lag_ms)
        if lag_ms > 200:
            logger.warning(f"⚠️ Event loop lag: {lag_ms:.1f}ms")
        elif lag_ms > 50:
            logger.debug(f"Event loop lag: {lag_ms:.1f}ms")


@asynccontextmanager
async def lifespan(app: FastAPI):
    asyncio.create_task(_monitor_event_loop_lag())
    init_compactor()
    # Set anyio's default thread limiter to match BEDROCK_THREAD_POOL_SIZE
    # so streaming boto3 calls (which must use anyio threads for from_thread.run) are bounded
    import anyio
    limiter = anyio.to_thread.current_default_thread_limiter()
    limiter.total_tokens = config.BEDROCK_THREAD_POOL_SIZE
    logger.info(f"anyio thread limiter set to {config.BEDROCK_THREAD_POOL_SIZE} threads")
    yield


# Initialize FastAPI app
app = FastAPI(title="Claude Proxy", version="1.0.0", lifespan=lifespan)

# Initialize metrics collector
metrics = MetricsCollector()

# Initialize providers
anthropic = AnthropicProvider()
bedrock = BedrockProvider()

# Create fallback handler with provider priority
fallback = FallbackHandler([anthropic, bedrock], metrics=metrics)


# Dashboard HTML template
DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Claude Proxy Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: #0a0a0a;
            color: #e0e0e0;
            padding: 20px;
        }
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 24px;
            padding-bottom: 16px;
            border-bottom: 1px solid #333;
        }
        h1 {
            font-size: 28px;
            font-weight: 600;
            color: #fff;
        }
        .status-bar {
            display: flex;
            gap: 16px;
            align-items: center;
        }
        .provider-status {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 14px;
        }
        .status-indicator {
            width: 10px;
            height: 10px;
            border-radius: 50%;
            display: inline-block;
        }
        .status-active { background: #10b981; }
        .status-cooldown { background: #f59e0b; }
        .refresh-time {
            color: #888;
            font-size: 14px;
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 16px;
            margin-bottom: 24px;
        }
        .stat-card {
            background: #1a1a1a;
            border: 1px solid #2a2a2a;
            border-radius: 8px;
            padding: 16px;
        }
        .stat-label {
            font-size: 12px;
            color: #888;
            text-transform: uppercase;
            margin-bottom: 8px;
        }
        .stat-value {
            font-size: 32px;
            font-weight: 600;
            color: #fff;
        }
        .stat-subtitle {
            font-size: 14px;
            color: #666;
            margin-top: 4px;
        }
        .charts-grid {
            display: grid;
            grid-template-columns: 2fr 1fr 1fr;
            gap: 16px;
            margin-bottom: 24px;
        }
        .chart-container {
            background: #1a1a1a;
            border: 1px solid #2a2a2a;
            border-radius: 8px;
            padding: 16px;
        }
        .chart-title {
            font-size: 14px;
            font-weight: 600;
            color: #fff;
            margin-bottom: 12px;
        }
        .errors-section {
            background: #1a1a1a;
            border: 1px solid #2a2a2a;
            border-radius: 8px;
            padding: 16px;
        }
        .errors-title {
            font-size: 14px;
            font-weight: 600;
            color: #fff;
            margin-bottom: 12px;
        }
        .errors-table {
            width: 100%;
            border-collapse: collapse;
        }
        .errors-table th {
            text-align: left;
            font-size: 12px;
            color: #888;
            padding: 8px 12px;
            border-bottom: 1px solid #2a2a2a;
        }
        .errors-table td {
            font-size: 13px;
            padding: 8px 12px;
            border-bottom: 1px solid #2a2a2a;
        }
        .error-type {
            display: inline-block;
            padding: 2px 8px;
            background: #7c2d12;
            color: #fca5a5;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 500;
        }
        .no-errors {
            color: #666;
            font-size: 14px;
            padding: 16px;
            text-align: center;
        }
        @media (max-width: 1024px) {
            .charts-grid {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>Claude Proxy</h1>
        <div class="status-bar">
            <div class="provider-status">
                <span class="status-indicator" id="anthropic-status"></span>
                <span id="anthropic-text">Anthropic</span>
            </div>
            <div class="provider-status">
                <span class="status-indicator" id="bedrock-status"></span>
                <span id="bedrock-text">Bedrock</span>
            </div>
            <div class="refresh-time" id="refresh-time">Loading...</div>
        </div>
    </div>

    <div class="stats-grid">
        <div class="stat-card">
            <div class="stat-label">Total Requests</div>
            <div class="stat-value" id="total-requests">0</div>
        </div>
        <div class="stat-card">
            <div class="stat-label">Success Rate</div>
            <div class="stat-value" id="success-rate">0%</div>
            <div class="stat-subtitle" id="success-count">0 successful</div>
        </div>
        <div class="stat-card">
            <div class="stat-label">Error Rate</div>
            <div class="stat-value" id="error-rate">0%</div>
            <div class="stat-subtitle" id="error-count">0 errors</div>
        </div>
        <div class="stat-card">
            <div class="stat-label">Fallbacks</div>
            <div class="stat-value" id="fallback-count">0</div>
        </div>
        <div class="stat-card">
            <div class="stat-label">Loop Lag (current)</div>
            <div class="stat-value" id="loop-lag">0ms</div>
            <div class="stat-subtitle" id="loop-lag-status">healthy</div>
        </div>
        <div class="stat-card">
            <div class="stat-label">Tokens Saved</div>
            <div class="stat-value" id="tokens-saved">0</div>
            <div class="stat-subtitle" id="compression-ratio">— compression</div>
        </div>
    </div>

    <div class="charts-grid">
        <div class="chart-container">
            <div class="chart-title">Requests Per Minute (15 min)</div>
            <canvas id="rpm-chart"></canvas>
        </div>
        <div class="chart-container">
            <div class="chart-title">Providers</div>
            <canvas id="provider-chart"></canvas>
        </div>
        <div class="chart-container">
            <div class="chart-title">Duration</div>
            <canvas id="duration-chart"></canvas>
        </div>
    </div>

    <div class="chart-container" style="margin-bottom: 24px;">
        <div class="chart-title">Event Loop Lag — max ms per minute (15 min)</div>
        <canvas id="lag-chart"></canvas>
    </div>

    <div class="chart-container" style="margin-bottom: 24px;">
        <div class="chart-title">Latency by Provider</div>
        <div class="stats-grid" style="margin-top: 12px; margin-bottom: 0;">
            <div class="stat-card">
                <div class="stat-label">Anthropic Avg Duration</div>
                <div class="stat-value" id="lat-anthropic-dur">—</div>
                <div class="stat-subtitle" id="lat-anthropic-req">0 requests</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Anthropic Avg TTFT</div>
                <div class="stat-value" id="lat-anthropic-ttft">—</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Bedrock Avg Duration</div>
                <div class="stat-value" id="lat-bedrock-dur">—</div>
                <div class="stat-subtitle" id="lat-bedrock-req">0 requests</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Bedrock Avg TTFT</div>
                <div class="stat-value" id="lat-bedrock-ttft">—</div>
            </div>
        </div>
    </div>

    <div class="chart-container" style="margin-bottom: 24px;">
        <div class="chart-title">Compression</div>
        <div class="stats-grid" style="margin-top: 12px; margin-bottom: 0;">
            <div class="stat-card">
                <div class="stat-label">Requests Compressed</div>
                <div class="stat-value" id="comp-requests">0</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Avg Compression Ratio</div>
                <div class="stat-value" id="comp-ratio">0%</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Total Tokens Before</div>
                <div class="stat-value" id="comp-before">0</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Total Tokens After</div>
                <div class="stat-value" id="comp-after">0</div>
            </div>
        </div>
        <div id="compression-disabled-notice" style="display:none; color:#888; font-size:13px; padding:8px 0; text-align:center;">
            Compression inactive — no requests compressed yet (or STAPLER_COMPRESS=0)
        </div>
    </div>

    <div class="errors-section" style="margin-bottom: 24px;">
        <div class="errors-title">Recent Requests</div>
        <table class="errors-table">
            <thead>
                <tr>
                    <th>Time</th>
                    <th>ID</th>
                    <th>Provider</th>
                    <th>Model</th>
                    <th>Duration</th>
                    <th>TTFT</th>
                    <th>Tokens Before → After</th>
                    <th>Saved</th>
                    <th>Msgs</th>
                    <th>Content Types</th>
                    <th>Type</th>
                </tr>
            </thead>
            <tbody id="requests-body">
                <tr><td colspan="9" class="no-errors">No requests yet</td></tr>
            </tbody>
        </table>
    </div>

    <div class="errors-section" style="margin-bottom: 24px;">
        <div class="errors-title">count_tokens Health</div>
        <div class="stats-grid" style="margin-top: 12px; margin-bottom: 0;">
            <div class="stat-card">
                <div class="stat-label">Total Calls</div>
                <div class="stat-value" id="ct-total">0</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Failures</div>
                <div class="stat-value" id="ct-failures">0</div>
                <div class="stat-subtitle" id="ct-failure-rate">0% failure rate</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Last Token Count</div>
                <div class="stat-value" id="ct-last-count">—</div>
                <div class="stat-subtitle" id="ct-last-model">—</div>
            </div>
        </div>
        <div style="color:#888;font-size:12px;padding:8px 0;">
            count_tokens drives Claude Code auto-compaction. Failures here prevent compaction from triggering.
        </div>
    </div>

    <div class="errors-section" style="margin-bottom: 24px;">
        <div class="errors-title">Unique Error Types (persistent)</div>
        <table class="errors-table">
            <thead>
                <tr>
                    <th>Fingerprint</th>
                    <th>Provider</th>
                    <th>Type</th>
                    <th>Count</th>
                    <th>First Seen</th>
                    <th>Last Seen</th>
                    <th>Message</th>
                </tr>
            </thead>
            <tbody id="error-types-body">
                <tr><td colspan="7" class="no-errors">Loading...</td></tr>
            </tbody>
        </table>
    </div>

    <div class="errors-section">
        <div class="errors-title">Recent Errors (in-memory)</div>
        <table class="errors-table">
            <thead>
                <tr>
                    <th>Time</th>
                    <th>Type</th>
                    <th>Provider</th>
                    <th>Model</th>
                </tr>
            </thead>
            <tbody id="errors-body">
                <tr><td colspan="4" class="no-errors">No errors yet</td></tr>
            </tbody>
        </table>
    </div>

    <!-- Request body inspection modal -->
    <div id="body-modal" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,0.7);z-index:1000;overflow:auto;" onclick="if(event.target===this)closeModal()">
        <div style="background:#1a1a1a;border:1px solid #333;border-radius:8px;max-width:900px;margin:40px auto;padding:24px;position:relative;">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;">
                <span id="modal-title" style="font-weight:600;color:#e5e5e5;font-size:14px;"></span>
                <div style="display:flex;gap:8px;align-items:center;">
                    <button id="modal-stage-orig" onclick="switchStage('original')" style="background:#2a2a2a;border:1px solid #444;color:#ccc;cursor:pointer;padding:3px 10px;border-radius:4px;font-size:12px;font-weight:bold;">Original</button>
                    <button id="modal-stage-comp" onclick="switchStage('compressed')" style="background:#2a2a2a;border:1px solid #444;color:#ccc;cursor:pointer;padding:3px 10px;border-radius:4px;font-size:12px;font-weight:normal;">Compressed</button>
                    <button onclick="closeModal()" style="background:#333;border:none;color:#aaa;cursor:pointer;padding:4px 10px;border-radius:4px;font-size:14px;">✕</button>
                </div>
            </div>
            <pre id="modal-body" style="background:#111;border:1px solid #2a2a2a;border-radius:6px;padding:16px;overflow:auto;max-height:70vh;font-size:12px;line-height:1.5;color:#d4d4d4;white-space:pre-wrap;word-break:break-all;margin:0;"></pre>
        </div>
    </div>

    <script>
        // Chart instances
        let rpmChart, providerChart, durationChart, lagChart;

        // Initialize charts
        function initCharts() {
            const chartDefaults = {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: { display: false }
                }
            };

            rpmChart = new Chart(document.getElementById('rpm-chart'), {
                type: 'line',
                data: { labels: [], datasets: [{ data: [], borderColor: '#3b82f6', tension: 0.4 }] },
                options: {
                    ...chartDefaults,
                    scales: {
                        y: { beginAtZero: true, grid: { color: '#2a2a2a' }, ticks: { color: '#888' } },
                        x: { grid: { display: false }, ticks: { color: '#888' } }
                    }
                }
            });

            providerChart = new Chart(document.getElementById('provider-chart'), {
                type: 'doughnut',
                data: {
                    labels: ['Anthropic', 'Bedrock', 'Failed'],
                    datasets: [{
                        data: [0, 0, 0],
                        backgroundColor: ['#3b82f6', '#10b981', '#ef4444']
                    }]
                },
                options: {
                    ...chartDefaults,
                    plugins: { legend: { display: true, position: 'bottom', labels: { color: '#888' } } }
                }
            });

            durationChart = new Chart(document.getElementById('duration-chart'), {
                type: 'bar',
                data: {
                    labels: ['< 1s', '1-5s', '5-30s', '30-60s', '> 60s'],
                    datasets: [{ data: [0, 0, 0, 0, 0], backgroundColor: '#3b82f6' }]
                },
                options: {
                    ...chartDefaults,
                    scales: {
                        y: { beginAtZero: true, grid: { color: '#2a2a2a' }, ticks: { color: '#888' } },
                        x: { grid: { display: false }, ticks: { color: '#888' } }
                    }
                }
            });

            lagChart = new Chart(document.getElementById('lag-chart'), {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [
                        {
                            label: 'max',
                            data: [],
                            borderColor: '#ef4444',
                            backgroundColor: 'rgba(239,68,68,0.1)',
                            fill: true,
                            tension: 0.4
                        },
                        {
                            label: 'avg',
                            data: [],
                            borderColor: '#f59e0b',
                            borderDash: [4, 4],
                            tension: 0.4
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: true,
                    plugins: {
                        legend: { display: true, position: 'top', labels: { color: '#888' } },
                        tooltip: { callbacks: { label: ctx => `${ctx.dataset.label}: ${ctx.parsed.y.toFixed(2)}ms` } }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            grid: { color: '#2a2a2a' },
                            ticks: { color: '#888', callback: v => v + 'ms' }
                        },
                        x: { grid: { display: false }, ticks: { color: '#888' } }
                    }
                }
            });
        }

        // Load metrics and update dashboard
        async function loadMetrics() {
            try {
                const response = await fetch('/metrics');
                const data = await response.json();

                // Update stats
                document.getElementById('total-requests').textContent = data.summary.total_requests.toLocaleString();
                document.getElementById('success-rate').textContent = data.summary.success_rate.toFixed(1) + '%';
                document.getElementById('success-count').textContent = data.summary.total_success.toLocaleString() + ' successful';
                document.getElementById('error-rate').textContent = data.summary.error_rate.toFixed(1) + '%';
                document.getElementById('error-count').textContent = data.summary.total_errors.toLocaleString() + ' errors';
                document.getElementById('fallback-count').textContent = data.summary.total_fallbacks.toLocaleString();

                // Update provider status
                if (data.cooldowns) {
                    for (const [provider, status] of Object.entries(data.cooldowns)) {
                        const indicator = document.getElementById(`${provider}-status`);
                        const text = document.getElementById(`${provider}-text`);
                        if (status.cooling_down && status.remaining_seconds > 0) {
                            indicator.className = 'status-indicator status-cooldown';
                            text.textContent = `${provider.charAt(0).toUpperCase() + provider.slice(1)} (${status.remaining_seconds}s)`;
                        } else {
                            indicator.className = 'status-indicator status-active';
                            text.textContent = provider.charAt(0).toUpperCase() + provider.slice(1);
                        }
                    }
                }

                // Update RPM chart
                rpmChart.data.labels = data.rpm_data.map(d => d.minute);
                rpmChart.data.datasets[0].data = data.rpm_data.map(d => d.requests);
                rpmChart.update();

                // Update provider chart
                providerChart.data.datasets[0].data = [
                    data.providers.anthropic?.requests || 0,
                    data.providers.bedrock?.requests || 0,
                    data.providers.none?.requests || 0
                ];
                providerChart.update();

                // Update duration chart
                const dist = data.duration_distribution;
                durationChart.data.datasets[0].data = [
                    dist['< 1s'] || 0,
                    dist['1-5s'] || 0,
                    dist['5-30s'] || 0,
                    dist['30-60s'] || 0,
                    dist['> 60s'] || 0
                ];
                durationChart.update();

                // Update loop lag stat card
                const lagMs = data.current_lag_ms || 0;
                const lagEl = document.getElementById('loop-lag');
                const lagStatus = document.getElementById('loop-lag-status');
                lagEl.textContent = lagMs.toFixed(1) + 'ms';
                if (lagMs >= 50) {
                    lagEl.style.color = '#ef4444';
                    lagStatus.textContent = 'contended';
                } else if (lagMs >= 10) {
                    lagEl.style.color = '#f59e0b';
                    lagStatus.textContent = 'elevated';
                } else {
                    lagEl.style.color = '#10b981';
                    lagStatus.textContent = 'healthy';
                }

                // Update event loop lag chart
                if (data.lag_data) {
                    lagChart.data.labels = data.lag_data.map(d => d.minute);
                    lagChart.data.datasets[0].data = data.lag_data.map(d => d.max_ms);
                    lagChart.data.datasets[1].data = data.lag_data.map(d => d.avg_ms);
                    lagChart.update();
                }

                // Update compression stats
                if (data.compression) {
                    const c = data.compression;
                    const saved = c.total_tokens_saved || 0;
                    const ratio = c.avg_compression_ratio || 0;
                    const requests = c.total_requests_compressed || 0;

                    document.getElementById('tokens-saved').textContent = saved.toLocaleString();
                    document.getElementById('compression-ratio').textContent =
                        ratio > 0 ? (ratio * 100).toFixed(1) + '% avg saved' : '— compression';

                    document.getElementById('comp-requests').textContent = requests.toLocaleString();
                    document.getElementById('comp-ratio').textContent =
                        ratio > 0 ? (ratio * 100).toFixed(1) + '%' : '0%';
                    document.getElementById('comp-before').textContent =
                        (c.total_tokens_before || 0).toLocaleString();
                    document.getElementById('comp-after').textContent =
                        (c.total_tokens_after || 0).toLocaleString();

                    const notice = document.getElementById('compression-disabled-notice');
                    notice.style.display = requests === 0 ? 'block' : 'none';
                }

                // Update recent requests table
                const requestsBody = document.getElementById('requests-body');
                if (data.recent_requests && data.recent_requests.length > 0) {
                    const abbrevModel = m => {
                        if (!m || m === 'unknown') return m || '—';
                        if (m.includes('opus')) return 'opus';
                        if (m.includes('sonnet')) return 'sonnet';
                        if (m.includes('haiku')) return 'haiku';
                        return m.split('-').slice(-1)[0] || m;
                    };
                    const fmtMs = ms => !ms ? '—' : ms >= 1000 ? (ms/1000).toFixed(1)+'s' : Math.round(ms)+'ms';
                    const provColor = p => p === 'anthropic' ? '#1e3a5f' : p === 'bedrock' ? '#1a3a2a' : '#2a2a2a';
                    const fmtTypes = (json, cm) => {
                        if (!json) return '—';
                        try {
                            const t = JSON.parse(json);
                            const abbrevs = {text:'T', tool_use:'TU', tool_result:'TR', image:'IMG', document:'DOC', search_result:'SR'};
                            const parts = Object.entries(t).map(([k,v]) => `${abbrevs[k]||k}:${v}`);
                            const cmBadge = cm ? ' <span class="error-type" style="background:#3a2a1a;font-size:10px">CM</span>' : '';
                            return `<span style="font-size:11px;color:#aaa">${parts.join(' ')}</span>${cmBadge}`;
                        } catch { return json; }
                    };
                    requestsBody.innerHTML = data.recent_requests.slice(0, 20).map(r => {
                        const time = new Date(r.timestamp).toLocaleTimeString();
                        const saved = r.tokens_before > 0 ? r.tokens_before - r.tokens_after : 0;
                        const pct = r.tokens_before > 0 ? ((saved / r.tokens_before) * 100).toFixed(1) + '%' : '—';
                        const tokStr = r.compressed
                            ? `${r.tokens_before.toLocaleString()} → ${r.tokens_after.toLocaleString()}`
                            : `${r.tokens_before.toLocaleString()}`;
                        const typeLabel = r.stream
                            ? '<span class="error-type" style="background:#1e3a5f">stream</span>'
                            : '<span class="error-type" style="background:#1a3a1a">sync</span>';
                        const provLabel = r.provider && r.provider !== 'unknown'
                            ? `<span class="error-type" style="background:${provColor(r.provider)}">${r.provider}</span>`
                            : '—';
                        const ttft = r.bedrock_first_byte_ms > 0 ? fmtMs(r.bedrock_first_byte_ms) : fmtMs(r.first_byte_ms);
                        return `<tr style="cursor:pointer" onclick="showRequestBody('${r.request_id}','${r.model}','${time}')">
                            <td>${time}</td>
                            <td style="font-family:monospace;font-size:11px">${r.request_id}</td>
                            <td>${provLabel}</td>
                            <td>${abbrevModel(r.model)}</td>
                            <td style="font-family:monospace">${fmtMs(r.duration_ms)}</td>
                            <td style="font-family:monospace">${ttft}</td>
                            <td style="font-family:monospace">${tokStr}</td>
                            <td>${r.compressed ? pct : '—'}</td>
                            <td style="font-family:monospace">${r.message_count || '—'}</td>
                            <td>${fmtTypes(r.msg_types, r.has_context_management)}</td>
                            <td>${typeLabel}</td>
                        </tr>`;
                    }).join('');
                } else {
                    requestsBody.innerHTML = '<tr><td colspan="11" class="no-errors">No requests yet</td></tr>';
                }

                // Update provider latency cards
                if (data.provider_latency) {
                    const fmtMs = ms => ms > 0 ? (ms >= 1000 ? (ms/1000).toFixed(1)+'s' : ms+'ms') : '—';
                    for (const p of ['anthropic', 'bedrock']) {
                        const pl = data.provider_latency[p] || {};
                        document.getElementById(`lat-${p}-dur`).textContent = fmtMs(pl.avg_duration_ms || 0);
                        document.getElementById(`lat-${p}-ttft`).textContent = fmtMs(pl.avg_first_byte_ms || 0);
                        document.getElementById(`lat-${p}-req`).textContent = (pl.requests || 0).toLocaleString() + ' requests';
                    }
                }

                // Update errors table
                const errorsBody = document.getElementById('errors-body');
                if (data.recent_errors && data.recent_errors.length > 0) {
                    errorsBody.innerHTML = data.recent_errors.map(err => {
                        const time = new Date(err.timestamp).toLocaleTimeString();
                        return `
                            <tr>
                                <td>${time}</td>
                                <td><span class="error-type">${err.error_type}</span></td>
                                <td>${err.provider}</td>
                                <td>${err.model}</td>
                            </tr>
                        `;
                    }).join('');
                } else {
                    errorsBody.innerHTML = '<tr><td colspan="4" class="no-errors">No errors yet</td></tr>';
                }

                // Update count_tokens stats
                if (data.count_tokens) {
                    const ct = data.count_tokens;
                    document.getElementById('ct-total').textContent = ct.total.toLocaleString();
                    document.getElementById('ct-failures').textContent = ct.failures.toLocaleString();
                    document.getElementById('ct-failure-rate').textContent = (ct.failure_rate * 100).toFixed(1) + '% failure rate';
                    if (ct.failures > 0) {
                        document.getElementById('ct-failures').style.color = '#ef4444';
                    }
                    document.getElementById('ct-last-count').textContent = ct.last_count > 0 ? ct.last_count.toLocaleString() : '—';
                    document.getElementById('ct-last-model').textContent = ct.last_model || '—';
                }

                // Update refresh time
                const now = new Date();
                document.getElementById('refresh-time').textContent = `↺ ${now.toLocaleTimeString()}`;

            } catch (error) {
                console.error('Failed to load metrics:', error);
            }
        }

        function closeModal() {
            document.getElementById('body-modal').style.display = 'none';
        }
        document.addEventListener('keydown', e => { if (e.key === 'Escape') closeModal(); });

        let _modalRequestId = null;
        let _modalStage = 'original';

        async function fetchAndRenderBody() {
            document.getElementById('modal-body').textContent = 'Loading…';
            try {
                const resp = await fetch(`/requests/${_modalRequestId}?stage=${_modalStage}`);
                if (!resp.ok) {
                    document.getElementById('modal-body').textContent = _modalStage === 'compressed'
                        ? '(no compressed snapshot — compression may have been skipped)'
                        : 'Not found or evicted from ring buffer';
                    return;
                }
                const data = await resp.json();
                document.getElementById('modal-body').textContent = JSON.stringify(data, null, 2);
            } catch (e) {
                document.getElementById('modal-body').textContent = 'Error: ' + e.message;
            }
        }

        async function showRequestBody(requestId, model, time) {
            _modalRequestId = requestId;
            _modalStage = 'original';
            document.getElementById('modal-stage-orig').style.fontWeight = 'bold';
            document.getElementById('modal-stage-comp').style.fontWeight = 'normal';
            document.getElementById('modal-title').textContent = `[${requestId}] ${model} — ${time}`;
            document.getElementById('body-modal').style.display = 'block';
            await fetchAndRenderBody();
        }

        async function switchStage(stage) {
            _modalStage = stage;
            document.getElementById('modal-stage-orig').style.fontWeight = stage === 'original' ? 'bold' : 'normal';
            document.getElementById('modal-stage-comp').style.fontWeight = stage === 'compressed' ? 'bold' : 'normal';
            await fetchAndRenderBody();
        }

        async function loadErrorTypes() {
            try {
                const data = await fetch('/errors/summary').then(r => r.json());
                const tbody = document.getElementById('error-types-body');
                if (data.errors && data.errors.length > 0) {
                    tbody.innerHTML = data.errors.map(e => {
                        const first = new Date(e.first_seen).toLocaleString();
                        const last = new Date(e.last_seen).toLocaleString();
                        const fp = e.fingerprint.substring(0, 8);
                        const msg = e.message.length > 80 ? e.message.substring(0, 80) + '…' : e.message;
                        return `
                            <tr>
                                <td style="font-family:monospace;font-size:11px;">${fp}</td>
                                <td>${e.provider}</td>
                                <td><span class="error-type">${e.error_type}</span></td>
                                <td>${e.count}</td>
                                <td style="font-size:11px;">${first}</td>
                                <td style="font-size:11px;">${last}</td>
                                <td style="font-size:11px;max-width:300px;word-break:break-word;" title="${e.message}">${msg}</td>
                            </tr>
                        `;
                    }).join('');
                } else {
                    tbody.innerHTML = '<tr><td colspan="7" class="no-errors">No errors recorded yet</td></tr>';
                }
            } catch (error) {
                console.error('Failed to load error types:', error);
            }
        }

        // Initialize and start auto-refresh
        initCharts();
        loadMetrics();
        loadErrorTypes();
        setInterval(loadMetrics, 30000); // Refresh every 30 seconds
        setInterval(loadErrorTypes, 60000); // Refresh error types every 60 seconds
    </script>
</body>
</html>
"""


@app.middleware("http")
async def monitor_request_duration(request: Request, call_next):
    """Monitor request duration to detect blocking operations."""
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time

    # Log slow requests
    if duration > BLOCKING_REQUEST_THRESHOLD:
        logger.error(f"⚠️  BLOCKING REQUEST: {request.url.path} took {duration:.1f}s (threshold: {BLOCKING_REQUEST_THRESHOLD}s)")
    elif duration > SLOW_REQUEST_THRESHOLD:
        logger.warning(f"🐌 Slow request: {request.url.path} took {duration:.1f}s")

    # Add duration header for monitoring
    response.headers["X-Request-Duration"] = f"{duration:.2f}"
    return response


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": "1.0.0"}


@app.get("/v1/models")
async def list_models():
    """
    OpenAI-compatible models endpoint for LiteLLM.
    Returns list of available Claude models.
    """
    models = [
        {"id": "claude-opus-4-6", "object": "model", "created": 1234567890, "owned_by": "anthropic"},
        {"id": "claude-sonnet-4-6", "object": "model", "created": 1234567890, "owned_by": "anthropic"},
        {"id": "claude-opus-4-5-20251101", "object": "model", "created": 1234567890, "owned_by": "anthropic"},
        {"id": "claude-sonnet-4-5-20250929", "object": "model", "created": 1234567890, "owned_by": "anthropic"},
        {"id": "claude-opus-4-20250514", "object": "model", "created": 1234567890, "owned_by": "anthropic"},
        {"id": "claude-sonnet-4-20250514", "object": "model", "created": 1234567890, "owned_by": "anthropic"},
        {"id": "claude-3-7-sonnet-20250219", "object": "model", "created": 1234567890, "owned_by": "anthropic"},
        {"id": "claude-3-5-sonnet-20241022", "object": "model", "created": 1234567890, "owned_by": "anthropic"},
        {"id": "claude-3-5-haiku-20241022", "object": "model", "created": 1234567890, "owned_by": "anthropic"},
        {"id": "claude-haiku-4-5-20251001", "object": "model", "created": 1234567890, "owned_by": "anthropic"},
        {"id": "claude-3-opus-20240229", "object": "model", "created": 1234567890, "owned_by": "anthropic"},
        {"id": "claude-3-haiku-20240307", "object": "model", "created": 1234567890, "owned_by": "anthropic"},
    ]
    return {"object": "list", "data": models}


@app.post("/v1/messages")
async def messages_endpoint(request: Request):
    """
    Main messages endpoint compatible with Claude Code.
    Handles both streaming and non-streaming requests.
    """
    import uuid
    request_id = str(uuid.uuid4())[:8]

    logger.info(f"[{request_id}] → /v1/messages")

    try:
        # Get authentication
        token, auth_type = get_auth_from_request(request)

        # Parse request body
        body = await request.json()

        # Collect message type analytics before compression mutates the body
        original_messages = body.get("messages", [])
        _msg_types_json, _msg_types_dict = _msg_type_summary(original_messages)
        _has_cm = "context_management" in body
        _message_count = len(original_messages)

        # Store body in ring buffer for dashboard inspection (before compression)
        metrics.store_request_body(request_id, body)

        _beta = request.headers.get("anthropic-beta", "")
        logger.info(
            f"[{request_id}] model={body.get('model')} max_tokens={body.get('max_tokens')} "
            f"stream={body.get('stream', False)} msgs={_message_count} "
            f"types={_msg_types_json or '{}'} cm={_has_cm} beta={_beta or 'none'}"
        )

        # Compression tracking vars (populated below if compression runs)
        comp_stats: dict = {}

        # Compress messages before forwarding (ADR-001)
        if config.COMPRESS_ENABLED:
            try:
                flags = get_flags()
                compressed_msgs, updated_tools, comp_stats = await compress_messages(
                    body.get("messages", []),
                    body.get("tools") or [],
                    flags,
                )
                body = {**body, "messages": compressed_msgs, "tools": updated_tools}
                if comp_stats and "original_tokens" in comp_stats:
                    metrics.record_compression(
                        comp_stats["original_tokens"],
                        comp_stats["compressed_tokens"],
                    )
                metrics.store_request_body(request_id, body, stage="compressed")
            except Exception as comp_err:
                logger.error(f"[{request_id}] Compression failed — forwarding uncompressed: {comp_err}")

        _tokens_before = comp_stats.get("original_tokens", 0)
        _tokens_after = comp_stats.get("compressed_tokens", 0)
        _compressed = bool(_tokens_before)

        # Get headers to forward
        headers = {}
        if "anthropic-version" in request.headers:
            headers["anthropic-version"] = request.headers["anthropic-version"]
        if "anthropic-beta" in request.headers:
            headers["anthropic-beta"] = request.headers["anthropic-beta"]

        # Check if streaming is requested
        if body.get("stream", False):
            # Stream response - handle errors gracefully
            chunk_count = 0
            async def generate():
                nonlocal chunk_count
                try:
                    async for chunk in fallback.stream_message(body, token, auth_type, headers, request_id):
                        chunk_count += 1
                        # Log first 3 chunks to debug
                        if chunk_count <= 3:
                            logger.debug(f"[{request_id}] Yielding chunk {chunk_count}: {chunk[:150]}...")
                        yield chunk
                except RateLimitError as e:
                    # Return rate limit error event with retry info
                    logger.error(f"🚫 [{request_id}] RATE LIMIT in streaming - returning overloaded_error event: {e}")
                    error_event = {
                        "type": "error",
                        "error": {
                            "type": "overloaded_error",  # Use overloaded_error for better retry handling
                            "message": "Both Anthropic and AWS Bedrock have rate limited your requests after 20+ retry attempts. Please wait 30-60 seconds before trying again. This usually happens during high-traffic periods."
                        }
                    }
                    yield f"data: {json.dumps(error_event)}\n\n"
                except Exception as e:
                    # Return generic error event for other errors
                    error_event = {
                        "type": "error",
                        "error": {"type": "api_error", "message": str(e)}
                    }
                    yield f"data: {json.dumps(error_event)}\n\n"

            metrics.record_request_detail(request_id, body.get("model", "unknown"),
                _tokens_before, _tokens_after, _compressed, stream=True,
                msg_types=_msg_types_json, has_context_management=_has_cm,
                message_count=_message_count)
            logger.info(f"[{request_id}] ✓ Starting streaming response")
            return StreamingResponse(
                generate(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",
                    "X-Request-ID": request_id
                }
            )
        else:
            # Non-streaming response
            result = await fallback.send_message(body, token, auth_type, headers, request_id)
            metrics.record_request_detail(request_id, body.get("model", "unknown"),
                _tokens_before, _tokens_after, _compressed, stream=False,
                msg_types=_msg_types_json, has_context_management=_has_cm,
                message_count=_message_count)
            logger.info(f"[{request_id}] ✓ Non-streaming response complete")
            return JSONResponse(content=result, headers={"X-Request-ID": request_id})

    except HTTPException:
        raise
    except ValidationError as e:
        # Log concise request info for debugging validation errors
        logger.error(f"[{request_id}] Validation error: {e}")
        logger.error(f"[{request_id}] Request: model={body.get('model')}, max_tokens={body.get('max_tokens')}, tools={len(body.get('tools', []))}, messages={len(body.get('messages', []))}")
        raise HTTPException(status_code=e.status_code, detail=str(e))
    except AuthenticationError as e:
        logger.error(f"[{request_id}] Authentication error: {e}")
        raise HTTPException(status_code=401, detail=str(e))
    except RateLimitError as e:
        logger.error(f"🚫 [{request_id}] RATE LIMIT in non-streaming - returning 429 status: {e}")
        # Return 429 with Retry-After header for proper client handling
        return JSONResponse(
            status_code=429,
            content={
                "error": {
                    "type": "rate_limit_error",
                    "message": "Both Anthropic and AWS Bedrock have rate limited your requests after 20+ retry attempts. Please wait 30-60 seconds before trying again. This usually happens during high-traffic periods."
                }
            },
            headers={"Retry-After": "60"}  # Suggest 60 second retry
        )
    except Exception as e:
        logger.error(f"Error in messages endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/messages/dry-run")
async def messages_dry_run(request: Request):
    """
    Compression preview endpoint — no upstream API call, no metrics recorded.
    Returns before/after token counts and the compressed body for inspection.
    """
    import uuid
    request_id = str(uuid.uuid4())[:8]

    try:
        get_auth_from_request(request)  # validate auth header is present
        body = await request.json()
        messages = body.get("messages", [])
        tools = body.get("tools") or []
        model = body.get("model", "unknown")

        flags = get_flags()
        compressed_msgs, updated_tools, stats = await compress_messages(messages, tools, flags)

        tokens_before = stats.get("original_tokens", 0)
        tokens_after = stats.get("compressed_tokens", 0)
        rewind_injected = (
            any(t.get("name") == "rewind_retrieve" for t in updated_tools)
            and not any(t.get("name") == "rewind_retrieve" for t in tools)
        )

        compressed_body = {**body, "messages": compressed_msgs, "tools": updated_tools}

        return JSONResponse({
            "request_id": request_id,
            "model": model,
            "compression": {
                "enabled": flags.get("enabled", False),
                "skipped": stats.get("skipped", False),
                "tokens_before": tokens_before,
                "tokens_after": tokens_after,
                "tokens_saved": tokens_before - tokens_after,
                "reduction_pct": round(stats.get("reduction_pct", 0.0), 2),
                "timing_ms": round(stats.get("total_timing_ms", 0.0), 2),
            },
            "rewind_tool_injected": rewind_injected,
            "original_body": body,
            "compressed_body": compressed_body,
        })
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[{request_id}] dry-run error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/requests")
async def recent_requests_endpoint():
    """Return the last 100 request details (newest first) for benchmarking inspection."""
    return JSONResponse(metrics.get_recent_requests())


@app.post("/v1/messages/count_tokens")
async def count_tokens_endpoint(request: Request):
    """
    Token counting endpoint - passthrough to Anthropic API.
    Used by Claude Code to count tokens before making actual requests.
    """
    import uuid
    request_id = str(uuid.uuid4())[:8]

    try:
        # Get authentication
        token, auth_type = get_auth_from_request(request)

        # Parse request body
        body = await request.json()
        model = body.get("model", "unknown")

        logger.info(f"[{request_id}] → /v1/messages/count_tokens (model={model})")

        # Get headers to forward
        headers = {}
        if "anthropic-version" in request.headers:
            headers["anthropic-version"] = request.headers["anthropic-version"]
        if "anthropic-beta" in request.headers:
            headers["anthropic-beta"] = request.headers["anthropic-beta"]

        # Forward to Anthropic API (only anthropic provider supports token counting)
        from providers.anthropic import AnthropicProvider
        provider = AnthropicProvider()

        # Normalize model name
        if "model" in body:
            body["model"] = provider.normalize_model_name(body["model"])

        # Build headers for Anthropic
        api_headers = {}
        if auth_type == "bearer":
            api_headers["Authorization"] = f"Bearer {token}"
        else:
            api_headers["x-api-key"] = token

        if "anthropic-version" in headers:
            api_headers["anthropic-version"] = headers["anthropic-version"]
        if "anthropic-beta" in headers:
            api_headers["anthropic-beta"] = headers["anthropic-beta"]

        # Make request to count_tokens endpoint
        response = await provider.client.post(
            f"{provider.base_url}/v1/messages/count_tokens",
            json=body,
            headers=api_headers
        )

        if response.status_code != 200:
            # Known Claude Code bug: count_tokens is called without proper auth headers
            # This is harmless - regular message requests work fine
            if response.status_code == 401:
                logger.info(f"[{request_id}] count_tokens auth error (known Claude Code bug): {response.status_code}")
            else:
                logger.error(f"[{request_id}] ✗ count_tokens failed: {response.status_code} - {response.text}")
            metrics.record_count_tokens(success=False, model=model)
            raise HTTPException(status_code=response.status_code, detail=response.text)

        result = response.json()
        token_count = result.get('input_tokens', 0)
        logger.info(f"[{request_id}] ✓ count_tokens: {token_count} tokens (model={model})")
        metrics.record_count_tokens(success=True, model=model, token_count=token_count)
        return JSONResponse(content=result, headers={"X-Request-ID": request_id})

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[{request_id}] Error in count_tokens endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat/completions")
@app.post("/v1/chat/completions")
async def openai_compatibility_endpoint(request: Request):
    """
    OpenAI-compatible endpoint for testing and LiteLLM compatibility.
    Converts OpenAI format to Anthropic format.
    """
    import uuid
    request_id = str(uuid.uuid4())[:8]

    logger.info(f"[{request_id}] → /v1/chat/completions (OpenAI)")

    try:
        # Get authentication
        token, auth_type = get_auth_from_request(request)

        # Parse request body
        openai_body = await request.json()

        logger.info(f"[{request_id}] OpenAI Request: model={openai_body.get('model')}, max_tokens={openai_body.get('max_tokens')}, stream={openai_body.get('stream', False)}")

        # Convert OpenAI format to Anthropic format
        anthropic_body = {
            "model": openai_body.get("model", "claude-3-haiku-20240307"),
            "messages": openai_body.get("messages", []),
            "max_tokens": openai_body.get("max_tokens", 1024),
            "temperature": openai_body.get("temperature", 1.0),
            "stream": openai_body.get("stream", False)
        }

        # Get headers
        headers = {}
        if "anthropic-version" in request.headers:
            headers["anthropic-version"] = request.headers["anthropic-version"]
        if "anthropic-beta" in request.headers:
            headers["anthropic-beta"] = request.headers["anthropic-beta"]

        # Handle streaming
        if anthropic_body.get("stream", False):
            async def generate():
                try:
                    async for chunk in fallback.stream_message(anthropic_body, token, auth_type, headers, request_id):
                        yield chunk
                except RateLimitError as e:
                    # Return rate limit error event with retry info
                    logger.error(f"🚫 [{request_id}] RATE LIMIT in OpenAI streaming - returning overloaded_error event: {e}")
                    error_event = {
                        "type": "error",
                        "error": {
                            "type": "overloaded_error",  # Use overloaded_error for better retry handling
                            "message": "Both Anthropic and AWS Bedrock have rate limited your requests after 20+ retry attempts. Please wait 30-60 seconds before trying again. This usually happens during high-traffic periods."
                        }
                    }
                    yield f"data: {json.dumps(error_event)}\n\n"
                except Exception as e:
                    # Return generic error event for other errors
                    error_event = {
                        "type": "error",
                        "error": {"type": "api_error", "message": str(e)}
                    }
                    yield f"data: {json.dumps(error_event)}\n\n"

            logger.info(f"[{request_id}] ✓ Starting OpenAI streaming response")
            return StreamingResponse(
                generate(),
                media_type="text/event-stream",
                headers={"X-Request-ID": request_id}
            )
        else:
            # Non-streaming response
            result = await fallback.send_message(anthropic_body, token, auth_type, headers, request_id)

            # Convert to OpenAI format
            openai_response = {
                "id": result.get("id", "msg-proxy"),
                "object": "chat.completion",
                "created": 1234567890,
                "model": result.get("model"),
                "choices": [{
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": result.get("content", [{"text": ""}])[0].get("text", "")
                    },
                    "finish_reason": "stop"
                }],
                "usage": result.get("usage", {})
            }
            logger.info(f"[{request_id}] ✓ OpenAI non-streaming response complete")
            return JSONResponse(content=openai_response, headers={"X-Request-ID": request_id})

    except HTTPException:
        raise
    except ValidationError as e:
        # Log request body for debugging validation errors
        sanitized_body = {k: v for k, v in anthropic_body.items() if k not in ['messages']}  # Exclude messages to avoid logging sensitive data
        sanitized_body['message_count'] = len(anthropic_body.get('messages', []))
        logger.error(f"[{request_id}] Validation error: {e}")
        logger.error(f"[{request_id}] Request params: {json.dumps(sanitized_body)}")
        raise HTTPException(status_code=e.status_code, detail=str(e))
    except AuthenticationError as e:
        logger.error(f"[{request_id}] Authentication error: {e}")
        raise HTTPException(status_code=401, detail=str(e))
    except RateLimitError as e:
        logger.error(f"🚫 [{request_id}] RATE LIMIT in OpenAI non-streaming - returning 429 status: {e}")
        # Return 429 with Retry-After header for proper client handling
        return JSONResponse(
            status_code=429,
            content={
                "error": {
                    "type": "rate_limit_error",
                    "message": "Both Anthropic and AWS Bedrock have rate limited your requests after 20+ retry attempts. Please wait 30-60 seconds before trying again. This usually happens during high-traffic periods."
                }
            },
            headers={"Retry-After": "60"}  # Suggest 60 second retry
        )
    except Exception as e:
        logger.error(f"Error in OpenAI compatibility endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/event_logging/batch")
async def litellm_event_logging(request: Request):
    """
    LiteLLM telemetry endpoint stub.
    LiteLLM sends usage events here - we accept them silently.
    """
    # Accept the events but don't process them
    return {"status": "success"}


@app.post("//v1/messages")
async def double_slash_error(request: Request):
    """Error handler for double slash in URL."""
    raise HTTPException(
        status_code=400,
        detail="Invalid URL: double slash detected. Your base URL should be 'http://localhost:47000' (without trailing /v1). Current request path: '//v1/messages'"
    )


@app.post("/v1/v1/messages")
async def double_v1_error(request: Request):
    """Error handler for double /v1 prefix."""
    raise HTTPException(
        status_code=400,
        detail="Invalid URL: double /v1 prefix detected. Your base URL should be 'http://localhost:47000' (without /v1) OR 'http://localhost:47000/v1' (with /v1), but not both. Current request path: '/v1/v1/messages'"
    )


@app.get("/dashboard", response_class=HTMLResponse)
async def get_dashboard():
    """Browser-accessible monitoring dashboard."""
    return DASHBOARD_HTML


@app.get("/errors/summary")
async def errors_summary():
    """Return deduplicated error types from persistent storage (last 100, newest first)."""
    try:
        errors = error_tracker.search_errors(limit=100)
        return JSONResponse({"errors": errors, "total": len(errors)})
    except Exception as e:
        logger.error(f"Failed to query error tracker: {e}")
        return JSONResponse({"errors": [], "total": 0, "error": str(e)})


@app.get("/requests/{request_id}")
async def get_request_body(request_id: str, stage: str = "original"):
    """Return stored request body snapshot (stage: 'original' or 'compressed')."""
    body = metrics.get_request_body(request_id, stage)
    if body is None:
        return JSONResponse({"error": "not found or evicted"}, status_code=404)
    return JSONResponse(body)


@app.get("/metrics")
async def get_metrics():
    """JSON metrics endpoint for dashboard and API consumers."""
    stats = metrics.get_stats()

    # Add count_tokens stats
    stats["count_tokens"] = metrics.get_count_tokens_stats()

    # Add live cooldown status from FallbackHandler
    stats["cooldowns"] = {
        p.name: {
            "cooling_down": fallback._is_in_cooldown(p.name),
            "remaining_seconds": max(0, int((fallback.cooldowns.get(p.name) or 0) - time.time()))
        }
        for p in fallback.providers
    }

    return JSONResponse(stats)


@app.get("/")
async def root():
    """Root endpoint with basic info."""
    return {
        "name": "Claude Proxy",
        "version": "1.0.0",
        "endpoints": [
            "/v1/messages - Claude Code compatible endpoint",
            "/v1/models - List available models (LiteLLM)",
            "/chat/completions - OpenAI compatible endpoint",
            "/v1/chat/completions - OpenAI compatible endpoint (LiteLLM)",
            "/dashboard - Monitoring dashboard (HTML)",
            "/metrics - Metrics endpoint (JSON)",
            "/health - Health check"
        ]
    }


if __name__ == "__main__":
    import uvicorn

    # Note: workers > 1 requires passing app as import string
    # Each worker gets its own process and event loop
    uvicorn.run(
        "main:app",  # Import string required for multi-worker mode
        host="127.0.0.1",
        port=config.PROXY_PORT,
        workers=config.WORKERS,
        log_level="info",
        # Enable asyncio debug mode in each worker
        loop="asyncio",
        access_log=True
    )