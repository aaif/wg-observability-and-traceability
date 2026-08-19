# AAIF Reference Architecture: PostHog

| Field | Value |
|-------|-------|
| **Subject** | [PostHog](https://github.com/PostHog/posthog) |
| **Version** | 1.x (Cloud) / Self-hosted |
| **Date** | 2026-06-29 |

## Objective

Reference architecture for PostHog as an agent telemetry backend — specifically how AI agent frameworks (exemplified by Goose) use PostHog's Capture API for product analytics, adoption tracking, and behavioral event collection while preserving user privacy.

## Scope / Zoom Level

**System layer — telemetry sink.** PostHog sits outside the agent runtime as a cloud-hosted or self-hosted analytics platform. Agent frameworks emit structured events to PostHog's ingestion API. PostHog handles event storage, user identification, funnel analysis, cohort segmentation, and feature flag evaluation. This document focuses on the ingestion surface and how agent telemetry maps to PostHog's data model.

## Prerequisites

| Component | Version | Notes |
|-----------|---------|-------|
| PostHog Cloud or Self-hosted | 1.x+ | Cloud: `us.i.posthog.com` or `eu.i.posthog.com` |
| PostHog Project API Key | — | `phc_*` format, embedded in client |
| HTTP client | Any | Agent sends POST requests directly (no SDK required) |
| Agent framework | Goose 1.39.0 | Reference integration |

## Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────────┐
│                        Agent Runtime (Goose)                          │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │  Telemetry Module (posthog.rs)                                 │  │
│  │                                                                │  │
│  │  ┌──────────────┐  ┌───────────────┐  ┌────────────────────┐  │  │
│  │  │ Installation │  │ Event Builder │  │ PII Sanitizer      │  │  │
│  │  │ Tracker      │  │               │  │ (regex patterns)   │  │  │
│  │  │ (UUID on     │  │ session_start │  │                    │  │  │
│  │  │  disk)       │  │ error         │  │ Strips: paths,     │  │  │
│  │  └──────┬───────┘  │ onboarding_*  │  │ keys, emails,      │  │  │
│  │         │           └───────┬───────┘  │ tokens, UUIDs      │  │  │
│  │         │                   │          └─────────┬──────────┘  │  │
│  │         ▼                   ▼                    ▼              │  │
│  │  ┌─────────────────────────────────────────────────────────┐   │  │
│  │  │              CaptureEvent Payload                        │   │  │
│  │  │  { api_key, event, distinct_id, properties, timestamp } │   │  │
│  │  └────────────────────────────┬────────────────────────────┘   │  │
│  └───────────────────────────────┼────────────────────────────────┘  │
└──────────────────────────────────┼───────────────────────────────────┘
                                   │ HTTPS POST
                                   ▼
┌──────────────────────────────────────────────────────────────────────┐
│                    PostHog Capture API                                │
│           https://us.i.posthog.com/capture/                          │
│                                                                      │
│  ┌────────────────┐  ┌─────────────┐  ┌──────────────────────────┐  │
│  │ Ingestion      │  │ Event       │  │ Person Profiles          │  │
│  │ Pipeline       │──▶ Store       │  │ (distinct_id → person)   │  │
│  │ (Kafka→CH)     │  │ (ClickHouse)│  └──────────────────────────┘  │
│  └────────────────┘  └──────┬──────┘                                 │
│                              │                                        │
│  ┌───────────────────────────▼───────────────────────────────────┐   │
│  │                     Analytics Engine                            │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐  │   │
│  │  │ Funnels  │  │ Trends   │  │ Cohorts  │  │ Feature Flags│  │   │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────────┘  │   │
│  └────────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────┘
```

## Instrumentation Walkthrough

### What Is Captured

| Event Name | When Fired | Key Properties |
|------------|-----------|----------------|
| `session_started` | Each agent session begins | os, arch, version, provider, model, extensions list/count, session_number, days_since_install, install_method, interface, is_resumed, setting_mode, db_schema_version, total_sessions, total_tokens |
| `onboarding_*` | During first-use setup flow | Step-specific properties (bypass telemetry opt-in gate) |
| `telemetry_preference_set` | User makes opt-in/out choice | Preference value |
| `error` | On errors (currently disabled) | error_type, error_category, error_message (sanitized), component, action |
| `custom_slash_command_used` | When user runs custom commands (currently disabled) | Basic context only |

### Mechanism

1. **Installation Identity**: First launch creates `telemetry_installation.json` in the state directory containing:
   - `installation_id`: UUID v4 (the PostHog `distinct_id`)
   - `first_seen`: ISO 8601 timestamp
   - `session_count`: Monotonically incrementing counter

2. **Event Emission**: Fire-and-forget async HTTP POST via `tokio::spawn`:
   ```
   POST https://us.i.posthog.com/capture/
   Content-Type: application/json

   {
     "api_key": "phc_...",
     "event": "session_started",
     "distinct_id": "<installation_id>",
     "properties": { ... },
     "timestamp": "2026-06-29T19:57:02Z"
   }
   ```

3. **Privacy Sanitization**: All string properties pass through regex-based PII stripping before transmission:
   - `/Users/<username>` → `[REDACTED]`
   - `/home/<username>` → `[REDACTED]`
   - `sk-*`, `pk-*`, `key-*`, `token-*` → `[REDACTED]`
   - Email addresses → `[REDACTED]`
   - Bearer tokens → `[REDACTED]`
   - UUIDs in error messages → `[REDACTED]`
   - Property keys containing "key", "token", "secret", "password", "credential" are dropped entirely

4. **Opt-in Gate**: Telemetry requires explicit user opt-in (`GOOSE_TELEMETRY_ENABLED=true` in config). Additional override: `GOOSE_TELEMETRY_OFF=1` env var. Onboarding events bypass this gate to track the opt-in funnel itself.

### Data Format

```json
{
  "api_key": "phc_RyX5CaY01VtZJCQyhSR5KFh6qimUy81YwxsEpotAftT",
  "event": "session_started",
  "distinct_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "properties": {
    "os": "linux",
    "arch": "x86_64",
    "version": "1.39.0",
    "is_dev": false,
    "platform_version": "24.04",
    "install_method": "binary",
    "interface": "cli",
    "is_resumed": false,
    "session_number": 47,
    "days_since_install": 23,
    "provider": "anthropic",
    "model": "claude-sonnet-4-20250514",
    "setting_mode": "auto",
    "extensions_count": 3,
    "extensions": ["developer", "computercontroller", "memory"],
    "db_schema_version": 14,
    "total_sessions": 142,
    "total_tokens": 2847561
  },
  "timestamp": "2026-06-29T19:57:02.854Z"
}
```

## Sample Trace Output

PostHog does not produce traces in the OpenTelemetry sense. Its data model is event-centric:

```json
{
  "uuid": "01902f3a-4b5c-7d8e-9f0a-1b2c3d4e5f6a",
  "event": "session_started",
  "distinct_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "properties": {
    "$lib": "custom",
    "os": "linux",
    "arch": "x86_64",
    "version": "1.39.0",
    "provider": "anthropic",
    "model": "claude-sonnet-4-20250514",
    "session_number": 47,
    "extensions_count": 3,
    "days_since_install": 23
  },
  "timestamp": "2026-06-29T19:57:02.854Z",
  "person": {
    "distinct_ids": ["a1b2c3d4-e5f6-7890-abcd-ef1234567890"],
    "properties": {
      "first_seen": "2026-06-06T10:00:00Z",
      "os": "linux"
    }
  }
}
```

## Cost Profile

### PostHog Pricing (Cloud)

| Tier | Events/month | Cost |
|------|-------------|------|
| Free | 1M events | $0 |
| Pay-as-you-go | >1M | $0.00005/event |

### Agent-Generated Volume

| Scenario | Events/month | Monthly Cost |
|----------|-------------|--------------|
| Single developer (5 sessions/day) | ~150 | $0 (free tier) |
| Team of 20 (10 sessions/day each) | ~6,000 | $0 (free tier) |
| 10,000 active installations | ~300,000 | $0 (free tier) |
| 100,000 active installations | ~3,000,000 | ~$100 |

### Compute/IO Overhead Per Operation

| Operation | Overhead |
|-----------|----------|
| Event emission | <1ms (fire-and-forget async spawn) |
| PII sanitization | <0.5ms (11 regex patterns) |
| Installation file I/O | <1ms (JSON read/write, cached in practice) |
| Network round-trip | 50–200ms (does not block agent) |

### Storage Growth

- PostHog manages storage internally (ClickHouse)
- Local: `telemetry_installation.json` — static ~200 bytes, never grows

## Validation Criteria

### Functional Verification

1. **Opt-in respected**: Set `GOOSE_TELEMETRY_ENABLED=false`, start session, verify no network call to `posthog.com`
2. **Event delivery**: Set `GOOSE_TELEMETRY_ENABLED=true`, start session, check PostHog dashboard for `session_started` event
3. **Privacy sanitization**: Trigger an error containing a file path and API key, verify transmitted payload shows `[REDACTED]`
4. **Installation persistence**: Delete `telemetry_installation.json`, start session, verify new UUID is generated and persisted

### Smoke Test

```bash
# Intercept the PostHog call with a local proxy
export HTTPS_PROXY=http://localhost:8080
export GOOSE_TELEMETRY_ENABLED=true

goose session
# Type "hello" then exit

# Inspect captured request to us.i.posthog.com/capture/
# Verify: event=session_started, distinct_id is UUID v4, no PII in properties
```

## Limitations / Out of Scope

| Area | Status | Notes |
|------|--------|-------|
| Per-session trace correlation | Not supported | PostHog events are independent; no parent/child linking |
| Token-level usage analytics | Not captured | Only aggregate `total_tokens` sent in session_started |
| Real-time dashboarding | Supported by PostHog | But event frequency is low (1 per session) |
| Error tracking (active) | Disabled | Error events exist in code but are commented out |
| Custom slash command tracking | Disabled | Event exists but returns early |
| Conversion funnels | Partial | Onboarding events support funnel analysis; session depth requires external enrichment |
| A/B testing / Feature flags | Not used | PostHog supports them but Goose does not integrate |
| Session replay | Not applicable | No browser UI captured |
| User identification | Anonymous only | Installation UUID; no email, name, or account binding |
| Self-hosted PostHog | Requires code change | API URL is hardcoded to `us.i.posthog.com` |
| Batch ingestion | Not used | Events sent individually (volume is low enough) |
| Retry on failure | None | Fire-and-forget; failed events are silently dropped |

---

## Evaluation Assessment

### Observability

**Rating: Partial**

**Strengths:**
- Clean event schema with rich context (OS, arch, provider, model, extensions, session count)
- Cumulative metrics (total_sessions, total_tokens) give longitudinal view of adoption
- PostHog's analytics engine provides trends, funnels, cohorts out of the box
- Installation identity enables per-user journey tracking without PII

**Gaps:**
- Only one active event type (`session_started`) — no in-session behavioral granularity
- No correlation between events within a session (no session_id property)
- Error and command-usage events are defined but disabled
- No latency, performance, or quality metrics emitted
- No trace/span hierarchy — flat event model only

**Implementations would need to add:**
- Session-scoped events (tool_called, provider_error, compaction_triggered) for within-session observability
- A `session_id` property linking events within a single session
- Latency/performance properties on session_ended events

---

### Security

**Rating: Moderate**

**Strengths:**
- Opt-in by default — no telemetry sent without explicit user consent
- PII sanitization via 11 regex patterns strips paths, keys, emails, tokens, UUIDs
- Property key filtering drops any key containing "secret", "password", "credential", "key", "token"
- No conversation content, file contents, or tool outputs are ever sent
- API key is project-scoped (write-only capture key), not a full-access admin key
- `GOOSE_TELEMETRY_OFF=1` environment override for CI/automated environments

**Gaps:**
- PostHog project API key is embedded in source code (public, but worth noting)
- No request signing or integrity verification — anyone with the key can submit fake events
- No encryption beyond HTTPS transport (PostHog Cloud handles at-rest encryption)
- Sanitization patterns could miss novel PII formats (e.g., custom token prefixes)
- No data retention policy enforcement from the client side
- Extension names are transmitted unsanitized (could contain internal/sensitive names)

**Implementations would need to add:**
- Event signing with a per-installation secret for integrity verification
- Configurable sanitization patterns (allow users to add custom regexes)
- Extension name allowlist/blocklist for sensitive environments
- Client-side data retention limits (max events buffered)

---

### Identity Management

**Rating: Partial**

**Strengths:**
- Anonymous-by-design: installation_id is a random UUID with no link to human identity
- Persistent identity enables longitudinal tracking (days_since_install, session_count)
- No email, username, IP, or account information captured
- Each installation generates its own identity independently

**Gaps:**
- No mechanism to link installation_id to an organizational identity (for enterprise analytics)
- No support for identity merge when user reinstalls or uses multiple machines
- No group/organization analytics (PostHog supports groups but Goose doesn't use them)
- Installation ID is stored as plaintext JSON — anyone with file access can read/spoof it
- No identity rotation or expiration

**Implementations would need to add:**
- Optional organization_id for enterprise deployments (group analytics)
- Identity merge API calls when user links accounts
- Encrypted storage of installation identity file

---

### Reliability

**Rating: Weak**

**Strengths:**
- Fire-and-forget design means telemetry failures never impact agent operation
- Installation data persisted to disk survives process restarts
- Async emission (tokio::spawn) prevents blocking the agent loop

**Gaps:**
- No retry on network failure — events are silently dropped
- No local queue or buffer — if network is unavailable, event is lost permanently
- No acknowledgment processing — no way to know if PostHog received the event
- No deduplication — if somehow double-sent, duplicates appear in analytics
- No backpressure or rate limiting — rapid session starts could flood the API (unlikely in practice)
- No graceful shutdown flush — events spawned just before exit may not complete

**Implementations would need to add:**
- Local event queue with persistence (write to disk, flush on next startup)
- Retry with exponential backoff for transient failures
- Graceful shutdown: await in-flight telemetry before process exit
- Client-side deduplication (event_id based)

---

### Accuracy

**Rating: Moderate**

**Strengths:**
- Properties are computed at emission time from authoritative sources (Config, SessionManager)
- Session counter is atomic (file-persisted increment)
- Timestamps use UTC with RFC 3339 precision
- Error classification provides structured categorization of error strings
- Platform detection logic covers macOS, Linux, Windows with fallbacks

**Gaps:**
- `total_tokens` and `total_sessions` are fetched from SQLite at event time — could be stale if DB is locked
- `install_method` detection is heuristic-based (path substring matching) — could misclassify
- `is_dev` is compile-time only (`cfg!(debug_assertions)`) — not runtime-configurable
- No validation that PostHog actually stored the event correctly
- Extension names reflect config-time state, not runtime state (extensions may fail to load)

**Implementations would need to add:**
- Event delivery confirmation (check PostHog decide/capture response)
- Runtime extension status (loaded vs configured) distinction
- Install method verification against package manager metadata

---

## Summary

| Dimension | Rating | Key Gap |
|-----------|--------|---------|
| Observability | Partial | Only 1 active event type; no in-session behavioral data |
| Security | Moderate | Strong PII sanitization; no event integrity signing |
| Identity | Partial | Anonymous UUID; no org/group identity or merge |
| Reliability | Weak | Fire-and-forget; no retry, queue, or delivery confirmation |
| Accuracy | Moderate | Heuristic install detection; no delivery verification |
