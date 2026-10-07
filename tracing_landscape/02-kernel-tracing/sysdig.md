# AAIF Reference Architecture: sysdig (open source)

| Field | Value |
|-------|-------|
| **Subject** | [sysdig (OSS)](https://github.com/draios/sysdig) |
| **Version** | 0.38.x (libs/driver API-locked) |
| **Date** | 2026-09-21 |

---

## Objective

Demonstrates how the open-source `sysdig` tool captures the complete kernel syscall stream via an eBPF probe or kernel module, enriches every event with process/container/Kubernetes state through the shared `libscap`/`libsinsp` libraries, and lets operators record, filter, and replay system activity — functioning as a system-level tracer (strace/tcpdump for the whole machine) that is the capture-and-inspection sibling of the [Falco](falco.md) detection engine.

---

## Scope / Zoom Level

**System layer — kernel syscall source through userspace enrichment to interactive capture/replay.**

sysdig sits at the same layer as [Falco](falco.md) and shares its entire lower stack: the kernel driver (modern eBPF CO-RE / legacy eBPF / kernel module), `libscap` (capture), and `libsinsp` (state and enrichment). Where Falco *evaluates* the enriched event stream against rules to *detect*, sysdig *records and inspects* it — writing full `.scap` capture files, replaying them offline, filtering with the same field syntax, and running "chisels" (Lua analysis scripts) over the stream. It is a tracing/forensics tool, not a security policy engine and not a statistical profiler.

---

## Prerequisites

| Component | Version / Pinned | Notes |
|-----------|-----------------|-------|
| sysdig (OSS) | 0.38.x | CLI (`sysdig`) + ncurses UI (`csysdig`); version-coupled to libs/driver API |
| Driver | modern eBPF **or** legacy eBPF **or** kernel module | Modern eBPF needs kernel ≥ 5.8 (CO-RE, BPF ring buffer) |
| Linux kernel | ≥ 5.8 for modern eBPF; ≥ 4.14 for legacy eBPF / kmod | `CONFIG_BPF`, `CONFIG_BPF_SYSCALL`, BTF for CO-RE |
| Privileges | `CAP_BPF`+`CAP_PERFMON`+`CAP_SYS_RESOURCE` (modern eBPF) or privileged for kmod | Least-privilege possible with modern eBPF |
| Shared libs | `libscap`, `libsinsp` (the "libs") | Same foundation as Falco; version-locked to the driver |
| Chisels (optional) | Bundled Lua scripts | e.g. `topfiles_bytes`, `spy_users`, `httptop` |
| Container runtime (optional) | Docker/containerd/CRI-O | For container/image enrichment |
| Kubernetes (optional) | Any supported | For pod/namespace/label enrichment |

---

## Architecture Diagram

```
┌───────────────────────────────────────────────────────────────────────────┐
│                              KERNEL SPACE                                   │
│  syscalls (execve, open, read, write, connect, accept, ...) ──┐             │
│                                                               ▼             │
│  ┌───────────────────────────────────────────────────────────────────┐    │
│  │  Shared driver (same as Falco):                                    │    │
│  │   • modern eBPF probe (CO-RE, ring buffer)  [preferred]            │    │
│  │   • legacy eBPF probe  •  kernel module (scap.ko)                  │    │
│  └───────────────────────────────┬───────────────────────────────────┘    │
└───────────────────────────────────┼─────────────────────────────────────────┘
                                    │ per-CPU ring buffers
┌───────────────────────────────────▼─────────────────────────────────────────┐
│                              USERSPACE (sysdig)                               │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  libscap — capture layer                                            │    │
│  │  • drains buffers, decodes raw syscalls                             │    │
│  │  • WRITE/READ .scap capture files (record + replay)                 │    │
│  └───────────────────────────────┬─────────────────────────────────────┘    │
│                                   ▼                                            │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  libsinsp — state & enrichment                                      │    │
│  │  • thread/process + fd tables, container & k8s metadata             │    │
│  │  • filter fields: proc.name, fd.name, evt.type, container.id, ...   │    │
│  └───────────────────────────────┬─────────────────────────────────────┘    │
│                                   ▼                                            │
│  ┌───────────────────┐  ┌───────────────────┐  ┌────────────────────────┐   │
│  │  Filter + format  │  │  Chisels (Lua)    │  │  csysdig (ncurses UI)  │   │
│  │  -p output spec   │  │  spy_users,       │  │  live views: procs,    │   │
│  │  filter exprs     │  │  topfiles_bytes,  │  │  connections, files    │   │
│  └─────────┬─────────┘  │  httptop, ...     │  └────────────────────────┘   │
│            │            └───────────────────┘                                │
│            ▼                                                                   │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  Output: stdout (text) │ JSON (-j) │ .scap file (-w) │ replay (-r)   │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
└───────────────────────────────────────────────────────────────────────────┘
```

---

## Instrumentation Walkthrough

### What is captured

| Category | Data Captured |
|----------|---------------|
| **Every syscall** | enter/exit for the full syscall set (unless filtered): exec, file I/O, network, IPC, signals, mmap, etc. |
| **Syscall arguments** | Decoded parameters (fd, path, buffer sizes, flags, socket tuples, return values) |
| **Process context** | PID/TID, comm, exe, args, cwd, parent lineage, user/group |
| **FD context** | fd type, file path, socket 5-tuple, protocol |
| **Container/K8s context** | container id/name/image; pod/namespace/labels when available |
| **I/O payloads (optional)** | Actual read/write buffer contents with `-X`/`evt.buffer` (data-exfil-sensitive) |
| **Capture file** | Complete `.scap` record for offline replay and analysis |

### The mechanism

1. **Shared driver + libs.** sysdig loads the same driver as Falco and drains per-CPU ring buffers via `libscap`; `libsinsp` maintains live process/fd/container/k8s state and exposes the same filter fields (`proc.name`, `fd.name`, `evt.type`, `container.id`, `k8s.pod.name`, ...).

2. **Filtering.** A filter expression (identical syntax to Falco conditions) selects which events to show/record, e.g. `fd.name contains /etc and evt.type=open`.

3. **Formatting.** `-p` output specifiers render selected fields per event; `-j` emits JSON. `csysdig` provides live ncurses "views" (top processes, connections, files, containers).

4. **Recording & replay.** `-w file.scap` records the (optionally filtered) stream to a capture file; `-r file.scap` replays it later with different filters/chisels — decoupling capture from analysis for forensics.

5. **Chisels.** Lua scripts (`-c <chisel>`) run over the stream for higher-level analysis (`spy_users`, `topfiles_bytes`, `httptop`, `echo_fds`), aggregating raw syscalls into human-meaningful reports.

### Data format produced

- **Text output:** one formatted line per event via the default or `-p` template.
- **JSON output (`-j`):** structured per-event objects with resolved fields.
- **`.scap` capture:** self-contained binary syscall capture (the same format `libscap` writes for Falco/`libsinsp`), replayable and portable.

---

## Sample Trace Output

### Default text output (live)

```
254internal 16:41:07.882140321 3 nginx (4521) < open fd=12(<f>/etc/nginx/nginx.conf) name=/etc/nginx/nginx.conf flags=1(O_RDONLY) mode=0
254internal 16:41:07.882201110 3 nginx (4521) > read fd=12(<f>/etc/nginx/nginx.conf) size=4096
254internal 16:41:07.882260901 3 nginx (4521) < read data=user www-data; worker_processes auto; ...
254internal 16:41:07.885003221 5 curl  (4590) < connect fd=3(<4t>10.0.0.7:443) tuple=10.0.0.5:51022->10.0.0.7:443
```

### JSON output (`sysdig -j`)

```json
{
  "evt.num": 254011,
  "evt.time": "2026-09-21T20:41:07.882140321Z",
  "evt.cpu": 3,
  "evt.dir": "<",
  "evt.type": "open",
  "proc.name": "nginx",
  "proc.pid": 4521,
  "proc.ppid": 4500,
  "thread.tid": 4533,
  "user.name": "www-data",
  "fd.name": "/etc/nginx/nginx.conf",
  "fd.type": "file",
  "evt.arg.flags": "O_RDONLY",
  "container.id": "3f9a1c2b7d40",
  "container.image.repository": "registry.internal/edge-proxy",
  "k8s.ns.name": "prod",
  "k8s.pod.name": "edge-proxy-6d5c9f7b8-abcde"
}
```

### Chisel output (`sysdig -c topfiles_bytes`)

```
Bytes     Filename
--------------------------------------------------------------------------------
4.12M     /var/log/nginx/access.log
1.88M     /var/lib/app/cache/index.db
612.4K    /etc/nginx/nginx.conf
94.2K     /proc/net/tcp
```

---

## Cost Profile

### LLM token cost

**Not applicable.** sysdig is a syscall tracer with no AI/LLM component. It is relevant to AI agent infrastructure as a forensic/tracing tool for the *execution environment* of an agent (e.g. capturing exactly which files/sockets an agent's sandbox touched).

### Compute/IO overhead per operation

| Factor | Overhead | Notes |
|--------|----------|-------|
| Full-stream capture (modern eBPF) | Higher than Falco — captures *all* events, not just matches | Filter aggressively to reduce cost |
| Filtered capture | Proportional to matched-event rate | Kernel-side filtering (eBPF) helps |
| Enrichment | µs-scale per event | Same table lookups as Falco |
| Payload capture (`-X`) | Elevated (copies buffers) | Data-heavy; use only when needed |
| Replay (`-r`) | Offline; no live overhead | Analysis cost only |

### Storage growth rate

| Scenario | Data Rate | Notes |
|----------|-----------|-------|
| Unfiltered `.scap` on busy host | High — MB–GB/min | Every syscall is recorded |
| Filtered capture | Much lower | e.g. only `evt.type in (open,connect,execve)` |
| Live text/JSON to stdout | Depends on filter | No file unless `-w` |
| With payloads (`-X`) | Substantially higher | Buffer contents inflate records |

---

## Validation Criteria

1. **Driver loads:** `sysdig --version` reports engine/driver; live capture starts without error.
2. **Live events flow:** `sysdig proc.name=cat` then running `cat` in another shell shows its syscalls.
3. **Enrichment present:** events include container/k8s fields when run in a container/pod.
4. **Filtering works:** a filter expression restricts output to matching events only.
5. **Record + replay round-trip:** `sysdig -w run.scap` then `sysdig -r run.scap` reproduces the events.
6. **JSON valid:** `sysdig -j` emits one valid JSON object per event.
7. **Chisels run:** `sysdig -cl` lists chisels; `sysdig -c topfiles_bytes` produces a ranked table.

### Quick smoke test

```bash
# Confirm engine + driver
sysdig --version

# Capture 5s of file opens system-wide to a file
sudo timeout 5 sysdig -w opens.scap "evt.type=open"

# Replay and show top files by bytes
sysdig -r opens.scap -c topfiles_bytes | head
# Expect: a ranked list of files touched during the capture window
```

---

## Limitations / Out of Scope

| Item | Status |
|------|--------|
| Threat detection / alerting | Not its job — that is [Falco](falco.md); sysdig captures/inspects, it does not evaluate rules |
| Prevention / enforcement | None — read-only observation |
| Statistical CPU/GPU profiling | Not a sampler; use perf/Tracy for profiling |
| Distributed tracing / trace-id propagation | Not a distributed tracer |
| Non-Linux hosts | Linux-centric, kernel-driver dependent |
| Always-on full capture at scale | Full-stream capture is expensive; intended for targeted/forensic sessions |
| Standardized output format | `.scap` is libs-specific; JSON export for interchange |
| Transport/at-rest security | `.scap` files are unencrypted and may contain payloads/secrets |
| Deep application-layer decode | Sees syscalls + raw buffers, not protocol-aware DPI (that is Wireshark territory) |
| AI/ML analysis | None built in; chisels are deterministic Lua |

---

## Evaluation Assessment

### Observability

**Rating: Strong**

| Aspect | Assessment |
|--------|------------|
| **Strengths** | Complete, ground-truth visibility into system behavior: every syscall with decoded arguments, enriched with process lineage, container, and Kubernetes context. Record/replay decouples capture from analysis (forensics-friendly). `csysdig` gives live drill-down views; chisels turn raw events into higher-level reports. Same field vocabulary as Falco, so investigation skills transfer. |
| **Gaps** | Not a metrics/dashboard/alerting system — it is an interactive/forensic tracer. Full capture is heavy; long-horizon observability needs filtering and rotation. No time-series profiling or distributed traces. |
| **Implementations must add** | Capture rotation/retention, downstream indexing/search, and integration with monitoring backends for anything beyond ad-hoc investigation. |

### Security

**Rating: Weak**

| Aspect | Assessment |
|--------|------------|
| **Strengths** | Modern eBPF driver enables least-privilege capture vs a privileged kmod. Useful *for* security investigations (incident forensics). Kernel-sourced events are hard for userspace to forge. |
| **Gaps** | sysdig itself is a powerful data-exfiltration surface: full syscall capture with `-X` payloads exposes file contents, credentials in argv, and socket data. `.scap` files are unencrypted, unsigned, and highly sensitive. No built-in access control on captures. Running it requires elevated kernel access — a valuable target. It observes but does not protect. |
| **Implementations must add** | Strict access control and audit around who may capture, encryption/signing of `.scap` artifacts, payload redaction policies, and network isolation of capture storage. |

### Identity Management

**Rating: Moderate**

| Aspect | Assessment |
|--------|------------|
| **Strengths** | Rich per-event workload identity: user/group (name+id), full process lineage, container id/name/image, Kubernetes pod/namespace/labels. Strong attribution of *which principal/workload* performed an action. |
| **Gaps** | No operator identity for who ran the capture (delegated to host access controls). Identity is OS-resolved and thus spoofable at the app layer. No cryptographic principal binding, no session/provenance signing, no AI/agent identity concept. |
| **Implementations must add** | Operator/analyst identity and audit around capture sessions, cryptographic provenance on `.scap` files, and agent/service identity correlation if feeding a broader fabric. |

### Reliability

**Rating: Moderate**

| Aspect | Assessment |
|--------|------------|
| **Strengths** | Per-CPU ring buffers with a drain path; modern eBPF ring buffer reduces loss. Drop counters expose loss. Deterministic replay from `.scap` gives reproducible analysis. Per-CPU ordering preserved. |
| **Gaps** | Full-stream capture on busy hosts is prone to event drops under load (reported, not prevented) — an incomplete forensic record. `.scap` is a single local file with no rotation/replication built in. No delivery guarantee to any downstream. Backpressure manifests as drops by design. |
| **Implementations must add** | Drop-rate monitoring and capacity tuning, capture rotation/replication, and durable handoff to storage for long or high-rate sessions. |

### Accuracy

**Rating: Strong**

| Aspect | Assessment |
|--------|------------|
| **Strengths** | Events come from authoritative kernel tracepoints — exact, not sampled. Arguments and return values are decoded faithfully; nanosecond timestamps. `libsinsp` ties each event to real process/container/k8s state. Replay is deterministic, enabling reproducible investigation. Modern eBPF CO-RE keeps field semantics stable across kernels. |
| **Gaps** | Enrichment can be incomplete during races (short-lived processes, not-yet-resolved container metadata). Dropped events under load mean an incomplete record. Identity fields reflect OS resolution (misleading under privilege manipulation). Chisel accuracy depends on the script. |
| **Implementations must add** | Handling of enrichment races, drop-aware completeness accounting, and validation of chisel logic for derived metrics. |

---

## Assessment Summary

| Dimension | Rating | Key Gap |
|-----------|--------|---------|
| Observability | Strong | Forensic/interactive tracer, not metrics/alerting; full capture is heavy |
| Security | Weak | Powerful exfil surface; unencrypted/unsigned `.scap` with payloads; observation not protection |
| Identity | Moderate | Rich but OS-resolved (spoofable) attribution; no operator/AI identity or provenance |
| Reliability | Moderate | Event drops under load; single unrotated capture file; no delivery guarantee |
| Accuracy | Strong | Kernel-exact events, bounded by enrichment races and drops under load |
