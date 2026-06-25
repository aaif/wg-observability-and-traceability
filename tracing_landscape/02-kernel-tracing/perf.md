# AAIF Reference Architecture: Linux perf

| Field | Value |
|-------|-------|
| **Subject** | [perf (perf_events)](https://perf.wiki.kernel.org/) |
| **Version** | 6.8+ (tracks kernel version) |
| **Date** | 2026-06-25 |

---

## Objective

Demonstrates how Linux perf provides hardware-assisted performance profiling and tracing through the perf_events kernel subsystem, enabling sampling-based CPU profiling, hardware counter measurement, tracepoint tracing, and dynamic instrumentation with configurable overhead from near-zero (counting mode) to moderate (high-frequency sampling).

---

## Scope / Zoom Level

**System layer — hardware PMU through kernel subsystem to userspace analysis.**

perf spans from CPU hardware (Performance Monitoring Units) through the kernel's perf_events subsystem to userspace tools. It profiles entire systems, specific processes, or individual CPUs. It operates at a lower level than application tracing — observing hardware behavior (cache misses, branch mispredictions, cycles) alongside kernel tracepoints and dynamic probes.

---

## Prerequisites

| Component | Version / Pinned | Notes |
|-----------|-----------------|-------|
| Linux kernel | ≥ 3.x (5.8+ for CAP_PERFMON) | `CONFIG_PERF_EVENTS=y` (enabled by default) |
| perf userspace tool | Matches kernel version | `linux-tools-$(uname -r)` package |
| PMU hardware | Intel/AMD/ARM | Required for hardware counters; software events work anywhere |
| Root / CAP_PERFMON | — | Depending on `perf_event_paranoid` level |
| DWARF debug info | Optional | For source-level annotation and call graph unwinding |
| FlameGraph tools | Optional | For SVG flame graph generation |

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        CPU Hardware                                       │
│                                                                         │
│  ┌────────────────────────────────────────────────────────────────┐    │
│  │  Performance Monitoring Unit (PMU)                              │    │
│  │  Counters: cycles, instructions, cache-misses, branches, ...   │    │
│  │  Intel PT: branch trace packets                                │    │
│  │  LBR: last branch record stack (16-32 entries)                 │    │
│  └──────────────────────────────┬─────────────────────────────────┘    │
│                                 │ overflow → NMI                         │
└─────────────────────────────────┼───────────────────────────────────────┘
                                  │
┌─────────────────────────────────▼───────────────────────────────────────┐
│                    Kernel: perf_events subsystem                          │
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────┐      │
│  │  perf_event_open() syscall                                    │      │
│  │  • Creates struct perf_event per event/process/CPU            │      │
│  │  • Configures via perf_event_attr (type, config, sample_type) │      │
│  │  • Returns fd for read/mmap/ioctl                             │      │
│  └──────────────────────────────────────────────────────────────┘      │
│                                                                         │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐     │
│  │  Hardware PMU    │  │  Software Events │  │  Tracepoints     │     │
│  │  Events          │  │  (ctx-switch,    │  │  (sched_switch,  │     │
│  │  (cycles, etc.)  │  │   page-faults)   │  │   block_*, etc.) │     │
│  └────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘     │
│           └──────────────────────┼──────────────────────┘               │
│                                  ▼                                       │
│  ┌──────────────────────────────────────────────────────────────┐      │
│  │  Per-event mmap Ring Buffer (shared with userspace)           │      │
│  │  Page 0: perf_event_mmap_page (metadata: data_head/tail)     │      │
│  │  Pages 1..N: sample records (perf_event_header + payload)    │      │
│  └──────────────────────────────┬───────────────────────────────┘      │
└─────────────────────────────────┼───────────────────────────────────────┘
                                  │ mmap read (poll data_head)
                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    Userspace: perf tool                                   │
│                                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                 │
│  │ perf stat    │  │ perf record  │  │ perf top     │                 │
│  │ (counting)   │  │ (sampling)   │  │ (live)       │                 │
│  └──────┬───────┘  └──────┬───────┘  └──────────────┘                 │
│         │                  │                                            │
│         ▼                  ▼                                            │
│  ┌──────────────┐  ┌──────────────────────────────────┐               │
│  │ Terminal     │  │ perf.data (binary file)           │               │
│  │ stdout      │  │ Records: SAMPLE, MMAP, COMM, etc. │               │
│  └──────────────┘  │ Metadata: build-ids, topology    │               │
│                     └──────────────────┬───────────────┘               │
│                                        │                                │
│  ┌─────────────┐  ┌─────────────┐  ┌──▼──────────┐  ┌─────────────┐ │
│  │ perf report │  │ perf script │  │ perf annot. │  │ perf data   │ │
│  │ (TUI/stdio) │  │ (text/flame)│  │ (src/asm)   │  │ convert     │ │
│  └─────────────┘  └─────────────┘  └─────────────┘  └──────┬──────┘ │
│                                                              │         │
│                                              ┌───────────────┼───────┐ │
│                                              │  CTF  │  JSON  │ ...  │ │
│                                              └───────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Instrumentation Walkthrough

### What is captured

| Mode | Data Captured |
|------|---------------|
| **Counting** (`perf stat`) | Aggregate counter values: total cycles, instructions, cache-misses, etc. |
| **Sampling** (`perf record`) | Per-sample: IP, PID/TID, timestamp, CPU, call chain, branch stack |
| **Tracepoint tracing** | Full event payload (same fields as ftrace/LTTng tracepoints) |
| **kprobe/uprobe** | Function entry/exit with captured arguments |
| **Intel PT** | Complete control-flow trace (every branch taken/not-taken) |

### The mechanism

1. **perf_event_open()**: Userspace configures event via `perf_event_attr` struct (event type, sample frequency, sample fields requested) and gets back a file descriptor.

2. **mmap ring buffer**: Userspace mmaps the fd to get a shared-memory ring buffer. Kernel writes samples at `data_head`; userspace reads and advances `data_tail`.

3. **Counting mode**: Kernel increments hardware counters continuously. Userspace reads final values via `read(fd)` — no interrupts, near-zero overhead.

4. **Sampling mode**: Counter overflows at configured frequency → NMI fires → kernel captures sample record (IP, timestamp, callchain, etc.) → writes to ring buffer.

5. **Tracepoint mode**: Kernel tracepoint fires → perf callback captures full event payload → writes to ring buffer.

6. **perf.data**: `perf record` reads ring buffer and writes binary records to `perf.data` file with metadata headers (build-ids, CPU topology, command line).

### Data format produced

**perf.data** — proprietary binary format:
- Each record: `struct perf_event_header { type, misc, size }` + payload
- Record types: SAMPLE, MMAP2, COMM, FORK, EXIT, THROTTLE, etc.
- Metadata features: build-ids, hostname, arch, cmdline, CPU topology, NUMA info
- Convertible to CTF (`perf data convert --to-ctf`) or JSON

---

## Sample Trace Output

### perf stat (counting mode)

```
 Performance counter stats for './webserver --benchmark':

     12,345,678,901      cycles                    #    3.42 GHz                  (83.31%)
     21,456,789,012      instructions              #    1.74  insn per cycle       (83.33%)
        345,678,901      cache-references                                          (83.33%)
         12,345,678      cache-misses              #    3.57% of all cache refs    (83.35%)
      3,456,789,012      branch-instructions                                       (83.34%)
         89,012,345      branch-misses             #    2.58% of all branches      (83.34%)

       3.612345678 seconds time elapsed
       3.456789012 seconds user
       0.123456789 seconds sys
```

### perf script (sampling mode, one sample per line)

```
webserver  4521 [003] 51234.567890: cycles:
        ffffffff8107a2c0 native_write_msr+0x6 ([kernel.kallsyms])
        ffffffff81079e12 __intel_pmu_enable_all.isra.0+0x42 ([kernel.kallsyms])
        ffffffff810799a1 intel_pmu_enable_all+0x11 ([kernel.kallsyms])
        ffffffff81073c0a x86_pmu_enable+0x1a ([kernel.kallsyms])
        ffffffff811f4b23 ctx_resched+0xa3 ([kernel.kallsyms])
        ffffffff811f5d82 perf_event_exec+0x1a2 ([kernel.kallsyms])

webserver  4521 [003] 51234.577890: cycles:
        00007f4a12345678 compute_hash+0x42 (/usr/bin/webserver)
        00007f4a12345abc process_request+0x1c (/usr/bin/webserver)
        00007f4a12340100 main_loop+0x200 (/usr/bin/webserver)
        00007ffff7a2d830 __libc_start_main+0xf0 (/lib/x86_64-linux-gnu/libc.so.6)
```

### perf report (stdio, aggregated)

```
# Overhead  Command    Shared Object       Symbol
# ........  .........  ..................  .....................................
    23.45%  webserver  webserver           [.] compute_hash
    15.67%  webserver  libc.so.6           [.] __memcpy_avx2_unaligned
    12.34%  webserver  [kernel.kallsyms]   [k] copy_user_enhanced_fast_string
     8.90%  webserver  webserver           [.] parse_http_header
     6.78%  webserver  libpthread.so.0     [.] __pthread_mutex_lock
     5.43%  webserver  [kernel.kallsyms]   [k] _raw_spin_lock_irqsave
```

### perf trace (syscall tracing)

```
     0.000 ( 0.008 ms): nginx/4521 epoll_wait(epfd: 5, events: 0x7f4a00100000, maxevents: 512) = 1
     0.012 ( 0.003 ms): nginx/4521 accept4(fd: 6, upeer_sockaddr: 0x7ffd12340000, flags: NONBLOCK|CLOEXEC) = 12
     0.018 ( 0.002 ms): nginx/4521 fcntl(fd: 12, cmd: GETFL)                    = 0x802 (flags O_RDWR|O_NONBLOCK)
     0.023 ( 0.015 ms): nginx/4521 read(fd: 12, buf: 0x7f4a001a0000, count: 4096) = 456
     0.041 ( 0.025 ms): nginx/4521 write(fd: 12, buf: 0x7f4a001b0000, count: 1234) = 1234
```

---

## Cost Profile

### LLM token cost

**Not applicable.** perf is a kernel performance profiling tool with no AI/LLM component.

### Compute/IO overhead per operation

| Mode | Overhead | Notes |
|------|----------|-------|
| `perf stat` (counting) | ~0% CPU | Hardware counters free-run; read via rdpmc/read() |
| Sampling @ 99 Hz | <0.1% CPU | ~99 NMIs/sec/CPU; standard production rate |
| Sampling @ 997 Hz | <0.5% CPU | High-resolution profiling |
| Sampling @ 99999 Hz | 1–5% CPU | Maximum practical rate |
| Tracepoint event | 100–300 ns/event | Higher than ftrace due to ring buffer format overhead |
| Intel PT | 5–20% CPU + 100s MB/s I/O | Full control-flow reconstruction |
| `perf trace` (syscalls) | 1–3% CPU | Lower than strace (no ptrace stops) |

### Storage growth rate

| Mode | Data Rate | Notes |
|------|-----------|-------|
| perf stat | 0 (terminal output only) | No file produced |
| Sampling @ 99 Hz, 8 CPUs | ~50–200 KB/min | Depends on stack depth |
| Sampling @ 997 Hz, 8 CPUs | ~500 KB–2 MB/min | With DWARF call graphs |
| Tracepoint tracing (sched_switch) | 5–50 MB/min | Depends on system load |
| Intel PT | 60–600 MB/sec | Extreme; requires fast storage |

---

## Validation Criteria

1. **perf available**: `perf version` outputs version string matching kernel
2. **PMU accessible**: `perf stat -e cycles true` completes without permission error
3. **Events listed**: `perf list` shows hardware, software, tracepoint events
4. **Sampling works**: `perf record -F 99 sleep 1` produces `perf.data` with samples
5. **Symbols resolve**: `perf report --stdio` shows function names (not raw addresses)
6. **Counting accurate**: `perf stat -e instructions,cycles ./known_workload` produces expected IPC ratio
7. **No multiplexing artifacts**: Counter values show `(100.00%)` not `(N.NN%)` if enough PMU counters

### Quick smoke test

```bash
# Count instructions for a known command
perf stat -e cycles,instructions ls /tmp > /dev/null
# Verify: instructions > 0, IPC between 0.5 and 4.0

# Record and verify samples
perf record -F 99 -g -- sleep 2
perf report --stdio | head -20
# Verify: overhead percentages sum to ~100%, symbols resolved
```

---

## Limitations / Out of Scope

| Item | Status |
|------|--------|
| Application-level tracing (structured events) | Not the primary use case; use LTTng-UST or OpenTelemetry |
| Distributed tracing / trace-id propagation | Not supported |
| Always-on production tracing | Sampling only; not designed for continuous event capture at scale |
| Standardized output format | perf.data is proprietary; can export to CTF/JSON |
| Non-Linux platforms | Linux only |
| Unprivileged access (default) | Restricted by perf_event_paranoid; requires CAP_PERFMON |
| Real-time streaming to collectors | No native export pipeline; must post-process perf.data |
| Container-native isolation | Limited namespace support; perf is host-level |
| GUI (built-in) | No built-in GUI; use Hotspot, Firefox Profiler, or KernelShark |
| AI/ML integration | None |
| Encryption of perf.data | Not provided |
| Long-duration recording | perf.data grows unbounded; no built-in rotation |
| PMU counter virtualization | Hardware counter multiplexing introduces measurement error |

---

## Evaluation Assessment

### Observability

**Rating: Strong**

| Aspect | Assessment |
|--------|------------|
| **Strengths** | Hardware-level visibility unavailable from any other tool: CPU cycles, cache behavior, branch prediction, memory access latency. Sampling provides statistical profiling with minimal overhead. Integrates with kernel tracepoints for event-level detail. Flame graph pipeline provides immediate visual insight. `perf top` enables live system observation. Source-level annotation via `perf annotate`. |
| **Gaps** | No built-in dashboards, metrics export, or alerting. perf.data requires offline processing. No streaming pipeline to collectors (Prometheus/OTel). No structured application-level events — hardware/kernel focus only. |
| **Implementations must add** | Export pipelines to monitoring systems, continuous profiling infrastructure (see Parca/Pyroscope), real-time alerting on performance regressions. |

### Security

**Rating: Moderate**

| Aspect | Assessment |
|--------|------------|
| **Strengths** | `perf_event_paranoid` sysctl provides 5 restriction levels. Dedicated `CAP_PERFMON` capability (since 5.8) enables least-privilege. Kernel enforces per-process/per-CPU access boundaries. Build-id cache helps prevent symbol confusion attacks. |
| **Gaps** | perf.data files are unencrypted and contain sensitive information (function names, memory addresses, KASLR offsets). No authentication for who captured a profile. Intel PT captures exact control flow — massive information leakage if exfiltrated. No integrity protection on perf.data. Side-channel: PMU counters can be used for speculative execution attacks (Spectre-adjacent). |
| **Implementations must add** | Profile data encryption, access audit logging, perf.data signing, Intel PT data classification, PMU access restrictions in multi-tenant environments. |

### Identity Management

**Rating: Minimal**

| Aspect | Assessment |
|--------|------------|
| **Strengths** | Samples contain PID/TID/comm (process name) for attribution. `perf record -p <pid>` scopes to specific processes. CPU topology recorded in metadata. |
| **Gaps** | No concept of operator identity (who ran the profile). No linkage to user sessions or service identity. No AI identity. No authentication of the profiler. PID attribution is the only identity mechanism. |
| **Implementations must add** | Operator identity binding, profile provenance chain, service identity correlation, authenticated profiling sessions. |

### Reliability

**Rating: Moderate**

| Aspect | Assessment |
|--------|------------|
| **Strengths** | Counting mode is perfectly reliable (hardware counters don't miss events). Ring buffer overflow is detectable (THROTTLE records). NMI-based sampling is non-maskable — captures even in interrupt-disabled regions. Event groups ensure atomically-scheduled counter sets. |
| **Gaps** | Sampling is inherently statistical — rare events can be missed. Ring buffer overflow causes sample loss with only throttle notification. PMU counter multiplexing introduces measurement error (reported as percentage). perf.data is a single file with no rotation or replication. No guaranteed delivery to external systems. Long Intel PT traces can overflow AUX buffer. |
| **Implementations must add** | Continuous profiling with rotation, sample loss monitoring, multiplexing-aware analysis, distributed collection with redundancy. |

### Accuracy

**Rating: Strong**

| Aspect | Assessment |
|--------|------------|
| **Strengths** | Hardware counters provide exact event counts (counting mode). `precise_ip` levels (0–3) control skid — level 3 provides zero-skid precise sampling on supported hardware. LBR provides exact branch history. Intel PT provides exact instruction-level control flow. Timestamps from TSC with nanosecond resolution. |
| **Gaps** | Sampling mode is statistical — accuracy proportional to sample count. Instruction pointer "skid" at lower precise_ip levels (sample attributed to wrong instruction). Multiplexed counters are extrapolated (not measured). DWARF unwinding can fail on optimized/stripped binaries. Call graph accuracy varies by method (fp > DWARF > LBR in different scenarios). |
| **Implementations must add** | Statistical confidence intervals on sampled data, skid correction for imprecise events, automated detection of unwinding failures, multiplexing error bounds reporting. |

---

## Assessment Summary

| Dimension | Rating | Key Gap |
|-----------|--------|---------|
| Observability | Strong | No streaming export pipeline; offline processing only |
| Security | Moderate | perf.data unencrypted; Intel PT leaks control flow; no audit trail |
| Identity | Minimal | PID-level attribution only; no operator/service identity |
| Reliability | Moderate | Sampling is statistical; ring buffer overflow loses data |
| Accuracy | Strong | IP skid at lower precision levels; multiplexing extrapolation error |
