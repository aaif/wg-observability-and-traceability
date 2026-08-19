# AAIF Reference Architecture: TMLL

| Field | Value |
|-------|-------|
| **Subject** | [TMLL](https://github.com/eclipse-tracecompass/tmll) |
| **Version** | 0.x (development) |
| **Date** | 2026-06-29 |

---

## Objective

Reference architecture for TMLL (Trace-Server Machine Learning Library), a Python library that applies automated ML pipelines to trace analysis outputs from Eclipse Trace Compass via the Trace Server Protocol — and exposes those analyses to AI agents through an MCP server interface.

---

## Scope / Zoom Level

**Orchestration layer — bridges deterministic trace analysis with ML inference and AI agent tooling.** TMLL sits between the Trace Compass analysis engine (consumed via TSP REST API) and AI agent runtimes (served via MCP stdio). It fetches time-series data from TC state systems, applies scikit-learn / statsmodels algorithms, and returns structured results. It does not produce or store traces — it derives ML insights from them.

---

## Prerequisites

| Component | Version | Notes |
|-----------|---------|-------|
| Python | 3.8+ | Runtime |
| Trace Compass Server | 12.0.0 | TSP backend (headless, Java) |
| scikit-learn | ≥1.4.0 | Isolation Forest, LOF |
| statsmodels | ≥0.14.1 | ARIMA, seasonal decomposition |
| ruptures | 1.1.9 | Change point detection (PELT, BOCPD) |
| pandas | ≥2.2.0 | Time-series manipulation |
| scipy | ≥1.12.0 | Statistical tests |
| mcp | 1.27.0 | Model Context Protocol server |
| matplotlib | ≥3.8.0 | Visualization (optional) |

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        AI Agent / MCP Client                             │
│  (Kiro, Claude, any MCP-compatible agent)                               │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │ MCP stdio (JSON-RPC)
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         TMLL MCP Server                                  │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │  Tools:                                                            │  │
│  │  • ensure_server      • create_experiment   • list_outputs        │  │
│  │  • fetch_data         • detect_anomalies    • detect_memory_leak  │  │
│  │  • detect_changepoints • analyze_correlation                      │  │
│  │  • detect_idle_resources • plan_capacity                          │  │
│  │  • plot_xy_with_anomalies (MCP App UI)                            │  │
│  └──────────────────────────────┬────────────────────────────────────┘  │
│                                 │                                        │
│  ┌──────────────────────────────▼────────────────────────────────────┐  │
│  │                      TMLLClient                                    │  │
│  │  • Experiment lifecycle (create, list, delete)                     │  │
│  │  • Output discovery (find_outputs by keyword/type)                │  │
│  │  • Data fetch (XY time-series, tables, time graphs)               │  │
│  └──────────────────────────────┬────────────────────────────────────┘  │
│                                 │                                        │
│  ┌──────────────────────────────▼────────────────────────────────────┐  │
│  │                      ML Modules                                    │  │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────────────────┐  │  │
│  │  │ Anomaly      │ │ Change Point │ │ Root Cause Correlation   │  │  │
│  │  │ Detection    │ │ Detection    │ │ (Pearson, Granger)       │  │  │
│  │  │ (IForest,    │ │ (PELT,BOCPD, │ │                          │  │  │
│  │  │  LOF, Z-score│ │  voting,PCA) │ │                          │  │  │
│  │  └──────────────┘ └──────────────┘ └──────────────────────────┘  │  │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────────────────┐  │  │
│  │  │ Memory Leak  │ │ Idle Resource│ │ Capacity Planning        │  │  │
│  │  │ Detection    │ │ Detection    │ │ (forecasting)            │  │  │
│  │  └──────────────┘ └──────────────┘ └──────────────────────────┘  │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                   Instrumentation (self-tracing)                   │  │
│  │  • Python function-level tracing (call graph to file)             │  │
│  │  • LTTng kernel session management (optional)                     │  │
│  └───────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │ HTTP REST (TSP)
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│              Trace Compass Server (headless, Java)                        │
│  /tsp/api/traces  /experiments  /outputs  /xy  /states  /timegraph      │
└─────────────────────────────────────────────────────────────────────────┘
                                 ▲
                                 │ reads
┌─────────────────────────────────────────────────────────────────────────┐
│  Trace Files (CTF, ftrace, pcap, Chrome Trace JSON, etc.)               │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Instrumentation Walkthrough

### What Is Captured

| Signal | Content | Mechanism |
|--------|---------|-----------|
| ML analysis results | Anomaly timestamps, change points, correlations, forecasts | Returned as structured dicts/DataFrames |
| Self-instrumentation (Python) | Function call graph with timestamps | `sys.settrace` writing to instrumentation file |
| Self-instrumentation (kernel) | LTTng session covering TMLL execution | Subprocess calls to `lttng create/enable/start` |
| TSP data | XY time-series, state intervals, tree models | HTTP GET/POST to TC Server |

### Mechanism

1. **TSP Client**: Wraps the Trace Server Protocol REST API. Fetches experiment outputs as pandas DataFrames (XY series indexed by nanosecond timestamps).
2. **ML Modules**: Each module inherits `BaseModule` which handles data fetch, preprocessing (resampling, normalization, NaN handling), then applies a specific algorithm.
3. **MCP Server**: Uses `FastMCP` to expose each ML module as a tool. Agent sends tool call → MCP server invokes CLI subprocess or direct Python call → returns JSON/PNG.
4. **Instrumentation Service**: Optional self-tracing via `sys.settrace` (Python-level) and LTTng (kernel-level) to profile TMLL's own execution using the same TC infrastructure it analyzes.

### Data Format Produced

- **MCP responses**: JSON (anomaly lists, correlation matrices, change point indices) or PNG images
- **Programmatic API**: pandas DataFrames, Python dicts with typed fields
- **Instrumentation output**: Text trace file (Python calls) or CTF (LTTng kernel session)

---

## Sample Trace Output

### MCP Tool Response (detect_anomalies)

```json
{
  "summary": "Found 12 anomalies across 3 outputs using 'iforest'.",
  "method": "iforest",
  "series": {
    "CPU Usage [cpu/0]": {
      "x": ["2026-06-29T10:00:00.000", "2026-06-29T10:00:00.100", "..."],
      "y": [23.4, 25.1, "..."],
      "anomaly_x": ["2026-06-29T10:05:32.400", "2026-06-29T10:05:32.500"],
      "anomaly_y": [98.7, 97.2],
      "periods": [["2026-06-29T10:05:32.300", "2026-06-29T10:05:32.600"]]
    }
  }
}
```

### Programmatic API (change point detection)

```python
from tmll.tmll_client import TMLLClient
from tmll.ml.modules.performance_trend.change_point_module import ChangePointDetection

client = TMLLClient(verbose=False)
experiment = client.create_experiment(
    traces=[{"path": "/traces/regression-test"}],
    experiment_name="deploy_comparison"
)
outputs = experiment.find_outputs(keyword=["cpu usage"], type=["xy"])
cpd = ChangePointDetection(client, experiment, outputs)
results = cpd.detect(method="pelt")
# results.change_points = {"CPU Usage": [1750878600000000000, 1750878900000000000]}
# results.segments = {"CPU Usage": [{"start": ..., "end": ..., "mean": 34.2}, ...]}
```

---

## Cost Profile

### Compute Overhead

| Operation | Typical Duration | Notes |
|-----------|-----------------|-------|
| TSP data fetch (1M points) | 2–10s | Network + JSON deserialization |
| Anomaly detection (Isolation Forest, 100K points) | 1–5s | scikit-learn model fit + predict |
| Change point detection (PELT, 100K points) | 0.5–3s | ruptures library |
| Correlation analysis (10 series) | <1s | pandas/scipy |
| Capacity planning (forecast 100 steps) | 2–8s | statsmodels ARIMA fit |
| MCP tool call overhead | 50–200ms | Subprocess spawn + JSON serialize |

### Storage

| Artifact | Size |
|----------|------|
| TMLL Python package | ~500 KB |
| Dependencies (venv) | ~300 MB |
| Self-instrumentation trace | 1–10 MB per session |
| ML model state | In-memory only; not persisted |

### No LLM Token Cost

TMLL uses traditional ML (scikit-learn, statsmodels) — no LLM inference, no token consumption. Cost is purely compute.

---

## Validation Criteria

### Functional Verification

1. **TSP connectivity**: `TMLLClient(verbose=True)` → "Connected to TSP server" message
2. **Experiment creation**: `client.create_experiment(traces=[...])` → experiment UUID returned
3. **Anomaly detection**: Run on known-anomalous trace → anomalies detected at expected timestamps
4. **MCP server responds**: `echo '{"jsonrpc":"2.0","method":"tools/list","id":1}' | python -m tmll.mcp.server` → tool list returned

### Smoke Test

```bash
# Start Trace Compass Server
./tracecompass-server -vmargs -Dtraceserver.port=8080 &

# Run TMLL CLI
python -m tmll.mcp.cli create /path/to/kernel-trace -n "test"
python -m tmll.mcp.cli anomaly <UUID> -k "cpu usage" -m iforest

# Expected: JSON output with anomaly_x/anomaly_y arrays
```

---

## Limitations / Out of Scope

| Area | Status | Notes |
|------|--------|-------|
| Real-time / streaming ML | Not supported | Batch analysis only; requires complete trace |
| Deep learning | Not used | Classical ML only (IForest, PELT, ARIMA); no neural networks |
| Model persistence | Not implemented | Models are fit per-invocation; no saved model reuse |
| Multi-user / auth | Not supported | Single-user library; no access control |
| GPU-accelerated ML | Not used | CPU-only scikit-learn/statsmodels |
| Custom trace formats | Requires TC support | TMLL cannot parse traces directly; depends on TC server |
| Distributed analysis | Not supported | Single-process; no Spark/Dask integration |
| Labelled training data | Not required | All methods are unsupervised or statistical |

---

## Evaluation Assessment

### Observability

**Rating: Moderate**

**Strengths:**
- Self-instrumentation module can trace TMLL's own execution at Python function level and kernel level (LTTng)
- All ML results are structured and machine-readable (JSON/DataFrames)
- MCP tool annotations mark read-only vs destructive operations
- Verbose logging via loguru with structured output

**Gaps:**
- No metrics export (no Prometheus/OTel metrics on analysis duration, error rates)
- No distributed tracing — MCP calls are not correlated with TSP requests via trace context
- Self-instrumentation is optional and off by default
- No health endpoint for the MCP server itself

**Implementations would need to add:**
- OTel span emission for each ML analysis (correlating with TSP server spans)
- Prometheus metrics on analysis invocation count, duration, error rate
- MCP server health/readiness signal

---

### Security

**Rating: Minimal**

**Strengths:**
- MCP server communicates via stdio (no network exposure by default)
- Trace data stays local (TSP server is typically localhost)
- No credentials stored in code; TSP server requires no auth by default

**Gaps:**
- No authentication on TSP communication (plain HTTP)
- No input validation on trace paths (potential path traversal via MCP tool arguments)
- Subprocess invocation of CLI without argument sanitization
- No encryption of data in transit (HTTP to TSP server)
- Dependencies include broad scientific packages with large attack surfaces

**Implementations would need to add:**
- TSP client TLS support
- Input path validation and sandboxing
- Dependency pinning with hash verification
- MCP argument schema validation beyond type checking

---

### Identity Management

**Rating: None**

**Strengths:**
- (None — single-user library with no identity model)

**Gaps:**
- No user identity; operates as the OS process owner
- No attribution of which agent/user requested which analysis
- No session linking between MCP calls and TSP experiments
- No audit trail of analyses performed

**Implementations would need to add:**
- Caller identity propagation from MCP client metadata
- Analysis audit log (who ran what, when, on which experiment)
- Experiment ownership model if multi-user TSP is introduced

---

### Reliability

**Rating: Partial**

**Strengths:**
- TSP health check on client initialization (fails fast if server unreachable)
- Auto-install of Trace Compass Server if not running (`ensure_server` tool)
- Graceful error handling in MCP tools (errors returned as JSON, not crashes)
- CLI subprocess timeout (120s) prevents hung analyses

**Gaps:**
- No retry logic on TSP HTTP failures
- No checkpointing of long-running analyses (crash = restart from zero)
- MCP server is single-threaded; concurrent tool calls queue
- No backpressure if TSP server is overloaded
- No deduplication of repeated identical analysis requests

**Implementations would need to add:**
- HTTP retry with exponential backoff for TSP calls
- Analysis result caching (same experiment + same params = cached result)
- Async/concurrent MCP tool handling
- Circuit breaker for TSP server connectivity

---

### Accuracy

**Rating: Moderate**

**Strengths:**
- Multiple anomaly detection methods available (IForest, LOF, Z-score, IQR, seasonality, frequency domain, combined voting)
- Change point detection uses proven algorithms (PELT with BIC penalty)
- Correlation analysis offers multiple methods (Pearson, Spearman, Kendall, Granger causality)
- Data preprocessing handles NaN, resampling, normalization before ML application
- Statistical tests (not just thresholds) for memory leak detection

**Gaps:**
- No ground-truth validation — anomaly detection accuracy is not benchmarked against labeled datasets
- Hyperparameters (contamination ratio, penalty values) use defaults without per-trace tuning
- No confidence scores on anomaly predictions (binary anomaly/not-anomaly)
- Resampling frequency selection is heuristic, not adaptive
- No ensemble calibration — combined method is simple voting, not calibrated probability

**Implementations would need to add:**
- Confidence/probability scores per anomaly
- Adaptive hyperparameter selection based on trace characteristics
- Benchmark suite with labeled anomaly traces for precision/recall measurement
- Ensemble calibration (Platt scaling or isotonic regression)

---

## Summary

| Dimension | Rating | Key Gap |
|-----------|--------|---------|
| Observability | Moderate | No OTel/metrics export; no distributed trace correlation |
| Security | Minimal | No auth; plain HTTP to TSP; no input sanitization |
| Identity | None | No user/session identity model |
| Reliability | Partial | No retry logic; single-threaded MCP; no result caching |
| Accuracy | Moderate | No confidence scores; no ground-truth benchmarking |
