# AAIF Reference Architecture: bpftrace

| Field | Value |
|-------|-------|
| **Subject** | [bpftrace](https://github.com/bpftrace/bpftrace) |
| **Version** | 0.21.x |
| **Date** | 2026-08-21 |

---

## Objective

Demonstrates how bpftrace provides a high-level, AWK-like tracing language that compiles to BPF bytecode via LLVM, enabling safe, dynamic kernel and userspace instrumentation with in-kernel aggregation through BPF maps — making complex observability queries expressible as one-liners with near-zero setup and verified-safe execution.

---

## Scope / Zoom Level

**System layer — Linux BPF-based dynamic tracing.**

bpftrace sits above the raw BPF machinery and below application-level observability. It provides a domain-specific language for expressing tracing programs that attach to kernel functions, userspace functions, tracepoints, and hardware events. Programs are compiled to BPF bytecode, verified by the kernel's BPF verifier for safety, and execute in-kernel with zero-copy aggregation. It is the interactive query layer for the BPF tracing ecosystem — analogous to what AWK is for text processing, bpftrace is for system observability.

---

## Prerequisites

| Component | Version / Pinned | Notes |
|-----------|-----------------|-------|
| Linux kernel | ≥ 4.9 (5.x+ for full features) | `CONFIG_BPF=y`, `CONFIG_BPF_SYSCALL=y`, `CONFIG_BPF_EVENTS=y` |
| LLVM | ≥ 12 (bundled or system) | Backend for BPF bytecode generation |
| BTF (BPF Type Format) | Kernel with `CONFIG_DEBUG_INFO_BTF=y` | Enables CO-RE — no kernel headers needed |
| libbpf | ≥ 1.0 | BPF loading and CO-RE relocations |
| Root / CAP_BPF + CAP_PERFMON | — | Required for BPF program loading and perf event attachment |
| bpftrace binary | 0.21.x | Single binary; available via package managers or static builds |
| kernel headers (fallback) | Matching running kernel | Only needed if BTF is unavailable |

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Userspace                                         │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  bpftrace Script / One-liner                                     │   │
│  │  e.g.: bpftrace -e 'kprobe:vfs_read { @[comm] = count(); }'    │   │
│  └──────────────────────────────┬──────────────────────────────────┘   │
│                                 │                                        │
│  ┌──────────────────────────────▼──────────────────────────────────┐   │
│  │  Lexer / Parser (flex/bison)                                     │   │
│  │  • Tokenizes bpftrace language                                   │   │
│  │  • Produces Abstract Syntax Tree (AST)                           │   │
│  └──────────────────────────────┬──────────────────────────────────┘   │
│                                 │                                        │
│  ┌──────────────────────────────▼──────────────────────────────────┐   │
│  │  Semantic Analysis & AST Passes                                  │   │
│  │  • Type checking, map type inference                             │   │
│  │  • BTF lookups for struct field access                           │   │
│  │  • Resource allocation (map creation plan)                       │   │
│  └──────────────────────────────┬──────────────────────────────────┘   │
│                                 │                                        │
│  ┌──────────────────────────────▼──────────────────────────────────┐   │
│  │  LLVM IR Codegen                                                 │   │
│  │  • Emits LLVM IR targeting BPF backend                           │   │
│  │  • One BPF program per probe attachment point                    │   │
│  └──────────────────────────────┬──────────────────────────────────┘   │
│                                 │                                        │
│  ┌──────────────────────────────▼──────────────────────────────────┐   │
│  │  LLVM Backend → BPF Bytecode (.o ELF)                           │   │
│  │  • Optimized BPF instructions (ALU64, JMP, LD/ST)               │   │
│  │  • CO-RE relocations embedded for BTF                            │   │
│  └──────────────────────────────┬──────────────────────────────────┘   │
│                                 │ bpf() syscall                          │
└─────────────────────────────────┼───────────────────────────────────────┘
                                  │
┌─────────────────────────────────▼───────────────────────────────────────┐
│                         Kernel                                            │
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  BPF Verifier                                                     │  │
│  │  • Validates all paths terminate (no infinite loops)              │  │
│  │  • Checks memory safety (pointer bounds, alignment)              │  │
│  │  • Verifies map access patterns                                   │  │
│  │  • Enforces instruction limit (1M verified instructions)          │  │
│  │  • Rejects unsafe programs before execution                       │  │
│  └──────────────────────────────┬───────────────────────────────────┘  │
│                                 │ verified OK                            │
│  ┌──────────────────────────────▼───────────────────────────────────┐  │
│  │  BPF JIT Compiler                                                 │  │
│  │  • Translates BPF bytecode → native machine code (x86/ARM)       │  │
│  │  • Near-native execution speed                                    │  │
│  └──────────────────────────────┬───────────────────────────────────┘  │
│                                 │                                        │
│  ┌──────────────────────────────▼───────────────────────────────────┐  │
│  │  Attach Points                                                    │  │
│  │                                                                   │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────┐   │  │
│  │  │ kprobes  │ │ uprobes  │ │ trace-   │ │ perf events      │   │  │
│  │  │ kfuncs   │ │ uretprbs │ │ points   │ │ (hw/sw/profile)  │   │  │
│  │  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────────┬─────────┘   │  │
│  │       └─────────────┴────────────┴────────────────┘              │  │
│  │                              │                                    │  │
│  │  ┌───────────────────────────▼────────────────────────────────┐  │  │
│  │  │  BPF Maps (in-kernel data structures)                       │  │  │
│  │  │  • Hash maps: @map[key] = value                             │  │  │
│  │  │  • Per-CPU arrays: efficient counters                       │  │  │
│  │  │  • Histogram maps: log2 and linear distributions            │  │  │
│  │  │  • Stack trace maps: kstack/ustack storage                  │  │  │
│  │  └───────────────────────────┬────────────────────────────────┘  │  │
│  │                              │                                    │  │
│  │  ┌───────────────────────────▼────────────────────────────────┐  │  │
│  │  │  Perf Buffer / Ring Buffer (per-CPU)                        │  │  │
│  │  │  • Event-by-event output to userspace                       │  │  │
│  │  │  • printf() data, per-event records                         │  │  │
│  │  └───────────────────────────┬────────────────────────────────┘  │  │
│  └──────────────────────────────┼───────────────────────────────────┘  │
└─────────────────────────────────┼───────────────────────────────────────┘
                                  │ poll/mmap
                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  bpftrace Userspace Output                                               │
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  • printf() events (streaming, per-event)                         │  │
│  │  • Map dumps at exit or on interval (aggregated summaries)        │  │
│  │  • Histogram ASCII rendering                                      │  │
│  │  • JSON output mode (-f json)                                     │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Instrumentation Walkthrough

### Probe Types

| Probe Type | Syntax | What It Attaches To |
|------------|--------|---------------------|
| `kprobe` / `kretprobe` | `kprobe:vfs_read` | Dynamic kernel function entry/return (int3 or ftrace-based) |
| `kfunc` / `kretfunc` | `kfunc:vfs_read` | BTF-based kernel function tracing (type-safe args access) |
| `uprobe` / `uretprobe` | `uprobe:/bin/bash:readline` | Dynamic userspace function entry/return (int3 breakpoint) |
| `tracepoint` | `tracepoint:syscalls:sys_enter_read` | Static kernel tracepoints (stable ABI) |
| `rawtracepoint` | `rawtracepoint:sched_switch` | Raw tracepoint access (no format parsing overhead) |
| `software` | `software:page-faults:100` | Software perf events with count threshold |
| `hardware` | `hardware:cache-misses:1000` | Hardware PMU overflow events |
| `profile` | `profile:hz:99` | Timer-based CPU sampling (all CPUs) |
| `interval` | `interval:s:1` | Periodic timer for reporting (single CPU) |
| `BEGIN` / `END` | `BEGIN { ... }` | Program start/finish (setup and teardown) |
| `iter` | `iter:task` | Iterate over kernel data structures (tasks, etc.) |

### Attach Mechanisms

| Mechanism | Used By | How It Works |
|-----------|---------|--------------|
| kprobes (ftrace-based) | `kprobe`, `kretprobe` | Patches function prologue via ftrace infrastructure; lower overhead than int3 |
| kprobes (int3) | `kprobe` (legacy/non-ftrace functions) | Inserts breakpoint instruction; trap handler invokes BPF program |
| fentry/fexit (BTF) | `kfunc`, `kretfunc` | Direct trampoline attachment via BPF trampoline; lowest overhead |
| uprobes | `uprobe`, `uretprobe` | Inserts int3 in userspace binary text; kernel trap handler dispatches |
| tracepoint | `tracepoint` | Static call site in kernel; branch to BPF program when enabled |
| perf_event_open | `software`, `hardware`, `profile` | Kernel perf subsystem delivers events via overflow/timer |
| Timer-based | `interval` | hrtimer fires on single CPU; invokes BPF program |

### Map Types and Aggregation Functions

| Function | Map Type | Semantics |
|----------|----------|-----------|
| `count()` | Per-CPU hash + sum | Increment counter for key |
| `sum(x)` | Per-CPU hash + sum | Accumulate value |
| `avg(x)` | Hash (count + sum) | Running average |
| `min(x)` / `max(x)` | Hash | Track extremes |
| `stats(x)` | Hash | Combined count, sum, avg |
| `hist(x)` | Log2 histogram | Power-of-2 bucket distribution |
| `lhist(x, min, max, step)` | Linear histogram | Fixed-step bucket distribution |
| `@` (scalar) | Array element 0 | Global single value |
| `@[key]` | Hash map | Per-key aggregation |
| `@[key1, key2]` | Multi-key hash | Composite key aggregation |

### Output Modes

| Mode | Trigger | Format |
|------|---------|--------|
| `printf()` | Per-event (inline) | Formatted string to perf buffer → userspace |
| Map auto-print | Program exit (Ctrl-C) | All maps printed with keys and values |
| `print(@map)` | Explicit in probe | Dump map contents at that point |
| `interval:s:N` | Timer | Periodic map snapshots |
| `clear(@map)` | Explicit | Reset map between intervals |
| JSON (`-f json`) | All output | Structured JSON for programmatic consumption |

---

## Sample Trace Output

### Syscall Counting by Process

```
$ sudo bpftrace -e 'tracepoint:raw_syscalls:sys_enter { @[comm] = count(); }'
Attaching 1 probe...
^C

@[irqbalance]: 12
@[containerd]: 87
@[dockerd]: 156
@[postgres]: 892
@[nginx]: 4521
@[python3]: 12045
```

### Read Latency Histogram

```
$ sudo bpftrace -e '
kprobe:vfs_read { @start[tid] = nsecs; }
kretprobe:vfs_read /@start[tid]/ {
    @usecs = hist((nsecs - @start[tid]) / 1000);
    delete(@start[tid]);
}'
Attaching 2 probes...
^C

@usecs:
[0]                    5 |                                                    |
[1]                  312 |@@@@@@@@@@@@                                        |
[2, 4)               891 |@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@                 |
[4, 8)              1302 |@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@|
[8, 16)              987 |@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@             |
[16, 32)             445 |@@@@@@@@@@@@@@@@@                                   |
[32, 64)             201 |@@@@@@@@                                            |
[64, 128)             89 |@@@                                                 |
[128, 256)            34 |@                                                   |
[256, 512)            12 |                                                    |
[512, 1K)              3 |                                                    |
[1K, 2K)               1 |                                                    |
```

### Kernel Stack Trace on Block I/O

```
$ sudo bpftrace -e '
tracepoint:block:block_rq_issue {
    @[kstack, comm] = count();
}'
Attaching 1 probe...
^C

@[
    blk_mq_start_request+0x1a
    scsi_queue_rq+0x5e8
    blk_mq_dispatch_rq_list+0x124
    __blk_mq_sched_dispatch_requests+0xf2
    blk_mq_sched_dispatch_requests+0x32
    __blk_mq_run_hw_queue+0x89
    blk_mq_run_work_fn+0x1e
    process_one_work+0x1c8
    worker_thread+0x4a
    kthread+0xf5
    ret_from_fork+0x2f
, kworker/3:1H]: 234

@[
    blk_mq_start_request+0x1a
    nvme_queue_rq+0x156
    blk_mq_dispatch_rq_list+0x124
    __blk_mq_do_dispatch_sched+0x2af
    __blk_mq_sched_dispatch_requests+0x13c
    blk_mq_sched_dispatch_requests+0x32
    __blk_mq_run_hw_queue+0x89
    blk_mq_submit_bio+0x1f4
    submit_bio_noacct_nocheck+0x2c6
    ext4_io_submit+0x4e
    ext4_do_writepages+0x6b1
, postgres]: 1892
```

### Per-Second Network Throughput

```
$ sudo bpftrace -e '
kprobe:tcp_sendmsg { @bytes = sum(arg2); }
interval:s:1 { print(@bytes); clear(@bytes); }'
Attaching 2 probes...
@bytes: 14523892
@bytes: 15891204
@bytes: 13209451
@bytes: 16102339
^C
```

### Process Exec Tracing

```
$ sudo bpftrace -e '
tracepoint:syscalls:sys_enter_execve {
    printf("%-8d %-6d %s ", elapsed / 1e9, pid, str(args->filename));
}'
Attaching 1 probe...
1.002134   4521   /usr/bin/curl
1.523891   4522   /usr/bin/grep
2.891023   4523   /bin/sh
5.012345   4524   /usr/local/bin/python3
^C
```

---

## Cost Profile

### Compilation Cost

| Phase | Time | Notes |
|-------|------|-------|
| Parse + AST | < 1 ms | Trivial for typical scripts |
| LLVM IR generation | 10–50 ms | Depends on program complexity |
| LLVM → BPF compile | 50–200 ms | LLVM optimization passes; one-time startup cost |
| BPF verification | 1–50 ms | Verifier walks all paths; complex programs take longer |
| Total startup | 100–500 ms | Dominated by LLVM; amortized over trace duration |

### Per-Probe Execution Overhead

| Probe Type | Per-invocation Cost | Notes |
|------------|---------------------|-------|
| kfunc/kretfunc (BTF) | 20–50 ns | BPF trampoline — lowest overhead; no int3 |
| kprobe (ftrace-based) | 50–100 ns | ftrace caller path + BPF dispatch |
| kprobe (int3) | 100–300 ns | Breakpoint trap + register save/restore |
| tracepoint | 30–80 ns | Static branch + BPF dispatch |
| uprobe | 1–5 µs | int3 in userspace → kernel trap → BPF → return; expensive |
| profile (timer) | 50–100 ns per tick | Timer interrupt + BPF execution |

### BPF Program Limits

| Resource | Limit | Notes |
|----------|-------|-------|
| Verified instructions | 1,000,000 | Per-program complexity limit (kernel 5.2+) |
| Stack size | 512 bytes | Per-BPF-program stack frame |
| Map entries | Configurable (default varies) | Hash maps: 4096–65536 entries typical |
| Map memory | Bounded at creation | Pre-allocated; does not grow |
| Tail calls | 33 max depth | For chained BPF programs |
| Loop iterations | Bounded (verifier-checked) | Kernel 5.3+; must be provably finite |

### Memory Footprint

| Component | Size | Notes |
|-----------|------|-------|
| bpftrace process | 30–80 MB RSS | LLVM libraries dominate |
| BPF program (kernel) | 4 KB–1 MB | JIT'd native code |
| BPF map (per-map) | Entries × (key_size + value_size) | Pre-allocated at map creation |
| Perf buffer | 64–512 pages per CPU | Configurable via `BPFTRACE_PERF_RB_PAGES` |
| Ring buffer (5.8+) | Single shared buffer | More memory-efficient than per-CPU perf buffers |

---

## Validation Criteria

1. **Kernel BPF support**: `/proc/config.gz` or `/boot/config-*` contains `CONFIG_BPF=y`, `CONFIG_BPF_SYSCALL=y`
2. **BTF available**: `/sys/kernel/btf/vmlinux` exists (enables CO-RE, field access without headers)
3. **bpftrace binary functional**: `bpftrace --version` returns version string
4. **Probe listing**: `bpftrace -l 'kprobe:vfs_*'` enumerates matching kernel functions
5. **Simple program executes**: `bpftrace -e 'BEGIN { printf("ok\n"); exit(); }'` prints "ok"
6. **Kernel probes attach**: `bpftrace -e 'kprobe:do_nanosleep { printf("%s\n", comm); }'` captures sleep calls
7. **Maps aggregate correctly**: histogram output shows proper bucket distribution for known workload
8. **BPF verifier rejects unsafe**: intentionally unsafe program (e.g., unbounded loop on old kernel) is rejected with verifier error

### Quick Smoke Test

```bash
# Verify bpftrace can compile, load, and execute a BPF program
sudo bpftrace -e '
BEGIN {
    printf("bpftrace smoke test: OK\n");
    printf("Kernel: %s\n", uname);
    exit();
}'

# Expected output:
# Attaching 1 probe...
# bpftrace smoke test: OK
# Kernel: 6.x.y

# Verify dynamic tracing works end-to-end
sudo bpftrace -e '
kprobe:do_nanosleep { @[comm] = count(); }
interval:s:2 { exit(); }
' &
sleep 1  # trigger do_nanosleep
wait

# Expected: map showing "sleep" or "bash" with count >= 1

# Verify histogram aggregation
sudo bpftrace -e '
software:cpu-clock:1000000 { @cpus = hist(cpu); }
interval:s:1 { exit(); }
'
# Expected: histogram showing CPU distribution
```

---

## Limitations / Out of Scope

| Item | Status |
|------|--------|
| Non-Linux platforms | Not supported — BPF is Linux-only |
| Persistent tracing daemon | bpftrace is interactive/script-based; exits when terminated |
| Structured binary output | No CTF/protobuf/binary format; text and JSON only |
| Distributed tracing | No cross-host correlation; local machine only |
| Pre-kernel-4.9 systems | BPF infrastructure unavailable |
| Unprivileged execution | Not possible — requires root or CAP_BPF + CAP_PERFMON |
| Container namespace isolation | BPF programs see host-level kernel; limited cgroup filtering available |
| Long-running aggregation (hours+) | Map memory is fixed; hash collisions increase with cardinality |
| Userspace-only tracing | uprobes work but with high overhead (1–5 µs); not suitable for hot paths |
| Real-time alerting | No built-in notification mechanism; must pipe output externally |
| Encryption of trace data | None — output is plaintext |
| WASM/non-native targets | BPF bytecode only; no portability beyond Linux BPF |
| GUI / visualization | No built-in visualization; must feed to external tools |
| Production-safe by default | Wildcard probes (e.g., `kprobe:*`) can crash or overload systems |
| Stable API for kernel internals | kprobes attach to internal functions that change between kernel versions; BTF/kfunc mitigates |

---

## Evaluation Assessment

### Observability

**Rating: Strong**

| Aspect | Assessment |
|--------|------------|
| **Strengths** | Unmatched breadth: a single tool attaches to any kernel function, userspace function, tracepoint, hardware event, or timer. In-kernel aggregation via BPF maps eliminates the need to stream raw events — histograms, counts, and statistics are computed at the source. AWK-like syntax enables ad-hoc queries in seconds without code compilation cycles. Stack traces (kstack/ustack) provide immediate root-cause context. BTF/CO-RE makes programs portable across kernel versions. JSON output enables integration with monitoring pipelines. One-liners replace hundreds of lines of custom C BPF programs. |
| **Gaps** | No built-in dashboarding, metrics export (Prometheus/OTLP), or persistent storage. Output is ephemeral — stops when bpftrace exits. No native integration with distributed tracing systems. No anomaly detection or threshold alerting. Limited to what BPF can express (no arbitrary kernel memory traversal, bounded computation). |
| **Implementations must add** | Metrics pipeline integration (bpftrace → prometheus-exporter or OTLP), persistent trace collection, correlation with application-level spans, visualization layer, alerting rules on bpftrace output. |

### Security

**Rating: Strong**

| Aspect | Assessment |
|--------|------------|
| **Strengths** | The BPF verifier is a kernel-enforced safety guarantee: every bpftrace program is mathematically proven to terminate, proven memory-safe, and proven to access only permitted memory regions — before a single instruction executes. This eliminates entire classes of tracing-induced crashes (infinite loops, null pointer dereferences, buffer overflows, stack exhaustion). JIT hardening (constant blinding, randomized image base) prevents BPF programs from being exploited. `CAP_BPF` + `CAP_PERFMON` capability separation (kernel 5.8+) provides finer-grained privilege than blanket root. BPF programs cannot modify arbitrary kernel state (read-mostly; limited helpers for write). Seccomp-BPF integration demonstrates BPF's security pedigree. |
| **Gaps** | Still requires elevated privileges — no unprivileged tracing path. BPF programs can read sensitive kernel memory (credentials, keys) if attached to the right functions. No audit trail of which BPF programs were loaded, by whom, or when. No encryption of collected data. Wildcard kprobes can introduce non-trivial overhead (denial-of-service potential). No RBAC for different tracing scopes. |
| **Implementations must add** | BPF program audit logging (who loaded what, when), RBAC for probe scopes, trace data encryption at rest, monitoring of BPF program resource consumption, restricting sensitive function attachment. |

### Identity Management

**Rating: Minimal**

| Aspect | Assessment |
|--------|------------|
| **Strengths** | Every event carries process identity: `pid`, `tid`, `uid`, `gid`, `comm` (process name), `cgroup` path. Can filter by cgroup for container-level scoping. `curtask` provides access to full `task_struct` for detailed process context. The tracing process itself runs as a known user (whoever ran `sudo bpftrace`). |
| **Gaps** | No concept of operator identity — tracing sessions are anonymous. No session identifiers linking a trace to a specific investigation. No AI/agent identity for automated tracing. No authentication or authorization beyond Unix permissions. No trace provenance metadata (who collected this, why, under what authority). No service identity for the target being traced. |
| **Implementations must add** | Operator identity binding (who initiated the trace), session identifiers, provenance metadata in trace output, integration with identity systems for access control, service identity correlation. |

### Reliability

**Rating: Strong**

| Aspect | Assessment |
|--------|------------|
| **Strengths** | BPF programs execute in kernel context — no userspace daemon crash can lose in-flight data. BPF maps persist in kernel memory for the lifetime of the program. Verifier-guaranteed termination means a BPF program cannot hang or deadlock the kernel. Per-CPU maps eliminate contention — no lock-induced reliability issues under load. If userspace bpftrace crashes, kernel-side BPF programs are automatically detached (fd reference counting). Perf buffer overflow is detectable (lost event count). Ring buffer (5.8+) provides more reliable delivery than perf buffer (single producer/consumer). No external dependencies at runtime (no network, no disk, no daemon). |
| **Gaps** | Perf buffer overflow drops events silently under extreme load (unless explicitly checked). Map hash collisions at high cardinality can cause silent data loss. No persistent storage — power loss loses all accumulated map data. bpftrace output depends on userspace process staying alive (unlike ftrace ring buffer). No redundancy or replication. uprobe attachment can race with process exec/exit. |
| **Implementations must add** | Lost event monitoring and alerting, periodic map snapshots to persistent storage, graceful overflow handling (backpressure or sampling), watchdog for bpftrace process, map cardinality monitoring. |

### Accuracy

**Rating: Strong**

| Aspect | Assessment |
|--------|------------|
| **Strengths** | kprobes/kfuncs fire at exact function boundaries — deterministic, not sampled. Timestamps from hardware TSC via `nsecs` — nanosecond precision. BPF maps provide exact counts (not estimates) — `count()` is a true counter, `hist()` buckets are exact. Stack traces are captured at the precise point of execution. BTF provides type-safe field access — no manual offset calculations that could drift. tracepoints provide stable, well-defined event semantics. Aggregation happens in-kernel, eliminating data loss between capture and processing. |
| **Gaps** | Probe overhead (especially uprobes at 1–5 µs) distorts timing measurements — observer effect. kprobe attachment to optimized/inlined functions may miss invocations. Compiler optimization can eliminate or reorder code, making probe placement unpredictable for internal functions. Stack traces may be incomplete with aggressive inlining or frame pointer omission. `comm` is 16 bytes maximum (truncated process names). Userspace symbol resolution depends on debug info availability. |
| **Implementations must add** | Overhead compensation for timing measurements, validation that probe points match expected functions (checksums), cross-reference with compiler output for inlining, frame pointer enforcement or DWARF-based unwinding for complete stacks. |

---

## Assessment Summary

| Dimension | Rating | Key Gap |
|-----------|--------|---------|
| Observability | Strong | No built-in metrics export, dashboarding, or persistent storage |
| Security | Strong | Requires elevated privileges; no audit trail of BPF program loading |
| Identity | Minimal | PID/cgroup-level only; no operator, session, or AI identity |
| Reliability | Strong | Perf buffer overflow drops events; no persistent aggregation |
| Accuracy | Strong | Probe overhead distorts short-duration measurements (observer effect) |
