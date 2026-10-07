# AAIF Reference Architecture: Falco

| Field | Value |
|-------|-------|
| **Subject** | [Falco](https://github.com/falcosecurity/falco) |
| **Version** | 0.39.x (libs/driver API-locked) |
| **Date** | 2026-09-21 |

---

## Objective

Demonstrates how Falco turns a real-time kernel syscall stream (via eBPF or a kernel module) into enriched, container- and Kubernetes-aware security events, evaluates them against a YAML rules engine, and emits prioritized alerts to pluggable outputs — providing runtime threat detection for hosts, containers, and orchestrated workloads.

---

## Scope / Zoom Level

**System layer — kernel event source through a userspace enrichment/rules engine to alert outputs.**

Falco spans from the kernel (a syscall-capturing driver: modern eBPF CO-RE probe, legacy eBPF, or `falco.ko` kernel module) up through the userspace libraries (`libscap` capture, `libsinsp` state/enrichment), a rules-evaluation engine, and an output layer. It is a *detection* system, not a profiler or tracer: it observes system behavior to flag policy violations and threats. Beyond syscalls, its plugin framework ingests non-syscall event sources (Kubernetes Audit Logs, cloud audit trails), positioning Falco as a runtime security decision point rather than a raw telemetry recorder.

> **Sysdig lineage.** Falco was created by Sysdig Inc. and shares its foundation with the open-source [sysdig](sysdig.md) CLI: both build on the same **libs** (`libscap` capture + `libsinsp` state/enrichment) and the same set of kernel drivers (modern eBPF / legacy eBPF / kernel module). The division of labor is: **sysdig** *records and inspects* the full syscall stream (a system-level tracer, akin to strace/tcpdump for syscalls), whereas **Falco** *evaluates* that same enriched stream against a rules engine to *detect* threats. See [sysdig.md](sysdig.md) for the tracing-focused sibling.

---

## Prerequisites

| Component | Version / Pinned | Notes |
|-----------|-----------------|-------|
| Falco | 0.39.x | Userspace engine + rules; version-coupled to libs/driver API |
| Driver | modern eBPF **or** legacy eBPF **or** kernel module | Modern eBPF needs kernel ≥ 5.8 (CO-RE, ring buffer) |
| Linux kernel | ≥ 5.8 for modern eBPF; ≥ 4.14 for legacy eBPF / kmod | `CONFIG_BPF`, `CONFIG_BPF_SYSCALL`, BTF (`CONFIG_DEBUG_INFO_BTF`) for CO-RE |
| Privileges | `CAP_BPF`+`CAP_PERFMON`+`CAP_SYS_RESOURCE` (modern eBPF) or privileged for kmod | Least-privilege possible with modern eBPF |
| Falco rules | `falco_rules.yaml` (default ruleset) | Versioned; loaded from `/etc/falco/` |
| falcoctl | 0.9.x | Rules/plugin artifact management and updates |
| Falcosidekick | 2.x (optional) | Fan-out to Slack, Elastic, Loki, webhook, etc. |
| Plugins (optional) | k8saudit, cloudtrail, etc. | For non-syscall event sources |
| Kubernetes (optional) | Any supported | For k8s metadata enrichment and audit-log source |

---

## Architecture Diagram

```
┌───────────────────────────────────────────────────────────────────────────┐
│                              KERNEL SPACE                                   │
│                                                                             │
│  syscalls (execve, open, connect, setuid, ptrace, ...) ──┐                  │
│                                                          ▼                  │
│  ┌───────────────────────────────────────────────────────────────────┐    │
│  │  Falco driver (one of):                                            │    │
│  │   • modern eBPF probe (CO-RE, BPF ring buffer)   [preferred]       │    │
│  │   • legacy eBPF probe (perf buffer)                                │    │
│  │   • kernel module falco.ko                                         │    │
│  │  Captures syscall enter/exit into per-CPU ring/perf buffers         │    │
│  └───────────────────────────────┬───────────────────────────────────┘    │
└───────────────────────────────────┼─────────────────────────────────────────┘
                                    │ mmap ring buffers
┌───────────────────────────────────▼─────────────────────────────────────────┐
│                              USERSPACE (falco)                                │
│                                                                               │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  libscap — capture layer                                            │    │
│  │  • drains ring buffers, decodes raw syscall events                  │    │
│  │  • can read/write .scap capture files                               │    │
│  └───────────────────────────────┬─────────────────────────────────────┘    │
│                                   ▼                                            │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  libsinsp — state & enrichment                                      │    │
│  │  • thread/process table, fd table, container detection              │    │
│  │  • Kubernetes metadata (pod/ns/labels), user/group resolution       │    │
│  │  • exposes filter fields:  proc.name, fd.name, container.id, k8s.*  │    │
│  └───────────────────────────────┬─────────────────────────────────────┘    │
│                                   │                                            │
│   plugins ─────────────┐          │                                            │
│   (k8saudit, cloudtrail│──────────┤  (alternative event sources)               │
│    via plugin API)     │          │                                            │
│                        ▼          ▼                                            │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  Rules Engine                                                       │    │
│  │  • YAML rules: condition (filter expr) + output + priority          │    │
│  │  • macros (reusable conditions) + lists (value sets)                │    │
│  │  • matches enriched event → renders output string + fields          │    │
│  └───────────────────────────────┬─────────────────────────────────────┘    │
│                                   ▼                                            │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  Output channels (per priority)                                     │    │
│  │  stdout │ file │ syslog │ program │ HTTP/webhook │ gRPC API          │    │
│  └───────────────────────────────┬─────────────────────────────────────┘    │
└───────────────────────────────────┼─────────────────────────────────────────┘
                                    │
                                    ▼
                   ┌────────────────────────────────────┐
                   │  Falcosidekick (optional fan-out)   │
                   │  Slack, Elastic, Loki, S3, SIEM,    │
                   │  PagerDuty, webhook, FaaS, ...      │
                   └────────────────────────────────────┘
```

---

## Instrumentation Walkthrough

### What is captured

| Category | Data Captured |
|----------|---------------|
| **Syscall events** | Enter/exit for a configured syscall set: process exec, file open/read/write, network connect/accept, privilege changes (setuid/setgid), ptrace, mount, chmod, symlink, etc. |
| **Process context** | PID/TID, comm, exe path, args, cwd, parent lineage, user/group (name + id), TTY, container entrypoint |
| **File descriptor context** | fd type, file path, socket 5-tuple, protocol |
| **Container context** | Container id/name/image/repository, container runtime |
| **Kubernetes context** | Pod name, namespace, labels, deployment (when k8s metadata available) |
| **Plugin sources** | Kubernetes Audit events, cloud audit trails (e.g. CloudTrail) via the plugin API |
| **Alert record** | Matched rule name, priority, rendered output message, resolved output fields, timestamp, source, tags |

### The mechanism

1. **Driver selection.** Falco loads one driver: the modern eBPF probe (CO-RE, portable across kernels via BTF, uses the BPF ring buffer) is preferred; a legacy eBPF probe and a kernel module remain for older kernels. The driver attaches to syscall tracepoints and copies event data into per-CPU ring buffers.

2. **Capture (`libscap`).** Userspace drains the ring buffers and decodes the raw syscall parameters into structured events. The same layer can serialize to / replay from `.scap` capture files, enabling offline rule testing.

3. **Enrichment (`libsinsp`).** Falco maintains live state — a thread/process table, per-process fd tables, and container/Kubernetes association — so each event is enriched with derived fields (`proc.name`, `proc.pcmdline`, `fd.name`, `container.image.repository`, `k8s.pod.name`, `user.name`, ...). These fields are what rules filter on.

4. **Rule evaluation.** Rules are YAML: a `condition` written in Falco's filtering syntax, an `output` template, a `priority`, and `tags`. `macros` (named reusable conditions) and `lists` (named value sets) keep rules composable. The engine evaluates each enriched event against all rules; a match renders the output template with resolved field values.

5. **Output.** Alerts are routed by the output layer to any enabled channels — stdout, a file, syslog, an external program, an HTTP webhook, or the gRPC output API — and are commonly fanned out by **Falcosidekick** to SIEMs, chat, object storage, and FaaS.

6. **Plugin sources.** The plugin framework lets Falco treat non-syscall streams (k8s audit, cloud trails) as first-class event sources with their own filter fields, evaluated by the same rules engine.

### Data format produced

- **Alert output:** either a rendered text line (with the rule's `output` template) or a structured JSON object (`json_output: true`) containing rule, priority, time, source, tags, and an `output_fields` map of resolved fields.
- **Rules:** declarative YAML (`rule`, `macro`, `list` items) loaded from `/etc/falco/`.
- **Captures:** `.scap` binary capture files (via libscap) for offline analysis and rule regression testing.

---

## Sample Trace Output

### Rule (input)

```yaml
- macro: spawned_process
  condition: evt.type in (execve, execveat) and evt.dir=<

- list: shell_binaries
  items: [bash, sh, zsh, dash, ksh]

- rule: Terminal shell in container
  desc: A shell was spawned inside a container with an attached terminal.
  condition: >
    spawned_process and container
    and proc.name in (shell_binaries)
    and proc.tty != 0
  output: >
    Shell spawned in container
    (user=%user.name container=%container.name image=%container.image.repository
    proc=%proc.name parent=%proc.pname cmdline=%proc.cmdline)
  priority: NOTICE
  tags: [container, shell, mitre_execution]
```

### Alert (JSON output)

```json
{
  "hostname": "node-07",
  "output": "16:41:07.882140321: Notice Shell spawned in container (user=root container=payments-api image=registry.internal/payments proc=bash parent=containerd-shim cmdline=bash -i)",
  "priority": "Notice",
  "rule": "Terminal shell in container",
  "source": "syscall",
  "tags": ["container", "shell", "mitre_execution"],
  "time": "2026-09-21T20:41:07.882140321Z",
  "output_fields": {
    "container.id": "3f9a1c2b7d40",
    "container.name": "payments-api",
    "container.image.repository": "registry.internal/payments",
    "evt.time": 1789590067882140321,
    "k8s.ns.name": "prod",
    "k8s.pod.name": "payments-api-7c9f8b6d5-2xk4t",
    "proc.cmdline": "bash -i",
    "proc.name": "bash",
    "proc.pname": "containerd-shim",
    "user.name": "root",
    "user.uid": 0
  }
}
```

### Alert (default text output, stdout)

```
16:41:07.882140321: Notice Shell spawned in container (user=root container=payments-api image=registry.internal/payments proc=bash parent=containerd-shim cmdline=bash -i) k8s.ns=prod k8s.pod=payments-api-7c9f8b6d5-2xk4t
```

---

## Cost Profile

### LLM token cost

**Not applicable.** Falco is a runtime security engine with no AI/LLM component. It is, however, highly relevant to AI agent infrastructure as a *detection* control around agent execution environments (e.g. flagging an agent's sandbox spawning an unexpected shell or making unexpected network connections).

### Compute/IO overhead per operation

| Factor | Overhead | Notes |
|--------|----------|-------|
| Syscall capture (modern eBPF) | ~2–7% CPU typical; workload-dependent | Scales with syscall rate; ring buffer reduces copies vs perf buffer |
| Syscall capture (kernel module) | Comparable-to-higher | Kmod has broader privilege footprint |
| Per-event enrichment | µs-scale per event | Table lookups (thread/fd/container) in userspace |
| Rule evaluation | Grows with rule count/complexity | Macros/lists compiled; heavy regex conditions cost more |
| Syscall-heavy workloads (DBs, proxies) | Higher end of range | Tune the captured syscall set to reduce cost |

### Storage growth rate

| Scenario | Data Rate | Notes |
|----------|-----------|-------|
| Alerts only (typical) | Low — KB/min | Falco emits on matches, not on every syscall |
| Noisy/over-broad ruleset | Elevated | Poorly scoped rules generate alert floods |
| `.scap` full capture | High (MB–GB/min) | Only for offline analysis/debugging, not steady state |
| Downstream (Falcosidekick → SIEM) | Depends on backend | Retention governed by the sink, not Falco |

---

## Validation Criteria

1. **Driver loads:** `falco --version` reports the engine/driver, and startup logs show the selected driver (modern eBPF / legacy eBPF / kmod) attached without error.
2. **Rules parse:** `falco -L` lists loaded rules; a malformed rule fails validation with a line reference.
3. **Live events flow:** with default rules running, triggering a known behavior produces an alert (see smoke test).
4. **Enrichment present:** alerts include container/k8s fields when run inside a container/pod.
5. **Priority filtering:** `priority` in `falco.yaml` suppresses lower-severity rules as configured.
6. **JSON output valid:** with `json_output: true`, each alert is a single valid JSON object with an `output_fields` map.
7. **Offline replay:** a `.scap` capture replayed with `falco -e capture.scap -r rules.yaml` reproduces the same matches (rule regression test).

### Quick smoke test

```bash
# 1) Confirm engine + driver
falco --version

# 2) Run Falco with default rules (foreground), modern eBPF driver
sudo falco -o engine.kind=modern_ebpf -o json_output=true &

# 3) Trigger the built-in "Read sensitive file untrusted" style rule
sudo cat /etc/shadow > /dev/null

# 4) Expect a JSON alert on Falco's stdout, e.g.:
#    {"rule":"Read sensitive file untrusted", "priority":"Warning",
#     "output_fields":{"fd.name":"/etc/shadow","proc.name":"cat", ...}}
```

---

## Limitations / Out of Scope

| Item | Status |
|------|--------|
| Prevention / blocking | Detection only — Falco alerts; it does not enforce/kill by itself (response is external) |
| Full audit trail of all syscalls | Emits on rule matches, not a complete forensic record (use `.scap` capture for that) |
| Distributed tracing / trace-id propagation | Not a tracer; no span/trace correlation across services |
| Non-Linux hosts | Linux-centric; kernel-driver dependent |
| Rule quality is the operator's job | Detection efficacy = quality of rules; defaults are a baseline, not complete coverage |
| Encryption/auth of outputs | stdout/file/syslog are plaintext; TLS/auth exist for gRPC and via sidekick, but must be configured |
| High-cardinality/high-rate tuning | Syscall-heavy workloads need syscall-set tuning to bound overhead |
| Deep payload inspection | Sees syscall arguments/metadata, not application-layer packet payloads (that is network DPI territory) |
| AI/ML detection | No built-in ML; rules are deterministic conditions |
| Long-term storage/retention | Delegated to downstream sinks (SIEM/object store) |

---

## Evaluation Assessment

### Observability

**Rating: Strong**

| Aspect | Assessment |
|--------|------------|
| **Strengths** | Deep, real-time visibility into kernel-level behavior (process exec, file access, network, privilege changes) enriched with process lineage, container, and Kubernetes context — a security-relevant view few tools match at this granularity. Pluggable outputs (stdout/file/syslog/gRPC/webhook) plus Falcosidekick fan-out integrate cleanly with SIEM/observability stacks. Falco self-reports internal metrics (`metrics` config, Prometheus-compatible) covering event/drop counters and rule stats. Offline `.scap` replay supports rule testing. |
| **Gaps** | It observes for *detection*, not general telemetry — no time-series profiling or distributed traces. Coverage of "what happened" is bounded to what rules match, unless full capture is enabled. Alert quality/visibility depends on ruleset completeness. |
| **Implementations must add** | A downstream store/dashboarding layer, alert triage/correlation (SIEM), and ruleset curation to close detection blind spots. |

### Security

**Rating: Moderate**

| Aspect | Assessment |
|--------|------------|
| **Strengths** | This *is* a security tool: it detects runtime threats and policy violations. Modern eBPF driver enables least-privilege capture (`CAP_BPF`/`CAP_PERFMON`) versus a privileged kernel module. Rules can be signed/distributed via falcoctl OCI artifacts. gRPC output supports mutual TLS. Kernel-sourced events are hard for userspace processes to forge. |
| **Gaps** | Default text/file/syslog outputs are unauthenticated plaintext. Falco itself is a high-value target — compromising it (or its config/rules) blinds detection; rule/config integrity must be protected out of band. Detection ≠ prevention: no built-in enforcement. Evasion is possible (behaviors not covered by rules, or driver-level gaps). No built-in encryption of `.scap` captures, which contain sensitive syscall data (paths, args, secrets in argv). |
| **Implementations must add** | TLS/auth on all output paths, tamper protection and provenance for rules/config, an enforcement/response layer (e.g. admission control, kill/quarantine), capture encryption, and continuous rule-coverage validation. |

### Identity Management

**Rating: Moderate**

| Aspect | Assessment |
|--------|------------|
| **Strengths** | Rich workload identity per event: user/group (name+uid/gid), full process lineage, container id/name/image, and Kubernetes pod/namespace/labels/service-account context. This binds an observed action to a concrete principal and workload — strong for attribution. |
| **Gaps** | No operator identity for who runs/configures Falco or acknowledges alerts (delegated to the platform). No cryptographic verification of the principal — it reports OS-resolved identity, which can be spoofed at the app layer (e.g. dropped-privilege confusion). No AI/agent identity concept. Alert provenance/signing is not intrinsic. |
| **Implementations must add** | Operator/analyst identity and audit around Falco management, cryptographic principal binding where required, agent/service identity correlation, and signed alert provenance if alerts feed automated response. |

### Reliability

**Rating: Moderate**

| Aspect | Assessment |
|--------|------------|
| **Strengths** | Per-CPU ring buffers with a dedicated drain path; modern eBPF ring buffer reduces loss versus perf buffers. Falco exposes drop counters and event statistics so loss is *observable*. Deterministic rule evaluation; ordering preserved per CPU. Outputs can fan out to durable sinks via sidekick. |
| **Gaps** | Under syscall floods the driver can drop events (`n_drops`) — detection gaps that are reported but not prevented. No delivery guarantee on lightweight outputs (stdout/file/syslog can lose data on crash/rotation). No built-in dedup or replay of missed alerts. Single-node engine: HA/redundancy is an external concern. Backpressure ultimately manifests as drops rather than blocking the workload (by design). |
| **Implementations must add** | Drop-rate alerting and capacity tuning, durable/acknowledged output transport, HA deployment (DaemonSet per node), and alert delivery guarantees at the sink. |

### Accuracy

**Rating: Strong**

| Aspect | Assessment |
|--------|------------|
| **Strengths** | Events originate from authoritative kernel tracepoints — the syscall record is exact, not sampled. `libsinsp` enrichment ties each event to real process/container/k8s state. Nanosecond timestamps. Rules are deterministic, and `.scap` replay gives reproducible, testable matches. Modern eBPF CO-RE keeps field semantics consistent across kernels. |
| **Gaps** | False positives/negatives are a function of rule precision, not the capture layer — over-broad conditions over-alert, gaps under-detect. Enrichment can be incomplete during races (very short-lived processes, container metadata not yet resolved). Dropped events (under load) mean missed detections. Identity fields reflect OS resolution and can be misleading under privilege manipulation. |
| **Implementations must add** | Rule tuning with false-positive/negative measurement, handling of enrichment races, drop-aware confidence in detection completeness, and periodic rule regression testing against captures. |

---

## Assessment Summary

| Dimension | Rating | Key Gap |
|-----------|--------|---------|
| Observability | Strong | Detection-scoped (rule matches), not full telemetry; needs downstream store/triage |
| Security | Moderate | Plaintext default outputs; detection ≠ prevention; Falco/config integrity must be protected |
| Identity | Moderate | Rich workload attribution but OS-resolved (spoofable); no operator/AI identity or signed provenance |
| Reliability | Moderate | Event drops under load are reported, not prevented; lightweight outputs lack delivery guarantees |
| Accuracy | Strong | Kernel-exact events, but efficacy bounded by rule precision and enrichment races |
