# AAIF Reference Architecture: Eclipse Trace Compass + Incubator

| Field | Value |
|-------|-------|
| **Subject** | [Eclipse Trace Compass](https://eclipse.dev/tracecompass/) + [Incubator](https://github.com/eclipse-tracecompass-incubator/org.eclipse.tracecompass.incubator) |
| **Version** | 12.0.0 (June 2026) |
| **Date** | 2026-06-29 |

---

## Objective

Reference architecture for Eclipse Trace Compass, a multi-format trace analysis framework that correlates kernel, userspace, GPU, network, and AI framework traces through a unified state-system engine — enabling cross-layer performance analysis from hardware counters to PyTorch operator timelines.

---

## Scope / Zoom Level

**Analysis framework — spans all instrumentation layers.** Trace Compass is not a trace producer; it is the offline analysis and visualization engine that consumes traces from every layer in the AAIF stack (CTF/LTTng, ftrace, perf, pcap, Chrome Trace/PyTorch, GPU tracepoints). It correlates events across these sources using a disk-backed state system (interval tree) and presents unified timeline views. The Incubator extends this with experimental analyses (GPU, virtual machine, perf data) and the Trace Server Protocol (TSP) for headless/remote operation.

---

## Prerequisites

| Component | Version | Notes |
|-----------|---------|-------|
| Eclipse IDE | 2024-03+ | Eclipse RCP platform |
| Java | 17+ | Runtime for TC core |
| Trace Compass | 12.0.0 | Stable release (June 2026) |
| Trace Compass Incubator | HEAD | Experimental analyses |

### Supported Trace Inputs

| Format | Source | Status |
|--------|--------|--------|
| CTF | LTTng kernel/UST traces | Stable — native parser |
| ftrace | Linux kernel function/event tracing | Stable — text and raw binary |
| BTF | Best Trace Format (automotive) | Stable |
| pcap / pcapng | Network packet captures (tcpdump, Wireshark) | Stable |
| Chrome Trace JSON | Chrome DevTools, PyTorch Profiler, Perfetto | Stable |
| GDB tracepoints | GDB remote trace files | Stable |
| perf.data | Linux perf record output | PR in progress (Incubator) |
| GPU tracepoints | i915/amdgpu via ftrace | Incubator — experimental |

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Trace Sources (Producers)                             │
│                                                                             │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────────────┐  │
│  │ LTTng    │ │ ftrace   │ │ perf     │ │ pcap/    │ │ Chrome Trace   │  │
│  │ (CTF)    │ │ (text/   │ │ (perf.   │ │ pcapng   │ │ (JSON)         │  │
│  │          │ │  binary) │ │  data)   │ │          │ │ PyTorch/Chrome │  │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘ └───────┬────────┘  │
│       │             │            │             │               │            │
└───────┼─────────────┼────────────┼─────────────┼───────────────┼────────────┘
        │             │            │             │               │
        ▼             ▼            ▼             ▼               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    Trace Compass Core (Java / Eclipse RCP)                    │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                         Trace Type Registry                            │  │
│  │  CTF Parser │ Ftrace Parser │ Pcap Parser │ Chrome JSON │ BTF │ GDB   │  │
│  │             │               │ [perf: PR]  │   Parser    │     │       │  │
│  └──────────────────────────────────┬────────────────────────────────────┘  │
│                                     │ ITmfEvent stream                       │
│  ┌──────────────────────────────────▼────────────────────────────────────┐  │
│  │                      Analysis Engine                                   │  │
│  │                                                                        │  │
│  │  ┌─────────────────┐  ┌──────────────────┐  ┌─────────────────────┐  │  │
│  │  │ State System    │  │ Event Matching   │  │ Statistics          │  │  │
│  │  │ (Interval Tree  │  │ (request/reply   │  │ (per-event-type    │  │  │
│  │  │  on disk, HT)   │  │  correlation)    │  │  aggregation)      │  │  │
│  │  └────────┬────────┘  └────────┬─────────┘  └──────────┬──────────┘  │  │
│  │           │                    │                        │             │  │
│  │  ┌────────▼────────────────────▼────────────────────────▼──────────┐  │  │
│  │  │              Built-in Analyses                                   │  │  │
│  │  │  • OS Execution (sched_switch → thread states)                  │  │  │
│  │  │  • Syscall Latency                                              │  │  │
│  │  │  • IRQ/SoftIRQ Analysis                                         │  │  │
│  │  │  • Critical Path                                                │  │  │
│  │  │  • Memory Usage                                                 │  │  │
│  │  │  • Network Latency (pcap correlation)                           │  │  │
│  │  └────────────────────────────────────────────────────────────────┘  │  │
│  │                                                                        │  │
│  │  ┌────────────────────────────────────────────────────────────────┐  │  │
│  │  │         Incubator Analyses (Experimental)                       │  │  │
│  │  │  • GPU Analysis (i915/amdgpu ftrace tracepoints)               │  │  │
│  │  │  • Virtual Machine Analysis (KVM entry/exit correlation)       │  │  │
│  │  │  • perf.data Import [PR in progress]                           │  │  │
│  │  │  • Flame Chart / Flame Graph (call stack profiling)            │  │  │
│  │  │  • Chrome Trace correlation (PyTorch op→kernel mapping)        │  │  │
│  │  └────────────────────────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                      Presentation Layer                                │  │
│  │  ┌───────────┐ ┌──────────┐ ┌───────────┐ ┌──────────┐ ┌─────────┐  │  │
│  │  │ Timeline  │ │Histogram │ │ Flame     │ │Statistics│ │Critical │  │  │
│  │  │ (Gantt)   │ │          │ │ Chart/    │ │ Table    │ │ Path    │  │  │
│  │  │           │ │          │ │ Graph     │ │          │ │         │  │  │
│  │  └───────────┘ └──────────┘ └───────────┘ └──────────┘ └─────────┘  │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │              Trace Server Protocol (TSP) — Incubator                   │  │
│  │  REST API (JSON over HTTP) exposing:                                   │  │
│  │  • /traces — open/list traces                                         │  │
│  │  • /experiments — correlate multiple traces                           │  │
│  │  • /outputs — query analysis results (time graphs, XY, tables)       │  │
│  │  • /states — state system interval queries                            │  │
│  │  Clients: Theia (web), VS Code extension, custom                     │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Instrumentation Walkthrough

### What Is Captured

Trace Compass itself captures nothing — it analyzes. The instrumentation walkthrough describes what the analysis engine *derives* from raw trace input:

| Derived Signal | Mechanism | Source Format |
|----------------|-----------|---------------|
| Thread state timeline | `sched_switch`/`sched_wakeup` events → state machine | CTF (LTTng), ftrace |
| Syscall latency distribution | Entry/exit event matching | CTF, ftrace |
| IRQ handler duration | `irq_handler_entry`/`exit` pairing | CTF, ftrace |
| Critical path | Blocking dependency graph (wait-for analysis) | CTF (requires kernel + UST) |
| Network round-trip time | pcap timestamp correlation with kernel send/recv | pcap + CTF |
| GPU command latency | `i915_request_submit`→`i915_request_retire` matching | ftrace (i915 tracepoints) |
| PyTorch op→GPU kernel | Chrome Trace `dur` events correlated by tid/timestamp | Chrome Trace JSON |
| Flame graph | Sampled or instrumented call stacks aggregated | perf.data [PR], ftrace function_graph |
| VM guest/host correlation | `kvm_entry`/`kvm_exit` matched to guest traces | CTF (host) + CTF (guest) |

### The Mechanism: State System

The state system is TC's core data structure — a disk-backed **History Tree** (segmented interval tree stored as an append-only file):

1. **Build phase**: Events stream in time-order. Each analysis module maintains an `ITmfStateSystemBuilder` that maps events to state changes (e.g., "CPU 3 transitions to thread 1842 at timestamp T").
2. **Storage**: State intervals `[start, end, attribute, value]` are packed into tree nodes on disk. The tree structure enables O(log n) point queries ("what was the state of CPU 3 at time T?").
3. **Query phase**: Views issue `querySingleState(time, attribute)` or range queries. The HT backend serves these from memory-mapped file pages without loading the entire trace.

### Data Format Produced

TC does not produce a standardized output format. Results are:
- **Internal**: State system `.ht` files (proprietary binary, per-analysis)
- **Visual**: Rendered in SWT/Draw2d timeline widgets
- **TSP**: JSON responses over HTTP when using Trace Server Protocol
- **Export**: CSV/TSV export from statistics views; screenshot export from timelines

---

## Experiments and Trace Sets

An **experiment** in Trace Compass is a synchronized collection of traces from different sources that are analyzed as a single correlated dataset. This is the mechanism that elevates TC from a single-format viewer to a cross-layer analysis platform.

### Composition Model

```
┌─────────────────────────────────────────────────────────────┐
│  Experiment: "ML Training Debug Session"                     │
│                                                             │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────────┐  │
│  │ LTTng CTF   │  │ ftrace       │  │ Chrome Trace JSON  │  │
│  │ (kernel     │  │ (GPU i915    │  │ (PyTorch Profiler  │  │
│  │  sched +    │  │  tracepoints)│  │  operator timeline)│  │
│  │  net events)│  │              │  │                    │  │
│  └──────┬──────┘  └──────┬───────┘  └─────────┬─────────┘  │
│         │                │                     │            │
│         └────────────────┼─────────────────────┘            │
│                          ▼                                   │
│              ┌───────────────────────┐                       │
│              │  Time Synchronization │                       │
│              │  (offset + drift)     │                       │
│              └───────────┬───────────┘                       │
│                          ▼                                   │
│              Unified State System + Views                    │
└─────────────────────────────────────────────────────────────┘
```

Multiple traces contribute complementary views of the same time window:

| Trace Source | Contributes | Combined Insight |
|-------------|-------------|-----------------|
| LTTng kernel | CPU scheduling, syscalls, network stack | Which threads ran where, why they blocked |
| ftrace GPU tracepoints | GPU command submission/completion | GPU pipeline utilization alongside CPU activity |
| Chrome Trace (PyTorch) | Framework-level operator names, durations | Maps high-level `torch.nn.Linear` to underlying GPU kernel dispatch |
| pcap | Wire-level packet timing | Correlates network latency with kernel `tcp_sendmsg` tracepoints |
| perf.data [PR] | Hardware PMU samples (IPC, cache misses) | Statistical CPU microarchitecture view overlaid on deterministic events |

### Time Synchronization and Convex Hull

Traces from different machines or clock domains require **time correlation**. TC implements two approaches:

**1. Direct Offset (single-machine, multi-source)**

When traces originate from the same host (e.g., LTTng kernel + ftrace + Chrome Trace), they share a common `CLOCK_MONOTONIC` base. TC applies a simple constant offset if clock sources differ (e.g., TSC vs HPET).

**2. Convex Hull Algorithm (distributed / cloud analysis)**

For traces captured on different machines — the critical case for cloud and distributed AI workloads — TC uses the **convex hull** synchronization algorithm:

- Network events visible in both traces (e.g., TCP SYN seen in sender's trace and receiver's pcap) establish **timestamp pairs** `(t_local, t_remote)`.
- The convex hull of these pairs defines the tightest linear bounds on clock relationship: `t_remote = α·t_local + β` (drift + offset).
- The upper and lower hulls bound the uncertainty: any event's true time lies within the hull envelope.
- TC computes the **best-fit line** through the hull midpoints, applying this as the transform for all events in the remote trace.

This enables:
- **Multi-node AI training analysis**: Correlate `AllReduce` communication events across GPU nodes with per-node kernel scheduling
- **Microservice latency attribution**: Match an HTTP request's departure (sender pcap) to its arrival (receiver LTTng) with bounded clock error
- **Host-guest VM correlation**: Synchronize a KVM host's `kvm_exit` events with the guest kernel's trap handler entry, even when guest TSC is offset

### AAIF Relevance: Cross-Layer AI Workload Analysis

A single experiment combining:
1. **PyTorch Chrome Trace** → operator names and durations
2. **ftrace i915/amdgpu** → GPU command queue depth and completion
3. **LTTng kernel** → CPU scheduling, NUMA memory allocation, network I/O
4. **pcap** → parameter server communication latency (distributed training)

...produces a unified timeline showing exactly where time is spent: is the GPU starved because the data loader is blocked on I/O? Is `AllReduce` latency dominated by network or by kernel scheduling of the NCCL threads? Convex hull synchronization makes this analysis valid even across a multi-node training cluster.

---

## Sample Trace Output

### TSP Query Response (time graph model)

```json
{
  "model": {
    "rows": [
      {
        "id": 1,
        "parentId": -1,
        "labels": ["CPU 0"],
        "style": { "parentKey": "cpu" },
        "states": [
          {
            "start": 1750878545000000000,
            "end": 1750878545000450000,
            "value": 1842,
            "label": "python3",
            "style": { "key": "running" }
          },
          {
            "start": 1750878545000450000,
            "end": 1750878545000890000,
            "value": 0,
            "label": "swapper/0",
            "style": { "key": "idle" }
          }
        ]
      },
      {
        "id": 2,
        "parentId": -1,
        "labels": ["GPU i915 Ring 0"],
        "states": [
          {
            "start": 1750878545000100000,
            "end": 1750878545000750000,
            "label": "batch_matmul [ctx=42]",
            "style": { "key": "gpu_active" }
          }
        ]
      }
    ]
  },
  "status": "COMPLETED",
  "statusMessage": ""
}
```

### State System Query (programmatic)

```java
// Query what was running on CPU 0 at a specific time
int cpuQuark = ss.getQuarkAbsolute("CPUs", "0", "Current_thread");
ITmfStateInterval interval = ss.querySingleState(1750878545000200000L, cpuQuark);
// interval.getValue() → 1842 (pid of python3)
// interval.getStartTime() → 1750878545000000000
// interval.getEndTime()   → 1750878545000450000
```

---

## Cost Profile

### Compute/IO Overhead

| Operation | Cost | Notes |
|-----------|------|-------|
| Trace indexing (CTF, 1 GB) | 15–45s | Sequential read, builds packet index |
| State system build (kernel trace, 1M events) | 5–20s | CPU-bound; writes .ht file |
| State system disk usage | ~50–200 bytes/interval | History tree node overhead |
| Point query (single state) | <1ms | Memory-mapped B-tree traversal |
| Range query (10s window, 1000 intervals) | 5–50ms | Depends on tree depth |
| Experiment synchronization (convex hull) | 1–5s | Linear in number of sync events |
| Chrome Trace JSON parse (100 MB) | 10–30s | JSON deserialization overhead vs binary CTF |
| TSP REST response | 10–100ms | Depends on query complexity and time range |

### Storage Growth

| Artifact | Size Relative to Source |
|----------|----------------------|
| Packet index (.idx) | ~1–2% of CTF trace |
| State history (.ht) | 30–100% of source trace (depends on state density) |
| Supplementary files | 5–15% (statistics caches, bookmarks) |
| Experiment metadata | Negligible (<1 KB per trace in experiment) |

### No LLM Token Cost

Trace Compass is a deterministic analysis tool — no LLM inference, no token consumption.

---

## Validation Criteria

### Functional Verification

1. **Trace opens successfully**: File → Open Trace → select a CTF/ftrace/pcap directory → events appear in Events view
2. **State system builds**: Control Flow view populates with thread state timelines within seconds of opening a kernel trace
3. **Experiment correlation works**: Create experiment from LTTng kernel + Chrome Trace → both appear on same timeline with correct time alignment
4. **Convex hull sync**: Open two traces from different machines with overlapping network events → Synchronization view shows computed offset/drift with bounded uncertainty
5. **GPU analysis (Incubator)**: Open ftrace trace containing `i915_request_*` events → GPU view shows command submission/completion timeline

### Smoke Test

```bash
# Download sample LTTng kernel trace
wget https://archive.eclipse.org/tracecompass/test-traces/ctf/kernel/kernel-trace.tar.gz
tar xzf kernel-trace.tar.gz

# Launch Trace Compass (standalone RCP)
./tracecompass &

# Open trace: File → Open Trace → select extracted directory
# Verify: Events view shows sched_switch, sys_* events
# Verify: Control Flow view shows colored thread state bars
# Verify: Resources view shows per-CPU utilization

# TSP headless verification (if trace-server installed)
curl http://localhost:8080/tsp/api/traces \
  -X POST -H "Content-Type: application/json" \
  -d '{"parameters":{"uri":"/path/to/kernel-trace"}}'
# Expected: 200 OK with trace UUID and indexing status
```

---

## TMLL: ML-Enhanced Trace Analysis

[TMLL](https://github.com/eclipse-tracecompass/tmll) (Trace-Server Machine Learning Library) is a separate companion project that applies machine learning to Trace Compass analysis outputs via the Trace Server Protocol. It is not part of TC itself — it consumes TSP as a client and layers automated ML pipelines on top of TC's deterministic analysis results.

### Architecture Relationship

```
┌─────────────────────────────────────────────────────────┐
│  TMLL (Python)                                           │
│  ┌──────────────────────────────────────────────────┐   │
│  │  ML Modules                                       │   │
│  │  • Anomaly Detection (Isolation Forest, LOF)     │   │
│  │  • Memory Leak Detection (trend + heuristic)     │   │
│  │  • Change Point Detection (PELT, BOCPD)          │   │
│  │  • Root Cause Correlation (Pearson, Granger)     │   │
│  │  • Idle Resource Detection                       │   │
│  │  • Capacity Planning (forecasting)              │   │
│  └──────────────────────────┬───────────────────────┘   │
│                             │ fetch XY/state data        │
│  ┌──────────────────────────▼───────────────────────┐   │
│  │  TSP Client (Python)                              │   │
│  │  /traces, /experiments, /outputs, /xy, /states   │   │
│  └──────────────────────────┬───────────────────────┘   │
│                             │                            │
│  ┌──────────────────────────▼───────────────────────┐   │
│  │  MCP Server (stdio)                               │   │
│  │  Exposes ML analyses as MCP tools for AI agents  │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────┼───────────────────────────┘
                              │ HTTP (TSP REST API)
                              ▼
┌─────────────────────────────────────────────────────────┐
│  Trace Compass Server (Java, headless)                   │
│  State systems, analyses, experiments                    │
└─────────────────────────────────────────────────────────┘
```

### ML Modules

| Module | Technique | What It Detects |
|--------|-----------|-----------------|
| Anomaly Detection | Isolation Forest, LOF, Z-score | Unusual CPU/memory/disk patterns in time-series |
| Memory Leak Detection | Trend analysis + statistical heuristics | Monotonically growing allocations |
| Change Point Detection | PELT, BOCPD | Performance regime shifts (before/after deploy) |
| Root Cause Correlation | Pearson, Spearman, Granger causality | Which metrics co-vary with observed anomalies |
| Idle Resource Detection | Threshold + statistical classification | Underutilized CPUs, idle disk, wasted memory |
| Capacity Planning | Time-series forecasting | When resources will exhaust at current growth rate |

### MCP Integration

TMLL exposes its analyses as MCP (Model Context Protocol) tools, allowing AI agents to programmatically:
- Create experiments from trace files
- Fetch analysis data (CPU usage, memory, disk XY series)
- Run anomaly detection, correlation, change point analysis
- Plot results as interactive visualizations

This makes Trace Compass analysis accessible to LLM-based agents without requiring human interaction with the TC GUI — a direct bridge between the AAIF observability stack and AI agent workflows.

---

## Limitations / Out of Scope

| Area | Status | Notes |
|------|--------|-------|
| Live tracing | Partial | LTTng live session support exists but is limited; most analysis is post-mortem |
| Trace production | Not applicable | TC analyzes — it does not instrument or produce traces |
| perf.data ingestion | PR in progress | Not yet merged into Incubator mainline |
| NVIDIA CUPTI / ROCm traces | Not supported | GPU analysis limited to ftrace-exposed tracepoints (i915, amdgpu) |
| OpenTelemetry / OTLP | Not supported | No native OTel span ingestion; would require conversion to Chrome Trace |
| Distributed tracing (span graphs) | Supported (Incubator) | OpenTracing (pre-OTel) span ingestion and visualization via Incubator plugin |
| Real-time alerting | Not supported | Offline analysis tool; no streaming alert evaluation |
| ARM GPU (Mali) tracing | Not supported | No parser for Mali-specific trace formats |
| Windows ETW | Partial | Basic support exists but is not actively maintained |
| Cloud-native deployment | TSP only | Full GUI requires Eclipse RCP desktop; TSP enables headless but is experimental |

---

## Evaluation Assessment

### Observability

**Rating: Strong**

**Strengths:**
- Comprehensive multi-format ingestion: a single tool correlates kernel scheduling, GPU commands, network packets, and framework-level AI operations
- State system provides arbitrary point-in-time queries — "what was every CPU/thread/GPU doing at nanosecond T?"
- Experiment model enables cross-source correlation that no single-format tool can achieve
- Extensible analysis framework: custom analyses plug in via Eclipse extension points or XML-driven state machines
- TSP enables programmatic access to all analysis results without GUI dependency

**Gaps:**
- No self-observability — TC does not instrument its own analysis performance (build times, query latencies) for external consumption
- No streaming/live analysis pipeline for always-on monitoring
- Visualization is tightly coupled to Eclipse SWT; web frontends via TSP are still experimental
- No built-in mechanism to export derived state as OTel spans or metrics for downstream observability platforms

**Implementations would need to add:**
- OTel exporter for derived analysis results (e.g., detected latency anomalies as spans)
- Analysis performance metrics (state system build time, query response time)
- Streaming analysis mode for near-real-time use cases

---

### Security

**Rating: Minimal**

**Strengths:**
- Trace files are read-only inputs — TC never modifies source traces
- TSP server can be bound to localhost only, limiting network exposure
- Eclipse RCP inherits OS-level file permissions for trace access

**Gaps:**
- No authentication or authorization on TSP REST API
- No encryption of state system files on disk (derived data may contain sensitive kernel state)
- No access control model — anyone with filesystem access to traces can analyze them
- No audit log of who queried what analysis results
- Trace files themselves may contain sensitive data (syscall arguments, network payloads) with no redaction capability
- No integrity verification of trace files (a tampered trace produces silently wrong analysis)

**Implementations would need to add:**
- TSP authentication (OAuth2/mTLS) for multi-user deployments
- Trace file integrity verification (cryptographic signatures or checksums)
- Field-level redaction for sensitive event payloads
- Access control model mapping users to permitted trace sets

---

### Identity Management

**Rating: None**

**Strengths:**
- (None applicable — TC is a single-user desktop tool with no identity model)

**Gaps:**
- No user identity concept — operates as whichever OS user launches it
- No session identity beyond Eclipse workspace metadata
- No attribution of which analyst performed which queries or annotations
- TSP has no concept of authenticated principals
- Trace provenance is not tracked — no chain-of-custody for forensic use

**Implementations would need to add:**
- User authentication for TSP multi-user scenarios
- Trace provenance metadata (who captured, when, on what machine, chain of custody)
- Annotation attribution (which analyst marked which region of interest)

---

### Reliability

**Rating: Moderate**

**Strengths:**
- State system is crash-resilient: the History Tree is append-only with checkpoint nodes; a crashed build can be detected and rebuilt from the source trace
- Packet-based CTF indexing enables random access — corruption in one packet does not invalidate the entire trace
- Experiment model tolerates partial trace availability (missing traces degrade analysis but don't crash)
- `events_discarded` counter in CTF packets surfaces data loss from the producer transparently

**Gaps:**
- No redundancy — state system files are single-copy local disk; loss requires full rebuild
- Large traces (>10 GB) can exhaust Java heap if analysis modules are not memory-conscious
- TSP server has no HA mode, health checks, or graceful degradation under load
- No backpressure mechanism for TSP clients issuing expensive queries
- Convex hull synchronization degrades gracefully but provides no confidence interval to consumers — the uncertainty envelope is computed but not surfaced in query results

**Implementations would need to add:**
- TSP server clustering or at minimum health/readiness endpoints
- Query cost estimation and timeout/cancellation for expensive range queries
- Confidence metadata on synchronized timestamps exposed to analysis consumers
- Incremental state system update without full rebuild on trace append

---

### Accuracy

**Rating: Strong**

**Strengths:**
- Nanosecond timestamp precision preserved end-to-end from CTF/ftrace source through state system to view rendering
- Convex hull synchronization provides mathematically bounded clock uncertainty rather than hiding error
- State system is lossless for the analysis it models — every state transition in the source trace produces an interval
- Event matching (request/reply pairing) uses strict criteria (matching fields, ordering) preventing false correlations
- Statistics views compute exact distributions, not sampled approximations
- CTF parser validates packet checksums and magic numbers, rejecting corrupt data

**Gaps:**
- Convex hull accuracy depends on density of synchronization events — sparse network traffic produces wide uncertainty bounds
- Chrome Trace JSON timestamps are microsecond-precision (vs nanosecond for CTF), introducing quantization when correlating with kernel events
- perf.data import [PR] will introduce sampling-based data where accuracy is inherently statistical, not deterministic
- No validation that trace sources in an experiment actually cover the same time window — user error can produce meaningless correlations
- GPU tracepoint analysis trusts ftrace timestamps which may have clock source drift relative to CTF traces on the same machine

**Implementations would need to add:**
- Automatic overlap detection warning when experiment traces have disjoint time ranges
- Confidence annotations on correlated events from different clock domains
- Statistical accuracy metadata for sampling-based analyses (perf)

---

## Summary

| Dimension | Rating | Key Gap |
|-----------|--------|---------|
| Observability | Strong | No self-observability; no OTel export of derived analysis |
| Security | Minimal | No auth on TSP; no trace integrity verification; no redaction |
| Identity | None | No user/session identity model whatsoever |
| Reliability | Moderate | Single-copy state files; no TSP HA; no query backpressure |
| Accuracy | Strong | Microsecond Chrome Trace quantization; convex hull depends on sync event density |
