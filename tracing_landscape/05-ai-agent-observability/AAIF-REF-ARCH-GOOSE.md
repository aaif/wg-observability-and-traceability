# AAIF Reference Architecture: Goose

| Field | Value |
|-------|-------|
| **Subject** | [Goose](https://github.com/aaif-goose/goose) |
| **Version** | 1.39.0 |
| **Date** | 2026-06-29 |

## Objective

Reference architecture for Goose, an open-source general-purpose AI agent framework that provides a complete runtime for LLM-driven tool execution with built-in observability, security scanning, permission management, and extensibility via the Model Context Protocol (MCP) and Agent Client Protocol (ACP).

## Scope / Zoom Level

**System layer.** Goose is a full agent runtime — not a primitive library or single-step orchestration helper. It manages the complete lifecycle: UI presentation, REST API server, agent loop (including multi-turn tool execution, context compaction, subagent delegation), session persistence, extension lifecycle, security enforcement, and telemetry export. It operates as a local service binding a single user's desktop/terminal session to one or more LLM providers and extension processes.

## Prerequisites

| Component | Version | Notes |
|-----------|---------|-------|
| Rust toolchain | 1.91.1+ | Build requirement |
| Goose binary | 1.39.0 | `goosed` (server) + `goose` (CLI) |
| SQLite | 3.x | Session storage (embedded via sqlx) |
| LLM Provider | Any of 15+ supported | API key or OAuth configured |
| OpenTelemetry Collector | 0.90+ | Optional; HTTP/protobuf on port 4318 |
| Langfuse | 2.x+ | Optional; self-hosted or cloud |
| MCP extensions | Per-extension | stdio or SSE transport |
| Node.js | 24.x | For desktop UI build only |

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          User Interfaces                                    │
│  ┌──────────────┐   ┌──────────────┐   ┌────────────────────────────────┐  │
│  │  goose CLI   │   │  Desktop App │   │  Custom UI / ACP Client        │  │
│  │  (goose-cli) │   │  (Electron)  │   │  (JetBrains, Zed, etc.)       │  │
│  └──────┬───────┘   └──────┬───────┘   └───────────────┬────────────────┘  │
└─────────┼──────────────────┼────────────────────────────┼──────────────────┘
          │ REST/SSE         │ REST/SSE                   │ ACP (stdio)
          ▼                  ▼                            ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                     goose-server (goosed)                                   │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  Axum Router                                                         │   │
│  │  /reply  /session  /agent  /config  /recipe  /schedule               │   │
│  │  /session_events (SSE)  /sampling  /telemetry  /setup                │   │
│  │  /mcp_app_proxy  /mcp_ui_proxy  /dictation  /local_inference         │   │
│  └──────────────────────────────┬───────────────────────────────────────┘   │
│                                 │                                           │
│  ┌──────────────────────────────▼───────────────────────────────────────┐   │
│  │                        Agent Core                                    │   │
│  │  ┌─────────────┐  ┌──────────────┐  ┌────────────────────────────┐  │   │
│  │  │ Provider    │  │ Permission   │  │ Security Manager           │  │   │
│  │  │ (LLM chat) │  │ Inspector    │  │ (pattern + ML scanner)     │  │   │
│  │  └──────┬──────┘  └──────┬───────┘  └─────────────┬──────────────┘  │   │
│  │         │                 │                        │                  │   │
│  │  ┌──────▼─────────────────▼────────────────────────▼──────────────┐  │   │
│  │  │                   Agent Loop                                   │  │   │
│  │  │  request → provider_chat → tool_calls → permission_check →    │  │   │
│  │  │  security_scan → tool_execution → context_revision → repeat   │  │   │
│  │  └───────────────────────────┬────────────────────────────────────┘  │   │
│  │                              │                                        │   │
│  │  ┌──────────────┐  ┌────────▼─────┐  ┌───────────────────────────┐  │   │
│  │  │ Retry Mgr    │  │ Extension    │  │ Context Manager           │  │   │
│  │  │              │  │ Manager      │  │ (compaction @ 80%)        │  │   │
│  │  └──────────────┘  └──────┬───────┘  └───────────────────────────┘  │   │
│  │                           │                                           │   │
│  └───────────────────────────┼───────────────────────────────────────────┘   │
│                              │ MCP (stdio/SSE)                               │
└──────────────────────────────┼──────────────────────────────────────────────┘
                               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Extensions (MCP Servers)                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │  developer   │  │  computer-   │  │  memory      │  │  70+ third-  │   │
│  │  (shell,     │  │  controller  │  │  (sqlite     │  │  party MCP   │   │
│  │   editor)    │  │  (PDF, DOCX) │  │   store)     │  │  servers     │   │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘

                    ┌─────────────────────────────────────┐
                    │         Telemetry Sinks              │
                    │  ┌─────────┐ ┌────────┐ ┌────────┐  │
                    │  │ OTel    │ │Langfuse│ │PostHog │  │
                    │  │Collector│ │        │ │        │  │
                    │  └─────────┘ └────────┘ └────────┘  │
                    └─────────────────────────────────────┘
```

## Instrumentation Walkthrough

### What Is Captured

| Signal | Content | Granularity |
|--------|---------|-------------|
| Traces | Agent loop spans, provider chat calls, tool executions, security scans | Per-turn, per-tool-call |
| Metrics | Token usage (input/output/cache), prompt injection findings, tool call pass/fail counters | Per-session cumulative |
| Logs | Structured tracing events (security actions, extension lifecycle, compaction events) | Per-event |
| Session data | Full conversation history, extension state, model config, usage totals | Per-session (SQLite) |

### Mechanisms

1. **OpenTelemetry OTLP Export** (`crates/goose/src/otel/otlp.rs`):
   - `SdkTracerProvider` + `SdkMeterProvider` + `SdkLoggerProvider` all export via HTTP/protobuf
   - A dedicated single-thread Tokio runtime (`OTEL_RT`) drives async reqwest exports from batch processor threads
   - `tracing-opentelemetry` bridge maps Rust `tracing` spans/events → OTel spans/logs
   - `MetricsLayer` maps `tracing` counter macros (e.g., `monotonic_counter.goose.prompt_injection_finding`) → OTel metrics
   - Resource attributes include service name, version, environment

2. **Langfuse Observation Layer** (`crates/goose/src/tracing/langfuse_layer.rs`):
   - Custom `tracing_subscriber::Layer` implementation
   - Maps tracing spans → Langfuse observations (generations, spans)
   - Batches events every 5 seconds, sends to Langfuse `/api/public/ingestion` endpoint
   - Tracks span hierarchy via `SpanTracker` (span_id → observation_id mapping)

3. **PostHog Telemetry** (`crates/goose/src/posthog.rs`):
   - Product analytics: session starts, provider selection, extension usage patterns
   - Disabled via `GOOSE_DISABLE_TELEMETRY=1`

4. **Security Event Logging** (`crates/goose/src/security/mod.rs`):
   - Every tool call scan emits structured tracing events with:
     - `security.event_type`, `security.action` (ALLOW/BLOCK/LOG)
     - `security.confidence`, `security.threshold`, `security.finding_id`
     - `tool.name`, `tool.request_id`, `tool.call_json`
   - Counter metrics: `goose.prompt_injection_finding`, `goose.prompt_injection_tool_call_passed`

5. **Lifecycle Hooks** (`crates/goose/src/hooks/mod.rs`):
   - Plugin-defined scripts invoked at: PreToolUse, PostToolUse, PostToolUseFailure, SessionStart, SessionEnd, BeforeShellExecution, AfterShellExecution, AfterFileEdit, Stop
   - Hooks receive JSON context on stdin, execute as subprocesses with 30s default timeout
   - Defined in plugin `hooks.json` with regex matchers for tool names

### Data Format

- OTLP: protobuf over HTTP (port 4318 default)
- Langfuse: JSON batch ingestion API
- PostHog: JSON event API
- Session storage: SQLite with JSON-serialized conversation/extension data

## Sample Trace Output

```json
{
  "resourceSpans": [{
    "resource": {
      "attributes": [
        { "key": "service.name", "value": { "stringValue": "goose" } },
        { "key": "service.version", "value": { "stringValue": "1.39.0" } }
      ]
    },
    "scopeSpans": [{
      "scope": { "name": "goose::agents::agent" },
      "spans": [
        {
          "traceId": "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6",
          "spanId": "1234567890abcdef",
          "name": "agent_reply",
          "kind": "SPAN_KIND_INTERNAL",
          "startTimeUnixNano": "1719676800000000000",
          "endTimeUnixNano": "1719676812000000000",
          "attributes": [
            { "key": "session.id", "value": { "stringValue": "sess_abc123" } },
            { "key": "provider.name", "value": { "stringValue": "anthropic" } },
            { "key": "model.name", "value": { "stringValue": "claude-sonnet-4-20250514" } }
          ]
        },
        {
          "traceId": "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6",
          "spanId": "fedcba0987654321",
          "parentSpanId": "1234567890abcdef",
          "name": "provider_chat",
          "kind": "SPAN_KIND_CLIENT",
          "startTimeUnixNano": "1719676800100000000",
          "endTimeUnixNano": "1719676803500000000",
          "attributes": [
            { "key": "gen_ai.usage.input_tokens", "value": { "intValue": "4250" } },
            { "key": "gen_ai.usage.output_tokens", "value": { "intValue": "890" } }
          ]
        },
        {
          "traceId": "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6",
          "spanId": "abcdef1234567890",
          "parentSpanId": "1234567890abcdef",
          "name": "tool_execution",
          "kind": "SPAN_KIND_INTERNAL",
          "startTimeUnixNano": "1719676803600000000",
          "endTimeUnixNano": "1719676805200000000",
          "attributes": [
            { "key": "tool.name", "value": { "stringValue": "developer__shell" } },
            { "key": "security.action", "value": { "stringValue": "ALLOW" } },
            { "key": "security.confidence", "value": { "doubleValue": 0.02 } },
            { "key": "permission.level", "value": { "stringValue": "approved" } }
          ]
        }
      ]
    }]
  }]
}
```

## Cost Profile

### LLM Token Cost

| Operation | Typical Tokens | Cost (Claude Sonnet 4) |
|-----------|---------------|------------------------|
| Single turn (user → response) | 2K–8K input, 500–2K output | $0.006–$0.024 input, $0.0075–$0.030 output |
| Tool call (per call) | +500–2K input (tool result) | $0.0015–$0.006 |
| Context compaction | 8K–50K input, 2K–5K output | $0.024–$0.150 input, $0.030–$0.075 output |
| Session naming | 500–1K input (uses fast model) | <$0.001 |

### Compute/IO Overhead Per Operation

| Operation | Overhead |
|-----------|----------|
| Security scan (pattern-only) | <1ms per tool call |
| Security scan (ML classifier) | 10–50ms per tool call (model inference) |
| OTLP batch export | ~5ms per batch (async, non-blocking) |
| Langfuse batch flush | ~10ms per 5s batch (async HTTP) |
| SQLite session persist | 1–5ms per message write |
| MCP tool call (stdio) | 10–100ms (subprocess IPC) |
| Context compaction (LLM call) | 3–15s (LLM inference time) |

### Storage Growth Rate

| Store | Growth |
|-------|--------|
| SQLite session DB | ~10–50KB per session (JSON conversations) |
| Tracing logs (file) | ~1–5MB per hour of active use |
| OTLP spans (collector) | ~50–200 spans per active session-hour |

## Validation Criteria

### Functional Verification

1. **Agent loop completes**: `goose session` → user message → tool execution → response displayed
2. **Security scanning active**: Set `SECURITY_PROMPT_ENABLED=true`, trigger a suspicious tool call, verify `BLOCK` log entry
3. **Permission system enforced**: Configure `permission_level: ask_every_time`, verify tool calls prompt for approval
4. **Context compaction fires**: Send messages until 80% of context window consumed, verify compaction message appears
5. **Extension connectivity**: Configure an MCP extension, verify tools appear in tool list

### Telemetry Verification (Smoke Test)

```bash
# Start collector
docker run -p 4318:4318 otel/opentelemetry-collector:latest

# Configure goose
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318
export OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf

# Start goose session and send a message
goose session

# Verify spans arrive at collector (check collector logs)
# Expected: agent_reply span with child provider_chat and tool_execution spans
```

### Langfuse Verification

```bash
export LANGFUSE_PUBLIC_KEY=pk-lf-...
export LANGFUSE_SECRET_KEY=sk-lf-...
export LANGFUSE_HOST=http://localhost:3000

# Run goose session, verify traces appear in Langfuse UI
# Expected: trace with generation observations per LLM call
```

## Limitations / Out of Scope

| Area | Status | Notes |
|------|--------|-------|
| Multi-user / multi-tenant | Not supported | Single-user local agent; no user isolation or RBAC |
| Distributed tracing across agents | Partial | ACP inter-agent calls do not propagate trace context |
| Trace context in MCP calls | Not implemented | MCP protocol has no trace propagation header spec |
| Token-level streaming telemetry | Not captured | Only aggregate token counts per LLM call |
| Cost attribution per session | Partial | Token usage tracked per session but $ cost requires model price lookup |
| Audit log tamper resistance | None | SQLite and log files are writable by the agent process |
| Network egress filtering | Partial | Egress inspector exists but is advisory, not enforced |
| Sandboxed extension execution | Not enforced by default | Extensions run as user-level processes; optional Docker sandbox |
| Real-time alerting | Not built-in | Requires external alerting on OTel collector or Langfuse |
| Offline / air-gapped operation | Partial | Local inference supported (llama.cpp) but most providers require internet |

---

## Evaluation Assessment

### Observability

**Rating: Strong**

**Strengths:**
- Three independent telemetry pipelines (OTLP, Langfuse, PostHog) covering traces, metrics, logs, and product analytics
- Structured security event emission with finding IDs, confidence scores, and tool call context
- Token usage tracking per session with input/output/cache breakdown
- Session event bus (SSE) enables real-time UI observation of agent state
- `tracing` macros throughout the codebase emit counters and structured fields automatically

**Gaps:**
- No trace context propagation to MCP extensions or ACP consumers — tool execution in remote processes is a black box
- No built-in dashboarding or alerting; requires external infrastructure
- Langfuse layer is optional and requires self-hosting or a paid account
- No span-level cost attribution (tokens are counted but not priced in telemetry)

**Implementations would need to add:**
- W3C Trace Context headers in MCP/ACP transport for end-to-end distributed tracing
- Built-in cost calculation using the canonical model registry's pricing data
- Health check endpoints exposing agent loop state metrics

---

### Security

**Rating: Moderate**

**Strengths:**
- Prompt injection detection with dual approach: pattern matching (regex-based, zero latency) and ML classification (configurable threshold)
- Permission system with three levels: always allow, always deny, ask every time — plus tool annotation support (readOnly hints)
- Security findings tagged with unique IDs, confidence scores, and configurable thresholds (BLOCK above threshold, LOG below)
- Egress inspector for network access monitoring
- Adversary inspector for detecting adversarial manipulation patterns
- Extension malware checking before loading
- SECURITY.md documents threat model and responsible disclosure

**Gaps:**
- Security scanning is disabled by default (`SECURITY_PROMPT_ENABLED` defaults to false)
- No encryption at rest for session data (SQLite files are plaintext)
- Secret management relies on system keyring — no HSM or vault integration
- API key for goose-server is a static shared secret, not short-lived tokens
- No sandboxing by default — extensions execute with full user privileges
- Permission decisions are not cryptographically signed or auditable beyond logs
- ML classifier availability depends on build features and model download

**Implementations would need to add:**
- Encryption at rest for session database
- Per-extension sandboxing (seccomp, namespaces, or container isolation) enforced by default
- Short-lived token authentication for the REST API
- Integration with external secret managers (HashiCorp Vault, AWS Secrets Manager)

---

### Identity Management

**Rating: Partial**

**Strengths:**
- Session-level identity: each session has a unique UUID, tied to a working directory and creation timestamp
- Provider authentication via OAuth flows (Google, GitHub Copilot, xAI, HuggingFace, Databricks) with token refresh
- Instance ID for the goose process (used in telemetry correlation)
- ACP server identifies itself with server metadata (name, version)
- PostHog anonymous distinct_id for product analytics without PII

**Gaps:**
- No human identity binding — no concept of "who is the user" beyond implicit OS user
- No AI agent identity verification — no cryptographic proof of which model/provider generated a response
- No session-to-user linking beyond filesystem permissions
- OAuth tokens stored in keyring but no rotation policy enforcement
- No identity federation or SSO for enterprise deployments
- MCP extensions cannot verify the identity of the calling agent

**Implementations would need to add:**
- Explicit user identity model (OIDC/SAML integration for enterprise)
- Signed agent responses with provider attestation
- Extension-level mutual authentication (mTLS or token exchange)
- Session ownership model with explicit user binding

---

### Reliability

**Rating: Moderate**

**Strengths:**
- Retry manager with configurable backoff for LLM provider failures
- Context compaction prevents context window overflow (triggers at 80% utilization)
- Extension manager handles extension crash/reconnection gracefully
- Session persistence in SQLite survives agent restarts — conversations are recoverable
- Cancellation token support for graceful shutdown of in-flight operations
- Stop hook block cap (default 8) prevents infinite loops from misconfigured hooks
- Error recovery: tool execution errors are fed back to the LLM as context rather than crashing

**Gaps:**
- No message delivery guarantees — if the agent crashes mid-tool-execution, partial results may be lost
- No deduplication of tool calls on retry — retried LLM calls may produce duplicate tool executions
- No backpressure mechanism between UI and agent — fast message submission could overwhelm the agent loop
- SQLite single-writer limitation — concurrent access from multiple processes is not supported
- No health check / liveness probe for the goose-server process
- Telemetry export is best-effort (batch processors drop data on buffer overflow)

**Implementations would need to add:**
- WAL-mode checkpoint management for SQLite reliability under crash
- Idempotency keys for tool executions to prevent duplicate side effects on retry
- Server health check endpoint with dependency status
- Graceful degradation when telemetry backends are unreachable

---

### Accuracy

**Rating: Moderate**

**Strengths:**
- Token counting via dedicated `token_counter` module with model-specific tokenizers
- Canonical model registry maps provider-specific model names to standardized capabilities (context limits, pricing, reasoning flag)
- Security scan confidence scores are numeric (0.0–1.0) with configurable thresholds
- Context compaction uses dedicated summarization prompts designed to preserve critical information
- Tool results are passed back verbatim to the LLM (no lossy transformation)
- Permission check results categorize tool calls precisely: approved, needs_approval, denied

**Gaps:**
- Token counting is approximate — different providers tokenize differently, and the counter may not match the provider's actual count
- Context compaction necessarily loses information — no mechanism to verify compaction fidelity
- Security classifier confidence calibration is not documented or validated against benchmarks
- No data validation on tool results returned from MCP extensions (trusts extension output)
- No semantic verification that LLM responses are factually correct
- Cost estimation depends on canonical registry accuracy which requires manual maintenance

**Implementations would need to add:**
- Provider-specific tokenizer validation (compare local count vs. provider-reported usage)
- Compaction quality metrics (e.g., key-fact retention score)
- Security classifier calibration benchmarks with published precision/recall
- Schema validation for MCP tool responses

---

## Summary

| Dimension | Rating | Key Gap |
|-----------|--------|---------|
| Observability | Strong | No trace propagation to MCP extensions; no built-in alerting |
| Security | Moderate | Scanning disabled by default; no extension sandboxing enforced |
| Identity | Partial | No human identity model; no agent response attestation |
| Reliability | Moderate | No tool call idempotency; no message delivery guarantees |
| Accuracy | Moderate | Approximate token counting; no compaction fidelity validation |
