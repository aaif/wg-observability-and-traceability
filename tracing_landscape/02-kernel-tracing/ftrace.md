# AAIF Reference Architecture: FTrace

| Field | Value |
|-------|-------|
| **Subject** | [FTrace](https://www.kernel.org/doc/html/latest/trace/ftrace.html) |
| **Version** | Built into Linux kernel (since 2.6.27) |
| **Date** | 2026-06-25 |

---

## Objective

Demonstrates how FTrace provides kernel function tracing and event recording through a filesystem-based interface (tracefs), using dynamic NOP-to-call patching for zero-overhead-when-disabled instrumentation of every kernel function, with text-based output readable without specialized tools.

---

## Scope / Zoom Level

**System layer — kernel-internal tracing infrastructure.**

FTrace is built directly into the Linux kernel. It instruments kernel function entry/exit points and tracepoint events, writing to per-CPU ring buffers accessible through a virtual filesystem. It is the lowest-friction kernel tracing tool — always available on any Linux system without additional packages.

---

## Prerequisites

| Component | Version / Pinned | Notes |
|-----------|-----------------|-------|
| Linux kernel | ≥ 2.6.27 (4.7+ for histograms) | `CONFIG_FTRACE=y`, `CONFIG_FUNCTION_TRACER=y` |
| tracefs | Mounted | `/sys/kernel/tracing/` (or `/sys/kernel/debug/tracing/`) |
| Root / CAP_SYS_ADMIN | — | Required for all tracefs access |
| trace-cmd | 3.x (optional) | Userspace CLI wrapper |
| KernelShark | 2.x (optional) | Qt-based GUI visualization |
| GCC `-pg`/`-mfentry` | — | Used during kernel compilation for instrumentation sites |

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        Linux Kernel                                       │
│                                                                         │
│  ┌────────────────────────────────────────────────────────────────┐    │
│  │  Kernel Functions (compiled with -mfentry)                      │    │
│  │                                                                 │    │
│  │  func_A:                    func_B:                             │    │
│  │    [NOP/call ftrace_caller]   [NOP/call ftrace_caller]          │    │
│  │    <function body>            <function body>                    │    │
│  │    ret                        ret                               │    │
│  │                                                                 │    │
│  │  When disabled: 5-byte NOP (0f 1f 44 00 00)                    │    │
│  │  When enabled: call ftrace_caller (patched via text_poke_bp)    │    │
│  └─────────────────────────────────┬──────────────────────────────┘    │
│                                    │                                     │
│  ┌─────────────────────────────────▼──────────────────────────────┐    │
│  │  FTrace Core                                                    │    │
│  │                                                                 │    │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐     │    │
│  │  │   function   │  │ function_    │  │   Tracepoint     │     │    │
│  │  │   tracer     │  │ graph tracer │  │   Events         │     │    │
│  │  └──────┬───────┘  └──────┬───────┘  └────────┬─────────┘     │    │
│  │         └──────────────────┼────────────────────┘               │    │
│  │                            ▼                                    │    │
│  │  ┌──────────────────────────────────────────────────────┐      │    │
│  │  │  Per-CPU Ring Buffers (lock-free)                     │      │    │
│  │  │  CPU0: [page|page|page|...]  Default: 1408 KB/CPU    │      │    │
│  │  │  CPU1: [page|page|page|...]                          │      │    │
│  │  │  ...                                                  │      │    │
│  │  └──────────────────────────────────────────────────────┘      │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  Latency Tracers                                                 │   │
│  │  irqsoff | preemptoff | preemptirqsoff | wakeup | wakeup_rt     │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  Histogram / Trigger Engine (4.7+)                               │   │
│  │  hist:keys=<field>:vals=hitcount | stacktrace | snapshot         │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
┌────────────────────────────────────▼────────────────────────────────────┐
│              tracefs (/sys/kernel/tracing/)                               │
│                                                                         │
│  ┌────────────────────┐  ┌────────────────────┐  ┌─────────────────┐  │
│  │ current_tracer     │  │ trace / trace_pipe  │  │ events/         │  │
│  │ tracing_on         │  │ (text output)       │  │  sched/         │  │
│  │ set_ftrace_filter  │  │                     │  │  irq/           │  │
│  │ set_ftrace_pid     │  │                     │  │  block/         │  │
│  │ buffer_size_kb     │  │                     │  │  net/           │  │
│  └────────────────────┘  └────────────────────┘  └─────────────────┘  │
│                                                                         │
│  ┌────────────────────────────────────────────────────┐                │
│  │ instances/ (concurrent trace sessions)              │                │
│  │  ├── mytracer1/ (full tracefs subtree)             │                │
│  │  └── mytracer2/ (full tracefs subtree)             │                │
│  └────────────────────────────────────────────────────┘                │
└─────────────────────────────────┬───────────────────────────────────────┘
                                  │ read/write/poll
                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        Userspace                                          │
│                                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────────────────┐    │
│  │ cat/echo     │  │ trace-cmd    │  │ KernelShark (GUI)         │    │
│  │ (direct I/O) │  │ (.dat binary)│  │                           │    │
│  └──────────────┘  └──────────────┘  └───────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Instrumentation Walkthrough

### What is captured

| Tracer | Data Captured |
|--------|---------------|
| `function` | Every kernel function call: caller → callee, timestamp, CPU, PID |
| `function_graph` | Function entry + exit with duration, call depth, call graph structure |
| Tracepoint events | Structured event payloads (same as perf/LTTng: sched_switch fields, etc.) |
| `irqsoff` | Maximum duration with interrupts disabled; full stack trace at max |
| `preemptoff` | Maximum duration with preemption disabled |
| `wakeup` / `wakeup_rt` | Worst-case scheduling latency for highest-priority task |
| `hwlat` | Hardware-induced latency (SMI/NMI) |
| Histograms | Aggregated distributions keyed by event fields |

### The mechanism

1. **Dynamic patching**: At kernel compile time, GCC inserts `call __fentry__` (5 bytes) at every function prologue. At boot, `ftrace_init()` patches all sites to 5-byte NOPs via the `__mcount_loc` section table. **Zero overhead when disabled.**

2. **Enable path**: When tracing is enabled for specific functions (or all), the NOP is live-patched to `call ftrace_caller` using `text_poke_bp()` (breakpoint-mediated safe text patching). No stopping the system.

3. **Trampoline execution**: `ftrace_caller` saves registers, invokes registered `ftrace_ops` callbacks (function tracer, kprobes, live-patching, BPF), restores registers, returns to original function.

4. **Ring buffer write**: The callback writes a record to the current CPU's ring buffer. Lock-free: no contention between CPUs.

5. **Tracepoint events**: Use the `TRACE_EVENT()` macro infrastructure (shared with perf and LTTng). Enabled per-event via `events/<subsys>/<event>/enable`.

6. **Reading**: `cat trace` reads a snapshot; `cat trace_pipe` streams (consuming entries). Both produce human-readable text.

### Data format produced

**Text** (primary) — human-readable directly from tracefs:

```
# tracer: function_graph
#
# CPU  DURATION                  FUNCTION CALLS
# |     |   |                     |   |   |   |
  0)               |  do_syscall_64() {
  0)               |    __x64_sys_write() {
  0)   0.123 us    |      down_write_trylock();
  0) + 15.789 us   |    }
  0) + 19.123 us   |  }
```

**Binary** (trace-cmd) — `.dat` format for efficient storage and GUI analysis.

---

## Sample Trace Output

### Function tracer

```
# tracer: function
#
#                                _-----=> irqs-off
#                               / _----=> need-resched
#                              | / _---=> hardirq/softirq
#                             || / _--=> preempt-depth
#                            ||| /     delay
#           TASK-PID    CPU#  ||||   TIMESTAMP  FUNCTION
#              | |       |   ||||      |         |
           nginx-4521   [002] ....  1234.567890: tcp_sendmsg <-sock_sendmsg
           nginx-4521   [002] ....  1234.567892: lock_sock_nested <-tcp_sendmsg
           nginx-4521   [002] ....  1234.567893: _raw_spin_lock_bh <-lock_sock_nested
           nginx-4521   [002] d..1  1234.567894: tcp_push <-tcp_sendmsg
```

### Function graph tracer

```
# tracer: function_graph
#
# CPU  DURATION                  FUNCTION CALLS
# |     |   |                     |   |   |   |
  2)               |  tcp_sendmsg() {
  2)               |    lock_sock_nested() {
  2)   0.089 us    |      _raw_spin_lock_bh();
  2)   0.456 us    |    }
  2)               |    tcp_push() {
  2)               |      __tcp_push_pending_frames() {
  2)               |        tcp_write_xmit() {
  2)   0.234 us    |          tcp_transmit_skb();
  2) + 12.345 us   |        }
  2) + 13.012 us   |      }
  2) + 13.456 us   |    }
  2)   0.067 us    |    release_sock();
  2) + 15.234 us   |  }
```

### Tracepoint events

```
           nginx-4521   [002] d..2  1234.567890: sched_switch: prev_comm=nginx prev_pid=4521 prev_prio=120 prev_state=S ==> next_comm=kworker/2:1 next_pid=187 next_prio=120
     kworker/2:1-187    [002] ....  1234.567920: sched_wakeup: comm=nginx pid=4522 prio=120 target_cpu=003
```

### Histogram output

```
# cat /sys/kernel/tracing/events/sched/sched_switch/hist
# event histogram
#
# trigger info: hist:keys=next_comm:vals=hitcount:sort=hitcount.descending:size=2048 [active]
#

{ next_comm: nginx             } hitcount:      45231
{ next_comm: kworker/0:1       } hitcount:      12345
{ next_comm: postgres          } hitcount:       8901
{ next_comm: swapper/0         } hitcount:       6789
{ next_comm: bash              } hitcount:        234

Totals:
    Hits: 73500
    Entries: 5
    Dropped: 0
```

---

## Cost Profile

### LLM token cost

**Not applicable.** FTrace is a kernel tracing infrastructure with no AI/LLM component.

### Compute/IO overhead per operation

| Operation | Overhead | Notes |
|-----------|----------|-------|
| Function entry (disabled) | ~0.5 ns | Single 5-byte NOP in function prologue |
| Function entry (enabled) | 10–20 ns | Register save/restore + ring buffer write |
| Function graph (entry+exit) | 20–40 ns | Both entry and return instrumented |
| Tracepoint (disabled) | 1–3 ns | Static branch (jump label) |
| Tracepoint (enabled) | 40–100 ns | Event formatting + ring buffer write |
| Ring buffer write | 40–80 ns | Per-CPU, lock-free |
| `trace_pipe` read | ~0 per event | Consumes from ring buffer on demand |

**Throughput ceiling**: 5–50M events/sec depending on event size and CPU speed.

### Storage growth rate

| Mode | Output | Notes |
|------|--------|-------|
| `cat trace` | In-memory ring buffer | Fixed size (default 1408 KB/CPU) |
| `cat trace_pipe` | Streaming text | No persistent storage by default |
| `trace-cmd record` | Binary .dat file | 5–50 MB/min typical; compressed |
| Histograms | Fixed memory (2048 entries default) | No growth; aggregated in-place |

FTrace is unique in that its default mode uses **no disk I/O** — data stays in the kernel ring buffer until read. This makes it suitable for always-on flight-recorder usage.

---

## Validation Criteria

1. **tracefs mounted**: `mount | grep tracefs` shows `/sys/kernel/tracing`
2. **Tracers available**: `cat /sys/kernel/tracing/available_tracers` lists `function function_graph nop ...`
3. **Functions filterable**: `wc -l /sys/kernel/tracing/available_filter_functions` shows thousands of functions
4. **Function tracing works**: Enable function tracer, run workload, `cat trace` shows function entries
5. **Events available**: `ls /sys/kernel/tracing/events/` shows sched/, irq/, block/, net/, etc.
6. **Timestamps monotonic**: Within each CPU column, timestamps strictly increase
7. **Instances work**: `mkdir /sys/kernel/tracing/instances/test` succeeds; independent trace session

### Quick smoke test

```bash
# Function graph for tcp_sendmsg
cd /sys/kernel/tracing
echo function_graph > current_tracer
echo tcp_sendmsg > set_graph_function
echo 1 > tracing_on
curl -s http://localhost/ > /dev/null
echo 0 > tracing_on
head -30 trace
# Verify: call graph showing tcp_sendmsg with nested calls and durations

# Cleanup
echo nop > current_tracer
echo > set_graph_function
```

---

## Limitations / Out of Scope

| Item | Status |
|------|--------|
| Userspace tracing | Not supported (kernel functions only); use uprobes via perf |
| Structured binary output | Text only from tracefs; binary requires trace-cmd |
| Standardized format | .dat format is not formally specified; not CTF-compatible |
| Network streaming | Not built-in; trace-cmd has agent mode but limited |
| Unprivileged access | Not possible; root/CAP_SYS_ADMIN required |
| Container isolation | tracefs not namespaced; host-level only |
| Persistent storage | Ring buffer is in-memory; must actively read or use trace-cmd |
| Encryption / integrity | None |
| Source-level attribution | Function names only; no DWARF line-level info |
| Cross-host correlation | Not supported |
| Non-Linux platforms | Linux only |
| Real-time alerting | Triggers can stop tracing or snapshot; no external notification |
| BPF co-existence | BPF programs attach via fentry/fexit; shared infrastructure but separate interface |

---

## Evaluation Assessment

### Observability

**Rating: Strong**

| Aspect | Assessment |
|--------|------------|
| **Strengths** | Always available on every Linux system — zero install. Function graph tracer provides unique call-tree visualization with timing that no other tool matches. Latency tracers (irqsoff, preemptoff, wakeup) provide worst-case latency detection built into the kernel. Histograms enable lightweight in-kernel aggregation without data export. Multiple concurrent instances for different use cases. `trace_pipe` provides real-time streaming. |
| **Gaps** | Text output requires parsing for programmatic analysis. No built-in metrics export or dashboards. No remote viewing capability. No structured binary format from the filesystem interface. No correlation with userspace events. |
| **Implementations must add** | Structured export (trace-cmd provides partial answer), remote collection infrastructure, metrics derivation from histograms, userspace correlation. |

### Security

**Rating: Partial**

| Aspect | Assessment |
|--------|------------|
| **Strengths** | tracefs requires root/CAP_SYS_ADMIN — hard privilege boundary. Kernel lockdown mode can fully disable tracefs access. No network exposure by default. Function names only exposed with tracefs access (protects KASLR from unprivileged users). |
| **Gaps** | No granular access control within tracefs (all-or-nothing root access). Trace data contains full kernel function flows — sensitive for security analysis. No encryption of trace data. No audit log of tracing operations. In containers, any escape to host grants full tracing. tracefs permissions can be loosened dangerously (chmod). |
| **Implementations must add** | Fine-grained access control (per-instance permissions), trace data encryption, operation audit logging, container-aware access policy. |

### Identity Management

**Rating: Minimal**

| Aspect | Assessment |
|--------|------------|
| **Strengths** | PID/TID/process name in every trace entry. `set_ftrace_pid` can scope to specific processes. Instances can be informally "owned" by different tracing sessions. |
| **Gaps** | No concept of who initiated tracing. No operator identity binding. No service identity. No AI identity. No authentication of trace readers. Trace data does not carry provenance about who captured it. |
| **Implementations must add** | Operator identity (who enabled tracing), provenance metadata, trace session authentication. |

### Reliability

**Rating: Strong**

| Aspect | Assessment |
|--------|------------|
| **Strengths** | In-kernel ring buffer — no userspace daemon to crash. Zero external dependencies — works even in degraded system states. Per-CPU lock-free buffers — no contention, no deadlock risk. Overwrite mode keeps most recent data (flight recorder). Dynamic patching is safe (text_poke_bp uses breakpoint-mediated transition). Instances are independent — one failing trace session doesn't affect others. `tracing_on` provides instant kill switch. |
| **Gaps** | Ring buffer overflow loses oldest data silently (no discard counter in text output). No persistent storage by default — power loss means data loss. No redundancy. No delivery guarantees to external systems. trace-cmd agent mode is limited. |
| **Implementations must add** | Overflow notification/counting, persistent trace archiving, remote collection with delivery guarantees, ring buffer fullness monitoring. |

### Accuracy

**Rating: Strong**

| Aspect | Assessment |
|--------|------------|
| **Strengths** | Function tracer captures exact function entry (precise instrumentation point). function_graph provides per-call nanosecond timing. Timestamps from TSC — nanosecond precision. Latency tracers track exact preemption/IRQ disable durations. Histograms provide exact distribution counts. No sampling — deterministic capture of all matching events. |
| **Gaps** | Function tracer adds overhead that perturbs timing measurements (observer effect). function_graph overhead (~30ns) distorts short-function timings. Duration markers (`+`, `!`, `#`) lose precision (coarse bucketing). Text output formatting rounds timestamps. `set_ftrace_filter` glob matching may inadvertently include/exclude functions. |
| **Implementations must add** | Overhead compensation in timing measurements, binary output for full-precision timestamps, filter validation tooling. |

---

## Assessment Summary

| Dimension | Rating | Key Gap |
|-----------|--------|---------|
| Observability | Strong | Text-only output; no remote viewing or metrics export |
| Security | Partial | All-or-nothing root access; no encryption or audit trail |
| Identity | Minimal | PID-level only; no operator or session identity |
| Reliability | Strong | Ring buffer overflow is silent; no persistent storage |
| Accuracy | Strong | Observer effect distorts timing of short functions |
