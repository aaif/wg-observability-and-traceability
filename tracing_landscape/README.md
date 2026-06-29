# AAIF Reference Architecture Assessments

Structured assessments of observability, tracing, and profiling technologies — evaluated through the lens of AI agent infrastructure. The documents build from foundational concepts upward to agent-level observability.

## Narrative Structure

The collection follows a bottom-up path through the observability stack: from how bits are encoded on disk, through kernel and hardware instrumentation, up to how AI agents expose their behavior to operators.

```
┌─────────────────────────────────────────────────────────┐
│  05  AI Agent Observability                             │  ← What agents emit
│      Agent runtimes, LLM tracing platforms,             │
│      product analytics                                  │
├─────────────────────────────────────────────────────────┤
│  04  Network                                            │  ← What's on the wire
│      Protocol analysis, packet capture                  │
├─────────────────────────────────────────────────────────┤
│  03  Hardware Accelerators                              │  ← What GPUs do
│      GPU kernel profiling, tensor core utilization,     │
│      framework-to-hardware correlation                  │
├─────────────────────────────────────────────────────────┤
│  02  Kernel Tracing                                     │  ← What the OS does
│      Function tracing, performance counters,            │
│      driver instrumentation                             │
├─────────────────────────────────────────────────────────┤
│  01  Foundations                                        │  ← How traces are encoded
│      Binary formats, comparative frameworks             │
└─────────────────────────────────────────────────────────┘
```

## Documents

### 01 — Foundations

The encoding and comparative context that all tracing systems build upon.

| Document | Subject | Key Insight |
|----------|---------|-------------|
| [ctf.md](01-foundations/ctf.md) | Common Trace Format | Self-describing binary format for zero-copy, nanosecond-precision traces |
| [linux-tracing-comparison.md](01-foundations/linux-tracing-comparison.md) | LTTng vs perf vs FTrace | Comparative assessment across AAIF dimensions; each excels differently |

### 02 — Kernel Tracing

How the Linux kernel exposes its behavior — the mechanisms that make OS-level observability possible.

| Document | Subject | Key Insight |
|----------|---------|-------------|
| [ftrace.md](02-kernel-tracing/ftrace.md) | FTrace | Always-available kernel function tracer; zero-overhead when disabled via NOP patching |
| [perf.md](02-kernel-tracing/perf.md) | Linux perf | Hardware PMU-driven profiling; statistical sampling with configurable overhead |
| [lttng-kernel-tracing.md](02-kernel-tracing/lttng-kernel-tracing.md) | LTTng (kernel) | Lock-free per-CPU ring buffers producing CTF; designed for always-on production use |
| [lttng-ust.md](02-kernel-tracing/lttng-ust.md) | LTTng-UST | Userspace tracing with no kernel transition on fast path; shared-memory ring buffers |
| [driver-tracing.md](02-kernel-tracing/driver-tracing.md) | Linux Driver Tracing | Layered driver observability: dev_dbg, dynamic debug, tracepoints, bus tracers |
| [linux-driver-tracing.md](02-kernel-tracing/linux-driver-tracing.md) | Linux Driver Tracing (extended) | Complete mechanism catalog for driver debugging and observation |

### 03 — Hardware Accelerators

How GPU hardware and AI frameworks expose tensor operations, memory transfers, and kernel execution.

| Document | Subject | Key Insight |
|----------|---------|-------------|
| [gpu-ai-tracing.md](03-hardware-accelerators/gpu-ai-tracing.md) | GPU Driver Tracing (multi-vendor) | Cross-vendor view: NVIDIA CUPTI, AMD ROCm, Intel oneAPI tracing surfaces |
| [nvidia-nsight.md](03-hardware-accelerators/nvidia-nsight.md) | NVIDIA Nsight Systems/Compute | System-wide timeline + per-kernel hardware counters via CUPTI |
| [amd-rocprofiler.md](03-hardware-accelerators/amd-rocprofiler.md) | AMD roctracer/rocprofiler | Open-source GPU profiling: HIP/HSA API tracing, Matrix Core counters |
| [pytorch-profiler.md](03-hardware-accelerators/pytorch-profiler.md) | PyTorch Profiler | Framework-level: Python ops → ATen → GPU kernels; Chrome Trace output |

### 04 — Network

Wire-level observation of what goes between processes and machines.

| Document | Subject | Key Insight |
|----------|---------|-------------|
| [wireshark.md](04-network/wireshark.md) | Wireshark | Deep packet inspection with 3000+ protocol dissectors; privilege-separated capture |

### 05 — AI Agent Observability

How AI agents expose their runtime behavior — the application-level telemetry that rides on top of everything below.

| Document | Subject | Key Insight |
|----------|---------|-------------|
| [agent-trace.md](05-ai-agent-observability/agent-trace.md) | Agent Trace spec | Line-level code attribution: which AI model produced which code |
| [AAIF-REF-ARCH-GOOSE.md](05-ai-agent-observability/AAIF-REF-ARCH-GOOSE.md) | Goose (agent runtime) | Full agent framework: triple telemetry pipeline, security scanning, MCP extensions |
| [AAIF-REF-ARCH-LANGFUSE.md](05-ai-agent-observability/AAIF-REF-ARCH-LANGFUSE.md) | Langfuse | LLM tracing platform: hierarchical traces of agent execution with timing and metadata |
| [AAIF-REF-ARCH-POSTHOG.md](05-ai-agent-observability/AAIF-REF-ARCH-POSTHOG.md) | PostHog | Product analytics: adoption tracking with privacy-preserving event collection |

## Reading Order

**For the full narrative** (bottom-up): Start at 01, read sequentially. Each layer builds context for the next.

**For AI agent focus** (top-down): Start at 05 (Goose → Langfuse → PostHog → Agent Trace), then reference lower layers as needed for implementation context.

**For GPU/ML workload tracing**: Read 03 (PyTorch Profiler → GPU overview → vendor-specific), referencing 01/CTF for format details.

## Evaluation Dimensions

Every document assesses its subject across five dimensions:

| Dimension | What It Measures |
|-----------|-----------------|
| **Observability** | Can you observe the system? Metrics, logs, traces, self-monitoring |
| **Security** | Access control, integrity, encryption, tamper resistance |
| **Identity** | Human identity, AI identity, verification, session linking |
| **Reliability** | Delivery guarantees, failure modes, recovery, ordering |
| **Accuracy** | Correctness of captured data, validation, semantic precision |
