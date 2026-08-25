# AAIF Reference Architecture: LTTng-UST

| Field | Value |
|-------|-------|
| **Subject** | [LTTng-UST](https://lttng.org) |
| **Version** | 2.13 (stable) |
| **Date** | 2026-06-25 |

---

## Objective

Demonstrates how LTTng-UST provides near-zero-overhead userspace tracing by compiling tracepoints directly into application code and recording events into shared-memory ring buffers without kernel transitions or locks on the fast path.

---

## Scope / Zoom Level

**Inside a single process (primitive layer) — extending to system layer via session daemon coordination.**

LTTng-UST instruments individual application processes. Each traced application links against `liblttng-ust`, defines tracepoint providers, and writes events into per-process shared-memory ring buffers. The session daemon coordinates multiple applications, and the consumer daemon extracts data to CTF trace files on disk.

---

## Prerequisites

| Component | Version / Pinned | Notes |
|-----------|-----------------|-------|
| Linux | Any (no kernel features required) | Shared memory via `/dev/shm` |
| liblttng-ust | 2.13.x | Instrumentation library; linked into application |
| liburcu | 0.13+ | Userspace RCU; required by liblttng-ust |
| lttng-tools | 2.13.x | Session daemon, consumer daemon, CLI |
| babeltrace2 | 2.0.x | Trace reader/converter |
| GCC/Clang | Any C99+ | For compiling tracepoint providers |
| Root | **Not required** | Per-user session daemon; no kernel privilege needed |

Optional agents:
| Agent | Package | Use Case |
|-------|---------|----------|
| Python | `lttng-ust-agent-python` | Bridge `logging` module to LTTng |
| Java JUL | `lttng-ust-agent-jul` | Bridge `java.util.logging` |
| Java Log4j 2 | `lttng-ust-agent-log4j2` | Bridge Log4j 2.x |

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    Application Process (my_app)                           │
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                    Application Code                               │  │
│  │                                                                   │  │
│  │  tracepoint(my_app, request_start, id, "/api/data");             │  │
│  │  /* ... work ... */                                               │  │
│  │  tracepoint(my_app, request_end, id, 200, duration_ns);          │  │
│  └───────────────────────────────┬───────────────────────────────────┘  │
│                                  │                                       │
│                                  ▼                                       │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │              liblttng-ust (linked into process)                    │  │
│  │                                                                   │  │
│  │  1. Check tracepoint state (single branch; ~1ns if disabled)     │  │
│  │  2. Serialize fields via ctf_integer/ctf_string macros           │  │
│  │  3. Atomic CAS reservation in shared-memory ring buffer          │  │
│  │  4. Memcpy payload into reserved slot                            │  │
│  │  No syscalls. No locks. No allocation.                           │  │
│  └───────────────────────────────┬───────────────────────────────────┘  │
│                                  │                                       │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │         Shared-Memory Ring Buffers (/dev/shm/lttng-ust-*)         │  │
│  │                                                                   │
│  │  Per-PID mode: [sub0|sub1|sub2|sub3] per channel per process     │  │
│  │  Per-UID mode: shared across processes of same UID               │  │
│  │  Default: 4 sub-buffers × 4KB = 16KB per channel                 │  │
│  └───────────────────────────────┬───────────────────────────────────┘  │
└──────────────────────────────────┼───────────────────────────────────────┘
                                   │ Unix socket registration
                                   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                       lttng-sessiond (per-user)                           │
│                                                                         │
│  • Listens on ~/.lttng/ust-sock for app registration                   │
│  • Manages session state, channels, event enablement                    │
│  • Compiles filter bytecode, sends to app via socket                    │
│  • Coordinates consumer daemon                                          │
│  • No root required for UST tracing                                     │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                       lttng-consumerd                                     │
│                                                                         │
│  • Reads full sub-buffers from shared memory (mmap)                    │
│  • Writes CTF binary data to disk                                       │
│  • Or streams to lttng-relayd (TCP 5342/5343)                          │
│  • Batched: reads entire sub-buffers, not individual events            │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│              CTF Trace on Disk                                            │
│                                                                         │
│  ~/lttng-traces/my-session-20260625-144400/ust/uid/1000/64-bit/         │
│  ├── metadata        (TSDL event layouts)                               │
│  ├── channel0_0      (data stream)                                      │
│  └── channel0_1      (data stream)                                      │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Instrumentation Walkthrough

### What is captured

User-defined events with typed fields, plus optional context:

| Source | Events | Fields |
|--------|--------|--------|
| Custom tracepoints | Developer-defined via `TRACEPOINT_EVENT()` | Arbitrary: integers, strings, arrays, enums, structs |
| Python logging agent | All Python `logging` calls | Logger name, level, message, file, line |
| Java JUL/Log4j agent | All Java log calls | Logger, level, message, class, method, thread |
| liblttng-ust-libc-wrapper | `malloc`/`free`/`calloc`/`realloc` | Pointer, size, caller IP |
| liblttng-ust-dl | `dlopen`/`dlclose` | Library path, handle |
| liblttng-ust-cyg-profile | Function entry/exit (`-finstrument-functions`) | Function address, call site |

### The mechanism

**Tracepoint definition (compile-time):**

```c
/* tp_provider.h */
TRACEPOINT_EVENT(
    my_app,                          /* provider name */
    request_start,                   /* event name */
    TP_ARGS(
        int, request_id,
        const char *, endpoint
    ),
    TP_FIELDS(
        ctf_integer(int, id, request_id)
        ctf_string(endpoint, endpoint)
    )
)
TRACEPOINT_LOGLEVEL(my_app, request_start, TRACE_INFO)
```

**Instrumentation call (runtime):**

```c
tracepoint(my_app, request_start, req_id, "/api/users");
```

**Fast-path execution (when enabled, ~50-100ns):**
1. Check `__tracepoint_my_app___request_start.state` (single branch via RCU read)
2. Call probe callback registered by liblttng-ust
3. Serialize fields via `ctf_integer`/`ctf_string` into binary CTF layout
4. Atomic CAS to reserve space in per-process ring buffer
5. `memcpy()` payload into reserved slot
6. Memory barrier to publish

**Disabled path (~1-2ns):**
1. Single branch on tracepoint state variable → not taken → return

### Data format produced

**CTF 1.8** — identical binary format to kernel tracing. Events are self-describing via the metadata stream (TSDL). Ring buffers contain packets with headers, context, and serialized event payloads.

---

## Sample Trace Output

### babeltrace2 text output

```
[14:44:01.283491832] (+?.?????????) myhost my_app:request_start: { cpu_id = 3 }, { vpid = 28451, vtid = 28451, procname = "my_app" }, { id = 0, endpoint = "/api/data" }
[14:44:01.283527104] (+0.000035272) myhost my_app:request_end: { cpu_id = 3 }, { vpid = 28451, vtid = 28451, procname = "my_app" }, { id = 0, status = 200, duration_ns = 34891 }
[14:44:01.283531297] (+0.000004193) myhost my_app:request_start: { cpu_id = 3 }, { vpid = 28451, vtid = 28451, procname = "my_app" }, { id = 1, endpoint = "/api/data" }
[14:44:01.283566410] (+0.000035113) myhost my_app:request_end: { cpu_id = 3 }, { vpid = 28451, vtid = 28451, procname = "my_app" }, { id = 1, status = 200, duration_ns = 34722 }
```

### Structured representation (JSON-style)

```json
{
  "trace": {
    "uuid": "b2e4f691-3a1c-4e7d-8f0b-1c2d3e4a5b6c",
    "env": {
      "hostname": "myhost",
      "domain": "ust",
      "tracer_name": "lttng-ust",
      "tracer_major": 2,
      "tracer_minor": 13
    }
  },
  "events": [
    {
      "name": "my_app:request_start",
      "timestamp": 1750878241283491832,
      "stream_event_context": {
        "vpid": 28451,
        "vtid": 28451,
        "procname": "my_app",
        "pthread_id": 140234567890112
      },
      "payload": {
        "id": 0,
        "endpoint": "/api/data"
      }
    },
    {
      "name": "my_app:request_end",
      "timestamp": 1750878241283527104,
      "stream_event_context": {
        "vpid": 28451,
        "vtid": 28451,
        "procname": "my_app",
        "pthread_id": 140234567890112
      },
      "payload": {
        "id": 0,
        "status": 200,
        "duration_ns": 34891
      }
    }
  ]
}
```

### Python agent trace output

```
[14:44:02.100123456] (+0.000000000) myhost python:my_module: { cpu_id = 1 }, { vpid = 29001, vtid = 29001, procname = "python3" }, { msg = "Processing batch of 50 items", loglevel = 6, logger_name = "my_module", funcName = "process_batch", lineno = 42 }
```

---

## Cost Profile

### LLM token cost

**Not applicable.** LTTng-UST is a tracing infrastructure; no AI/LLM component.

### Compute/IO overhead per operation

| Operation | Overhead | Notes |
|-----------|----------|-------|
| Tracepoint disabled | ~1-2 ns | Single branch prediction |
| Tracepoint enabled, no filter | 50–100 ns | Atomic CAS + memcpy; no syscall |
| Tracepoint enabled, with filter | 80–150 ns | Bytecode evaluation before write |
| App registration with sessiond | ~1 ms (one-time) | Unix socket handshake at startup |
| Consumer sub-buffer read | Amortized ~0 per event | Batched: reads full sub-buffer at once |

**Comparison:**

| Mechanism | Per-event cost | Notes |
|-----------|---------------|-------|
| LTTng-UST tracepoint | 50–100 ns | Zero-syscall shared memory |
| `printf` to file | 1–5 μs | Involves write() syscall, formatting |
| syslog | 5–10 μs | Socket send, syslog daemon |
| OpenTelemetry span | 1–10 μs | Allocation, export queue, HTTP |

### Storage growth rate

| Workload | Events/sec | Disk growth | Notes |
|----------|-----------|-------------|-------|
| Light instrumentation (10 tracepoints) | 1–10K | 0.5–5 MB/min | Typical microservice |
| Heavy instrumentation (100+ tracepoints) | 50–200K | 25–100 MB/min | Performance profiling |
| Always-on production (key events only) | 100–1K | <1 MB/min | Flight recorder pattern |
| Function entry/exit (-finstrument-functions) | 1–10M+ | 500 MB–5 GB/min | Profiling only; not production |

**Memory**: Default 16 KB per channel per process (4 × 4 KB). Production configurations typically use 4 × 256 KB = 1 MB per channel.

---

## Validation Criteria

1. **App registers**: `lttng list -u` shows the application's tracepoint providers after the app starts
2. **Events available**: `lttng list -u` shows `my_app:request_start`, `my_app:request_end` etc.
3. **Trace produced**: After `lttng stop`, `babeltrace2 ~/lttng-traces/<session>-*` outputs events
4. **Field correctness**: Event payload fields match the values passed to `tracepoint()` calls
5. **Context present**: If contexts were added (`vpid`, `vtid`, `procname`), they appear in each event
6. **No discards**: babeltrace2 shows no `events_discarded` warnings
7. **Timestamp ordering**: Events from same thread are strictly monotonically increasing
8. **Log level filtering**: Events below the configured log level threshold are not recorded

### Quick smoke test

```bash
# Requires: app compiled with tracepoint provider linked
lttng create smoke
lttng enable-event -u 'my_app:*'
lttng add-context -u -t vpid -t vtid -t procname
lttng start
./my_app
lttng stop
lttng destroy
babeltrace2 ~/lttng-traces/smoke-* | head -5
# Verify: provider:event names, field values, context fields present
```

### Python agent smoke test

```bash
# pip install lttngust
lttng create py-test
lttng enable-event -u -a   # enable all UST events
lttng start
python3 -c "
import logging
import lttngust
logging.basicConfig()
logger = logging.getLogger('test')
logger.warning('hello from LTTng-UST python agent')
"
lttng stop && lttng destroy
babeltrace2 ~/lttng-traces/py-test-* | grep "hello"
```

---

## Limitations / Out of Scope

| Item | Status |
|------|--------|
| Kernel tracing | Separate component (lttng-modules); requires root |
| Distributed tracing / span correlation | Not supported; no trace-id propagation across processes |
| OpenTelemetry integration | No native bridge; manual field passing only |
| Dynamic tracepoint insertion (without recompile) | Not supported; tracepoints must be compiled in (unlike BPF/DTrace) |
| Trace encryption | Not provided; files and shared memory are plaintext |
| Cross-host aggregation | Requires lttng-relayd; no built-in clustering |
| Windows/macOS | Linux only |
| Automatic context propagation | No W3C trace-context or baggage propagation |
| Hot-patching tracepoints into running binaries | Not supported; must restart app to add new tracepoints |
| Structured logging (key-value) | CTF fields are typed but flat; no nested JSON-style structures |
| Sampling | All-or-nothing per event type; no probabilistic sampling |
| Process-death data loss (per-PID mode) | If process crashes, unflushed sub-buffer data may be lost |

---

## Evaluation Assessment

### Observability

**Rating: Strong**

| Aspect | Assessment |
|--------|------------|
| **Strengths** | Sub-microsecond per-event cost enables always-on production tracing. Nanosecond timestamps. Typed fields preserve full data fidelity (no string formatting). Correlatable with kernel traces via shared timeline. Live tracing via relayd. Python/Java agent bridges capture existing logging without code changes. Trace Compass provides rich visualization. |
| **Gaps** | No built-in metrics aggregation — events only. No alerting surface. No distributed trace correlation across services. No automatic instrumentation discovery. Requires explicit tracepoint placement by developers. |
| **Implementations must add** | Metrics derivation pipelines, distributed tracing bridges, automatic instrumentation (e.g., via LD_PRELOAD wrappers), alerting integration. |

### Security

**Rating: Moderate**

| Aspect | Assessment |
|--------|------------|
| **Strengths** | Non-root operation — per-user session daemon provides privilege separation. Shared memory ring buffers use owner-only permissions. Unix socket registration prevents cross-user tracing. Tracepoints are compiled in (no code injection vector). Consumer daemon isolation from traced processes. |
| **Gaps** | No encryption of trace data at rest or in transit. No authentication for relayd network streaming. No audit trail of session operations. Shared memory paths in `/dev/shm` are predictable. No data classification or field-level redaction. |
| **Implementations must add** | TLS for relayd, trace file encryption, sensitive field redaction policies, session operation audit logging. |

### Identity Management

**Rating: Weak**

| Aspect | Assessment |
|--------|------------|
| **Strengths** | `vpid`/`vtid`/`procname`/`pthread_id` contexts attribute events to processes and threads. UID-based session isolation maps to OS user identity. |
| **Gaps** | No application-level identity (user sessions, request IDs, tenant IDs) unless manually added as tracepoint fields. No concept of AI agent identity. No session linking across process restarts. No principal binding between trace sessions and authenticated operators. |
| **Implementations must add** | Application-layer identity fields in tracepoints, correlation with authentication systems, operator identity binding for session management, request-scoped trace IDs. |

### Reliability

**Rating: Strong**

| Aspect | Assessment |
|--------|------------|
| **Strengths** | Wait-free fast path — no possibility of priority inversion or deadlock. Configurable overflow: discard (with counter) or overwrite. Atomic event writes — no partial events. Consumer reads in batch (full sub-buffers) — efficient and reliable. Per-UID buffers survive individual process crashes. Snapshot mode enables flight-recorder pattern. Trigger framework for autonomous management. |
| **Gaps** | Per-PID mode loses unflushed data on process crash. Session daemon is single point of failure. No built-in replication. No guaranteed delivery to remote collectors (best-effort streaming). Consumer daemon crash loses in-flight data. |
| **Implementations must add** | Daemon supervision (systemd), per-UID mode for crash resilience, disk space monitoring, consumer redundancy, graceful degradation on buffer pressure. |

### Accuracy

**Rating: Strong**

| Aspect | Assessment |
|--------|------------|
| **Strengths** | Binary CTF format preserves exact field values — no string truncation or formatting loss. Hardware timestamps (TSC/monotonic) with nanosecond precision. Typed fields prevent type confusion. `events_discarded` counter provides explicit loss signal. Metadata stream self-describes all event layouts — no schema drift without detection. |
| **Gaps** | Filter bytecode errors fail silently (event not recorded, no error reported to app). No validation that tracepoint arguments match field types at runtime (compile-time only). Clock source may not be monotonic on all platforms (rare). Per-PID buffers have no cross-thread ordering guarantee without post-hoc sort. |
| **Implementations must add** | Filter validation tooling, runtime type checking (debug mode), cross-thread timestamp reconciliation verification. |

---

## Assessment Summary

| Dimension | Rating | Key Gap |
|-----------|--------|---------|
| Observability | Strong | No distributed trace correlation; events only, no metrics/alerting |
| Security | Moderate | No encryption at rest/in-transit; no relayd authentication |
| Identity | Weak | No application-level or operator identity; PID-level only |
| Reliability | Strong | Per-PID mode data loss on crash; session daemon SPOF |
| Accuracy | Strong | Filter errors fail silently; no runtime type validation |
