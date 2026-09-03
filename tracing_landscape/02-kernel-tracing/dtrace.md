# AAIF Reference Architecture: DTrace

| Field | Value |
|-------|-------|
| **Subject** | [DTrace](https://github.com/opendtrace/opendtrace) |
| **Version** | OpenDTrace 1.0 / Solaris lineage (2004–present) |
| **Date** | 2026-08-21 |

---

## Objective

Assesses how DTrace provides safe, dynamic, cross-platform kernel and userspace tracing through a provider-based instrumentation model, a verified D language virtual machine, and in-kernel aggregation — enabling production-safe observability with zero overhead when disabled.

---

## Scope / Zoom Level

**System layer — cross-platform dynamic tracing framework.**

DTrace is a comprehensive dynamic tracing framework originally created for Solaris in 2004 by Bryan Cantrill, Adam Leventhal, and Mike Shapiro at Sun Microsystems. It operates across kernel and userspace boundaries, providing unified tracing through a provider abstraction. Unlike Linux-specific tools (ftrace, perf), DTrace targets multiple operating systems: Solaris/illumos, macOS, FreeBSD, and Linux (via dtrace4linux and BPF-based ports). Its defining characteristic is the safety-verified D programming language that guarantees tracing programs cannot crash or hang the system.

---

## Prerequisites

| Component | Version / Pinned | Notes |
|-----------|-----------------|-------|
| Solaris / illumos | Solaris 10+ / illumos (any) | Native platform; full feature set |
| macOS | macOS 10.5+ (Leopard) | System Integrity Protection restricts some probes on 10.11+ |
| FreeBSD | FreeBSD 7.1+ | Kernel and userspace providers available |
| Linux (dtrace4linux) | dtrace4linux 0.8.x | Loadable kernel module; limited provider set |
| Linux (BPF-based) | Oracle Linux 6.x+ / kernel 5.x+ | BPF backend; subset of D language features |
| Root / privileges | — | `dtrace_kernel` or equivalent privilege required |
| D compiler | Built into libdtrace | No external toolchain needed |
| libdtrace | Ships with DTrace | Consumer API for programmatic access |
| CTF data (optional) | — | Compact Type Format enables typed argument access |

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          Userspace                                        │
│                                                                         │
│  ┌────────────────────────────────────────────────────────────────┐    │
│  │  D Script                                                       │    │
│  │                                                                 │    │
│  │  syscall::write:entry                                           │    │
│  │  /execname == "nginx"/                                          │    │
│  │  { @bytes[pid] = sum(arg2); }                                   │    │
│  └──────────────────────────────┬─────────────────────────────────┘    │
│                                 │                                        │
│  ┌──────────────────────────────▼─────────────────────────────────┐    │
│  │  libdtrace (Consumer Library)                                   │    │
│  │                                                                 │    │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐     │    │
│  │  │  D Lexer /   │  │    DIF       │  │   Safety         │     │    │
│  │  │  Parser      │──▶  Compiler    │──▶  Verifier        │     │    │
│  │  └──────────────┘  └──────────────┘  └────────┬─────────┘     │    │
│  │                                                │               │    │
│  │  DIF = DTrace Intermediate Format (RISC-like bytecode)         │    │
│  │  Verifier: no loops, no unverified pointer derefs,             │    │
│  │           bounded execution, bounded memory                    │    │
│  └────────────────────────────────────────────────┼───────────────┘    │
│                                                   │ ioctl()            │
│  ┌──────────────────────────────────────┐         │                    │
│  │  dtrace(1) CLI / custom consumers    │         │                    │
│  └──────────────────────────────────────┘         │                    │
└───────────────────────────────────────────────────┼────────────────────┘
                                                    │
════════════════════════════════════════════════════════════════════════════
                              Kernel Boundary
════════════════════════════════════════════════════════════════════════════
                                                    │
┌───────────────────────────────────────────────────▼────────────────────┐
│                          Kernel                                          │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  DTrace Framework (dtrace.ko / built-in)                         │   │
│  │                                                                  │   │
│  │  ┌──────────────────────────────────────────────────────────┐   │   │
│  │  │  DIF Virtual Machine (per-probe execution)                │   │   │
│  │  │  • Executes verified bytecode                             │   │   │
│  │  │  • Access to built-ins: timestamp, pid, execname, args    │   │   │
│  │  │  • Bounded execution time guaranteed                      │   │   │
│  │  └──────────────────────────────────────────────────────────┘   │   │
│  │                                                                  │   │
│  │  ┌─────────────────────────────────────────────────────┐        │   │
│  │  │  Providers                                           │        │   │
│  │  │                                                      │        │   │
│  │  │  ┌─────┐ ┌────────┐ ┌────┐ ┌───────┐ ┌─────┐      │        │   │
│  │  │  │ fbt │ │syscall │ │ io │ │ sched │ │proc │      │        │   │
│  │  │  └──┬──┘ └───┬────┘ └──┬─┘ └───┬───┘ └──┬──┘      │        │   │
│  │  │     │        │         │        │         │         │        │   │
│  │  │  ┌──┴──┐ ┌───┴───┐ ┌──┴──┐ ┌───┴──┐ ┌───┴───┐     │        │   │
│  │  │  │ pid │ │profile│ │lockstat│ │ vminfo│ │ tcp/ip│     │        │   │
│  │  │  └─────┘ └───────┘ └─────┘ └──────┘ └───────┘     │        │   │
│  │  └─────────────────────────────────────────────────────┘        │   │
│  │                                                                  │   │
│  │  ┌──────────────────────────────────────────────────────────┐   │   │
│  │  │  Per-CPU Buffers & Aggregation Engine                     │   │   │
│  │  │                                                           │   │   │
│  │  │  CPU0: [principal buf] [aggregation buf] [speculation buf]│   │   │
│  │  │  CPU1: [principal buf] [aggregation buf] [speculation buf]│   │   │
│  │  │  CPU2: [principal buf] [aggregation buf] [speculation buf]│   │   │
│  │  │  ...                                                      │   │   │
│  │  │                                                           │   │   │
│  │  │  Aggregations computed in-kernel (no raw data export)     │   │   │
│  │  └──────────────────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  Instrumentation Points                                          │   │
│  │                                                                  │   │
│  │  Disabled: NOP (or unpatched)     Enabled: trap/call to DTrace   │   │
│  │  Provider registers probe points → framework patches on enable   │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Instrumentation Walkthrough

### What is captured

| Provider | Probe Format | Data Captured |
|----------|-------------|---------------|
| `fbt` | `fbt:<module>:<function>:entry/return` | Kernel function entry/exit with arguments and return value |
| `syscall` | `syscall::<name>:entry/return` | System call entry/exit with all arguments and errno |
| `io` | `io:::start/done/wait-start/wait-done` | Block I/O requests: device, size, offset, latency |
| `sched` | `sched:::on-cpu/off-cpu/enqueue/dequeue` | Scheduler events: context switches, run queue operations |
| `proc` | `proc:::exec/exit/create/signal` | Process lifecycle: fork, exec, exit, signals |
| `profile` | `profile:::tick-<n>ms/hz-<n>` | Timer-based sampling: periodic stack capture |
| `pid` | `pid<PID>::<function>:entry/return` | Userspace function tracing for a specific process |
| `lockstat` | `lockstat:::adaptive-spin/block` | Lock contention: spin time, block time, callers |
| `vminfo` | `vminfo:::pgfault/majflt` | Virtual memory events: page faults, reclamation |
| `tcp` / `ip` | `tcp:::send/receive/connect` | Network stack: connection state, bytes, RTT |

### The mechanism

1. **Provider registration**: Each provider registers its probes with the DTrace framework at load time. Providers describe the universe of instrumentable points — for `fbt`, this is every kernel function entry and return; for `syscall`, every system call.

2. **D script compilation**: The user's D script is parsed and compiled by libdtrace into DIF (DTrace Intermediate Format) — a RISC-like bytecode designed for safe in-kernel execution.

3. **Safety verification**: Before any DIF program is loaded into the kernel, the verifier performs static analysis guaranteeing:
   - No unbounded loops (only bounded iteration via `tick-` probes and aggregation walks)
   - No pointer dereferences of unverified addresses (copyin/copyinstr for userspace access)
   - Bounded memory allocation (scratch space fixed per clause)
   - Bounded execution time (instruction count limits)
   - No modification of kernel state (read-only access to probe arguments)

4. **Probe enabling**: When the verified DIF is loaded via ioctl(), the framework calls each referenced provider's `enable` method. For `fbt`, this patches the function prologue from a NOP to a trap/call instruction. For `syscall`, it activates the system call table wrapper. **Zero overhead for non-enabled probes.**

5. **Probe firing**: When execution hits an enabled probe site, the DTrace framework executes the associated DIF program in the kernel context. The D program's predicate (`/condition/`) is evaluated first; if false, execution returns immediately with minimal cost.

6. **Data recording**: Actions write to per-CPU buffers — principal buffers for `trace()`/`printf()`, aggregation buffers for `@agg` operations, speculation buffers for speculative tracing. No locking between CPUs.

7. **Consumer retrieval**: The userspace consumer (dtrace(1) or libdtrace API) reads buffers via ioctl() at configurable intervals (default: 1 second). Aggregations are merged across CPUs at retrieval time.

### Data format

DTrace produces **text output** by default via `printf()` actions and `printa()` for aggregations. The output format is entirely user-defined in the D script. No fixed binary format is emitted to disk — data lives in kernel buffers until consumed.

For aggregations, DTrace performs the reduction in-kernel. Only the aggregated result (not individual data points) crosses the kernel-user boundary. This is a fundamental architectural difference from tools that export raw events.

### Probe naming convention

```
provider:module:function:name

Examples:
  syscall::write:entry          — entry to write() system call
  fbt:zfs:arc_read:entry        — entry to arc_read() in ZFS module
  pid1234::malloc:return         — return from malloc() in process 1234
  profile:::tick-1000ms          — fire every 1000ms on all CPUs
  io:::start                     — block I/O request submitted
```

---

## Sample Trace Output

### System call count by process

**D script:**

```d
#!/usr/sbin/dtrace -s

syscall:::entry
{
    @calls[execname, probefunc] = count();
}

dtrace:::END
{
    trunc(@calls, 10);
    printa("%-20s %-20s %@d\n", @calls);
}
```

**Output:**

```
dtrace: script './syscalls.d' matched 547 probes
^C

nginx                read                 145203
nginx                write                 89412
nginx                epoll_wait            45102
postgres             read                  38901
postgres             futex                 27654
postgres             write                 22345
node                 epoll_wait            18902
node                 read                  15678
bash                 wait4                  3456
sshd                 select                 2891
```

### I/O latency distribution (quantize)

**D script:**

```d
#!/usr/sbin/dtrace -s

io:::start
{
    start[args[0]->b_edev, args[0]->b_blkno] = timestamp;
}

io:::done
/start[args[0]->b_edev, args[0]->b_blkno]/
{
    this->delta = (timestamp - start[args[0]->b_edev, args[0]->b_blkno]) / 1000;
    @latency[args[1]->dev_statname] = quantize(this->delta);
    start[args[0]->b_edev, args[0]->b_blkno] = 0;
}
```

**Output:**

```
  sd0
           value  ------------- Distribution ------------- count
             128 |                                         0
             256 |@@                                       34
             512 |@@@@@@@@                                 187
            1024 |@@@@@@@@@@@@@@@@                         412
            2048 |@@@@@@@@@@                               256
            4096 |@@@@                                     89
            8192 |@                                        23
           16384 |                                         4
           32768 |                                         1
           65536 |                                         0
```

### Speculative tracing (commit on error)

**D script:**

```d
#!/usr/sbin/dtrace -s

syscall::open*:entry
{
    self->spec = speculation();
    speculate(self->spec);
    printf("pid=%d open(%s)", pid, copyinstr(arg0));
}

syscall::open*:return
/self->spec && arg1 == -1/
{
    /* Only commit the trace if open() failed */
    speculate(self->spec);
    printf(" = %d (errno %d)", arg1, errno);
    commit(self->spec);
    self->spec = 0;
}

syscall::open*:return
/self->spec && arg1 != -1/
{
    /* Discard trace for successful opens */
    discard(self->spec);
    self->spec = 0;
}
```

**Output:**

```
  CPU     ID                    FUNCTION:NAME
    1    214                      open64:entry pid=4521 open(/etc/nginx/missing.conf)
    1    215                     open64:return  = -1 (errno 2)
    3    214                      open64:entry pid=8832 open(/tmp/.lock.nonexist)
    3    215                     open64:return  = -1 (errno 2)
```

### Stack trace with aggregation

**D script:**

```d
#!/usr/sbin/dtrace -s

fbt::mutex_enter:entry
{
    @stacks[stack()] = count();
}

dtrace:::END
{
    trunc(@stacks, 5);
}
```

**Output:**

```
              genunix`mutex_enter
              zfs`arc_read+0x12c
              zfs`dbuf_read+0x94
              zfs`dmu_read_uio_dbuf+0x48
              zfs`zfs_read+0xd8
              genunix`fop_read+0x5c
              genunix`read+0x234
              unix`sys_syscall+0x17a
           2891

              genunix`mutex_enter
              genunix`taskq_dispatch+0x34
              zfs`spa_sync+0x248
              zfs`txg_sync_thread+0x15c
              unix`thread_start+0x8
           1456
```

### Thread-local and clause-local variables

**D script:**

```d
#!/usr/sbin/dtrace -s

syscall::read:entry
{
    self->ts = timestamp;    /* thread-local: tracks per-thread */
}

syscall::read:return
/self->ts/
{
    this->elapsed = (timestamp - self->ts) / 1000;  /* clause-local */
    @read_time[execname] = avg(this->elapsed);
    self->ts = 0;
}

tick-5s
{
    printa("%-20s avg read latency: %@d us\n", @read_time);
    clear(@read_time);
}
```

**Output:**

```
  postgres             avg read latency: 12 us
  nginx                avg read latency: 8 us
  node                 avg read latency: 45 us
  java                 avg read latency: 234 us
```

---

## Cost Profile

### Compute/IO overhead per operation

| State | Overhead | Mechanism |
|-------|----------|-----------|
| Probes disabled (no consumers) | **Zero** | Probe sites are NOPs or unpatched; provider code is never entered |
| Probe enabled, predicate false | 50–200 ns | Trap into DTrace framework, evaluate DIF predicate, return |
| Probe enabled, predicate true, simple action | 200–500 ns | Predicate + DIF execution + per-CPU buffer write |
| Probe enabled, aggregation action | 100–300 ns | In-kernel hash lookup + aggregating function (no buffer write) |
| Probe enabled, stack() action | 1–5 μs | Stack unwinding (depth-dependent) |
| Probe enabled, copyinstr() | 500 ns–2 μs | Copyin from userspace address space |
| Consumer buffer read (1s interval) | Per-CPU memcpy | Proportional to data volume; typically μs-scale |

### Key performance characteristics

| Property | Detail |
|----------|--------|
| Zero disabled cost | NOP patching (Solaris/illumos); trap patching (FreeBSD/macOS). No code path executed for disabled probes. |
| Per-CPU buffers | No cross-CPU locking. Each CPU writes only to its own buffer. |
| In-kernel aggregation | Aggregations (`count()`, `sum()`, `quantize()`, etc.) reduce data at the source. Only final results exported to userspace. Dramatically reduces bandwidth. |
| Speculative tracing | Data written to speculation buffer; committed or discarded atomically. Zero-cost discard (just reset pointer). |
| Scalability | Linear with CPU count — no shared state. Tested on 256+ CPU systems (Solaris). |
| Bounded overhead | DIF verifier guarantees bounded execution time per probe firing. No infinite loops possible. |

### Storage / Memory

| Resource | Budget | Notes |
|----------|--------|-------|
| Principal buffer | 4 MB/CPU (default, tunable) | Circular; overwrites oldest data |
| Aggregation buffer | 4 MB/CPU (default, tunable) | Hash table; fixed allocation |
| Speculation buffer | 4 MB/CPU (default, tunable) | Reserved for speculative tracing |
| Scratch space | 256 bytes/clause (default) | For clause-local string operations |
| Disk I/O | None by default | Data stays in kernel memory until consumed |

---

## Validation Criteria

### Functional verification

| # | Criterion | How to Verify |
|---|-----------|---------------|
| 1 | DTrace kernel module loaded | `modinfo | grep dtrace` (Solaris); `kextstat | grep dtrace` (macOS) |
| 2 | Providers available | `dtrace -l | awk '{print $2}' | sort -u` lists fbt, syscall, sched, etc. |
| 3 | Probe count reasonable | `dtrace -l | wc -l` returns tens/hundreds of thousands of probes |
| 4 | Predicate filtering works | Run predicate-guarded script; verify only matching events appear |
| 5 | Aggregation correct | Compare `@[key] = count()` output against known workload count |
| 6 | Timestamps monotonic | Verify `timestamp` values increase within each CPU |
| 7 | Stack unwinding correct | `stack()` output matches known call path |
| 8 | Per-CPU isolation | Multi-CPU workload produces buffer data from all CPUs independently |
| 9 | Safety verifier rejects bad programs | Attempt infinite loop in D script → verifier error |
| 10 | Zero disabled overhead | Benchmark target function with/without DTrace loaded but no probes enabled |

### Smoke test

```bash
# Verify DTrace is operational and basic probing works
# (Solaris/illumos or FreeBSD — adjust for platform)

# 1. List available providers
dtrace -l | awk '{print $2}' | sort -u | head -10

# 2. Count syscalls for 5 seconds
dtrace -n 'syscall:::entry { @[execname] = count(); }' -c 'sleep 5'

# 3. Verify safety: this must be REJECTED by the verifier
dtrace -n 'BEGIN { for (;;) { trace(1); } }' 2>&1 | grep -i "error"
# Expected: "dtrace: failed to compile ... infinite loop"

# 4. Test aggregation with quantize
dtrace -n '
  syscall::read:entry { self->ts = timestamp; }
  syscall::read:return /self->ts/ {
    @["read (ns)"] = quantize(timestamp - self->ts);
    self->ts = 0;
  }
  tick-3s { exit(0); }
'
# Expected: power-of-2 histogram of read() latencies

# 5. Verify zero-overhead when disabled
# Run benchmark with dtrace module loaded but no scripts active
# Confirm <0.1% performance difference vs unloaded module
```

---

## Limitations / Out of Scope

| Item | Status |
|------|--------|
| Linux feature parity | dtrace4linux and BPF-based ports lack full Solaris provider set (no `lockstat`, limited `pid`, no `vminfo`) |
| Structured binary format | No standardized binary trace format; output is text via `printf()`/`printa()` |
| CTF compatibility | DTrace does not emit CTF (Common Trace Format) traces; the "CTF" it uses is Compact Type Format (type info) |
| Remote/distributed tracing | No built-in network streaming or multi-host correlation |
| Unprivileged access | Requires root or `dtrace_*` privileges; no delegation model |
| Container-aware tracing | No namespace awareness; traces at host level across all containers |
| Persistent storage | Kernel buffers only; no built-in archival or replay |
| Userspace on Linux | `pid` provider severely limited on Linux ports |
| Encryption / integrity | No trace data encryption or tamper detection |
| Integration with OTel/metrics | No export to OpenTelemetry, Prometheus, or structured formats |
| Real-time alerting | No push notification mechanism; consumer must poll |
| macOS SIP restrictions | System Integrity Protection (10.11+) blocks kernel-level fbt/pid providers unless SIP partially disabled |
| Windows | Not supported on any Windows variant |

---

## Evaluation Assessment

### Observability

**Rating: Strong**

| Aspect | Assessment |
|--------|------------|
| **Strengths** | Unified framework for kernel and userspace tracing through a single language. Provider model offers comprehensive coverage: every kernel function (fbt), all syscalls, scheduler, I/O, networking, process lifecycle, and arbitrary userspace functions (pid provider). In-kernel aggregation enables efficient production monitoring without raw data export. Speculative tracing captures context only for interesting events (e.g., errors), eliminating noise. D language allows complex multi-probe correlation (thread-local variables, associative arrays). Single `dtrace -l` command exposes all possible instrumentation points — self-describing system. |
| **Gaps** | Text-only output requires parsing for programmatic analysis. No built-in dashboards, metrics export, or time-series integration. No remote collection or streaming capability. Consumer must actively poll buffers. No built-in event correlation across hosts. |
| **Implementations must add** | Structured output export (JSON/binary), remote collection infrastructure, metrics bridge to Prometheus/OTel, multi-host trace correlation, persistent trace archiving. |

### Security

**Rating: Strong**

| Aspect | Assessment |
|--------|------------|
| **Strengths** | **Safety verifier is the defining security property.** Every D program undergoes static verification before kernel execution: no unbounded loops, no arbitrary memory access, no kernel state modification, bounded scratch space. This guarantees that tracing cannot crash, hang, or corrupt the system — a property no other dynamic tracing framework (ftrace, perf, raw kprobes) provides at the language level. Privilege model requires explicit `dtrace_kernel`/`dtrace_proc`/`dtrace_user` privileges (Solaris RBAC). No network attack surface by default. Provider enable/disable is atomic — no partial instrumentation states. |
| **Gaps** | Trace data itself is unencrypted in kernel memory. No audit trail of who ran what D scripts. No per-probe access control (if you have dtrace_kernel privilege, you can probe anything). On Linux ports, relies on root with less granular privilege separation. Trace output may expose sensitive kernel/application data. |
| **Implementations must add** | Trace data encryption at rest, audit logging of tracing sessions, fine-grained probe access control, sensitive-data redaction in output. |

### Identity

**Rating: Minimal**

| Aspect | Assessment |
|--------|------------|
| **Strengths** | Built-in variables provide process identity: `execname`, `pid`, `tid`, `uid`, `gid`, `zonename` (Solaris zones), `curpsinfo` struct. Probe predicates can filter by identity attributes. `pid` provider traces specific processes by PID. `zonename` provides container-level identity on Solaris/illumos. |
| **Gaps** | No concept of who initiated the tracing session. No operator identity binding to trace data. No service identity or AI agent identity. No session authentication or provenance metadata. Trace output does not carry information about its capture context. No cryptographic identity verification. |
| **Implementations must add** | Operator identity (who ran the script), trace session provenance metadata, service identity correlation, session authentication. |

### Reliability

**Rating: Strong**

| Aspect | Assessment |
|--------|------------|
| **Strengths** | In-kernel execution — no userspace daemon required for probe firing. Safety verifier guarantees tracing cannot crash the system. Per-CPU buffers eliminate cross-CPU contention and deadlock risk. Atomic probe enable/disable — no inconsistent instrumentation states. Principal buffer overwrite policy keeps most recent data (flight recorder semantics). `dtrace:::ERROR` probe fires on runtime errors (e.g., illegal address) without terminating the session — graceful degradation. Aggregation buffers provide bounded memory usage regardless of event rate. Speculative tracing commit/discard is atomic. |
| **Gaps** | Buffer overflow drops data (switchpolicy: "switch" or "ring"). No delivery guarantees to consumer if consumer is slow. No redundancy or replication. Power loss means data loss (in-memory only). Consumer crash loses unfetched buffer data. On Linux ports, module stability is lower than native platforms. |
| **Implementations must add** | Drop counters surfaced to consumer, persistent trace archiving, consumer failover, buffer fullness monitoring/alerting. |

### Accuracy

**Rating: Strong**

| Aspect | Assessment |
|--------|------------|
| **Strengths** | Deterministic instrumentation — every probe fires for every matching event (no sampling for most providers). `timestamp` uses highest-resolution hardware clock (TSC/HPET) with nanosecond precision. Aggregations computed exactly (count, sum, min, max) — not statistical estimates. Arguments (`arg0`–`argN`) are captured directly from registers/stack at probe site — no reconstruction. `fbt` probes fire at exact function boundary — instruction-level precision. Type-safe access to kernel structures via CTF (Compact Type Format) data eliminates manual offset calculations. Speculative tracing ensures only relevant events are recorded — no noise in committed traces. |
| **Gaps** | Probe overhead (50–500 ns) perturbs timing measurements (observer effect); significant for nanosecond-scale functions. `profile` provider is statistical by nature (sampling). Clock skew across CPUs affects timestamp ordering (mitigated by per-CPU buffers). `copyinstr()` may race with userspace string modifications. Consumer poll interval (default 1s) introduces reporting latency. On Linux ports, some argument access may be unreliable. |
| **Implementations must add** | Overhead compensation for timing measurements, sub-microsecond consumer notification (for real-time use cases), cross-CPU timestamp normalization documentation. |

---

## Assessment Summary

| Dimension | Rating | Key Strength | Key Gap |
|-----------|--------|--------------|---------|
| Observability | Strong | Unified kernel + userspace tracing via provider model; in-kernel aggregation | Text-only output; no remote streaming or metrics export |
| Security | Strong | Safety verifier guarantees no system crash/hang; privilege-separated access | No encryption of trace data; no audit trail of tracing sessions |
| Identity | Minimal | Process-level identity (pid, execname, uid, zonename) available in every probe | No operator identity, no session provenance, no service/AI identity |
| Reliability | Strong | In-kernel execution with safety guarantees; per-CPU lock-free buffers; graceful error handling | Buffer overflow drops data silently; no persistent storage |
| Accuracy | Strong | Deterministic (non-sampling) instrumentation; nanosecond timestamps; exact aggregation | Observer effect perturbs short-function timing; consumer poll latency |
