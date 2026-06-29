# AAIF Reference Architecture: Datadog

| Field | Value |
|-------|-------|
| **Subject** | [Datadog](https://www.datadoghq.com/) |
| **Version** | Platform (SaaS); Agent 7.x |
| **Date** | 2026-06-29 |

---

## Objective

Reference architecture for Datadog as an AI agent observability platform — assessing its LLM Observability product, APM distributed tracing, and infrastructure monitoring capabilities through the lens of AI agent infrastructure requirements.

---

## Scope / Zoom Level

**System layer — full-stack commercial observability platform.** Datadog provides the complete observability pipeline: agent-based collection, SaaS ingestion and storage, query/visualization, alerting, and AI-specific LLM Observability features. Unlike OTel (plumbing only) or Trace Compass (analysis only), Datadog is an integrated platform covering collection through alerting in a single vendor offering.

---

## Prerequisites

| Component | Version | Notes |
|-----------|---------|-------|
| Datadog Agent | 7.x | Host/container-level collector |
| Datadog API key | — | Required for all data ingestion |
| Datadog App key | — | Required for API queries and configuration |
| dd-trace library | Language-specific | APM instrumentation (Python, Go, Java, Node, .NET, Ruby) |
| ddtrace LLM Obs SDK | 2.x+ (Python) | `ddtrace.llmobs` for AI/LLM tracing |

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     Instrumented AI Applications                             │
│                                                                             │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────────┐ │
│  │ AI Agent         │  │ LLM Gateway      │  │ Backend Services         │ │
│  │ (ddtrace.llmobs) │  │ (dd-trace APM)   │  │ (dd-trace APM)           │ │
│  │                  │  │                  │  │                          │ │
│  │ • LLMObs.llm()  │  │ • HTTP spans     │  │ • DB queries             │ │
│  │ • LLMObs.tool() │  │ • gen_ai attrs   │  │ • Queue operations       │ │
│  │ • LLMObs.agent()│  │                  │  │ • External API calls     │ │
│  │ • LLMObs.workflow│  │                  │  │                          │ │
│  └────────┬─────────┘  └────────┬─────────┘  └─────────────┬────────────┘ │
│           │                     │                           │              │
└───────────┼─────────────────────┼───────────────────────────┼──────────────┘
            │                     │                           │
            ▼                     ▼                           ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Datadog Agent (host/container)                        │
│                                                                             │
│  ┌───────────────┐  ┌───────────────┐  ┌──────────────┐  ┌─────────────┐ │
│  │ APM Trace     │  │ Metrics       │  │ Logs         │  │ Process     │ │
│  │ Agent         │  │ Forwarder     │  │ Agent        │  │ Agent       │ │
│  │ (port 8126)   │  │               │  │              │  │             │ │
│  └───────┬───────┘  └───────┬───────┘  └──────┬───────┘  └──────┬──────┘ │
│          │                  │                  │                  │        │
└──────────┼──────────────────┼──────────────────┼──────────────────┼────────┘
           │                  │                  │                  │
           └──────────────────┴──────────────────┴──────────────────┘
                                       │ HTTPS (compressed, batched)
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                       Datadog SaaS Platform                                  │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │  Ingestion & Storage                                                   │ │
│  │  • Trace ingestion (15-minute retention at full fidelity)             │ │
│  │  • Indexed spans (retention by plan: 15 days default)                 │ │
│  │  • Metrics storage (15 months default)                                │ │
│  │  • Log storage (configurable retention)                               │ │
│  │  • LLM Obs spans (prompt/completion/token storage)                    │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │  Analysis & Visualization                                              │ │
│  │  • APM: Service Map, Trace Explorer, Flame Graph                      │ │
│  │  • LLM Observability: Trace panel (agent→LLM→tool), Evaluations      │ │
│  │  • Dashboards, Notebooks, SLOs                                        │ │
│  │  • Watchdog (ML anomaly detection)                                    │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │  Alerting & Response                                                   │ │
│  │  • Monitors (threshold, anomaly, forecast, composite)                 │ │
│  │  • Incidents                                                          │ │
│  │  • Workflows (automated remediation)                                  │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Instrumentation Walkthrough

### What Is Captured

| Signal | Content | AI-Specific |
|--------|---------|-------------|
| APM Traces | Distributed spans (HTTP, DB, queue, custom) | `gen_ai.*` tags on LLM call spans |
| LLM Obs Spans | Agent, workflow, LLM, tool, retrieval spans | Full prompt/completion content, token counts, model, provider |
| Metrics | Host, container, custom, runtime metrics | Token usage gauges, latency histograms per model |
| Logs | Structured application logs with trace correlation | LLM error logs, prompt injection detection logs |
| Evaluations | Quality scores on LLM responses | Faithfulness, relevance, toxicity (built-in or custom) |

### Mechanism (LLM Observability SDK)

```python
from ddtrace.llmobs import LLMObs
from ddtrace.llmobs.decorators import agent, llm, tool, workflow

LLMObs.enable(ml_app="my-ai-agent", agentless_enabled=True)

@agent(name="research_agent")
def research(query: str):
    # Automatically creates an agent span
    context = retrieve_docs(query)   # tool span
    response = call_llm(context)     # llm span
    return response

@tool(name="doc_retrieval")
def retrieve_docs(query: str):
    # Captures input/output, duration
    return vector_db.search(query)

@llm(model_name="claude-sonnet-4-20250514", provider="anthropic")
def call_llm(context: str):
    # Captures prompt, completion, tokens, model, cost
    return client.messages.create(...)
```

### Data Format

- **Agent → Datadog Agent**: MessagePack over HTTP (port 8126) for APM; JSON for LLM Obs spans
- **Datadog Agent → SaaS**: HTTPS with zstd compression, batched every 10s
- **LLM Obs evaluations**: JSON submitted via API or SDK callback

---

## Sample Trace Output

### LLM Obs Trace (agent span with children)

```json
{
  "span_id": "abc123def456",
  "trace_id": "trace-789xyz",
  "parent_id": null,
  "name": "research_agent",
  "type": "agent",
  "ml_app": "my-ai-agent",
  "start_ns": 1751270400000000000,
  "duration_ns": 5200000000,
  "meta": {
    "input": {"value": "What is the AAIF framework?"},
    "output": {"value": "AAIF is a structured assessment framework for..."},
    "metadata": {"temperature": 0.7, "session_id": "sess_abc"}
  },
  "metrics": {
    "input_tokens": 3200,
    "output_tokens": 890,
    "total_tokens": 4090
  },
  "children": [
    {
      "span_id": "tool-span-001",
      "name": "doc_retrieval",
      "type": "tool",
      "start_ns": 1751270400100000000,
      "duration_ns": 800000000,
      "meta": {
        "input": {"value": "AAIF framework"},
        "output": {"value": "[3 documents retrieved]"}
      }
    },
    {
      "span_id": "llm-span-001",
      "name": "anthropic.claude-sonnet-4-20250514",
      "type": "llm",
      "start_ns": 1751270401000000000,
      "duration_ns": 4100000000,
      "meta": {
        "input": {"messages": [{"role": "user", "content": "Given these docs..."}]},
        "output": {"messages": [{"role": "assistant", "content": "AAIF is..."}]},
        "model_name": "claude-sonnet-4-20250514",
        "model_provider": "anthropic"
      },
      "metrics": {
        "input_tokens": 3200,
        "output_tokens": 890
      }
    }
  ]
}
```

---

## Cost Profile

### Platform Pricing (approximate, volume-dependent)

| Feature | Unit Cost | Notes |
|---------|-----------|-------|
| APM Traced Spans | $0.20/million indexed spans | Ingested spans free for 15 min |
| LLM Obs Spans | Per-host APM pricing applies | Included with APM Pro/Enterprise |
| Infrastructure hosts | $15–23/host/month | Agent-based |
| Logs (ingestion) | $0.10/GB ingested | Retention extra |
| Custom metrics | $0.05/metric/month | Per time series |

### Agent Overhead

| Operation | Overhead |
|-----------|----------|
| APM trace collection | 1–3% CPU per traced service |
| dd-trace library (Python) | 5–15MB additional memory |
| Span serialization (MessagePack) | <1ms per batch |
| Network (Agent → SaaS) | 10–50 KB/s per traced host |
| LLM Obs prompt/completion capture | Memory proportional to payload size |

### LLM Token Cost Attribution

Datadog LLM Obs tracks token usage per span but does **not** calculate dollar cost — cost attribution requires custom metric submission or dashboard formulas using model pricing tables.

---

## Validation Criteria

### Functional Verification

1. **Agent connectivity**: `datadog-agent status` → shows API key valid, forwarder running
2. **APM traces flow**: Instrument a service → verify traces in Datadog APM Trace Explorer
3. **LLM Obs spans**: Use `@llm` decorator → verify span with prompt/completion in LLM Obs UI
4. **Distributed trace**: Service A → Service B → trace shows both services linked
5. **Evaluations**: Submit evaluation score → verify it appears on the LLM Obs span

### Smoke Test

```bash
# Install agent (Linux)
DD_API_KEY=<key> DD_SITE="datadoghq.com" bash -c \
  "$(curl -L https://install.datadoghq.com/scripts/install_script_agent7.sh)"

# Verify
datadog-agent status | grep "API Key.*valid"

# Instrument Python app
pip install ddtrace
DD_SERVICE=test-agent DD_ENV=dev ddtrace-run python my_app.py

# Verify in UI: APM → Traces → filter by service:test-agent
# Expected: spans appear within 30 seconds
```

---

## Limitations / Out of Scope

| Area | Status | Notes |
|------|--------|-------|
| Self-hosted / on-premise | Not available | SaaS-only platform (GovCloud variant for compliance) |
| Open source | Partial | Agent is open source; backend is proprietary |
| MCP protocol awareness | Not supported | No native MCP tool call instrumentation |
| Offline / air-gapped | Not supported | Requires internet connectivity to SaaS |
| Agent loop semantic model | Partial | LLM Obs has agent/workflow/tool/llm span types but no reasoning-step granularity |
| Prompt injection detection | Built-in | Evaluations can flag injection attempts (Datadog-hosted evaluator) |
| Cost attribution | Partial | Token counts tracked; $ cost requires custom calculation |
| Data sovereignty | Region-limited | Data stored in selected region; no customer-managed encryption keys (except Enterprise) |
| OTel native | Partial | Accepts OTLP via collector; full feature set requires dd-trace SDK |

---

## Evaluation Assessment

### Observability

**Rating: Strong**

**Strengths:**
- Unified platform: traces, metrics, logs, LLM Obs, infrastructure in single pane
- LLM Observability provides purpose-built AI span types (agent, workflow, llm, tool, retrieval)
- Full prompt/completion capture with token accounting per span
- Watchdog ML anomaly detection automatically surfaces unusual patterns
- Service Map visualizes inter-service dependencies including LLM provider calls
- Correlated views: click from trace → logs → infrastructure → LLM Obs seamlessly
- Built-in evaluation framework for LLM response quality scoring

**Gaps:**
- No MCP tool call visibility (MCP is opaque unless manually instrumented)
- Agent reasoning steps (chain-of-thought, context compaction) not captured as first-class signals
- Prompt/completion storage raises data volume concerns for high-throughput agents
- No Trace Compass-style state system for low-level kernel/GPU correlation

**Implementations would need to add:**
- MCP-aware auto-instrumentation (intercept tool calls as DD spans)
- Agent reasoning step span type (between agent and llm spans)
- Token cost calculation built into LLM Obs (model pricing × token count)

---

### Security

**Rating: Moderate**

**Strengths:**
- All data in transit encrypted (TLS to SaaS endpoints)
- API key + App key separation (ingest vs query permissions)
- Role-Based Access Control with granular permissions per product
- Sensitive Data Scanner: regex/ML-based PII detection and redaction in logs
- SOC 2 Type II, ISO 27001, HIPAA BAA available
- Audit trail of user actions in platform

**Gaps:**
- Prompt/completion content stored in cleartext in Datadog — no field-level encryption
- API keys are long-lived secrets (no automatic rotation)
- LLM Obs data (prompts containing secrets) visible to all org users with LLM Obs access
- No customer-managed encryption keys below Enterprise tier
- Sensitive Data Scanner does not cover LLM Obs span content by default
- Agent-to-SaaS communication uses shared API key (compromised key = full ingest access)

**Implementations would need to add:**
- Prompt/completion content encryption at rest with customer keys
- Automatic API key rotation
- Field-level access control on LLM Obs data (separate from APM access)
- Sensitive Data Scanner coverage for LLM Obs prompts/completions

---

### Identity Management

**Rating: Partial**

**Strengths:**
- SAML/SSO integration for user authentication
- SCIM provisioning for user lifecycle management
- Service identity via `service.name` + `env` + `version` tags
- Trace context propagation carries identity across distributed services
- Audit log attributes user actions to specific accounts

**Gaps:**
- No AI agent identity model — which agent instance generated a span is custom tagging only
- No end-user identity in traces (must inject via custom span tags)
- `ml_app` identifies the application but not the session or user
- No cryptographic attestation of which model produced which response
- Multi-tenant isolation requires separate Datadog orgs (no native sub-tenant model)

**Implementations would need to add:**
- First-class agent identity attributes (agent.instance_id, agent.session_id)
- End-user identity correlation (user_id → LLM Obs traces)
- Model response attestation / provenance metadata

---

### Reliability

**Rating: Strong**

**Strengths:**
- Datadog Agent buffers locally on network failure (disk-backed forwarder queue)
- SaaS platform: 99.9% SLA (Enterprise), multi-region redundancy
- Ingestion accepts bursts; backpressure via HTTP 429 with retry guidance
- APM trace sampling: intelligent sampling preserves error/slow traces
- LLM Obs spans submitted asynchronously (does not block application)
- Monitors with escalation policies, auto-resolve, and composite conditions

**Gaps:**
- Vendor lock-in: SaaS outage = total observability loss (no local fallback)
- 15-minute full-fidelity retention for uninxed spans (older spans require indexing = cost)
- Intelligent sampling may drop relevant traces in high-volume scenarios
- No offline/degraded mode for the SDK (if agent unreachable, spans silently dropped after buffer fills)
- Evaluation pipeline availability depends on Datadog-hosted ML models

**Implementations would need to add:**
- Local fallback visualization during SaaS outage
- Configurable SDK behavior when agent unreachable (persist to disk vs drop)
- Guaranteed retention for LLM Obs spans (separate from APM sampling)

---

### Accuracy

**Rating: Strong**

**Strengths:**
- Token counts captured directly from LLM provider responses (not estimated)
- Nanosecond span timestamps from monotonic clock sources
- Full prompt/completion capture preserves exact I/O (no summarization loss)
- Evaluation scores computed by dedicated ML models (faithfulness, relevance, toxicity)
- APM error tracking captures exact exception type, message, and stack trace
- Service-level indicators (SLI/SLO) computed from actual trace data

**Gaps:**
- Token counts trust the provider response (no independent verification)
- Evaluation model accuracy is opaque (Datadog's model, not user-auditable)
- Intelligent sampling introduces statistical uncertainty in aggregated metrics
- LLM Obs does not validate that model name/provider tags are correct (trusts instrumentation)
- Cost estimation from tokens requires external pricing data (not built-in)

**Implementations would need to add:**
- Evaluation model transparency (confidence scores, known failure modes)
- Token count cross-validation against provider billing
- Built-in model pricing registry for automatic cost calculation
- Sampling impact quantification in aggregated dashboards

---

## Summary

| Dimension | Rating | Key Gap |
|-----------|--------|---------|
| Observability | Strong | No MCP awareness; no agent reasoning step spans |
| Security | Moderate | Prompt content stored cleartext; no field-level encryption |
| Identity | Partial | No first-class AI agent identity; no user-to-trace correlation standard |
| Reliability | Strong | SaaS single point of failure; no local fallback mode |
| Accuracy | Strong | Opaque evaluation models; no built-in cost attribution |
