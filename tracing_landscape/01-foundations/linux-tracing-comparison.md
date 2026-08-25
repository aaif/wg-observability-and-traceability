# AAIF Aggregate Assessment: Linux Kernel Tracing Technologies

| Field | Value |
|-------|-------|
| **Subject** | LTTng / perf / FTrace — comparative assessment |
| **Date** | 2026-06-25 |

---

## Objective

Comparative analysis of the three primary Linux kernel tracing frameworks — LTTng, perf, and FTrace — evaluated through AAIF dimensions to identify which technology is strongest in each area and where architectural gaps persist across all three.

---

## Technology Overview

| Attribute | LTTng (kernel + UST) | perf (perf_events) | FTrace |
|-----------|---------------------|-------------------|--------|
| **First released** | 2006 (LTTng 2.0: 2012) | 2009 (Linux 2.6.31) | 2008 (Linux 2.6.27) |
| **Maintained by** | EfficiOS Inc. | Kernel community (Arnaldo, Ingo, Peter) | Steven Rostedt |
| **Component model** | External modules + daemons | Built into kernel + userspace tool | Built into kernel |
| **Install required** | Yes (lttng-modules, lttng-tools) | Userspace tool only (`linux-tools`) | Nothing (always available) |
| **Primary interface** | CLI (`lttng`) + C API | CLI (`perf`) + syscall API | Filesystem (tracefs) + trace-cmd |
| **Output format** | CTF (binary, standardized) | perf.data (binary, proprietary) | Text (tracefs) / .dat (trace-cmd) |
| **Userspace tracing** | Yes (LTTng-UST) | Yes (uprobes, USDT) | No (kernel only) |
| **Hardware counters** | Via context fields (perf PMU) | Primary strength | No |

---

## Architectural Comparison

### Data Path

```
                LTTng                    perf                      FTrace
                ─────                    ────                      ──────
Instrumentation:
  Kernel tracepoints ────────── Shared TRACE_EVENT() infrastructure ──────────
  + kprobes, syscalls          + PMU hardware events             + function entry/exit
  + LTTng-UST (userspace)      + uprobes, USDT                  (kernel only)

Ring Buffer:
  Per-CPU, lock-free           Per-event mmap'd ring buffer     Per-CPU, lock-free
  Kernel memory (splice out)   Shared with userspace (mmap)     Kernel memory (tracefs read)

Extraction:
  Consumer daemon (splice)     perf tool (mmap read)            cat trace_pipe / trace-cmd
  → CTF files on disk          → perf.data file                 → text stream / .dat file

Analysis:
  babeltrace2 / Trace Compass  perf report / perf script        trace output / KernelShark
```

### Overhead Comparison

| Scenario | LTTng | perf | FTrace |
|----------|-------|------|--------|
| Tracepoint disabled | ~0 ns | ~0 ns | 1–3 ns (static branch) |
| Tracepoint enabled | 50–150 ns | 100–300 ns | 40–100 ns |
| Function trace (disabled) | N/A | N/A | ~0.5 ns (NOP) |
| Function trace (enabled) | N/A | N/A | 10–20 ns |
| Hardware counting | N/A | ~0% CPU | N/A |
| Sampling @ 99 Hz | N/A | <0.1% CPU | N/A |
| Maximum event throughput | 10M+/sec/CPU | ~1M/sec (tracepoints) | 5–50M/sec |
| Zero-copy extraction | Yes (splice) | Partial (mmap) | No (text formatting) |

### Feature Matrix

| Feature | LTTng | perf | FTrace |
|---------|-------|------|--------|
| Kernel function tracing | ✗ | ✗ | ✓ (function/function_graph) |
| Hardware PMU counters | As context | ✓ (primary) | ✗ |
| Kernel tracepoints | ✓ | ✓ | ✓ |
| kprobes (dynamic) | ✓ | ✓ | Via tracefs |
| Syscall tracing | ✓ | ✓ (perf trace) | Via events |
| Userspace tracing | ✓ (LTTng-UST) | ✓ (uprobes/USDT) | ✗ |
| Sampling/profiling | ✗ | ✓ (primary) | ✗ |
| Live streaming | ✓ (relayd) | ✗ | ✓ (trace_pipe) |
| Flight recorder (snapshot) | ✓ | ✗ | ✓ (overwrite mode) |
| Latency measurement | ✗ | perf sched | ✓ (irqsoff, wakeup) |
| In-kernel aggregation | ✗ | ✗ | ✓ (histograms) |
| Multiple concurrent sessions | ✓ (sessions) | ✓ (multiple events) | ✓ (instances) |
| Binary structured output | ✓ (CTF) | ✓ (perf.data) | ✗ (text default) |
| Standardized format | ✓ (CTF spec) | ✗ (proprietary) | ✗ |
| Non-root operation | ✓ (UST only) | Partial (perf_event_paranoid) | ✗ |
| Trigger/automation | ✓ (trigger framework) | ✗ | ✓ (event triggers) |
| Call graph visualization | ✗ | ✓ (flame graphs) | ✓ (function_graph) |
| GUI | Trace Compass | Hotspot/Firefox | KernelShark |
| CTF export | Native | ✓ (convert) | ✗ |

---

## AAIF Dimension Comparison

### Observability

| Technology | Rating | Strengths | Key Gap |
|------------|--------|-----------|---------|
| **LTTng** | **Strong** | Lowest-overhead structured tracing; live streaming; CTF format; correlate kernel + userspace | No metrics aggregation or alerting |
| **perf** | **Strong** | Hardware counter visibility; statistical profiling; flame graphs; source annotation | Offline processing only; no streaming |
| **FTrace** | **Strong** | Always available; function graph unique; latency tracers; in-kernel histograms | Text output; no remote viewing |

**Best for**: LTTng for structured event tracing at scale; perf for CPU profiling and hardware behavior; FTrace for kernel debugging and latency analysis.

### Security

| Technology | Rating | Strengths | Key Gap |
|------------|--------|-----------|---------|
| **LTTng** | **Partial** | Root required for kernel; tracing group delegation; consumer isolation | No encryption; no daemon authentication |
| **perf** | **Moderate** | 5-level paranoid sysctl; CAP_PERFMON capability; per-process scoping | perf.data unencrypted; Intel PT leaks control flow |
| **FTrace** | **Partial** | Root-only tracefs; kernel lockdown integration | All-or-nothing; no per-user access |

**Best for**: perf has the most granular privilege model (perf_event_paranoid + CAP_PERFMON). All three lack encryption and audit logging.

### Identity Management

| Technology | Rating | Strengths | Key Gap |
|------------|--------|-----------|---------|
| **LTTng** | **Minimal** | PID/TID/cgroup context; namespace-aware | No operator identity; no session binding |
| **perf** | **Minimal** | PID/TID/comm in samples; per-process scoping | No operator identity; no provenance |
| **FTrace** | **Minimal** | PID/process name; set_ftrace_pid scoping | No operator identity; no provenance |

**Best for**: None — all three operate at the PID/process level only. Identity management is a universal gap in Linux tracing infrastructure.

### Reliability

| Technology | Rating | Strengths | Key Gap |
|------------|--------|-----------|---------|
| **LTTng** | **Strong** | Lock-free; explicit discard counter; flight recorder; trigger framework | Session daemon SPOF |
| **perf** | **Moderate** | Hardware counters perfect; NMI non-maskable; event groups atomic | Sampling is statistical; ring buffer overflow |
| **FTrace** | **Strong** | In-kernel (no daemon to crash); works in degraded states; independent instances | Silent overflow; no persistent storage |

**Best for**: FTrace for reliability in adverse conditions (works even when system is failing); LTTng for production tracing with loss detection.

### Accuracy

| Technology | Rating | Strengths | Key Gap |
|------------|--------|-----------|---------|
| **LTTng** | **Strong** | Binary CTF preserves full fidelity; nanosecond TSC; events_discarded counter | Cross-CPU TSC skew on multi-socket |
| **perf** | **Strong** | Hardware counters exact; precise_ip for zero-skid; Intel PT exact | Sampling is statistical; multiplexing extrapolation |
| **FTrace** | **Strong** | Deterministic capture (no sampling); function_graph per-call timing | Observer effect distorts timing |

**Best for**: perf for hardware measurement accuracy (counting mode); LTTng for event data fidelity; FTrace for deterministic function-level tracing.

---

## Complementary Usage Patterns

These tools are not competitors but complementary layers:

| Use Case | Best Tool | Why |
|----------|-----------|-----|
| "Where is my CPU time going?" | perf (sampling) | Statistical profiling with flame graphs |
| "What happened in the kernel during this request?" | FTrace (function_graph) | Call graph with timing |
| "Capture all sched_switch events for 1 hour" | LTTng | Lowest overhead; CTF for structured analysis |
| "Worst-case interrupt latency?" | FTrace (irqsoff) | Built-in latency tracer |
| "Cache miss rate for this function?" | perf (stat/annotate) | Hardware PMU counters |
| "Always-on tracing in production?" | LTTng (flight recorder) | Snapshot mode; low overhead |
| "Quick kernel debug, no tools installed?" | FTrace (tracefs) | Always present; zero install |
| "Correlate kernel + app events?" | LTTng (kernel + UST) | Unified CTF timeline |
| "How many instructions per cycle?" | perf (stat) | Hardware counters only |
| "Distribution of scheduling latencies?" | FTrace (histograms) | In-kernel aggregation |

---

## Universal Gaps (None of the Three Address)

| Gap | Description |
|-----|-------------|
| **Distributed tracing** | No trace-id propagation across hosts or services |
| **Operator identity** | No binding between tracing session and authenticated user |
| **Encryption at rest** | All three store trace data in plaintext |
| **Encryption in transit** | No TLS/SSH built into any tool's streaming |
| **Alerting** | No real-time notification to external systems |
| **Metrics export** | No native Prometheus/OTel/StatsD export |
| **Container-native isolation** | tracefs/perf not namespaced; all are host-level |
| **AI/agent identity** | Not applicable (no AI concept) |
| **Schema evolution** | No versioned schema migration across tool updates |
| **Cross-tool correlation** | No standard for linking perf samples to LTTng events to ftrace graphs |

---

## Summary Rating Matrix

| Dimension | LTTng | perf | FTrace | Best In Class |
|-----------|-------|------|--------|---------------|
| Observability | Strong | Strong | Strong | Tie (different strengths) |
| Security | Partial | Moderate | Partial | perf (CAP_PERFMON granularity) |
| Identity | Minimal | Minimal | Minimal | Tie (all PID-level only) |
| Reliability | Strong | Moderate | Strong | FTrace (no daemon dependency) |
| Accuracy | Strong | Strong | Strong | perf (hardware counters exact) |

---

## Recommendation

For comprehensive Linux observability, use all three:
1. **perf** for CPU profiling and hardware performance analysis
2. **LTTng** for production event tracing with structured output
3. **FTrace** for kernel debugging, latency analysis, and zero-install troubleshooting

The primary gap across all three is the **identity and security layer** — none provide encryption, operator authentication, or audit trails. Organizations deploying these in multi-tenant or regulated environments must layer additional controls (filesystem encryption, SSH tunneling, audit frameworks) on top.
