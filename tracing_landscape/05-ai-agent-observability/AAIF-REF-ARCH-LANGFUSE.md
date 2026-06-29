# AAIF Reference Architecture: Langfuse

| Field | Value |
|-------|-------|
| **Subject** | [Langfuse](https://github.com/langfuse/langfuse) |
| **Version** | 2.x (Cloud & Self-hosted) |
| **Date** | 2026-06-29 |

## Objective

Reference architecture for Langfuse as an LLM observability backend — specifically how AI agent frameworks (exemplified by Goose) use Langfuse's batch ingestion API to capture hierarchical traces of agent execution, including span timing, LLM generation metadata, and input/output payloads for debugging and evaluation.

## Scope / Zoom Level

**System layer — observability sink.** Langfuse sits outside the agent runtime as a dedicated LLM tracing platform. Agent frameworks emit structured observation data (traces, spans, generations) to Langfuse's ingestion API. Langfuse provides hierarchical trace visualization, latency analysis, cost tracking, evaluation scoring, and dataset management. This document focuses on the ingestion surface and how agent telemetry maps to Langfuse's data model.

## Prerequisites

| Component | Version | Notes |
|-----------|---------|-------|
| Langfuse Cloud or Self-hosted | 2.x+ | Cloud: `cloud.langfuse.com` (EU) or `us.cloud.langfuse.com` |
| Langfuse Public Key | — | `pk-lf-*` format |
| Langfuse Secret Key | — | `sk-lf-*` format |
| HTTP client (reqwest) | 0.13+ | 10s timeout, basic auth |
| Agent framework | Goose 1.39.0 | Reference integration via tracing_subscriber Layer |
| Rust tracing ecosystem | tracing 0.1, tracing-subscriber 0.3 | Span/event source |

## Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────────────┐
│                         Agent Runtime (Goose)                             │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │  Rust tracing Framework                                            │  │
│  │                                                                    │  │
│  │  ┌─────────────┐  ┌────────────────┐  ┌────────────────────────┐  │  │
│  │  │ agent_reply │  │ provider_chat  │  │ tool_execution         │  │  │
│  │  │ (span)      │──▶ (child span)   │  │ (child span)           │  │  │
│  │  └─────────────┘  └────────────────┘  └────────────────────────┘  │  │
│  │         │                                                          │  │
│  │         ▼ tracing_subscriber dispatch                              │  │
│  └─────────┼──────────────────────────────────────────────────────────┘  │
│            │                                                              │
│  ┌─────────▼──────────────────────────────────────────────────────────┐  │
│  │  ObservationLayer (tracing_subscriber::Layer impl)                 │  │
│  │                                                                    │  │
│  │  ┌──────────────┐  ┌──────────────────┐  ┌─────────────────────┐  │  │
│  │  │ SpanTracker  │  │ Level Mapper     │  │ Metadata Flattener  │  │  │
│  │  │ span_id →    │  │ ERROR → ERROR    │  │ Extracts: input,    │  │  │
│  │  │ observation_ │  │ WARN → WARNING   │  │ output, model_config│  │  │
│  │  │ id (UUID v4) │  │ INFO → DEFAULT   │  │ trace_input/output  │  │  │
│  │  └──────────────┘  │ DEBUG → DEBUG    │  └─────────────────────┘  │  │
│  │                     └──────────────────┘                           │  │
│  │  ┌────────────────────────────────────────────────────────────┐    │  │
│  │  │  LangfuseBatchManager                                      │    │  │
│  │  │  - Accumulates events in Vec<Value>                        │    │  │
│  │  │  - Flushes every 5 seconds (tokio timer)                   │    │  │
│  │  │  - HTTP POST with basic auth                               │    │  │
│  │  └───────────────────────────┬────────────────────────────────┘    │  │
│  └──────────────────────────────┼─────────────────────────────────────┘  │
└─────────────────────────────────┼────────────────────────────────────────┘
                                  │ HTTPS POST (every 5s)
                                  │ Authorization: Basic base64(pk:sk)
                                  ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                    Langfuse Ingestion API                                 │
│           POST /api/public/ingestion                                     │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │  Batch Processor                                                   │  │
│  │  Accepts: trace-create, observation-create, observation-update,    │  │
│  │           span-update, generation-create, generation-update,       │  │
│  │           score-create, event-create                               │  │
│  └───────────────────────────┬────────────────────────────────────────┘  │
│                              │                                            │
│  ┌───────────────────────────▼────────────────────────────────────────┐  │
│  │                     Data Model                                     │  │
│  │                                                                    │  │
│  │  Trace ─┬── Span (observation, type=SPAN)                         │  │
│  │         ├── Span                                                   │  │
│  │         │    └── Generation (observation, type=GENERATION)         │  │
│  │         └── Span                                                   │  │
│  │              └── Span (nested)                                     │  │
│  │                                                                    │  │
│  │  Each observation has: id, traceId, parentObservationId,           │  │
│  │  name, startTime, endTime, level, metadata, input, output          │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │                     UI / Analysis                                   │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────┐  │  │
│  │  │ Trace    │  │ Latency  │  │ Cost     │  │ Evaluation /     │  │  │
│  │  │ Viewer   │  │ Analysis │  │ Tracking │  │ Scoring          │  │  │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────────────┘  │  │
│  └────────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────────┘
```

## Instrumentation Walkthrough

### What Is Captured

| Observation Type | Mapped From | Content |
|-----------------|-------------|---------|
| Trace | First span in a session | Container for all observations; has input/output, timestamp, tags |
| Span (SPAN) | Each Rust tracing span with target `goose::*` | name, startTime, endTime, level, parentObservationId, metadata |
| Span metadata | `on_record` / `on_event` calls | input, output, model_config, arbitrary key-value fields |

### Mechanism

1. **Layer Registration**: `create_langfuse_observer()` checks for `LANGFUSE_PUBLIC_KEY` + `LANGFUSE_SECRET_KEY` env vars. If both present, creates an `ObservationLayer` and registers it with the tracing subscriber.

2. **Span Lifecycle Mapping**:
   - `on_new_span`: Creates a Langfuse `observation-create` event (type=SPAN) with UUID v4 observation_id, maps parent via SpanTracker
   - `on_close`: Emits `observation-update` with `endTime`
   - `on_record` / `on_event`: Emits `span-update` with recorded fields (input, output, model_config, other metadata)

3. **Trace Management**: First observation triggers `trace-create`. All subsequent observations in the session reference the same `traceId`. Special fields `trace_input` and `trace_output` update the trace itself rather than the span.

4. **Span Hierarchy**: `SpanTracker` maintains a `HashMap<u64, String>` mapping tracing's numeric span IDs to Langfuse UUID observation IDs. Parent lookup uses `ctx.span_scope(id).nth(1)` to find the parent span.

5. **Batch Delivery**: `LangfuseBatchManager` accumulates events in a `Vec<Value>`. A background tokio task flushes every 5 seconds via HTTP POST to `/api/public/ingestion` with basic auth.

6. **Filtering**: Only spans/events with target starting with `goose::` are captured (via `enabled()` method). This prevents library-internal tracing noise from reaching Langfuse.

### Data Format

Each batch POST contains:

```json
{
  "batch": [
    {
      "id": "evt-uuid-1",
      "timestamp": "2026-06-29T20:04:12Z",
      "type": "trace-create",
      "body": {
        "id": "trace-uuid",
        "name": "1719698652",
        "timestamp": "2026-06-29T20:04:12Z",
        "input": {},
        "metadata": {},
        "tags": [],
        "public": false
      }
    },
    {
      "id": "evt-uuid-2",
      "timestamp": "2026-06-29T20:04:12Z",
      "type": "observation-create",
      "body": {
        "id": "obs-uuid-1",
        "traceId": "trace-uuid",
        "type": "SPAN",
        "name": "agent_reply",
        "startTime": "2026-06-29T20:04:12Z",
        "parentObservationId": null,
        "metadata": { "session.id": "sess_abc123" },
        "level": "DEFAULT"
      }
    },
    {
      "id": "evt-uuid-3",
      "timestamp": "2026-06-29T20:04:13Z",
      "type": "observation-create",
      "body": {
        "id": "obs-uuid-2",
        "traceId": "trace-uuid",
        "type": "SPAN",
        "name": "provider_chat",
        "startTime": "2026-06-29T20:04:13Z",
        "parentObservationId": "obs-uuid-1",
        "metadata": { "provider": "anthropic" },
        "level": "DEFAULT"
      }
    }
  ]
}
```

## Sample Trace Output

As rendered in Langfuse's trace viewer:

```
Trace: 1719698652
├── agent_reply [SPAN] 12.4s
│   ├── provider_chat [SPAN] 3.2s
│   │   metadata: { "provider": "anthropic", "model": "claude-sonnet-4-20250514" }
│   │   input: { "messages": [...] }
│   │   output: { "response": "..." }
│   ├── tool_execution [SPAN] 1.6s
│   │   metadata: { "tool.name": "developer__shell", "command": "ls -la" }
│   │   input: { "command": "ls -la" }
│   │   output: { "stdout": "..." }
│   └── provider_chat [SPAN] 2.8s
│       metadata: { "provider": "anthropic" }
│       input: { "messages": [...] }
│       output: { "response": "Here are the files..." }
```

Langfuse API response on successful ingestion:

```json
{
  "successes": [
    { "id": "evt-uuid-1", "status": 201 },
    { "id": "evt-uuid-2", "status": 201 },
    { "id": "evt-uuid-3", "status": 201 }
  ],
  "errors": []
}
```

## Cost Profile

### Langfuse Pricing (Cloud)

| Tier | Observations/month | Cost |
|------|-------------------|------|
| Hobby | 50K | $0 |
| Pro | Included 100K, then $7/10K | From $59/month |
| Self-hosted | Unlimited | Infrastructure cost only |

### Agent-Generated Volume

| Scenario | Observations/session | Monthly (5 sessions/day) |
|----------|---------------------|--------------------------|
| Simple Q&A (1 turn) | ~4 (trace + reply + provider + close) | ~600 |
| Multi-turn with tools (5 turns) | ~20 | ~3,000 |
| Complex session (20 turns) | ~80 | ~12,000 |
| Team of 10, heavy use | — | ~60,000–120,000 |

### Compute/IO Overhead Per Operation

| Operation | Overhead |
|-----------|----------|
| Span creation (on_new_span) | <0.1ms (tokio::spawn async, non-blocking) |
| Span close (on_close) | <0.1ms (tokio::spawn async) |
| Metadata record (on_record) | <0.1ms (tokio::spawn async) |
| Batch flush (every 5s) | 10–50ms (HTTP POST, async) |
| SpanTracker lookup | O(1) HashMap access |
| Memory per active span | ~200 bytes (observation_id String + map entry) |

### Storage Growth

- Langfuse manages storage internally (Postgres + S3/ClickHouse)
- No local storage by the agent (batch is in-memory only)
- Memory: batch buffer grows ~500 bytes per observation until flush

## Validation Criteria

### Functional Verification

1. **Layer activation**: Set `LANGFUSE_PUBLIC_KEY` and `LANGFUSE_SECRET_KEY`, start goose, verify no "Failed to send batch" errors in logs
2. **Trace appears**: Run a session, check Langfuse UI for a trace with child spans
3. **Hierarchy correct**: Verify `provider_chat` spans appear as children of `agent_reply`
4. **Metadata attached**: Verify spans contain `input`, `output`, and `model_config` fields
5. **Level mapping**: Trigger a WARN-level event, verify it appears as level=WARNING in Langfuse

### Smoke Test

```bash
# Self-hosted Langfuse
docker compose -f documentation/docs/docker/docker-compose.yml up -d

export LANGFUSE_PUBLIC_KEY=pk-lf-1234567890
export LANGFUSE_SECRET_KEY=sk-lf-1234567890
export LANGFUSE_URL=http://localhost:3000

# Start goose and interact
goose session
# Send "what time is it?" then exit

# Check Langfuse at http://localhost:3000
# Expected: 1 trace with 2+ span observations (agent_reply, provider_chat)
```

### Failure Mode Verification

```bash
# Point at non-existent Langfuse
export LANGFUSE_URL=http://localhost:9999

goose session
# Verify: agent operates normally despite Langfuse being unreachable
# Verify: error log "Failed to send batch to Langfuse" appears but does not crash
```

## Limitations / Out of Scope

| Area | Status | Notes |
|------|--------|-------|
| Generation observations | Not emitted | Goose only creates SPAN type; no GENERATION with token counts/model/cost |
| Token usage in traces | Not captured | Provider token counts don't flow into Langfuse observations |
| Cost tracking | Not supported | Langfuse supports cost but Goose doesn't emit pricing data |
| Evaluation scoring | Not integrated | Langfuse supports scores but no automated scoring from agent |
| Dataset management | Not used | Langfuse datasets for fine-tuning/eval not connected |
| Prompt management | Not used | Langfuse prompt versioning not integrated |
| Multi-session traces | Single trace per session | No trace linking across resumed sessions |
| Retry on failure | None | Failed batches are lost; no local persistence |
| Backpressure | None | If Langfuse is slow, batch buffer grows unbounded in memory |
| Graceful shutdown | Not implemented | In-flight batch may be lost on process exit |
| User identity | Not linked | No user/session ID passed to Langfuse trace metadata |
| Conversation content | Partial | Depends on what tracing spans record; not systematically captured |
| MCP extension spans | Not captured | Extension tool execution happens in child processes with no Langfuse context |

---

## Evaluation Assessment

### Observability

**Rating: Strong**

**Strengths:**
- Hierarchical trace model captures full agent loop structure (reply → provider → tool → provider)
- Automatic span timing (startTime/endTime) enables latency analysis per operation
- Metadata attachment supports arbitrary structured data on any span
- Trace-level input/output enables session-level summarization
- Level mapping preserves severity information from the agent runtime
- Filtering by `goose::*` target keeps noise out of traces
- Langfuse UI provides trace visualization, latency histograms, and cost dashboards

**Gaps:**
- No GENERATION observations — LLM calls appear as generic spans, missing token counts and model-specific metadata
- No automatic cost calculation (requires generation observations with model/token data)
- No span-level error capture (errors are logged but not attached to specific observations as status)
- Single trace per session — no way to view cross-session patterns in trace viewer
- No sampling control — all spans are captured regardless of volume

**Implementations would need to add:**
- Emit `generation-create` events for provider_chat spans with model, token usage, and cost
- Span status (OK/ERROR) based on tool execution success/failure
- Configurable sampling rate for high-volume deployments
- Session ID and user ID in trace metadata for multi-session correlation

---

### Security

**Rating: Partial**

**Strengths:**
- Authentication via basic auth (public_key:secret_key) on every request
- HTTPS transport encryption in transit
- Self-hosting option keeps data within organizational boundary
- Filtering by `goose::*` prevents accidental capture of library internals

**Gaps:**
- Secret key stored as plaintext environment variable — no vault integration
- No encryption of observation payloads beyond transport TLS
- Input/output fields may contain sensitive data (user prompts, file contents, tool results) with no sanitization
- Batch buffer held in memory is unencrypted
- No client-side access control — any code in the process can access the batch manager
- No audit log of what was sent to Langfuse
- Keys are not rotated automatically

**Implementations would need to add:**
- Content sanitization layer before Langfuse emission (PII stripping like PostHog does)
- Secret key retrieval from keyring/vault rather than env vars
- Configurable field masking (e.g., never send tool outputs for shell commands)
- Local audit log of transmitted observation IDs

---

### Identity Management

**Rating: Minimal**

**Strengths:**
- Trace ID provides session-level correlation
- Observation IDs (UUID v4) uniquely identify each span globally
- Parent-child linking via `parentObservationId` establishes causal relationships

**Gaps:**
- No user identity attached to traces (no userId field populated)
- No session ID from the agent linked to the Langfuse trace
- No organization/project scoping beyond the API key's project
- Trace name is a Unix timestamp — not human-meaningful
- No mechanism to link traces to git commits, deployments, or releases
- No identity of which model/provider actually responded (only what was configured)

**Implementations would need to add:**
- Populate Langfuse trace `userId` field with installation_id or user-provided identity
- Set trace `sessionId` to goose session UUID for cross-trace correlation
- Add `release` and `version` tags to traces
- Set meaningful trace names (e.g., first user message or session name)

---

### Reliability

**Rating: Weak**

**Strengths:**
- Non-blocking async design — Langfuse failures never block agent operation
- Batch coalescing (5s window) reduces request count vs per-event sending
- `tokio::spawn` for span creation means tracing overhead is near-zero on the hot path
- Partial failure handling — batch clears on partial success (some items ingested)

**Gaps:**
- No retry on network failure — entire batch is lost on transient error
- No local persistence — if process exits between flushes, buffered observations are lost
- No backpressure — if Langfuse is slow or down, batch Vec grows without limit (memory leak risk)
- No graceful shutdown — `spawn_sender` loop runs forever with no cancellation token
- No deduplication — if a batch is partially processed and retried, duplicates could appear
- `block_in_place` in `send()` can stall the tokio runtime under load
- Complete failure (all items rejected) retains the batch but has no retry logic
- 10-second HTTP timeout may be too aggressive for large batches over slow connections

**Implementations would need to add:**
- Retry with exponential backoff for 5xx and timeout errors
- Maximum batch buffer size with oldest-event eviction
- Graceful shutdown: flush pending batch before process exit
- Local WAL/file buffer for crash recovery
- Cancellation token integration for clean shutdown

---

### Accuracy

**Rating: Moderate**

**Strengths:**
- Timestamps use UTC with RFC 3339 precision at actual event time
- Span hierarchy accurately reflects Rust tracing's parent-child relationships via `span_scope`
- UUID v4 for observation IDs eliminates collision risk
- Level mapping is deterministic and complete (all 5 tracing levels covered)
- Metadata flattening preserves structure while handling nested objects

**Gaps:**
- Trace name is a bare Unix timestamp — loses human context
- No validation that observations arrive in correct order (async spawns may reorder)
- Span end time is captured at `on_close` callback — may not reflect actual completion if span is held open
- No verification that Langfuse stored data correctly (success response is trusted without read-back)
- `parent_span_id` resolution depends on parent still being in `active_spans` map — if parent closed before child records, linkage is lost
- Metadata that arrives via `on_event` attaches to the current span, which may not be the most appropriate span

**Implementations would need to add:**
- Meaningful trace names derived from session name or first user message
- Ordering guarantees (sequence numbers or causal ordering in batch)
- Span data caching to prevent parent-resolution failures on closed spans
- Read-back verification for critical traces (e.g., check trace exists after flush)

---

## Summary

| Dimension | Rating | Key Gap |
|-----------|--------|---------|
| Observability | Strong | No GENERATION observations; no token/cost data in traces |
| Security | Partial | No content sanitization; secrets in env vars |
| Identity | Minimal | No user/session ID linked to traces |
| Reliability | Weak | No retry, no buffer limit, no graceful shutdown |
| Accuracy | Moderate | Async ordering issues; no meaningful trace names |
