# AAIF Reference Architecture: OpenTelemetry

| Field | Value |
|-------|-------|
| **Subject** | [OpenTelemetry](https://opentelemetry.io/) |
| **Version** | 1.x (stable signals); Collector 0.104.0 |
| **Date** | 2026-06-29 |

---

## Objective

Reference architecture for OpenTelemetry (OTel), the vendor-neutral observability framework that defines how traces, metrics, and logs are instrumented, collected, processed, and exported — assessed as the telemetry substrate for AI agent infrastructure.

---

## Scope / Zoom Level

**System layer — full observability pipeline from instrumentation to export.** OTel spans the entire path: SDK-level instrumentation in application code, wire protocol (OTLP), collector pipeline (receive → process → export), and semantic conventions that standardize what telemetry means. It is not an analysis tool or storage backend — it is the plumbing that connects instrumented applications to observability platforms.

---

## Prerequisites

| Component | Version | Notes |
|-----------|---------|-------|
| OTel Specification | 1.x | Stable for traces, metrics, logs |
| OTel Collector | 0.104.0 | Receive, process, export pipeline |
| OTel SDK (Python) | 1.25.0 | Application instrumentation |
| OTel SDK (Java) | 1.40.0 | Application instrumentation |
| OTel SDK (Go) | 1.28.0 | Application instrumentation |
| OTLP | 1.3.0 | Wire protocol (gRPC + HTTP/protobuf + HTTP/JSON) |
| Semantic Conventions | 1.27.0 | Standardized attribute names |

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     Instrumented Applications                                 │
│                                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │ AI Agent     │  │ LLM Gateway  │  │ MCP Server   │  │ Microservice │  │
│  │ (SDK traces, │  │ (gen_ai.*    │  │ (tool call   │  │ (HTTP spans, │  │
│  │  metrics)    │  │  semconv)    │  │  spans)      │  │  DB spans)   │  │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  │
│         │                  │                  │                  │          │
│         └──────────────────┴──────────────────┴──────────────────┘          │
│                                    │ OTLP (gRPC :4317 / HTTP :4318)         │
└────────────────────────────────────┼────────────────────────────────────────┘
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      OTel Collector Pipeline                                  │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  Receivers                                                             │  │
│  │  • otlp (gRPC + HTTP)    • prometheus (scrape)                        │  │
│  │  • jaeger               • zipkin                                      │  │
│  │  • filelog              • hostmetrics                                  │  │
│  └──────────────────────────────┬────────────────────────────────────────┘  │
│                                 ▼                                            │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  Processors                                                            │  │
│  │  • batch (buffer + flush)   • memory_limiter (backpressure)           │  │
│  │  • attributes (add/remove)  • filter (drop by condition)              │  │
│  │  • tail_sampling            • transform (OTTL)                        │  │
│  │  • redaction                • groupbyattrs                            │  │
│  └──────────────────────────────┬────────────────────────────────────────┘  │
│                                 ▼                                            │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  Exporters                                                             │  │
│  │  • otlp (to another collector)  • prometheus (remote write)           │  │
│  │  • jaeger        • zipkin       • datadog    • elasticsearch          │  │
│  │  • file          • debug        • loki       • clickhouse             │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  Extensions                                                            │  │
│  │  • health_check (:13133)   • pprof (:1777)   • zpages (:55679)       │  │
│  │  • bearertoken_auth        • oauth2client     • basicauth             │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
                                     │
                    ┌────────────────┼────────────────┐
                    ▼                ▼                ▼
          ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
          │  Jaeger      │ │  Prometheus  │ │  Datadog /   │
          │  (traces)    │ │  (metrics)   │ │  Grafana /   │
          │              │ │              │ │  vendor      │
          └──────────────┘ └──────────────┘ └──────────────┘
```

---

## Instrumentation Walkthrough

### What Is Captured

| Signal | Semantic Conventions | Example Attributes |
|--------|---------------------|-------------------|
| Traces | `gen_ai.*`, `http.*`, `db.*`, `rpc.*` | `gen_ai.system`, `gen_ai.request.model`, `gen_ai.usage.input_tokens` |
| Metrics | `http.server.request.duration`, `gen_ai.client.token.usage` | Histograms, counters, gauges |
| Logs | `log.record.*`, structured body | Severity, body, resource context |
| Baggage | User-defined key-value propagation | Cross-service context (tenant_id, session_id) |

### Mechanism

1. **Auto-instrumentation**: Language agents (Java agent, Python `opentelemetry-instrument`) patch libraries at load time — HTTP clients, DB drivers, gRPC stubs emit spans automatically.
2. **Manual instrumentation**: SDK `tracer.start_as_current_span("operation")` for custom business logic spans.
3. **Context propagation**: W3C Trace Context (`traceparent`/`tracestate` headers) propagates trace_id + span_id across process boundaries.
4. **OTLP export**: SDK batches spans/metrics/logs, serializes to protobuf, sends to collector on gRPC (:4317) or HTTP (:4318).
5. **Collector pipeline**: Receives → processes (batch, filter, sample, redact) → exports to one or more backends.

### Data Format (OTLP)

- **Wire format**: Protocol Buffers (primary), JSON (alternative)
- **Transport**: gRPC (bidirectional streaming), HTTP/1.1 (request/response)
- **Signals**: `ResourceSpans`, `ResourceMetrics`, `ResourceLogs` — each with resource attributes, scope info, and signal-specific data

---

## Sample Trace Output

### OTLP Trace (AI agent gen_ai semconv)

```json
{
  "resourceSpans": [{
    "resource": {
      "attributes": [
        {"key": "service.name", "value": {"stringValue": "ai-agent-gateway"}},
        {"key": "service.version", "value": {"stringValue": "2.1.0"}},
        {"key": "deployment.environment", "value": {"stringValue": "production"}}
      ]
    },
    "scopeSpans": [{
      "scope": {"name": "opentelemetry.instrumentation.genai", "version": "0.5.0"},
      "spans": [
        {
          "traceId": "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6",
          "spanId": "1234567890abcdef",
          "name": "chat anthropic.claude-sonnet-4-20250514",
          "kind": "SPAN_KIND_CLIENT",
          "startTimeUnixNano": "1751270400000000000",
          "endTimeUnixNano": "1751270403500000000",
          "attributes": [
            {"key": "gen_ai.system", "value": {"stringValue": "anthropic"}},
            {"key": "gen_ai.request.model", "value": {"stringValue": "claude-sonnet-4-20250514"}},
            {"key": "gen_ai.request.max_tokens", "value": {"intValue": "4096"}},
            {"key": "gen_ai.response.model", "value": {"stringValue": "claude-sonnet-4-20250514"}},
            {"key": "gen_ai.usage.input_tokens", "value": {"intValue": "3200"}},
            {"key": "gen_ai.usage.output_tokens", "value": {"intValue": "890"}},
            {"key": "gen_ai.response.finish_reasons", "value": {"arrayValue": {"values": [{"stringValue": "end_turn"}]}}}
          ],
          "events": [
            {
              "timeUnixNano": "1751270400100000000",
              "name": "gen_ai.content.prompt",
              "attributes": [
                {"key": "gen_ai.prompt", "value": {"stringValue": "[{\"role\":\"user\",\"content\":\"Analyze this trace\"}]"}}
              ]
            }
          ]
        },
        {
          "traceId": "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6",
          "spanId": "fedcba0987654321",
          "parentSpanId": "1234567890abcdef",
          "name": "POST",
          "kind": "SPAN_KIND_CLIENT",
          "startTimeUnixNano": "1751270400200000000",
          "endTimeUnixNano": "1751270403400000000",
          "attributes": [
            {"key": "http.request.method", "value": {"stringValue": "POST"}},
            {"key": "url.full", "value": {"stringValue": "https://api.anthropic.com/v1/messages"}},
            {"key": "http.response.status_code", "value": {"intValue": "200"}}
          ]
        }
      ]
    }]
  }]
}
```

---

## Cost Profile

### Compute/IO Overhead

| Operation | Overhead | Notes |
|-----------|----------|-------|
| Span creation (SDK) | 200–500ns | In-process, lock-free ring buffer |
| Context propagation (inject/extract) | <1μs | Header parse/serialize |
| OTLP batch export (200 spans) | 5–15ms | Async, non-blocking; protobuf serialize + HTTP POST |
| Collector receiver (per batch) | 1–5ms | Protobuf deserialize |
| Collector processor (batch) | <1ms | In-memory buffer management |
| Collector exporter (per batch) | 5–50ms | Depends on backend latency |
| Tail sampling decision | 1–10ms | Requires holding spans in memory until decision |

### Storage Growth (Collector)

| Configuration | Overhead |
|---------------|----------|
| Batch processor buffer | 8,192 spans default (configurable) |
| Memory limiter | Soft limit 80% / hard limit 85% of allocated |
| Persistent queue (experimental) | Disk-backed; survives collector restart |

### Estimated Per-Span Cost at Backend

| Backend | Per-span ingestion cost |
|---------|----------------------|
| Jaeger (self-hosted) | Storage only (~100–500 bytes/span compressed) |
| Datadog | ~$0.000002/span (volume-dependent) |
| Grafana Cloud | ~$0.000005/span |
| AWS X-Ray | $0.000005/trace recorded |

---

## Validation Criteria

### Functional Verification

1. **SDK emits spans**: Instrument a Python app → verify spans in debug exporter output
2. **Context propagates**: Service A calls Service B → both spans share same trace_id
3. **Collector receives**: `curl -X POST localhost:4318/v1/traces -H "Content-Type: application/json" -d @trace.json` → 200 OK
4. **Processing works**: Configure attribute processor → verify attributes added/removed in exported spans
5. **Backend receives**: Collector exports to Jaeger → trace visible in Jaeger UI

### Smoke Test

```bash
# Start collector with debug exporter
cat > otel-config.yaml << 'EOF'
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
      http:
        endpoint: 0.0.0.0:4318
processors:
  batch:
    timeout: 1s
exporters:
  debug:
    verbosity: detailed
service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [batch]
      exporters: [debug]
EOF

docker run --rm -p 4317:4317 -p 4318:4318 \
  -v $(pwd)/otel-config.yaml:/etc/otelcol/config.yaml \
  otel/opentelemetry-collector:0.104.0

# Send test span
curl -X POST http://localhost:4318/v1/traces \
  -H "Content-Type: application/json" \
  -d '{"resourceSpans":[{"resource":{"attributes":[{"key":"service.name","value":{"stringValue":"test"}}]},"scopeSpans":[{"spans":[{"traceId":"01020304050607080910111213141516","spanId":"0102030405060708","name":"test-span","kind":1,"startTimeUnixNano":"1751270400000000000","endTimeUnixNano":"1751270401000000000"}]}]}]}'

# Expected: Collector logs show received span with "test-span" name
```

---

## Limitations / Out of Scope

| Area | Status | Notes |
|------|--------|-------|
| Storage / query | Not provided | OTel is plumbing, not a backend; requires Jaeger/Tempo/vendor |
| Visualization | Not provided | No built-in UI; requires Grafana/Jaeger/vendor dashboards |
| Alerting | Not provided | Collector can route but not evaluate alert conditions |
| AI-specific semantic conventions | Experimental | `gen_ai.*` semconv still evolving; not yet stable |
| MCP/agent protocol awareness | Not defined | No semantic conventions for MCP tool calls or agent loops |
| Trace-to-trace correlation | Limited | No built-in mechanism to link independent traces (e.g., agent session → triggered workflow) |
| Cost attribution | Not built-in | Token costs require custom attributes; no standard semconv for $ cost |
| Sampling decisions | Collector-side | Head sampling loses context; tail sampling requires memory |

---

## Evaluation Assessment

### Observability

**Rating: Strong**

**Strengths:**
- Three signal types (traces, metrics, logs) with unified resource model and correlation
- W3C Trace Context enables end-to-end distributed tracing across any number of services
- Collector self-observes: internal metrics on spans received/exported/dropped, queue depth, export errors
- Semantic conventions standardize attribute names across all implementations
- `gen_ai.*` conventions emerging for LLM/agent workloads (token usage, model, system)
- Extension ecosystem: zpages for live debugging, pprof for collector profiling

**Gaps:**
- No agent-loop semantic conventions (reasoning steps, tool selection, context compaction)
- No MCP-aware context propagation (MCP protocol has no trace context header slot)
- Collector debug exporter is verbose but not structured for automated analysis
- Log signal correlation with traces requires explicit trace_id injection in log records

**Implementations would need to add:**
- Semantic conventions for AI agent operations (agent.loop, agent.tool_call, agent.reasoning)
- MCP transport extension for trace context propagation
- Standard cost-attribution attributes (gen_ai.usage.cost_usd)

---

### Security

**Rating: Moderate**

**Strengths:**
- Collector supports mTLS for receiver and exporter connections
- Authentication extensions: bearer token, OAuth2 client credentials, basic auth
- Redaction processor removes sensitive attributes before export
- OTLP over gRPC supports TLS by default in production configurations
- Collector RBAC possible via gateway patterns (collector-per-team)

**Gaps:**
- SDKs send telemetry in plaintext by default (TLS opt-in)
- No end-to-end encryption of span content (only transport-level)
- Prompt/completion content in `gen_ai.*` events is plaintext — sensitive data exposure risk
- No built-in field-level access control (all-or-nothing export to backends)
- Collector configuration file may contain secrets (exporter API keys) in plaintext

**Implementations would need to add:**
- Default-on TLS for OTLP in production SDK configurations
- Content filtering for LLM prompt/completion events (PII/secret redaction)
- Secret management integration for collector config (Vault, KMS)
- Field-level export policies (e.g., strip gen_ai.prompt for certain exporters)

---

### Identity Management

**Rating: Partial**

**Strengths:**
- `service.name` + `service.instance.id` uniquely identify each instrumented process
- W3C Trace Context carries trace identity across service boundaries
- Baggage propagation allows user-defined context (user_id, tenant_id) across services
- Resource attributes can encode deployment identity (k8s.pod.name, cloud.account.id)

**Gaps:**
- No human user identity in the spec — must be injected via custom attributes or baggage
- No AI agent identity concept — which model/provider generated a span is not standardized
- Baggage is not authenticated — any service can inject or modify baggage items
- No signed spans or tamper-proof trace identity
- `gen_ai.system` identifies the provider but not the specific agent instance

**Implementations would need to add:**
- Standard attributes for human operator identity (enduser.id is deprecated/experimental)
- AI agent identity conventions (agent.name, agent.version, agent.session_id)
- Authenticated baggage (signed context items)
- Span provenance attestation for audit trails

---

### Reliability

**Rating: Strong**

**Strengths:**
- Batch processor with configurable timeout and queue size prevents data loss during export failures
- Memory limiter processor provides backpressure (refuses data when memory threshold exceeded)
- Persistent queue (file-backed) survives collector restarts without span loss
- SDK retry with exponential backoff on transient export failures
- Collector health check extension enables load balancer integration
- Multiple exporter fanout: same data to multiple backends for redundancy
- Graceful shutdown: collector drains in-flight batches before terminating

**Gaps:**
- Head sampling decisions are irrevocable — sampled-out traces cannot be recovered
- Persistent queue is marked experimental; not all exporters support it
- No end-to-end delivery receipt (SDK cannot confirm backend ingested the span)
- Clock skew between services can cause incorrect span ordering in traces
- Large cardinality in attributes can cause metric explosion at backends

**Implementations would need to add:**
- Delivery acknowledgment protocol (SDK ↔ backend confirmation)
- Cardinality limiting in SDK (attribute value cardinality caps)
- Clock synchronization guidance / automatic skew detection

---

### Accuracy

**Rating: Strong**

**Strengths:**
- Nanosecond-precision timestamps from monotonic clocks
- Explicit status codes on spans (OK, ERROR, UNSET) with error descriptions
- Semantic conventions enforce consistent attribute naming (reducing misinterpretation)
- Exemplars link metrics to specific trace IDs for drill-down
- Span events capture precise moments within a span (not just start/end)
- Resource detection auto-populates host, OS, container, cloud attributes accurately

**Gaps:**
- Token counts in `gen_ai.usage.*` depend on SDK implementation accuracy (may not match provider billing)
- Sampling introduces statistical uncertainty in aggregated metrics
- No built-in validation that spans are semantically correct (wrong span kind, missing required attributes)
- Clock skew can produce negative durations or incorrect parent-child ordering
- Collector processing (attribute removal, redaction) may remove information needed for accurate analysis

**Implementations would need to add:**
- Schema validation for semantic convention compliance
- Token count reconciliation (compare SDK-reported vs provider-billed)
- Span correctness linting (CI-time validation of instrumentation)

---

## Summary

| Dimension | Rating | Key Gap |
|-----------|--------|---------|
| Observability | Strong | No AI agent loop / MCP semantic conventions yet |
| Security | Moderate | Plaintext by default; LLM prompt content exposure risk |
| Identity | Partial | No human/agent identity standard; unsigned baggage |
| Reliability | Strong | Head sampling irrevocable; persistent queue experimental |
| Accuracy | Strong | Token count accuracy depends on SDK; no schema validation |
