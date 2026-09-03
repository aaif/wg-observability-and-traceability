# AAIF Reference Architecture: InsightClaw

| Field | Value |
|-------|-------|
| **Subject** | [InsightClaw](https://github.com/outshift-open/insightclaw) |
| **Version** | 0.1.3 |
| **Date** | 2026-08-17 |

---

## Objective

Reference architecture for InsightClaw, a Cisco-authored OpenClaw observability plugin that adds OpenTelemetry-based distributed tracing, metrics, and cost accounting to multi-agent workflows — assessed as an instrumentation layer for AI agent infrastructure.

---

## Scope / Zoom Level

**Orchestration layer — agent runtime instrumentation inside a single OpenClaw gateway process.** InsightClaw operates between the application (multi-agent conversation runtime) and the telemetry export pipeline. It does not define storage, analysis, or alerting — it produces connected OTel traces and metrics that flow to any OTLP-compatible backend. Cross-process correlation is supported via W3C trace context propagation and agent handoff span links.

---

## Prerequisites

| Component | Version | Notes |
|-----------|---------|-------|
| OpenClaw Runtime | ≥2026.3.24 | Plugin API compatibility baseline |
| Node.js | 22+ | Required for ESM loader hooks (`--import`) |
| @opentelemetry/sdk-node | 0.203.0 | OTel SDK v2 (NodeTracerProvider, BatchSpanProcessor) |
| @opentelemetry/sdk-metrics | 2.0.1 | MeterProvider + PeriodicExportingMetricReader |
| @opentelemetry/semantic-conventions | 1.30.0 | gen_ai.* attributes |
| @traceloop/* instrumentations | 0.23.0 | OpenLLMetry: Anthropic, OpenAI, Bedrock, Vertex AI |
| import-in-the-middle | 1.15.0 | ESM module patching for provider SDK instrumentation |
| OTel Collector | 0.121.0 (contrib) | OTLP receiver → ClickHouse exporter |
| ClickHouse | 25.3 | Trace/metric/log storage |
| Grafana (optional) | latest | Pre-configured dashboard via ClickHouse datasource |

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                          OpenClaw Gateway Process                                 │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │                        InsightClaw Plugin                                │    │
│  │                                                                         │    │
│  │  ┌─────────────────────┐  ┌──────────────────────┐  ┌──────────────┐  │    │
│  │  │ Layer 1: Hook-Based │  │ Layer 2: Diagnostics │  │ Layer 3:     │  │    │
│  │  │ Workflow Tracing     │  │ Enrichment           │  │ GenAI SDK    │  │    │
│  │  │                     │  │                      │  │ Preload      │  │    │
│  │  │ • message_received  │  │ • model.usage        │  │ (optional)   │  │    │
│  │  │ • before_model_     │  │ • webhook.*          │  │              │  │    │
│  │  │   resolve           │  │ • queue.*            │  │ • Anthropic  │  │    │
│  │  │ • before_tool_call  │  │ • session.*          │  │ • OpenAI     │  │    │
│  │  │ • tool_result_      │  │ • tool.loop          │  │ • Bedrock    │  │    │
│  │  │   persist           │  │ • run.attempt        │  │ • Vertex AI  │  │    │
│  │  │ • agent_end         │  │                      │  │              │  │    │
│  │  │ • message_sent      │  │ Accurate token       │  │ via IITM +  │  │    │
│  │  │                     │  │ counts, cost, model  │  │ NODE_OPTIONS │  │    │
│  │  └────────┬────────────┘  └──────────┬───────────┘  └──────┬───────┘  │    │
│  │           │                          │                      │          │    │
│  │  ┌────────┴──────────────────────────┴──────────────────────┴───────┐  │    │
│  │  │                   Shared Telemetry Core                           │  │    │
│  │  │                                                                   │  │    │
│  │  │  NodeTracerProvider ──► BatchSpanProcessor                        │  │    │
│  │  │  MeterProvider ──► PeriodicExportingMetricReader                  │  │    │
│  │  │                                                                   │  │    │
│  │  │  Session Lifecycle Watcher (5min idle timeout)                    │  │    │
│  │  │  Agent Handoff Tracker (span links, sequence numbers)             │  │    │
│  │  │  Fork/Join Detector (2s window, branch annotations)              │  │    │
│  │  │  Span Cache (optional rolling window for derived metrics)        │  │    │
│  │  │  Cross-Plugin Wrapper (action hook wrapping of DefenseClaw etc.) │  │    │
│  │  └──────────────────────────────┬────────────────────────────────────┘  │    │
│  └─────────────────────────────────┼───────────────────────────────────────┘    │
│                                    │                                             │
│  ┌─────────────────────────────────┼───────────────────────────────────────┐    │
│  │ Other Plugins (e.g., DefenseClaw)                                        │    │
│  │   action hooks wrapped transparently ──────────────────────────────►     │    │
│  │   trace records: hook name, plugin ID, priority, input, result           │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
└────────────────────────────────────┼────────────────────────────────────────────┘
                                     │ OTLP/HTTP (:4318) or OTLP/gRPC (:4317)
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                      OTel Collector (otel/contrib:0.121.0)                        │
│                                                                                 │
│  Receivers: otlp (gRPC + HTTP), filelog (openclaw-*.log)                        │
│  Processors: batch (1s / 512 spans)                                             │
│  Exporters: clickhouse (tcp://clickhouse:9000, lz4, TTL 72h)                   │
│  Extensions: health_check (:13133)                                              │
└────────────────────────────────────┬────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                      ClickHouse (25.3)                                            │
│                                                                                 │
│  otel_traces  │  otel_logs  │  metrics tables (auto-created)                    │
│  DB: otel, User: otel, TTL: 72h                                                │
└────────────────────────────────────┬────────────────────────────────────────────┘
                                     │
                                     ▼ (optional)
┌─────────────────────────────────────────────────────────────────────────────────┐
│  Grafana (pre-provisioned)                                                       │
│  • ClickHouse datasource (native protocol, port 9000)                           │
│  • "OpenClaw Metrics Dashboard" auto-loaded                                     │
│  • http://localhost:3000 (admin/admin)                                           │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Instrumentation Walkthrough

### What Is Captured

InsightClaw captures three categories of telemetry through distinct mechanisms:

| Category | Signals | Mechanism |
|----------|---------|-----------|
| **Workflow tracing** | Request lifecycle, agent turns, tool calls, outbound messages | OpenClaw typed hooks (`api.on(...)`) |
| **Gateway diagnostics** | Token usage, cost, webhooks, queues, sessions, tool loops | OpenClaw diagnostic event bus (`onDiagnosticEvent`) |
| **Provider SDK calls** | Raw LLM API invocations (Anthropic, OpenAI, Bedrock, Vertex) | Node.js ESM preload + import-in-the-middle |

### Trace Hierarchy

The plugin produces a connected span tree for each inbound request:

```
openclaw.request                         ← root span (full message → response)
├── openclaw.agent.turn                  ← one per agent invocation
│   ├── tool.Read                        ← individual tool spans
│   ├── tool.exec
│   ├── tool.sessions_spawn              ← spawns child agent
│   ├── llm.claude-sonnet-4-20250514    ← provider SDK span (optional)
│   └── openclaw.tool.loop               ← diagnostic span (if loop detected)
├── openclaw.agent.turn                  ← second agent (linked via handoff)
│   └── tool.web_search
├── openclaw.message.sent                ← outbound delivery confirmation
└── openclaw.model.usage                 ← linked diagnostic span (cost/tokens)
```

### Hook Registration and Span Lifecycle

| Hook | Span Created | Key Attributes |
|------|-------------|----------------|
| `message_received` | `openclaw.request` (root) | `openclaw.session.key`, `openclaw.message.channel`, `gen_ai.input.messages` |
| `before_model_resolve` | `openclaw.agent.turn` | `gen_ai.agent.id`, `ioa_observe.agent.sequence`, handoff links |
| `before_tool_call` | `tool.<toolName>` (start) | `tool.name`, `gen_ai.tool.call.arguments`, fork annotations |
| `tool_result_persist` | `tool.<toolName>` (end) | `gen_ai.tool.call.result`, error status, duration |
| `agent_end` | Closes `openclaw.agent.turn` + `openclaw.request` | Token counts, model, provider, cost, `openclaw.agent.turn_duration` |
| `message_sent` | `openclaw.message.sent` | `openclaw.message.output` |
| `command:new` / `command:reset` | `openclaw.command.*` + `session.end` | `command.source` |

### Diagnostics Event Consumption

| Event | Telemetry Produced |
|-------|-------------------|
| `model.usage` | Enriches active `openclaw.agent.turn` with accurate token counts, model, cost; emits `openclaw.model.usage` span + metrics |
| `webhook.received` / `.processed` / `.error` | Counter + histogram + error spans |
| `message.queued` / `.processed` | Queue depth histogram, processing duration histogram |
| `queue.lane.enqueue` / `.dequeue` | Lane counters, wait time histogram |
| `session.state` / `.stuck` | Session state counter, stuck age histogram, error spans |
| `tool.loop` | Loop counter, diagnostic span under active agent turn |
| `run.attempt` | Attempt counter |

### Multi-Agent Correlation

**Agent Handoffs** — When agent B follows agent A in the same runtime session:
- `openclaw.agent.turn` (B) receives a span link with `link.type=agent_handoff`
- Attributes: `ioa_observe.agent.sequence=2`, `ioa_observe.agent.previous=A`

**Spawned Subagents** — When `sessions_spawn` creates a child under a new runtime session key:
- Child `openclaw.request` receives a span link to the spawning tool with `link.type=agent_spawn`
- Second span link back to source agent with `link.type=agent_handoff`

**Fork/Join** — When multiple tools fire within a 2-second window under the same agent:
- Each tool span: `ioa_observe.fork.id`, `ioa_observe.fork.branch_index`
- Next agent span (join): `ioa_observe.join.fork_id`, `ioa_observe.join.branch_count`, plus span links to branches

### Cross-Process Context Propagation

Headers propagated for cross-agent HTTP/MCP communication:

| Header | Purpose |
|--------|---------|
| `traceparent` | W3C trace context |
| `baggage` | W3C baggage |
| `x-session-id` | Plugin session identifier |
| `x-last-agent-span-id` | Previous agent span for linking |
| `x-last-agent-trace-id` | Previous agent trace for cross-trace links |
| `x-last-agent-name` | Agent identity for handoff attribution |
| `x-agent-sequence` | Position in execution chain |
| `x-fork-id` / `x-fork-parent-seq` / `x-fork-branch-index` | Fork topology |

### Session Lifecycle

The plugin defines its own session boundaries independently of OpenClaw:

- **Start**: First traced activity for a runtime session key (any hook)
- **End conditions**: `command:new`/`command:reset`, 5-minute idle timeout, process shutdown
- **Session ID**: Plugin-generated UUID (independent of `openclaw.session.key`)
- **Watcher**: Background interval checks every 30 seconds for expired sessions
- **Parallel agents**: Each distinct runtime session key gets its own `session.id`

### Metrics Emitted

| Metric | Type | Key Attributes |
|--------|------|----------------|
| `openclaw.llm.requests` | Counter | `gen_ai.response.model`, `openclaw.provider`, `openclaw.channel` |
| `openclaw.llm.tokens.prompt` | Counter | `gen_ai.response.model`, `token.type` (cache_read/cache_write) |
| `openclaw.llm.tokens.completion` | Counter | `gen_ai.response.model`, `openclaw.provider` |
| `openclaw.llm.tokens.total` | Counter | `gen_ai.response.model`, `openclaw.provider` |
| `openclaw.llm.duration` | Histogram | `gen_ai.response.model`, `openclaw.provider` |
| `openclaw.cost.usd` | Counter | `gen_ai.response.model`, `openclaw.provider` |
| `openclaw.tool.calls` | Counter | `tool.name`, `gen_ai.agent.id` |
| `openclaw.tool.errors` | Counter | `tool.name`, `gen_ai.agent.id` |
| `openclaw.tool.duration` | Histogram | `tool.name`, `gen_ai.agent.id` |
| `openclaw.agent.turn_duration` | Histogram | `gen_ai.response.model`, `gen_ai.agent.id` |
| `openclaw.messages.received` | Counter | `openclaw.message.channel` |
| `openclaw.messages.sent` | Counter | `openclaw.message.channel` |
| `openclaw.session.resets` | Counter | `command.source` |
| `openclaw.memory.search_hit` / `.search_miss` | Counter | `tool.name`, `gen_ai.agent.id` |
| `openclaw.memory.write_events` / `.read_events` / `.edit_events` | Counter | `tool.name`, `gen_ai.agent.id` |
| `openclaw.memory.search_fragmentation` | Histogram | `tool.name`, `gen_ai.agent.id` |
| `openclaw.context.system_size` / `.prompt_size` / `.history_*_size` | Histogram | `gen_ai.agent.id` |
| `openclaw.context.preparation_duration` | Histogram | `gen_ai.agent.id` |
| `openclaw.webhook.duration_ms` | Histogram | `openclaw.channel`, `openclaw.webhook` |
| `openclaw.queue.depth` | Histogram | `openclaw.channel` / `openclaw.lane` |
| `openclaw.queue.wait_ms` | Histogram | `openclaw.lane` |
| `openclaw.session.parallelisation_score` | Histogram | `openclaw.session.key` |
| `openclaw.session.repetition_score` | Histogram | `openclaw.session.key` |

All core counters emit periodic zero-value heartbeat points (`openclaw.idle=true`) to keep timeseries alive during idle periods.

---

## Sample Trace Output

A realistic OTLP trace export for a single agent turn with tool execution:

```json
{
  "resourceSpans": [{
    "resource": {
      "attributes": [
        { "key": "service.name", "value": { "stringValue": "openclaw-gateway" } },
        { "key": "service.version", "value": { "stringValue": "0.1.0" } },
        { "key": "openclaw.plugin", "value": { "stringValue": "insightClaw" } }
      ]
    },
    "scopeSpans": [{
      "scope": { "name": "insightClaw", "version": "0.1.0" },
      "spans": [
        {
          "traceId": "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6",
          "spanId": "1a2b3c4d5e6f7a8b",
          "name": "openclaw.request",
          "kind": "SPAN_KIND_SERVER",
          "startTimeUnixNano": "1723900000000000000",
          "endTimeUnixNano": "1723900045200000000",
          "attributes": [
            { "key": "openclaw.session.key", "value": { "stringValue": "sess_abc123" } },
            { "key": "session.id", "value": { "stringValue": "f47ac10b-58cc-4372-a567-0e02b2c3d479" } },
            { "key": "openclaw.message.channel", "value": { "stringValue": "discord" } },
            { "key": "workspace-id", "value": { "stringValue": "UUID1" } },
            { "key": "mas-id", "value": { "stringValue": "UUID2" } },
            { "key": "gen_ai.input.messages", "value": { "stringValue": "[{\"role\":\"user\",\"content\":\"Check the DB health for the payments service\"}]" } }
          ],
          "status": { "code": "STATUS_CODE_OK" }
        },
        {
          "traceId": "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6",
          "spanId": "2b3c4d5e6f7a8b9c",
          "parentSpanId": "1a2b3c4d5e6f7a8b",
          "name": "openclaw.agent.turn",
          "kind": "SPAN_KIND_INTERNAL",
          "startTimeUnixNano": "1723900000100000000",
          "endTimeUnixNano": "1723900042000000000",
          "attributes": [
            { "key": "gen_ai.agent.id", "value": { "stringValue": "sre-lead" } },
            { "key": "gen_ai.response.model", "value": { "stringValue": "claude-sonnet-4-20250514" } },
            { "key": "gen_ai.usage.input_tokens", "value": { "intValue": "2847" } },
            { "key": "gen_ai.usage.output_tokens", "value": { "intValue": "512" } },
            { "key": "openclaw.provider", "value": { "stringValue": "anthropic" } },
            { "key": "openclaw.cost.usd", "value": { "doubleValue": 0.0142 } },
            { "key": "ioa_observe.agent.sequence", "value": { "intValue": "1" } }
          ],
          "status": { "code": "STATUS_CODE_OK" }
        },
        {
          "traceId": "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6",
          "spanId": "3c4d5e6f7a8b9c0d",
          "parentSpanId": "2b3c4d5e6f7a8b9c",
          "name": "tool.Read",
          "kind": "SPAN_KIND_INTERNAL",
          "startTimeUnixNano": "1723900005000000000",
          "endTimeUnixNano": "1723900005400000000",
          "attributes": [
            { "key": "tool.name", "value": { "stringValue": "Read" } },
            { "key": "gen_ai.agent.id", "value": { "stringValue": "sre-lead" } },
            { "key": "gen_ai.tool.call.arguments", "value": { "stringValue": "{\"path\":\"/var/log/payments/health.json\"}" } },
            { "key": "gen_ai.tool.call.result", "value": { "stringValue": "{\"status\":\"degraded\",\"latency_p99_ms\":1240}" } }
          ],
          "status": { "code": "STATUS_CODE_OK" }
        },
        {
          "traceId": "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6",
          "spanId": "4d5e6f7a8b9c0d1e",
          "parentSpanId": "2b3c4d5e6f7a8b9c",
          "name": "tool.sessions_spawn",
          "kind": "SPAN_KIND_INTERNAL",
          "startTimeUnixNano": "1723900010000000000",
          "endTimeUnixNano": "1723900038000000000",
          "attributes": [
            { "key": "tool.name", "value": { "stringValue": "sessions_spawn" } },
            { "key": "gen_ai.agent.id", "value": { "stringValue": "sre-lead" } },
            { "key": "ioa_observe.fork.id", "value": { "stringValue": "a3f7c92d1e4b6a08" } },
            { "key": "ioa_observe.fork.branch_index", "value": { "intValue": "0" } },
            { "key": "ioa_observe.fork.parent_name", "value": { "stringValue": "sre-lead" } },
            { "key": "ioa_observe.fork.parent_sequence", "value": { "intValue": "1" } }
          ],
          "status": { "code": "STATUS_CODE_OK" }
        },
        {
          "traceId": "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6",
          "spanId": "5e6f7a8b9c0d1e2f",
          "parentSpanId": "1a2b3c4d5e6f7a8b",
          "name": "openclaw.message.sent",
          "kind": "SPAN_KIND_PRODUCER",
          "startTimeUnixNano": "1723900044000000000",
          "endTimeUnixNano": "1723900044500000000",
          "attributes": [
            { "key": "openclaw.message.channel", "value": { "stringValue": "discord" } }
          ],
          "status": { "code": "STATUS_CODE_OK" }
        }
      ]
    }]
  }]
}
```

---

## Cost Profile

### LLM Token Cost

InsightClaw itself makes **zero LLM calls**. It is a pure instrumentation plugin — all token costs are from the underlying agent workflow. The plugin captures and surfaces those costs via the `openclaw.cost.usd` metric derived from OpenClaw's `model.usage` diagnostic events.

### Compute/IO Overhead

| Operation | Overhead | Notes |
|-----------|----------|-------|
| Hook invocation (per hook) | ~50–200µs | JavaScript object allocation, span creation, attribute setting |
| BatchSpanProcessor flush | Amortized across 512 spans, async background thread | Non-blocking to agent execution |
| Fork/join detection | O(n) per tool call within 2s window | In-memory map keyed by session |
| Handoff state tracking | O(1) map lookups per agent start/end | Per-session key Map entries |
| Session watcher tick | 30s interval, iterates active sessions | Negligible for typical session counts (<100) |
| Span cache (when enabled) | ~2KB per span record × rolling window | In-process memory; optional |
| Metric heartbeat | Per metrics-export-interval (default 30s) | 15 zero-value counter.add() calls |
| Preload auto-instrumentation | Module load-time patching via IITM | One-time cost at gateway startup |
| Embeddings processing (experimental) | CPU-bound via @xenova/transformers | Significant; disabled by default |

### Storage Growth Rate

With the default ClickHouse TTL of 72 hours and a moderately active multi-agent system:

| Signal | Estimated Volume | Per Request |
|--------|-----------------|-------------|
| Trace spans | ~5–15 spans per request | ~2–4 KB compressed per request |
| Metrics (counters + histograms) | ~40 active metric streams | ~500 bytes per export interval |
| Logs (filelog ingestion) | Varies by gateway verbosity | Separate from plugin |

Typical growth: **~50–200 MB/day** for a single-gateway, moderate-traffic deployment (100–500 requests/day with 3–5 tools per request).

---

## Validation Criteria

### Quick Smoke Test

1. Start the observability stack:
   ```bash
   cd observability-plugin/deploy && docker-compose up -d
   ```

2. Verify collector health:
   ```bash
   curl -s http://localhost:13133 | grep -q '"status":"Server available"'
   ```

3. Add InsightClaw to `~/.openclaw/openclaw.json` with `endpoint: "http://localhost:4318"`.

4. Restart OpenClaw and send one message to any agent.

5. Confirm spans reached ClickHouse:
   ```bash
   docker exec clickhouse-server clickhouse-client \
     --query "SELECT ServiceName, SpanName, Duration FROM otel.otel_traces ORDER BY Timestamp DESC LIMIT 10"
   ```

   Expected: rows containing `openclaw.request`, `openclaw.agent.turn`, `tool.*`, `openclaw.message.sent`.

6. Confirm metrics exist:
   ```bash
   docker exec clickhouse-server clickhouse-client \
     --query "SELECT DISTINCT MetricName FROM otel.otel_metrics WHERE MetricName LIKE 'openclaw.%'"
   ```

   Expected: `openclaw.llm.requests`, `openclaw.tool.calls`, `openclaw.messages.received`, etc.

### Status Verification

From the OpenClaw CLI:
```bash
openclaw plugin otel
```

Expected output includes `Initialized: ✅`, `Traces: ✅`, `Metrics: ✅`.

### RPC Status Check

Programmatic verification via the registered gateway method:
```
insightclaw.status → { initialized: true, config: { traces: true, metrics: true, ... } }
```

---

## Limitations / Out of Scope

| Limitation | Impact | Workaround |
|-----------|--------|-----------|
| No built-in trace analysis or alerting UI | Must rely on external tools (Grafana, Jaeger, Datadog) for visualization | Deploy with the provided Grafana stack or export to a SaaS backend |
| `openclaw.llm.errors` counter never incremented in current source | LLM error rate metric always zero (only heartbeat points) | Use provider SDK span error status or agent_end error signals |
| `openclaw.sessions.active` gauge declared but never updated | No real-time active session count metric | Derive from `session.start`/`session.end` span timestamps |
| Provider SDK instrumentation requires `NODE_OPTIONS` preload | Cannot be enabled purely via plugin config — requires gateway process startup modification | Systemd override or wrapper script; plugin still works without it |
| LiteLLM streaming providers report zero tokens by default | Token counters unreliable for LiteLLM without per-model `compat.supportsUsageInStreaming` | Enable the streaming usage flag per model in provider config |
| OpenLLMetry does not extract tokens from streaming responses | SDK auto-instrumentation undercounts tokens | Apply the vendored patch (`openllmetry-patch-index.js`) or set `TRACELOOP_ENRICH_TOKENS=true` for tiktoken estimation |
| Embeddings-based similarity (`embeddingsProcessing`) requires `@xenova/transformers` | CPU-intensive; not suitable for high-throughput production | Disabled by default; Jaccard similarity used as lightweight fallback |
| Single-process only | Does not correlate spans across multiple gateway instances without explicit header propagation | Use W3C traceparent headers for multi-gateway deployments |
| No log signal export from plugin itself | Plugin emits to OpenClaw's own log stream; OTel log export depends on filelog receiver in collector | Collector filelog receiver captures `openclaw-*.log` files |
| No sampling support | All traces exported (100% sampling) | Configure tail_sampling in OTel Collector if volume reduction needed |
| 72-hour ClickHouse TTL in default deployment | Short retention for production use | Override TTL in collector config or use a retention-capable backend |
| No authentication on OTLP endpoints in default stack | Data exposure in shared networks | Set `headers` config for bearer-token auth to production backends |

---

## Evaluation Assessment

### Observability

**Rating: Strong**

InsightClaw's entire purpose is to produce observability for AI agent workflows. It succeeds comprehensively:

**Strengths:**
- Three-layer instrumentation (hooks + diagnostics + optional SDK auto-instrumentation) captures the full agent execution lifecycle
- Connected trace hierarchy from inbound message through agent turns, tool calls, and outbound delivery
- 40+ distinct metrics covering tokens, cost, duration, queue depth, webhook health, memory operations, and context assembly
- Multi-agent correlation via span links (handoff, fork/join, spawn) provides workflow-level visibility
- Cross-plugin tracing wraps other plugins' action hooks without requiring their cooperation
- Self-observation via RPC status endpoint, CLI command, and registered agent tool
- Heartbeat mechanism keeps metric timeseries alive during idle periods

**Gaps:**
- Does not consume its own telemetry for self-health alerting (no circuit breaker if export fails)
- No log signal emission from the plugin itself (depends on gateway log files + filelog receiver)
- `openclaw.llm.errors` and `openclaw.sessions.active` declared but non-functional
- No built-in sampling — relies on external collector configuration for volume management

---

### Security

**Rating: Partial**

**Strengths:**
- `captureContent: false` by default prevents accidental PII/prompt leakage in traces
- Content truncation at 4096 characters limits exposure surface even when capture is enabled
- Prompt-injection detection runs on inbound messages (span annotation)
- Sensitive-file and dangerous-command detection on tool calls
- Plugin registers with a stable ID; cannot be impersonated within the gateway process

**Gaps:**
- No encryption at rest for span data in the default ClickHouse deployment (plaintext `otel/otel` credentials)
- No TLS on default OTLP endpoints (HTTP `:4318` and gRPC `:4317` are unencrypted)
- No access control on the collector or ClickHouse in the Docker Compose stack
- `customHeaders` allows bearer-token auth to backends, but no mTLS support
- No audit log of configuration changes (who enabled `captureContent`)
- Tool input/output capture may contain secrets (API keys, credentials) — no redaction pipeline
- No data classification or PII filtering before export (must be done in collector)
- Default Grafana credentials (`admin/admin`) with no forced password change

---

### Identity Management

**Rating: Moderate**

**Strengths:**
- Agent identity tracked via `gen_ai.agent.id` on every agent turn span
- Handoff chain preserves sequential identity: `ioa_observe.agent.previous`, `ioa_observe.agent.sequence`
- Session identity model separates plugin sessions (`session.id`) from runtime sessions (`openclaw.session.key`)
- Cross-session spawn lineage maintained via span links with agent names
- `customAttributes` support for organization-level identity (workspace-id, mas-id)
- IOA-specific attributes enable downstream identity graph construction

**Gaps:**
- No human user identity binding — cannot determine which human initiated the conversation
- No cryptographic verification of agent identity (trusts OpenClaw-provided `agentId` strings)
- Session IDs are random UUIDs with no binding to authentication tokens or user principals
- No mechanism to verify that a span link accurately represents the agent that ran
- Cross-process propagation headers (`x-last-agent-*`) are unsigned — a malicious MCP server could forge handoff context
- No support for OAuth/OIDC token propagation through the trace context

---

### Reliability

**Rating: Moderate**

**Strengths:**
- BatchSpanProcessor with configurable flush ensures non-blocking telemetry export
- Graceful shutdown on SIGTERM/SIGINT flushes active sessions and pending spans
- Lazy telemetry initialization — hooks register during plugin load but SDK activates on service start
- Heartbeat mechanism prevents metric staleness and maintains timeseries continuity
- Session idle-timeout provides best-effort cleanup even if explicit end signals are lost
- ClickHouse healthcheck with retry in Docker Compose ensures collector only starts when storage is ready
- Collector batch processor (1s/512) provides backpressure buffer

**Gaps:**
- No retry logic for failed OTLP exports (relies on SDK's default retry which may silently drop spans)
- No dead-letter queue — if ClickHouse is unavailable, spans are lost after batch buffer fills
- No exactly-once delivery — duplicate spans possible after process restart during flush
- In-memory session state (handoff map, fork groups, pending tools) is lost on crash without recovery
- Span cache is in-process only — no persistence across restarts
- No circuit breaker between plugin and collector (export failures don't degrade gracefully)
- 500ms polling interval for hook wrapping means brief window where new plugins aren't yet wrapped
- No ordering guarantees on diagnostic events — race between `model.usage` and `agent_end` may cause enrichment to miss

---

### Accuracy

**Rating: Moderate**

**Strengths:**
- Diagnostics-driven token counts are authoritative (sourced from OpenClaw's model.usage events)
- Dual payload format (OTel GenAI semconv + openclaw.* namespaced) reduces semantic ambiguity
- Fork/join detection uses 2-second time window with retroactive first-branch annotation
- Context assembly metrics provide byte-level accuracy of what entered the model prompt
- Agent turn duration measured from first lifecycle hook to `agent_end` captures full turn
- Fallback hierarchy (`before_model_resolve` → `before_prompt_build` → `before_agent_start`) ensures spans are created even on older runtimes
- Tool errors accurately derived from exit codes and result status flags

**Gaps:**
- Session end time reflects last observed activity, not actual wall-clock session end (watcher granularity: 30s)
- OpenLLMetry streaming token counts are estimates (tiktoken) unless the vendored patch is applied
- Fork detection window (2s) is hardcoded — very fast sequential tools may be incorrectly flagged as parallel; very slow parallel tools may be missed
- Memory operation classification relies on path heuristics (contains "memory"/"memories" and ends with `.md`) — false positives/negatives for non-standard memory layouts
- `contextPreparationDuration` measures from agent lifecycle start to `llm_input`, which may include non-preparation work
- Repetition score and parallelisation score are session-level averages that may mask per-turn variance
- Experimental metrics (novelty/context-sharing) use cosine or Jaccard similarity which are coarse proxies for semantic overlap

---

## Summary

| Dimension | Rating | Key Gap |
|-----------|--------|---------|
| Observability | Strong | No self-health alerting; declared-but-unwired metrics |
| Security | Partial | No TLS/auth on default deployment; no PII redaction pipeline |
| Identity | Moderate | No human user binding; unsigned cross-process handoff headers |
| Reliability | Moderate | No retry/DLQ for export failures; in-memory state lost on crash |
| Accuracy | Moderate | Heuristic memory detection; hardcoded fork window; session-end granularity |
