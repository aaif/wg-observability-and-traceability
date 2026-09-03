# AAIF Reference Architecture: OCSF

| Field | Value |
|-------|-------|
| **Subject** | [Open Cybersecurity Schema Framework (OCSF)](https://github.com/ocsf) |
| **Version** | 1.9.0 (stable) |
| **Date** | 2026-08-24 |

---

## Objective

Reference architecture for OCSF, the vendor-neutral schema framework that normalizes security events across tools, platforms, and vendors — assessed as the security event correlation layer for AI agent infrastructure.

---

## Scope / Zoom Level

**System layer — security event normalization and cross-tool correlation.** OCSF defines what security events mean, not how they are transported or stored. It sits alongside OpenTelemetry (which handles transport) and SIEM/data lake backends (which handle storage). OCSF provides the semantic contract: event producers and consumers agree on field names, types, enumerations, and relationships. This enables correlation across kernel audit events, network IDS alerts, agent security scanning, and cloud security findings without per-vendor translation at query time.

---

## Prerequisites

| Component | Version | Notes |
|-----------|---------|-------|
| OCSF Schema | 1.9.0 | Core event taxonomy + profiles |
| ocsf-server | latest | Elixir-based schema validation and browsing |
| Schema Browser | schema.ocsf.io | Interactive exploration of classes/objects |
| JSON Schema (metaschema) | included | Validates event conformance |
| Transport (any) | — | OTLP, Kafka, S3, HTTP — OCSF is transport-agnostic |
| Storage (any) | — | Parquet, JSON, Avro — OCSF is format-agnostic |
| AWS Security Lake | current | Native OCSF consumer (Parquet + Iceberg) |

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       Security Event Producers                                │
│                                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │ AI Agent     │  │ EDR / XDR    │  │ Cloud        │  │ Network IDS  │  │
│  │ Security     │  │ (SentinelOne │  │ (CloudTrail, │  │ (Suricata,   │  │
│  │ Scanner      │  │  CrowdStrike)│  │  GuardDuty)  │  │  Zeek)       │  │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  │
│         │                  │                  │                  │          │
│         └──────────────────┴──────────────────┴──────────────────┘          │
│                                    │                                         │
│                          Native OCSF or Mapper                               │
└────────────────────────────────────┼────────────────────────────────────────┘
                                     │ OCSF Events (JSON / Parquet / Avro)
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      Normalization Pipeline                                    │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  Schema Validation                                                     │  │
│  │  • class_uid + activity_id → type_uid composition                     │  │
│  │  • Required field enforcement (metadata.version, time, severity_id)   │  │
│  │  • Enum range validation (0=Unknown, 99=Other always valid)           │  │
│  └──────────────────────────────┬────────────────────────────────────────┘  │
│                                 ▼                                            │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  Enrichment                                                            │  │
│  │  • Observable extraction (IPs, hashes, domains → observables[])       │  │
│  │  • MITRE ATT&CK mapping (attack object population)                   │  │
│  │  • Geolocation, ASN, threat intel correlation                         │  │
│  │  • correlation_uid injection for related events                       │  │
│  └──────────────────────────────┬────────────────────────────────────────┘  │
│                                 ▼                                            │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  Profile Application                                                   │  │
│  │  • security_control: disposition, MITRE, malware, policy              │  │
│  │  • ai_operation: agent identity, model, delegation chain              │  │
│  │  • trace: distributed trace context (trace_id, spans)                 │  │
│  │  • cloud: provider, account, region, resource                         │  │
│  │  • record_integrity: cryptographic attestation                        │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────┬────────────────────────────────────────┘
                                     │
                    ┌────────────────┼────────────────┐
                    ▼                ▼                ▼
          ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
          │ AWS Security │ │  SIEM        │ │  Data Lake   │
          │ Lake         │ │  (Splunk,    │ │  (Iceberg,   │
          │ (Parquet +   │ │   QRadar)    │ │   Delta)     │
          │  Iceberg)    │ │              │ │              │
          └──────────────┘ └──────────────┘ └──────────────┘
                    │                │                │
                    └────────────────┴────────────────┘
                                     │
                                     ▼
          ┌──────────────────────────────────────────────────┐
          │  Correlation & Detection                          │
          │  • Query by type_uid (precise event type)        │
          │  • Search observables[] (any IP/hash/domain)     │
          │  • Filter by profile (all security_control)      │
          │  • Join on correlation_uid (related events)      │
          │  • Timeline via time + metadata.logged_time      │
          └──────────────────────────────────────────────────┘
```

---

## Instrumentation Walkthrough

### What Is Captured

| Category | Event Classes | Example |
|----------|--------------|---------|
| System Activity | File Activity, Process Activity, Module Activity, Kernel Activity | Process spawn with full parent chain |
| Findings | Detection Finding, Compliance Finding, Vulnerability Finding | EDR alert with MITRE technique |
| IAM | Authentication, Account Change, Entity Management | Failed SSH login with geo context |
| Network Activity | DNS Activity, HTTP Activity, Network Connection, SSH Activity | Lateral movement detection |
| Discovery | Device Inventory, Process Query, Network Connection Query | Asset discovery scan |
| Application | API Activity, Datastore Activity, Web Resource Access | LLM API call with token counts |
| Remediation | File Remediation, Process Remediation, Network Remediation | Quarantined malicious file |

### Mechanism

OCSF operates at the schema level — it defines the contract, not the capture mechanism:

1. **Native producers** emit events directly in OCSF format (AWS services, modern EDR platforms)
2. **Mappers** translate vendor-native formats into OCSF events (log pipeline transformations)
3. **Extensions** add vendor-specific attributes without breaking the core schema (registered UID namespace)
4. **Profiles** dynamically overlay attributes onto event classes (security_control, ai_operation, trace)

The `type_uid` composition mechanism enables precise routing:
```
type_uid = class_uid × 100 + activity_id

Example: Authentication (class 3002) + Logon (activity 1) = type_uid 300201
```

### Data Format

OCSF is format-agnostic. The schema defines logical structure; serialization is implementation choice:

| Format | Use Case | Characteristics |
|--------|----------|-----------------|
| JSON | Real-time streaming, APIs | Human-readable, schema validation via JSON Schema |
| Apache Parquet | Data lake storage (AWS Security Lake) | Columnar, compressed, efficient for analytics |
| Apache Avro | Kafka streaming | Schema-embedded, compact binary |
| Protocol Buffers | High-throughput pipelines | Generated code, type-safe |

---

## Sample Trace Output

### Detection Finding (AI Agent Security Alert)

```json
{
  "class_uid": 2004,
  "category_uid": 2,
  "activity_id": 1,
  "type_uid": 200401,
  "severity_id": 4,
  "time": 1756137889268,
  "message": "AI agent attempted unauthorized tool invocation via prompt injection",
  "status_id": 1,
  "metadata": {
    "version": "1.9.0",
    "product": {
      "name": "Agent Security Scanner",
      "vendor_name": "AAIF",
      "version": "2.1.0"
    },
    "logged_time": 1756137889312,
    "uid": "evt-a3f7b2c1-9e4d-4a8b-b5c6-d7e8f9012345"
  },
  "finding_info": {
    "uid": "finding-001-prompt-injection",
    "title": "Prompt Injection: Unauthorized MCP Tool Call",
    "types": ["Threat"],
    "analytic": {
      "type": "Rule",
      "name": "agent-security-boundary-violation",
      "uid": "ASB-042",
      "version": "1.3"
    },
    "created_time": 1756137889268
  },
  "evidences": [
    {
      "data": "{\"tool\": \"filesystem_write\", \"path\": \"/etc/shadow\"}",
      "name": "blocked_tool_call"
    }
  ],
  "attacks": [
    {
      "tactic": {
        "uid": "TA0001",
        "name": "Initial Access"
      },
      "technique": {
        "uid": "T1059",
        "name": "Command and Scripting Interpreter"
      },
      "version": "14.1"
    }
  ],
  "confidence_id": 3,
  "confidence_score": 92,
  "is_alert": true,
  "disposition_id": 2,
  "disposition": "Blocked",
  "observables": [
    {
      "name": "agent_uid",
      "type": "Other",
      "type_id": 99,
      "value": "agent-7b3f-coding-assistant"
    },
    {
      "name": "dst.file.path",
      "type": "File Name",
      "type_id": 7,
      "value": "/etc/shadow"
    }
  ],
  "ai_agent": {
    "uid": "agent-7b3f-coding-assistant",
    "instance_uid": "run-2026-08-24-17-04-49",
    "name": "Coding Assistant",
    "type": "Native",
    "type_id": 0,
    "version": "3.2.1",
    "charter": "Code generation and review within workspace boundaries"
  },
  "ai_model": {
    "name": "claude-sonnet-4-20250514",
    "version": "20250514",
    "provider": "Anthropic"
  },
  "actor": {
    "user": {
      "name": "ematkho",
      "uid": "1000",
      "type_id": 1
    },
    "process": {
      "name": "agent-runtime",
      "pid": 48291,
      "cmd_line": "agent-runtime --workspace /home/ematkho/project"
    }
  },
  "device": {
    "hostname": "dev-workstation",
    "os": {
      "name": "Linux",
      "type_id": 200
    }
  },
  "timezone_offset": -240,
  "correlation_uid": "session-2026-08-24-corr-a1b2c3"
}
```

### Authentication Event (Agent API Key Usage)

```json
{
  "class_uid": 3002,
  "category_uid": 3,
  "activity_id": 1,
  "type_uid": 300201,
  "severity_id": 1,
  "time": 1756137890000,
  "message": "AI agent authenticated to LLM provider API",
  "status_id": 1,
  "status": "Success",
  "metadata": {
    "version": "1.9.0",
    "product": {
      "name": "OTel OCSF Mapper",
      "vendor_name": "AAIF",
      "version": "1.0.0"
    },
    "logged_time": 1756137890045
  },
  "auth_protocol_id": 99,
  "auth_protocol": "API Key (Bearer)",
  "dst_endpoint": {
    "hostname": "api.anthropic.com",
    "port": 443,
    "ip": "104.18.32.47"
  },
  "http_request": {
    "http_method": "POST",
    "url": {
      "path": "/v1/messages",
      "hostname": "api.anthropic.com",
      "scheme": "https"
    }
  },
  "actor": {
    "user": {
      "name": "agent-service-account",
      "type_id": 2
    },
    "process": {
      "name": "agent-runtime",
      "pid": 48291
    }
  },
  "ai_agent": {
    "uid": "agent-7b3f-coding-assistant",
    "instance_uid": "run-2026-08-24-17-04-49",
    "name": "Coding Assistant",
    "type": "Native",
    "type_id": 0
  },
  "observables": [
    {
      "name": "dst_endpoint.hostname",
      "type": "Hostname",
      "type_id": 1,
      "value": "api.anthropic.com"
    }
  ],
  "correlation_uid": "session-2026-08-24-corr-a1b2c3"
}
```

---

## Cost Profile

### Compute/IO Overhead

OCSF is a schema specification — it has no runtime overhead itself. Costs arise from implementation choices:

| Component | Overhead | Notes |
|-----------|----------|-------|
| Schema validation | 0.1–0.5 ms/event | JSON Schema validation at ingest; skippable in production |
| type_uid computation | Negligible | Single multiplication + addition |
| Observable extraction | 0.2–1 ms/event | Scanning nested fields for indicator types |
| Profile overlay | None at runtime | Compile-time schema expansion |
| Mapper translation | 1–5 ms/event | Vendor format → OCSF transformation |
| Enrichment (MITRE, geo) | 2–10 ms/event | External lookup latency; cache-dependent |

### Storage Growth

| Format | Size per Event | 10K events/sec | Daily Growth |
|--------|---------------|----------------|--------------|
| JSON (uncompressed) | 2–8 KB | 20–80 MB/s | 1.7–6.9 TB |
| JSON (gzip) | 0.3–1.2 KB | 3–12 MB/s | 259–1037 GB |
| Parquet (columnar) | 0.2–0.8 KB | 2–8 MB/s | 173–691 GB |
| Avro (binary) | 0.5–2 KB | 5–20 MB/s | 432–1728 GB |

### LLM Token Cost

None intrinsic to OCSF. LLM costs arise only if using AI for:
- Automated mapping (vendor format → OCSF): ~500–2000 tokens per novel event class mapping
- AI-assisted detection rule authoring: ~1000–5000 tokens per rule
- Natural language querying over OCSF events: standard RAG costs

---

## Validation Criteria

### Functional Verification

| Check | Method | Expected |
|-------|--------|----------|
| Schema conformance | ocsf-server `/validate` endpoint | No validation errors |
| type_uid composition | `class_uid * 100 + activity_id == type_uid` | Always true |
| Required fields present | JSON Schema validation | `metadata.version`, `class_uid`, `category_uid`, `activity_id`, `type_uid`, `severity_id`, `time` all present |
| Enum values in range | Schema enum definitions | All `*_id` fields within defined range or 0/99 |
| Sibling consistency | Custom rule | `activity_name` matches `activity_id` caption |
| Profile attributes present | Profile schema | If `profiles` array lists "ai_operation", then `ai_agent` or `ai_model` populated |
| Observable correctness | Type validation | Each observable `type_id` matches the actual value type |
| Timestamp ordering | Pipeline rule | `time <= metadata.logged_time` (event before logging) |

### Smoke Test

```bash
# 1. Validate a single event against the OCSF schema
curl -X POST http://localhost:8080/api/validate \
  -H "Content-Type: application/json" \
  -d @detection_finding.json

# Expected: {"valid": true, "errors": []}

# 2. Verify type_uid composition
python3 -c "
import json
with open('detection_finding.json') as f:
    event = json.load(f)
assert event['type_uid'] == event['class_uid'] * 100 + event['activity_id']
assert 'metadata' in event and 'version' in event['metadata']
assert event['metadata']['version'] == '1.9.0'
print('OCSF event valid: type_uid=%d' % event['type_uid'])
"

# 3. Verify observables extraction
python3 -c "
import json
with open('detection_finding.json') as f:
    event = json.load(f)
observables = event.get('observables', [])
assert len(observables) > 0, 'No observables extracted'
for obs in observables:
    assert 'name' in obs and 'type_id' in obs and 'value' in obs
print('Observables valid: %d indicators' % len(observables))
"
```

---

## Limitations / Out of Scope

| Limitation | Impact | Mitigation |
|-----------|--------|------------|
| No transport specification | Must pair with OTLP, Kafka, S3, or custom transport | Use OTel Collector as OCSF event router |
| No storage specification | Schema doesn't define how/where to persist | AWS Security Lake provides opinionated Parquet+Iceberg |
| No query language | Consumers must implement their own analytics | SPL, SQL, KQL all work over OCSF-shaped data |
| No real-time streaming semantics | No ordering guarantees, windowing, or watermarks | Kafka/Kinesis provide these at transport layer |
| Extension fragmentation | Vendor extensions may diverge in practice | Pin to core schema + specific extension versions |
| No built-in access control | Schema doesn't define who can read/write events | Layer RBAC at transport/storage (IAM, Kafka ACLs) |
| Mapping complexity | Translating 100+ vendor formats is labor-intensive | Mapper libraries exist but vary in quality |
| No native AI prompt content redaction | LLM I/O in events may contain PII | Add content redaction in enrichment pipeline |
| Enum exhaustion for novel attacks | New attack types must wait for schema release | Use `99` (Other) + sibling string as escape hatch |
| No trace sampling semantics | Unlike OTel, no head/tail sampling concepts | Apply sampling at transport layer before OCSF mapping |

---

## Evaluation Assessment

### Observability

**Rating: Strong**

**Strengths:**
- Comprehensive event taxonomy covering 8 security categories with 88+ event classes
- `observables[]` array surfaces all security indicators uniformly regardless of event structure
- Profile system allows dynamic attribute overlays (security_control, ai_operation, trace, cloud)
- `metadata.product` identifies the producing tool; `metadata.logged_time` vs `time` reveals pipeline latency
- `enrichments[]` array tracks what intelligence was added post-capture
- `ai_operation` profile provides first-class AI agent observability (agent identity, model, delegation)
- Schema browser at schema.ocsf.io enables interactive exploration

**Gaps:**
- No self-monitoring — OCSF doesn't define metrics about the schema pipeline itself (validation error rates, mapping failures)
- No built-in trace correlation UI — requires external tooling (SIEM, notebook, dashboard)
- Observable extraction is implementation-defined — no canonical algorithm specified
- No cardinality guidance — high-volume environments may produce billions of events without sampling

**Implementations would need to add:**
- Pipeline health metrics (events validated/rejected per second, mapping coverage percentage)
- Schema version drift detection (producers on different OCSF versions)
- Observable deduplication across enrichment stages

### Security

**Rating: Moderate**

**Strengths:**
- `record_integrity` profile enables cryptographic attestation over events (hash chains, signatures)
- `security_control` profile standardizes disposition (Allowed/Blocked/Quarantined) and policy attribution
- Immutable `type_uid` composition prevents event class spoofing at validation time
- Extension UID registration prevents namespace collisions
- `unmapped` field preserves original data for forensic verification

**Gaps:**
- No encryption specification — events may contain sensitive data (IPs, usernames, file paths) in cleartext
- No access control model — who can produce, validate, or consume events is undefined
- No field-level classification — no indication which attributes contain PII or secrets
- No signing standard beyond `record_integrity` profile hints — implementation varies
- AI prompt content in `ai_operation` events may expose proprietary system prompts

**Implementations would need to add:**
- Field-level encryption for sensitive attributes (token values, prompt content)
- Producer authentication (signed event submission with key attestation)
- Data classification labels per attribute for DLP integration
- Prompt content redaction or tokenization before OCSF emission

### Identity Management

**Rating: Moderate**

**Strengths:**
- `actor` object binds human identity (user) + machine identity (process) to every event
- `ai_agent` object provides stable UID across runs + per-instance UID per execution
- `ai_agent.charter` captures the declared role/constraints of the agent
- Framework type enumeration (Native, LangChain, AutoGen, CrewAI) identifies agent architecture
- `delegation` object in `ai_operation` profile tracks authority chains (who authorized the AI to act)
- `metadata.product` identifies the producing tool with vendor/version

**Gaps:**
- No cryptographic identity verification — UIDs are self-asserted strings
- No agent credential lifecycle management — rotation, revocation undefined
- No session concept linking multiple events from same agent invocation (must use `correlation_uid` manually)
- No trust hierarchy — a compromised agent can emit events claiming any identity
- Human-to-agent delegation lacks attestation (no proof the human actually authorized it)

**Implementations would need to add:**
- Signed agent identity claims (JWT or similar bound to agent UIDs)
- Session binding (automatic correlation_uid propagation within agent lifecycle)
- Delegation attestation (cryptographic proof of authorization chain)
- Identity federation with organizational IdP (agent UIDs linked to service accounts)

### Reliability

**Rating: Moderate**

**Strengths:**
- Schema versioning via SemVer ensures backward compatibility within major versions
- `status_id` with Unknown (0) / Other (99) pattern handles graceful degradation
- `unmapped` field preserves data that doesn't fit the schema — no silent data loss
- `raw_data` field retains original event for reprocessing if mapping fails
- `count` + `start_time` / `end_time` support event aggregation (compressed representation)
- Category-based partitioning enables independent scaling per event type

**Gaps:**
- No delivery guarantees — OCSF has no acknowledgment, retry, or ordering semantics
- No deduplication mechanism — duplicate events from redundant producers are invisible
- No backpressure signaling — producers cannot know if consumers are overwhelmed
- No event sequencing — related events may arrive out of order with no reconstruction mechanism
- Schema validation failures may silently drop events if pipeline isn't configured to preserve them

**Implementations would need to add:**
- Exactly-once semantics at transport layer (Kafka transactions, SQS dedup)
- Event sequencing via `metadata.sequence` or similar monotonic counter per producer
- Dead-letter queues for events failing schema validation
- Producer-side buffering with WAL for durability across restarts

### Accuracy

**Rating: Strong**

**Strengths:**
- Strict enum normalization eliminates ambiguity — every `activity_id` has one meaning per event class
- `type_uid` composition (class × 100 + activity) creates globally unique event type identifiers
- Metaschema validates the schema itself — preventing schema definition errors
- `confidence_id` / `confidence_score` explicitly quantify detection certainty
- Sibling convention (`activity_id` + `activity_name`) preserves both machine-parseable and human-readable forms
- `Unknown` (0) vs `Other` (99) distinguishes "source didn't tell us" from "source told us something we don't have an enum for"

**Gaps:**
- Timestamp precision is milliseconds — insufficient for kernel-level correlation (nanosecond events)
- No mandatory clock source identification — clock skew between producers is invisible
- Enum mapping correctness depends entirely on mapper implementation quality
- No validation of semantic correctness — schema validates structure, not meaning (a mapper could assign wrong `activity_id`)
- `confidence_score` has no calibration standard — 92% from one tool ≠ 92% from another

**Implementations would need to add:**
- Nanosecond timestamp support for kernel/hardware event correlation
- Clock source metadata (NTP stratum, PTP domain) for multi-source time alignment
- Mapper certification or test suites to validate semantic correctness
- Confidence score calibration framework (precision/recall at stated thresholds)

---

## Summary

| Dimension | Rating | Key Gap |
|-----------|--------|---------|
| Observability | Strong | No self-monitoring; no cardinality management |
| Security | Moderate | No encryption spec; field-level classification absent |
| Identity | Moderate | Self-asserted UIDs; no cryptographic verification |
| Reliability | Moderate | No delivery/ordering guarantees (transport-layer concern) |
| Accuracy | Strong | Millisecond timestamps; no mapper certification |

---

## OCSF ↔ AAIF Stack Correlation

OCSF's value in the AAIF ecosystem is as the **semantic normalization layer for security events** produced across all five layers:

| AAIF Layer | OCSF Category | Correlation Mechanism |
|-----------|---------------|----------------------|
| 02 — Kernel | System Activity (1) | `actor.process.pid` links to LTTng/FTrace sched_switch TID |
| 03 — Hardware | Application Activity (6) | GPU security events (side-channel, memory violation) via extension |
| 04 — Network | Network Activity (4) | `dst_endpoint.ip` + `src_endpoint.port` correlates with pcap |
| 05 — AI Agent | Findings (2), IAM (3) | `ai_agent.uid` + `correlation_uid` links to OTel trace_id |

### Correlation Keys Across Layers

| Key | Source | Links To |
|-----|--------|----------|
| `actor.process.pid` | OCSF event | LTTng sched_switch, perf samples, /proc |
| `correlation_uid` | OCSF event | OTel trace_id, Langfuse trace_id |
| `device.hostname` | OCSF event | All events from same host |
| `observables[].value` | OCSF finding | Network captures (IP), file system traces (path) |
| `time` | OCSF event | Timestamp correlation with all layers (ms precision) |
| `ai_agent.uid` | OCSF ai_operation | Agent runtime session, OTel resource attributes |
| `metadata.product.name` | OCSF event | Producer identification for multi-tool correlation |

---

*Generated from the AAIF Reference Architecture collection — OCSF assessed as the security event schema layer for AI agent infrastructure.*
