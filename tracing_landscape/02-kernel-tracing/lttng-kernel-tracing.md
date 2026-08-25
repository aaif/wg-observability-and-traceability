# AAIF Reference Architecture: LTTng Kernel Tracing

| Field | Value |
|-------|-------|
| **Subject** | [LTTng](https://lttng.org) |
| **Version** | 2.13 (stable) |
| **Date** | 2026-06-25 |

---

## Objective

Demonstrates how LTTng (Linux Trace Toolkit: next generation) provides high-throughput, low-overhead kernel tracing via per-CPU lock-free ring buffers and the Common Trace Format (CTF), enabling always-on production tracing with nanosecond-precision event capture.

---

## Scope / Zoom Level

**System layer — kernel instrumentation and trace collection infrastructure.**

LTTng operates below application code: it instruments the Linux kernel itself (scheduler, block I/O, networking, memory allocator, syscalls) and streams structured binary events through a multi-daemon pipeline to persistent CTF trace archives. This is infrastructure-level observability, not application-level telemetry.

---

## Prerequisites

| Component | Version / Pinned | Notes |
|-----------|-----------------|-------|
| Linux kernel | ≥ 4.4 (5.x+ recommended) | Must have `CONFIG_TRACEPOINTS=y`, `CONFIG_MODULES=y` |
| lttng-modules | 2.13.x | Kernel probe modules; must match kernel version |
| lttng-tools | 2.13.x | Session daemon, consumer daemon, relay daemon, CLI |
| liblttng-ctl | 2.13.x | C API for programmatic session control |
| babeltrace2 | 2.0.x | Trace reader, converter, live viewer |
| Trace Compass | 9.x+ (optional) | GUI analysis; Eclipse-based |
| Root/CAP_SYS_ADMIN | — | Required for kernel tracing; `tracing` group for delegated access |

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Linux Kernel                                       │
│                                                                             │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────────────┐   │
│  │ sched_*    │  │ block_*    │  │ net_*      │  │ syscall entry/exit │   │
│  │ tracepoints│  │ tracepoints│  │ tracepoints│  │ hooks              │   │
│  └─────┬──────┘  └─────┬──────┘  └─────┬──────┘  └─────────┬──────────┘   │
│        │                │                │                    │              │
│        ▼                ▼                ▼                    ▼              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    lttng-modules (probe callbacks)                    │   │
│  │  • Serialize event fields into binary CTF                           │   │
│  │  • Lock-free atomic reservation on per-CPU ring buffer              │   │
│  │  • Filter bytecode evaluation (kernel-side)                         │   │
│  └──────────────────────────────┬──────────────────────────────────────┘   │
│                                 │                                            │
│  ┌──────────────────────────────▼──────────────────────────────────────┐   │
│  │           Per-CPU Ring Buffers (kernel memory)                        │   │
│  │  CPU0: [sub0|sub1|sub2|sub3]  CPU1: [sub0|sub1|sub2|sub3]  ...      │   │
│  │  Default: 4 × 256KB per CPU = 1MB/CPU                               │   │
│  └──────────────────────────────┬──────────────────────────────────────┘   │
│                                 │ splice() zero-copy                        │
└─────────────────────────────────┼───────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Userspace Daemons                                    │
│                                                                             │
│  ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐      │
│  │  lttng-sessiond  │◄──►│ lttng-consumerd  │───►│  lttng-relayd    │      │
│  │  (session mgmt)  │    │ (data extraction)│    │  (network relay) │      │
│  │                  │    │                  │    │                  │      │
│  │  • Session state │    │  • splice() from │    │  • TCP 5342/5343 │      │
│  │  • Channel config│    │    ring buffers  │    │  • Multi-host    │      │
│  │  • Filter compile│    │  • Write to disk │    │    aggregation   │      │
│  │  • Trigger engine│    │    or relay      │    │  • Live streaming│      │
│  └────────┬─────────┘    └──────────────────┘    └──────────────────┘      │
│           │                                                                  │
│           ▼                                                                  │
│  ┌──────────────────┐                                                       │
│  │   lttng CLI      │                                                       │
│  │   liblttng-ctl   │                                                       │
│  └──────────────────┘                                                       │
└─────────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         CTF Trace on Disk                                    │
│                                                                             │
│  ~/lttng-traces/my-session-20260625-142900/kernel/                          │
│  ├── metadata          (TSDL: event layouts, clock defs, env)               │
│  ├── channel0_0        (CPU 0 data stream)                                  │
│  ├── channel0_1        (CPU 1 data stream)                                  │
│  └── ...                                                                    │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Trace Readers                                        │
│                                                                             │
│  ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐      │
│  │   babeltrace2    │    │  Trace Compass   │    │ Custom (Python/C)│      │
│  │   (CLI + API)    │    │  (GUI analysis)  │    │  bt2 bindings    │      │
│  └──────────────────┘    └──────────────────┘    └──────────────────┘      │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Instrumentation Walkthrough

### What is captured

| Category | Tracepoints | Example Events |
|----------|-------------|----------------|
| Scheduler | `sched_*` | `sched_switch`, `sched_wakeup`, `sched_process_fork` |
| Block I/O | `block_*` | `block_rq_issue`, `block_rq_complete`, `block_bio_queue` |
| Network | `net_*` | `net_dev_xmit`, `netif_receive_skb` |
| Memory | `kmem_*` | `kmalloc`, `kfree`, `mm_page_alloc` |
| Syscalls | `syscall_entry_*` / `syscall_exit_*` | All ~400+ Linux syscalls |
| IRQ/Softirq | `irq_*`, `softirq_*` | `irq_handler_entry`, `softirq_raise` |
| Timers | `timer_*` | `timer_start`, `hrtimer_expire_entry` |
| Filesystem | `ext4_*`, `btrfs_*` | `ext4_da_write_begin`, `ext4_sync_file_enter` |
| Dynamic | kprobes, kretprobes | Any kernel function by symbol/address |

### The mechanism

1. **Static tracepoints**: Linux kernel's `TRACE_EVENT()` macro defines instrumentation sites (~2000+ in mainline). When disabled: a NOP or never-taken branch (zero overhead via static keys/jump patching).

2. **Probe registration**: `lttng-modules` registers callbacks on kernel tracepoints at `lttng enable-event` time. The callback serializes event fields into the ring buffer.

3. **Ring buffer reservation**: Lock-free atomic `cmpxchg` reserves space in the current CPU's sub-buffer. No locks, no disabling preemption or interrupts on the fast path.

4. **Filter evaluation**: If a filter is attached, compiled bytecode runs in kernel context before ring buffer write. Filtered events never consume buffer space.

5. **Context enrichment**: Configured context fields (PID, TID, process name, perf counters, cgroup ID) are appended to each event at capture time.

6. **Consumer extraction**: `lttng-consumerd` uses `splice()` for zero-copy transfer from kernel ring buffers to disk or network socket via pipe.

### Data format produced

**CTF 1.8 (Common Trace Format)** — a binary, structured, self-describing trace format:

- **Metadata stream**: TSDL (Trace Stream Description Language) text describing all event layouts, clock definitions, and environment
- **Data streams**: One binary stream per CPU per channel, containing packets of serialized events
- **Packet structure**: Magic (0xC1FC1FC1) → packet header → packet context (timestamp range, content size, events_discarded) → event records
- **Event structure**: Event header (id, timestamp delta) → stream event context → event-specific payload fields

---

## Sample Trace Output

### babeltrace2 text output (sched_switch)

```
[14:29:05.847291532] (+0.000012843) myhost sched_switch: { cpu_id = 2 }, { prev_comm = "nginx", prev_tid = 4521, prev_prio = 20, prev_state = 1, next_comm = "kworker/2:1", next_tid = 187, next_prio = 20 }
[14:29:05.847304375] (+0.000012843) myhost sched_wakeup: { cpu_id = 0 }, { comm = "nginx", tid = 4522, prio = 20, target_cpu = 0 }
[14:29:05.847351218] (+0.000046843) myhost syscall_entry_read: { cpu_id = 0 }, { fd = 12, buf = 0x7FFF4A200000, count = 4096 }
[14:29:05.847359061] (+0.000007843) myhost syscall_exit_read: { cpu_id = 0 }, { ret = 1420 }
```

### CTF packet structure (conceptual JSON representation)

```json
{
  "trace": {
    "uuid": "a7f3c291-4e82-4b1a-9d05-6f8e2c4a7b30",
    "env": {
      "hostname": "myhost",
      "domain": "kernel",
      "tracer_name": "lttng-modules",
      "tracer_major": 2,
      "tracer_minor": 13
    }
  },
  "stream": {
    "id": 0,
    "cpu_id": 2
  },
  "packet_context": {
    "timestamp_begin": 1750878545847291532,
    "timestamp_end": 1750878545952184219,
    "content_size": 262144,
    "packet_size": 262144,
    "events_discarded": 0,
    "cpu_id": 2
  },
  "events": [
    {
      "name": "sched_switch",
      "timestamp": 1750878545847291532,
      "stream_event_context": {
        "pid": 4521,
        "tid": 4521,
        "procname": "nginx",
        "perf_cpu_cycles": 48291053821
      },
      "payload": {
        "prev_comm": "nginx",
        "prev_tid": 4521,
        "prev_prio": 20,
        "prev_state": 1,
        "next_comm": "kworker/2:1",
        "next_tid": 187,
        "next_prio": 20
      }
    },
    {
      "name": "block_rq_issue",
      "timestamp": 1750878545847304375,
      "stream_event_context": {
        "pid": 187,
        "tid": 187,
        "procname": "kworker/2:1"
      },
      "payload": {
        "dev": 8388624,
        "sector": 2048000,
        "nr_sector": 8,
        "rwbs": "R",
        "comm": "nginx"
      }
    }
  ]
}
```

### babeltrace2 Python analysis example

```python
import bt2

traces_path = "/home/user/lttng-traces/my-session-20260625-142900"
msg_it = bt2.TraceCollectionMessageIterator(traces_path)

sched_switch_count = 0
for msg in msg_it:
    if type(msg) is bt2._EventMessageConst:
        if msg.event.name == "sched_switch":
            sched_switch_count += 1
            ev = msg.event
            print(f"[{msg.default_clock_snapshot.ns_from_origin}] "
                  f"{ev['prev_comm']} ({ev['prev_tid']}) → "
                  f"{ev['next_comm']} ({ev['next_tid']})")

print(f"Total context switches: {sched_switch_count}")
```

---

## Cost Profile

### LLM token cost

**Not applicable.** LTTng is a kernel tracing infrastructure with no AI/LLM component. Zero token cost.

### Compute/IO overhead per operation

| Operation | Overhead | Notes |
|-----------|----------|-------|
| Tracepoint disabled | ~0 ns | NOP via static key; branch never taken |
| Event enabled, no filter | 50–80 ns | Atomic reservation + serialization |
| Event enabled, with filter | 80–150 ns | Bytecode evaluation before write |
| Timestamp read (TSC) | ~7 ns | x86_64 RDTSC instruction |
| Ring buffer reservation | 15–25 ns | Lock-free cmpxchg |
| Consumer splice() | zero-copy | Kernel→pipe→file without userspace copy |
| Total per event | **50–150 ns** | Negligible at <10M events/sec |

**Throughput ceiling**: 10+ million events/sec per CPU sustained without loss (with adequate buffer sizing).

**CPU overhead**: At 100K events/sec (typical production kernel workload), LTTng consumes <1% additional CPU. At 1M events/sec, ~2–5% CPU for consumer daemon.

### Storage growth rate

| Workload | Events/sec | Disk growth | Notes |
|----------|-----------|-------------|-------|
| Idle server | 1–10K | 1–10 MB/min | Mostly timer/scheduler events |
| Web server under load | 50–200K | 50–200 MB/min | Syscalls, network, scheduler |
| I/O-heavy (database) | 200K–1M | 200 MB–1 GB/min | Block I/O, filesystem tracepoints |
| All events enabled | 1–10M+ | 1–10+ GB/min | Not recommended for sustained use |

**Memory**: Default 1 MB/CPU allocated at channel creation (4 sub-buffers × 256 KB). Configurable from 8 KB to multiple GB per channel.

---

## Validation Criteria

1. **Modules loaded**: `lsmod | grep lttng` shows `lttng_tracer`, `lttng_lib_ring_buffer`, and relevant probe modules
2. **Session daemon running**: `pgrep lttng-sessiond` returns PID; `lttng list` responds without error
3. **Events available**: `lttng list --kernel` shows available kernel tracepoints
4. **Session active**: `lttng list my-session` shows `Tracing session my-session: [active]` with enabled events
5. **No discards**: babeltrace2 output shows `events_discarded = 0` in packet contexts (or check `lttng status`)
6. **Trace readable**: `babeltrace2 ~/lttng-traces/my-session-*/kernel/` produces parseable event output
7. **Timestamp monotonic**: Events on each CPU have strictly increasing timestamps
8. **Context present**: If contexts were added, events include `pid`, `tid`, `procname` fields

### Quick smoke test

```bash
# Create session, enable sched_switch, trace for 2 seconds, read output
lttng create smoke-test
lttng enable-event --kernel sched_switch
lttng add-context --kernel --type=pid --type=procname
lttng start
sleep 2
lttng stop
lttng destroy smoke-test
babeltrace2 ~/lttng-traces/smoke-test-* | head -20
# Verify: timestamps present, prev_comm/next_comm fields populated, pid context attached
```

---

## Limitations / Out of Scope

| Item | Status |
|------|--------|
| Userspace tracing (LTTng-UST) | Separate component; not covered here |
| Distributed tracing / span correlation | Not supported; LTTng traces are node-local |
| Trace encryption at rest | Not provided; files written with standard POSIX permissions |
| Network encryption (sessiond↔relayd) | Not provided; must tunnel via SSH/VPN |
| Authentication between daemons | None; relies on network trust |
| Fine-grained RBAC | Not available; only root vs. tracing group |
| Trace indexing / query language | Not built-in; relies on babeltrace2 linear scan or Trace Compass state system |
| Automatic trace rotation/GC | Trigger framework can rotate; no built-in purge policy |
| Cross-host time synchronization | Assumes synchronized clocks (NTP/PTP); no built-in correction |
| AI/ML integration | None; LTTng is a data capture layer |
| Application-level semantics | Captures kernel events only; application meaning must be inferred |
| Windows/macOS support | Linux only |
| Checksums on trace data | CTF 1.8 has no checksum fields; integrity relies on transport/filesystem |
| Real-time alerting | Not built-in; trigger framework limited to session management actions |

---

## Evaluation Assessment

### Observability

**Rating: Strong**

| Aspect | Assessment |
|--------|------------|
| **Strengths** | Full kernel-level visibility: scheduler, I/O, networking, memory, syscalls. Nanosecond-precision timestamps. Per-CPU lock-free capture means tracing itself minimally disturbs the observed system. Live streaming via relayd enables near-real-time observation. Babeltrace2 provides structured programmatic access. Trace Compass offers rich visualization (Gantt charts, CPU usage, critical path analysis). |
| **Gaps** | No built-in metrics aggregation or dashboarding — raw events only. No alerting surface; trigger framework handles session management, not anomaly detection. Cross-host correlation requires external tooling. No semantic event correlation (e.g., request tracing across kernel subsystems requires manual analysis). |
| **Implementations must add** | Metrics pipelines (e.g., export to Prometheus/OTEL), alerting rules, cross-host trace correlation, request-level tracing semantics. |

### Security

**Rating: Partial**

| Aspect | Assessment |
|--------|------------|
| **Strengths** | Kernel tracing requires root/CAP_SYS_ADMIN — strong privilege barrier. lttng-modules are read-only tracepoint hooks with minimal kernel attack surface. `tracing` group provides delegated access without full root. Ring buffer memory is kernel-space only; userspace reads via controlled splice() path. |
| **Gaps** | No encryption of trace data at rest or in transit. No authentication between sessiond, consumerd, and relayd. Trace data contains highly sensitive kernel state (file paths, network addresses, process arguments). No audit log of who created/read tracing sessions. No integrity protection (no checksums in CTF 1.8). Container tracing from host exposes all container internals without isolation. |
| **Implementations must add** | TLS for relayd connections, trace file encryption, mutual authentication between daemons, access audit logging, per-session access policies, trace data classification/redaction. |

### Identity Management

**Rating: Minimal**

| Aspect | Assessment |
|--------|------------|
| **Strengths** | Traces capture PID/TID/process name as context fields, enabling attribution of events to processes. Cgroup and namespace contexts allow container-level identity. UID context field available. |
| **Gaps** | No concept of human identity, user sessions, or principal binding. No way to attribute a tracing session to a specific operator beyond Unix UID. No AI identity concept (not applicable). No session tokens or identity verification. No linking between traced process identity and organizational identity. |
| **Implementations must add** | Integration with PAM/LDAP for operator identity, audit trail binding tracing sessions to authenticated users, correlation of process UIDs with directory services. |

### Reliability

**Rating: Strong**

| Aspect | Assessment |
|--------|------------|
| **Strengths** | Lock-free per-CPU design eliminates contention — no event loss from locking failures. Configurable overflow policy: discard (count lost events) or overwrite (keep most recent). Zero-copy splice() extraction minimizes consumer overhead. Events are atomic — no partial writes. Per-CPU strict ordering with cross-CPU merge-sort at read time. Trigger framework enables autonomous session management (rotate, snapshot on conditions). Flight recorder mode provides always-on tracing with bounded memory. |
| **Gaps** | Session daemon crash stops tracing with no automatic recovery. Consumer daemon crash can lose in-flight ring buffer data. No built-in replication or redundancy. Disk-full condition causes silent data loss (events accumulate in ring buffer then overflow). No cross-daemon health monitoring. |
| **Implementations must add** | Daemon supervision and auto-restart (systemd), disk space monitoring with proactive rotation, consumer daemon redundancy, health check endpoints, distributed trace collection for HA. |

### Accuracy

**Rating: Strong**

| Aspect | Assessment |
|--------|------------|
| **Strengths** | Nanosecond timestamp precision from hardware TSC — no approximation. Events captured at exact kernel execution point (not sampled). Binary CTF format preserves full field fidelity — no text truncation or formatting loss. All ~400+ syscall arguments captured verbatim. `events_discarded` counter provides explicit signal when data was lost (no silent loss). Metadata stream guarantees event layout is always self-describing. Per-CPU ordering eliminates timestamp inversions within a stream. |
| **Gaps** | Cross-CPU ordering relies on TSC synchronization (can skew on older multi-socket systems). kprobe events have no structured payload by default (just "function called"). Filter expressions can silently exclude events if written incorrectly. No validation that enabled tracepoints actually fire (dormant tracepoints produce no error). |
| **Implementations must add** | TSC offset calibration for multi-socket systems, filter expression testing/validation tooling, tracepoint liveness monitoring, semantic validation of captured data against expected patterns. |

---

## Assessment Summary

| Dimension | Rating | Key Gap |
|-----------|--------|---------|
| Observability | Strong | No built-in metrics/alerting; raw events only |
| Security | Partial | No encryption, no authentication between daemons, no audit trail |
| Identity | Minimal | No human/operator identity binding; PID-level process attribution only |
| Reliability | Strong | Session daemon is single point of failure with no auto-recovery |
| Accuracy | Strong | Cross-CPU TSC skew on multi-socket; no tracepoint liveness detection |
