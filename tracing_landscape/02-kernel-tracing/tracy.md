# AAIF Reference Architecture: Tracy Profiler

| Field | Value |
|-------|-------|
| **Subject** | [Tracy Profiler](https://github.com/wolfpld/tracy) |
| **Version** | 0.11.x |
| **Date** | 2026-09-21 |

---

## Objective

Demonstrates how Tracy combines compile-time source instrumentation (scoped "zones") with statistical call-stack sampling to produce nanosecond-resolution, real-time frame profiles that stream live from an instrumented client process to a remote profiler server over TCP, correlating CPU, GPU, lock, memory, and application-defined telemetry on a single time axis.

---

## Scope / Zoom Level

**Orchestration layer — single-process (and multi-thread/multi-GPU) instrumentation with a live client→server streaming pipeline.**

Tracy sits above hardware/kernel profilers (perf, ftrace) and below distributed tracing systems. It operates *inside* one instrumented process: the developer annotates source with zone macros, and a linked-in client library captures events into lock-free per-thread queues, then streams them to a separate profiler server (the GUI or a headless capture tool). It is not a distributed tracer — there is no trace-id propagation across services — but it correlates many concurrent producers (threads, GPU contexts, lock contention, allocator) within a single application's timeline. It spans from userspace instrumentation macros down to OS-level context-switch and sampling data (via kernel facilities where available).

---

## Prerequisites

| Component | Version / Pinned | Notes |
|-----------|-----------------|-------|
| Tracy | 0.11.x (client + server must match protocol version) | Client lib and server GUI are protocol-locked; mismatched versions refuse to connect |
| C/C++ compiler | C++11 minimum (C++17 recommended) | Client is a single `TracyClient.cpp` + headers |
| Build flag | `-DTRACY_ENABLE` | Without it, all macros compile to nothing (zero overhead) |
| Server GUI deps | GLFW + FreeType, or Wayland/EGL | For `tracy-profiler`; requires GPU for the ImGui frontend |
| CMake / build system | CMake ≥ 3.16 (for provided build) | Or vendor `public/` sources directly |
| Kernel (Linux) | perf_event access; `CAP_SYS_ADMIN` or `perf_event_paranoid ≤ 1` | For context-switch capture and sampling |
| GPU API | Vulkan 1.1+, OpenGL 3.2+, D3D11/12, OpenCL, or Metal | For GPU zone capture; optional |
| Network | TCP port 8086 (default) reachable client→server | Or use `capture` tool to write `.tracy` file |

---

## Architecture Diagram

```
┌───────────────────────────────────────────────────────────────────────────┐
│                    INSTRUMENTED CLIENT PROCESS                              │
│                    (application linked with TracyClient)                    │
│                                                                             │
│  Source instrumentation (compile-time macros, no-ops when disabled)         │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │  ZoneScoped;         // RAII CPU zone (begin at {, end at })         │  │
│  │  FrameMark;          // frame boundary marker                       │  │
│  │  TracyLockable(m,mx) // instrumented std::mutex                     │  │
│  │  TracyAlloc/Free     // memory allocation tracking                  │  │
│  │  TracyPlot("q",n)    // named numeric plot                          │  │
│  │  TracyMessage("...") // log-style message                          │  │
│  │  TracyGpuZone(...)   // GPU zone (VK/GL/D3D/CL/Metal)               │  │
│  └───────────────────────────────┬─────────────────────────────────────┘  │
│                                   │ RDTSC timestamp + event enqueue          │
│                                   ▼                                          │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │  Per-thread lock-free MPSC queues (Profiler singleton)              │  │
│  │  • Zone begin/end, source-loc pointers (interned), thread id        │  │
│  │  • Callstack capture (optional, on demand)                          │  │
│  └───────────────────────────────┬─────────────────────────────────────┘  │
│                                   │                                          │
│  ┌────────────────────┐   ┌───────▼──────────┐   ┌───────────────────────┐ │
│  │ OS sampler         │   │ Serialize +      │   │ GPU context calibration│ │
│  │ • ctx switches     │──▶│ LZ4-compress     │◀──│ • timestamp queries     │ │
│  │ • perf sampling    │   │ (worker thread)  │   │ • GPU↔CPU clock align   │ │
│  │ • kernel callstack │   └───────┬──────────┘   └───────────────────────┘ │
│  └────────────────────┘           │                                         │
│                                   │ TCP stream (port 8086)  OR  file sink    │
└───────────────────────────────────┼─────────────────────────────────────────┘
                                    │
              ┌─────────────────────┼─────────────────────┐
              │                     │                     │
              ▼                     ▼                     ▼
   ┌────────────────────┐  ┌────────────────────┐  ┌────────────────────┐
   │  tracy-profiler    │  │  tracy-capture     │  │  (any listener on   │
   │  (ImGui GUI server)│  │  (headless → file) │  │   the wire protocol)│
   │  • live timeline   │  │  • CI/automated    │  └────────────────────┘
   │  • flame/statistics│  │  • writes .tracy   │
   │  • memory/locks    │  └─────────┬──────────┘
   │  • find-zone       │            │
   └─────────┬──────────┘            ▼
             │              ┌────────────────────┐
             ▼              │  .tracy trace file │
   ┌────────────────────┐   │  (compressed, self-│
   │  On-demand queries │   │   contained)       │
   │  back to client:   │   └─────────┬──────────┘
   │  symbol resolution,│             │
   │  source, callstacks│             ▼
   └────────────────────┘   ┌────────────────────────────────────────────┐
                            │ tracy-csvexport / import-chrome /           │
                            │ import-fuchsia / update (offline analysis)  │
                            └────────────────────────────────────────────┘
```

---

## Instrumentation Walkthrough

### What is captured

| Category | Data Captured |
|----------|---------------|
| **CPU zones** | Scoped begin/end with source location (file, line, function), name, color, thread id, nanosecond timestamps; optional per-zone text/value payloads |
| **Frame markers** | Frame boundaries (named/discontinuous frames supported) for FPS and frame-time analysis |
| **Sampling** | Statistical call-stack samples from OS sampler (`perf_event` on Linux) — attributes time to functions without manual instrumentation |
| **Context switches** | Thread on/off-CPU transitions, core assignment, wait reasons (kernel-sourced) |
| **Locks** | Contended/uncontended acquire/release for instrumented mutexes; who holds, who waits |
| **Memory** | Alloc/free events with size, address, call stack; pool-scoped tracking; leak detection |
| **GPU zones** | GPU-side begin/end timestamps for Vulkan/OpenGL/D3D11/12/OpenCL/Metal, calibrated to CPU clock |
| **Plots** | Arbitrary named numeric time-series (queue depth, entity count, temperature, etc.) |
| **Messages** | Timestamped freeform log lines, optionally colored, per-thread |
| **Call stacks** | On-demand or per-zone stack capture; symbols resolved lazily by server query |

### The mechanism

1. **Compile-time macros.** Instrumentation is C/C++ macros. With `TRACY_ENABLE` undefined, `ZoneScoped` and friends expand to nothing — literally zero runtime cost and zero code size impact. This is the key gate: instrumentation ships in release binaries only when explicitly enabled.

2. **Interned source locations.** Each `ZoneScoped` references a `static const SourceLocationData` (file/line/function/name/color) emplaced at compile time. Only a *pointer* is enqueued per event, not the strings — the server resolves the pointer to text once.

3. **RDTSC timestamps.** The client reads the CPU timestamp counter directly (invariant TSC) for sub-nanosecond-cost, nanosecond-resolution timing, avoiding syscalls on the hot path.

4. **Lock-free per-thread queues.** Each thread enqueues events into its own MPSC queue. A dedicated profiler worker thread drains queues, serializes, LZ4-compresses, and pushes to the transport. No locks on the instrumented hot path.

5. **Transport.** The worker streams the compressed event log over TCP to a connected server (default port 8086), or a headless `tracy-capture` writes it to a `.tracy` file. The server can issue *reverse queries* to the client for symbol names, source snippets, and deferred call-stack resolution.

6. **Sampling + context switches.** On Linux, Tracy opens `perf_event` to collect periodic call-stack samples and scheduler context-switch events, interleaving hardware-observed timing with the manual zones on the same timeline.

7. **GPU calibration.** GPU zones use API timestamp queries; Tracy periodically calibrates the GPU clock against the CPU clock so GPU spans align with CPU spans on one axis.

### Data format produced

- **On-the-wire protocol:** a versioned, LZ4-compressed binary event stream. Protocol version is compiled into both ends; mismatched versions refuse the handshake.
- **`.tracy` capture file:** a self-contained compressed binary trace (events + string/source-location tables + symbol data), openable by the profiler GUI and export tools.
- **Export bridges:** `tracy-csvexport` (zone statistics to CSV), and importers from Chrome Trace JSON (`import-chrome`) and Fuchsia format (`import-fuchsia`) into `.tracy`.

---

## Sample Trace Output

Tracy's native format is compressed binary; the closest human-readable renderings are the CSV export and the Chrome-Trace interchange it imports/exports. A realistic zone-statistics CSV export:

```csv
name,src_file,src_line,total_ns,counts,mean_ns,min_ns,max_ns,std_ns
Render::SubmitFrame,src/render/frame.cpp,142,48213004,600,80355,61200,214880,18422
Physics::Step,src/sim/physics.cpp,88,31004556,600,51674,44010,98120,7233
AssetStream::Decode,src/io/assets.cpp,301,12880412,148,87030,52110,402990,41220
Net::PollSockets,src/net/poll.cpp,55,2044109,600,3406,1980,29940,2210
```

A realistic per-zone / GPU / lock event view, rendered as Chrome-Trace-style JSON (the interchange format Tracy can import and approximate on export):

```json
{
  "traceEvents": [
    {
      "name": "Render::SubmitFrame",
      "cat": "cpu",
      "ph": "X",
      "ts": 51234567.890,
      "dur": 80.355,
      "pid": 4521,
      "tid": 4533,
      "args": {
        "src": "src/render/frame.cpp:142",
        "frame": 10428,
        "color": "0x22AA88"
      }
    },
    {
      "name": "vkQueueSubmit",
      "cat": "gpu",
      "ph": "X",
      "ts": 51234568.010,
      "dur": 63.400,
      "pid": 4521,
      "tid": "GPU:0/graphics",
      "args": {
        "gpu_context": "Vulkan[NVIDIA RTX]",
        "cpu_gpu_skew_ns": 214
      }
    },
    {
      "name": "lock:g_sceneMutex",
      "cat": "lock",
      "ph": "X",
      "ts": 51234570.100,
      "dur": 4.120,
      "pid": 4521,
      "tid": 4540,
      "args": {
        "state": "wait->hold",
        "blocked_by_tid": 4533,
        "src": "src/render/scene.cpp:77"
      }
    },
    {
      "name": "alloc",
      "cat": "memory",
      "ph": "i",
      "ts": 51234571.220,
      "pid": 4521,
      "tid": 4533,
      "s": "t",
      "args": {
        "addr": "0x7f4a10a20000",
        "size": 262144,
        "pool": "textures",
        "callstack_id": 88213
      }
    },
    {
      "name": "queue_depth",
      "cat": "plot",
      "ph": "C",
      "ts": 51234571.500,
      "pid": 4521,
      "args": { "value": 37 }
    }
  ],
  "meta": {
    "tracy_protocol": 63,
    "capture_program": "game_client",
    "host": "workstation-07",
    "cpu": "invariant-tsc",
    "sampling": "perf_event@1000Hz"
  }
}
```

---

## Cost Profile

### LLM token cost

**Not applicable.** Tracy is a native code profiler with no AI/LLM component. (Its telemetry is highly relevant *below* AI agent runtimes — e.g. profiling an inference server or a C++ agent host — but Tracy itself emits no LLM traffic.)

### Compute/IO overhead per operation

| Operation | Overhead | Notes |
|-----------|----------|-------|
| Zone (disabled, `TRACY_ENABLE` off) | 0 ns | Macro compiles to nothing |
| Zone (enabled, no callstack) | ~1–3 ns enqueue + RDTSC | Lock-free per-thread queue |
| Zone with call-stack capture | ~hundreds ns–µs | Stack walk is the expensive part; use sparingly |
| Memory alloc/free tracking | ~10–50 ns + optional stack walk | Wrap allocator hot path carefully |
| Statistical sampling | Bounded by sample rate (e.g. 1 kHz) | Kernel-side cost, similar to `perf record` |
| GPU zone | 1 timestamp query pair per zone | API-dependent; negligible vs GPU work |
| Serialization/compression | Amortized on dedicated worker thread | LZ4 keeps bandwidth modest |

Whole-program overhead for a well-instrumented real-time app is typically low single-digit percent; pathological instrumentation (a zone in a tight inner loop with call-stack capture) can dominate.

### Storage growth rate

| Scenario | Data Rate | Notes |
|----------|-----------|-------|
| Moderate instrumentation, 60 FPS | ~1–10 MB/min | Zones + frames + plots, LZ4-compressed |
| Heavy zones + memory tracking | ~50–200 MB/min | Every alloc/free is an event |
| Sampling @ 1 kHz + context switches | +tens of MB/min | Scales with thread/core count |
| Live streaming | Bounded by TCP + server RAM | Server holds trace in memory; long captures are RAM-bound |

---

## Validation Criteria

1. **Disabled build is inert:** compiling without `TRACY_ENABLE` produces a binary with no Tracy symbols and no runtime cost (verify with `nm`/size comparison).
2. **Client connects:** with `TRACY_ENABLE`, launching the app and `tracy-profiler` shows a live connection and the app name/host in the connection dialog.
3. **Zones appear:** an instrumented function shows a named zone on the correct thread lane with plausible duration.
4. **Frame markers work:** `FrameMark` produces a frame-time graph; FPS matches an independent measurement.
5. **Sampling active:** on Linux with sufficient `perf_event` privileges, the statistics view shows sampled functions with no manual instrumentation.
6. **GPU alignment:** GPU zones line up under their submitting CPU zones with small, stable CPU↔GPU skew.
7. **Capture round-trips:** `tracy-capture -o run.tracy` then opening `run.tracy` in the GUI reproduces the same timeline; `tracy-csvexport run.tracy` yields non-empty statistics.

### Quick smoke test

```cpp
// main.cpp — build with: g++ -DTRACY_ENABLE main.cpp public/TracyClient.cpp -lpthread -ldl
#include "tracy/Tracy.hpp"
#include <thread>
#include <chrono>

void work() {
    ZoneScoped;                          // named after enclosing function
    std::this_thread::sleep_for(std::chrono::milliseconds(5));
}

int main() {
    for (int i = 0; i < 600; ++i) {
        ZoneScopedN("MainLoopIter");     // explicit name
        work();
        TracyPlot("iteration", (int64_t)i);
        FrameMark;                       // mark end of frame
    }
    return 0;
}
```

```bash
# Terminal 1: start the server (or use tracy-capture for headless)
./tracy-capture -o smoke.tracy &

# Terminal 2: run the instrumented app; it auto-connects to the local server
./a.out

# Verify the capture has content
./tracy-csvexport smoke.tracy | head
# Expect: MainLoopIter and work zones with ~5ms mean, 600 counts
```

---

## Limitations / Out of Scope

| Item | Status |
|------|--------|
| Distributed tracing / cross-service trace-id propagation | Not supported — single-process focus |
| Language coverage | C/C++ first-class; Lua, and community bindings (Rust, Python, others) exist but lag |
| Requires recompilation | Instrumentation is compile-time; no attach-to-running-unmodified-binary zones |
| Transport security | Plaintext TCP by default; no built-in auth or encryption |
| Server memory model | Trace held in RAM; very long captures are bounded by server memory |
| Sampling privileges | Context-switch/sampling need elevated `perf_event` access on Linux |
| Standardized output format | `.tracy` is Tracy-specific; interchange via Chrome-Trace/CSV bridges only |
| Non-desktop GPUs / exotic APIs | GPU capture limited to supported graphics APIs |
| Always-on production fleet telemetry | Designed for dev/profiling sessions, not fleet-wide continuous observability |
| Alerting / SLOs / dashboards | None — this is an interactive profiler, not a monitoring platform |
| AI/ML integration | None built in |
| Retention / rotation policy | No built-in rotation; managed by the operator via capture files |

---

## Evaluation Assessment

### Observability

**Rating: Strong**

| Aspect | Assessment |
|--------|------------|
| **Strengths** | Exceptional intra-process visibility: CPU zones, GPU zones, locks, memory, context switches, statistical sampling, plots, and messages all on one nanosecond-resolution timeline. Live streaming lets you watch behavior as it happens. Combines manual instrumentation (precise, named) with sampling (zero-instrumentation coverage) — few tools do both natively. Find-zone/statistics/flame views turn raw events into actionable analysis. GPU↔CPU correlation is first-class. |
| **Gaps** | No self-observability of the profiler pipeline as exported metrics (queue pressure is visible in-GUI but not emitted). No dashboards, no alerting, no SLO surfaces. Bounded to a single process — no cross-service view. No metrics/log export to external monitoring backends. |
| **Implementations must add** | Continuous/fleet profiling infrastructure, export to monitoring backends, alerting on regression, and correlation across process boundaries if a distributed view is needed. |

### Security

**Rating: Weak**

| Aspect | Assessment |
|--------|------------|
| **Strengths** | Instrumentation is opt-in at compile time (`TRACY_ENABLE`), so production release builds carry nothing unless deliberately enabled — a meaningful blast-radius control. Capture files are local artifacts under operator control. |
| **Gaps** | Client→server transport is plaintext TCP with no authentication, authorization, or encryption — anyone able to reach port 8086 can connect and stream the app's internals (source paths, symbols, memory addresses, plot values). Reverse queries expose source snippets and symbol data. No integrity protection or signing on `.tracy` files. Captures leak sensitive info (function names, file paths, KASLR-adjacent addresses, application data placed in zone text/plots). |
| **Implementations must add** | TLS/mutual-auth or SSH tunneling for the transport, network isolation of the profiler port, access control on capture files, redaction of sensitive zone payloads, and signing/encryption for stored traces. |

### Identity Management

**Rating: Minimal**

| Aspect | Assessment |
|--------|------------|
| **Strengths** | Captures OS-level identity of the workload: process id, thread ids/names, host name, and program name in the connection metadata. GPU context identity (device/queue) is recorded for GPU zones. |
| **Gaps** | No operator identity (who initiated/connected to the profile), no authenticated sessions, no service identity, no principal binding. No AI identity. Connection is anonymous — identity is limited to what the captured process reports about itself. |
| **Implementations must add** | Authenticated profiler connections, operator/session identity binding, provenance metadata on capture files, and service/principal correlation if integrating with a broader identity fabric. |

### Reliability

**Rating: Moderate**

| Aspect | Assessment |
|--------|------------|
| **Strengths** | Lock-free per-thread queues avoid contention and keep the hot path deterministic. Events are timestamped at source with monotonic RDTSC, so ordering per thread is well-defined. LZ4 compression keeps bandwidth manageable to avoid stalls. Headless capture provides a durable `.tracy` artifact independent of the interactive GUI. |
| **Gaps** | No delivery guarantee to the server: if queues saturate or the connection drops, events can be lost with no application-level acknowledgment. Server holds the trace in RAM, so very long sessions risk memory exhaustion. Startup events before the server connects may be buffered subject to limits. Sampling is statistical (rare events missed). No deduplication or replay; a dropped TCP connection ends the live session. |
| **Implementations must add** | Backpressure/loss monitoring and reporting, bounded-buffer policies with explicit drop accounting, durable spooling for long captures, and reconnect/resume semantics for unstable links. |

### Accuracy

**Rating: Strong**

| Aspect | Assessment |
|--------|------------|
| **Strengths** | Manual zones are exact begin/end pairs — no skid — with nanosecond RDTSC timestamps on invariant-TSC hardware. Source locations are interned and unambiguous (file/line/function). GPU zones are clock-calibrated against the CPU, keeping cross-device spans aligned. Context-switch data comes from the kernel scheduler, so on/off-CPU accounting is authoritative. |
| **Gaps** | Statistical sampling is approximate (accuracy scales with sample count and rate). RDTSC accuracy degrades without invariant TSC or across poorly synchronized cores. GPU↔CPU calibration carries residual skew. Values placed in plots/zone-text are only as accurate as the instrumentation the developer wrote. Symbol/source resolution depends on debug info availability. |
| **Implementations must add** | Confidence bounds on sampled statistics, invariant-TSC/clock-quality validation, calibration-skew reporting for GPU zones, and debug-info completeness checks for reliable symbolization. |

---

## Assessment Summary

| Dimension | Rating | Key Gap |
|-----------|--------|---------|
| Observability | Strong | Single-process only; no export/alerting/dashboards or cross-service view |
| Security | Weak | Plaintext, unauthenticated TCP transport; unencrypted, unsigned captures leak internals |
| Identity | Minimal | Only workload-reported PID/TID/host; no operator/service/AI identity or auth |
| Reliability | Moderate | No delivery guarantee; RAM-bound server; loss on saturation/disconnect |
| Accuracy | Strong | Sampling is statistical; residual GPU↔CPU skew; depends on invariant TSC and debug info |
