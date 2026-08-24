# AAIF Reference Architecture: Container Orchestration Tracing

| Field | Value |
|-------|-------|
| **Subject** | Container Orchestration Tracing (Kubernetes, k3s, containerd, Podman) |
| **Version** | Kubernetes 1.30+, k3s 1.30+ |
| **Date** | 2026-08-12 |

---

## Objective

Container orchestration adds scheduling layers — CFS pre-emption, cgroup CPU bandwidth throttling, and resource limit enforcement — that distort trace timing for containerized processes; OS-level tracepoints (scheduler, cgroup, namespace) expose the container-level behavior that application traces cannot see.

---

## Scope / Zoom Level

**Infrastructure layer — container scheduling and resource isolation above the kernel, below application-level observability.**

This document covers how Kubernetes, k3s, containerd, CRI-O, and Podman interact with kernel scheduling and isolation primitives, and how to observe those interactions using kernel tracepoints, perf, ftrace, LTTng, and BPF. It sits between the raw kernel tracing documents (ftrace.md, perf.md, lttng-kernel-tracing.md) and application-level agent observability (05-ai-agent-observability/).

---

## Prerequisites

| Component | Version / Pinned | Notes |
|-----------|-----------------|-------|
| Kubernetes | ≥ 1.30 | cgroup v2 unified hierarchy required |
| k3s | ≥ 1.30 | Single-binary distribution; reduced component set |
| containerd | ≥ 1.7 | Default CRI runtime for Kubernetes |
| CRI-O | ≥ 1.30 | Alternative CRI runtime; OCI-native |
| Podman | ≥ 4.9 | Daemonless container engine; rootless support |
| Linux kernel | ≥ 6.1 | cgroup v2, BPF CO-RE, BTF |
| perf | Matches kernel | `CAP_PERFMON` for container-scoped profiling |
| ftrace/tracefs | Built-in | `/sys/kernel/tracing/` mounted |
| LTTng | ≥ 2.13 | Kernel and UST tracing with PID namespace awareness |
| bpftrace | ≥ 0.20 | BTF-based, CO-RE enabled |
| BCC tools | ≥ 0.28 | Python/C BPF toolkit |
| Inspektor Gadget | ≥ 0.26 | Kubernetes-native BPF tracing |
| Cilium/Hubble | ≥ 1.15 | eBPF-based network observability |

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Physical Host (Node)                                │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  Kubernetes Control Plane (or k3s embedded)                            │  │
│  │  kube-apiserver ──── OpenTelemetry spans (API request lifecycle)       │  │
│  │  kube-scheduler ──── scheduling decision audit events                 │  │
│  │  etcd ────────────── watch latency, WAL sync                          │  │
│  └───────────────────────────────────┬───────────────────────────────────┘  │
│                                      │ gRPC                                  │
│  ┌───────────────────────────────────▼───────────────────────────────────┐  │
│  │  kubelet                                                               │  │
│  │  • Pod lifecycle management         ◄── tracepoint: GRPC/CRI calls    │  │
│  │  • CPU Manager (static policy)      ◄── cpuset assignment             │  │
│  │  • Topology Manager                 ◄── NUMA binding                  │  │
│  │  • OpenTelemetry spans (since 1.30)                                   │  │
│  └───────────────────────────────────┬───────────────────────────────────┘  │
│                                      │ CRI gRPC                              │
│  ┌───────────────────────────────────▼───────────────────────────────────┐  │
│  │  Container Runtime (containerd / CRI-O / Podman)                       │  │
│  │  • RunPodSandbox        ◄── ftrace: containerd function entry         │  │
│  │  • CreateContainer      ◄── audit log: container creation event       │  │
│  │  • StartContainer       ◄── clone3() syscall tracepoint               │  │
│  └───────────────────────────────────┬───────────────────────────────────┘  │
│                                      │ OCI runtime (runc/crun)               │
│  ┌───────────────────────────────────▼───────────────────────────────────┐  │
│  │  Kernel Isolation Primitives                                           │  │
│  │                                                                        │  │
│  │  ┌─────────────────────────┐  ┌────────────────────────────────────┐ │  │
│  │  │  cgroups v2             │  │  Namespaces                         │ │  │
│  │  │  /sys/fs/cgroup/        │  │  mnt, pid, net, uts, ipc, user,    │ │  │
│  │  │  kubepods.slice/        │  │  cgroup, time                       │ │  │
│  │  │    burstable/           │  │                                     │ │  │
│  │  │      pod<uid>/          │  │  ◄── tracepoint: nsproxy changes    │ │  │
│  │  │        <container-id>/  │  │                                     │ │  │
│  │  │                         │  │                                     │ │  │
│  │  │  ◄── tracepoints:      │  └────────────────────────────────────┘ │  │
│  │  │  cgroup_attach_task     │                                         │  │
│  │  │  cgroup_mkdir/rmdir     │                                         │  │
│  │  └─────────────────────────┘                                         │  │
│  │                                                                        │  │
│  │  ┌──────────────────────────────────────────────────────────────────┐ │  │
│  │  │  CFS Scheduler                                                    │ │  │
│  │  │  • cpu.max (quota/period)  ◄── bandwidth throttling               │ │  │
│  │  │  • cpu.weight             ◄── proportional sharing                 │ │  │
│  │  │  • cpuset.cpus            ◄── CPU pinning                         │ │  │
│  │  │                                                                    │ │  │
│  │  │  ◄── tracepoints: sched_switch, sched_wakeup, sched_stat_wait,   │ │  │
│  │  │      sched_stat_runtime, cfs_throttle                             │ │  │
│  │  └──────────────────────────────────────────────────────────────────┘ │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │  Pod Containers (workload processes)                                    │ │
│  │  PID namespace: isolated PID tree                                      │ │
│  │  Net namespace: veth pair → bridge/overlay                             │ │
│  │  Application traces see wall-clock time INCLUDING throttle gaps         │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Tracepoint Coverage at the OS Level

### Scheduler Tracepoints Relevant to Containers

CFS scheduling decisions for containerized processes are visible through these tracepoints, all firing in the context of the host kernel regardless of PID namespace isolation:

| Tracepoint | What It Shows for Containers |
|------------|------------------------------|
| `sched:sched_switch` | Context switch between container processes and other workloads; `prev_state` reveals voluntary vs forced pre-emption |
| `sched:sched_wakeup` | When a container's thread becomes runnable; target_cpu shows scheduler placement decisions |
| `sched:sched_process_fork` | Container process creation (container runtimes clone into new namespaces) |
| `sched:sched_stat_runtime` | Actual CPU time consumed by each container thread per scheduling epoch |
| `sched:sched_stat_wait` | Time a container thread spent in the runqueue waiting — this is the **noisy neighbor indicator** |
| `sched:sched_migrate_task` | When scheduler moves a container thread between CPUs (affects cache locality) |

Enable all scheduler tracepoints for a specific container's cgroup:

```bash
# Find container's cgroup ID
CGID=$(cat /sys/fs/cgroup/kubepods.slice/kubepods-burstable.slice/kubepods-burstable-pod${POD_UID}.slice/cri-containerd-${CONTAINER_ID}.scope/cgroup.id)

# bpftrace: trace sched_switch filtered by cgroup
bpftrace -e 'tracepoint:sched:sched_switch /cgroup == cgroupid("/sys/fs/cgroup/kubepods.slice/kubepods-burstable.slice/kubepods-burstable-pod${POD_UID}.slice/cri-containerd-${CID}.scope")/ {
    printf("%s [%d] -> %s [%d] on cpu %d\n", args->prev_comm, args->prev_pid, args->next_comm, args->next_pid, cpu);
}'
```

### Cgroup Tracepoints

Cgroup v2 operations emit tracepoints that track container lifecycle at the kernel level:

| Tracepoint | Meaning |
|------------|---------|
| `cgroup:cgroup_attach_task` | Process assigned to container's cgroup (container start) |
| `cgroup:cgroup_mkdir` | Container cgroup created by runtime |
| `cgroup:cgroup_rmdir` | Container cgroup destroyed (container exit/cleanup) |
| `cgroup:cgroup_release` | Cgroup reference count drops to zero |
| `cgroup:cgroup_transfer_tasks` | Processes moved between cgroups (rare, live migration) |

Controller-specific events are observable through the cgroup filesystem:

```bash
# Monitor CFS throttling events in real-time
bpftrace -e 'kprobe:throttle_cfs_rq {
    printf("CFS throttle: cpu=%d cgroup=%s\n", cpu, ((struct cfs_rq *)arg0)->tg->css.cgroup->kn->name);
}'

# Track cgroup memory reclaim
bpftrace -e 'tracepoint:vmscan:mm_vmscan_memcg_reclaim_begin {
    printf("memcg reclaim: order=%d gfp=%x\n", args->order, args->gfp_flags);
}'
```

Key cgroup v2 files for container resource state:

| File | Contents |
|------|----------|
| `/sys/fs/cgroup/.../cpu.stat` | `nr_throttled`, `throttled_usec`, `nr_periods` |
| `/sys/fs/cgroup/.../cpu.max` | `quota period` (e.g., `100000 100000` = 1 CPU) |
| `/sys/fs/cgroup/.../cpu.weight` | Proportional weight (1-10000, default 100) |
| `/sys/fs/cgroup/.../memory.current` | Current memory usage |
| `/sys/fs/cgroup/.../memory.events` | `oom`, `oom_kill`, `high`, `max` counters |
| `/sys/fs/cgroup/.../io.stat` | Per-device IO bytes/iops with latency |

### Namespace Tracepoints and Visibility Boundaries

Namespaces create visibility boundaries that affect what container-internal tracing can observe:

- **PID namespace**: Processes inside a container see PIDs starting from 1. Kernel tracepoints always report the host PID (`task->pid`) alongside namespace PID (`task->tgid` in ns context). Tracing from inside only sees the container's process tree.
- **Network namespace**: Each pod gets its own network namespace. Tracepoints like `net:net_dev_xmit` fire per-namespace. Traffic between pods traverses veth pairs, bridges, and overlay networks — each hop fires separate tracepoints.
- **Mount namespace**: tracefs is not typically mounted inside containers. Container-internal ftrace requires bind-mounting `/sys/kernel/tracing` (security risk).
- **cgroup namespace**: Since kernel 4.6, containers can have their own cgroup namespace root. This affects cgroup-filtered tracing from inside.

```bash
# Trace namespace transitions (container creation)
bpftrace -e 'kprobe:create_new_namespaces {
    printf("new namespaces: pid=%d comm=%s flags=0x%x\n", pid, comm, arg1);
}'
```

### Container Runtime Tracepoints

**containerd** emits structured events via its events API:

```bash
# Subscribe to containerd events
ctr events | grep -E "(TaskCreate|TaskStart|TaskExit|TaskOOM)"

# Events include:
# /tasks/create    — container process created
# /tasks/start     — container process started
# /tasks/exit      — container process exited (with exit code)
# /tasks/oom       — OOM killer invoked in container
# /snapshots/prepare — filesystem snapshot prepared
# /images/pull     — image layer pull initiated
```

**CRI-O** provides audit logging:

```bash
# CRI-O log entries with structured fields
journalctl -u crio -o json | jq 'select(.MESSAGE | contains("RunPodSandbox"))'
```

**Podman** events (daemonless — journald or file-based):

```bash
podman events --filter event=start --format json
```

### Kubernetes API Server and Kubelet Tracing

Since Kubernetes 1.27+, the API server and kubelet emit OpenTelemetry traces natively:

```yaml
# kube-apiserver feature gate
apiVersion: v1
kind: Pod
metadata:
  name: kube-apiserver
spec:
  containers:
  - command:
    - kube-apiserver
    - --feature-gates=APIServerTracing=true
    - --tracing-config-file=/etc/kubernetes/tracing-config.yaml
```

```yaml
# tracing-config.yaml
apiVersion: apiserver.config.k8s.io/v1beta1
kind: TracingConfiguration
endpoint: otel-collector.observability.svc:4317
samplingRatePerMillion: 10000  # 1%
```

Kubelet spans cover: pod sync loop, PLEG (Pod Lifecycle Event Generator), volume operations, image pulls, and CRI calls.

### BPF-Based Container-Aware Tracing

**Inspektor Gadget** — Kubernetes-native BPF tracing:

```bash
# Trace all syscalls in a specific pod
kubectl gadget trace exec -n default -p my-pod

# Profile CPU usage per container
kubectl gadget profile cpu -n default -p my-pod --timeout 30

# Trace DNS queries per pod
kubectl gadget trace dns -n default

# Trace TCP connections with container context
kubectl gadget trace tcp -n default
```

**Cilium/Hubble** — eBPF network observability:

```bash
# Observe all network flows with pod identity
hubble observe --namespace default --pod my-pod

# Flow visibility includes:
# - Source/destination pod names and namespaces
# - L3/L4/L7 protocol information
# - Network policy verdict (ALLOWED/DROPPED)
# - Latency (with Hubble metrics)
```

### k3s vs Full Kubernetes: Observability Surface Area

| Aspect | Full Kubernetes | k3s |
|--------|----------------|-----|
| API server tracing | Separate process, full OTel support | Embedded in k3s binary, same OTel support |
| etcd | External cluster, dedicated metrics | Embedded SQLite/etcd, limited observability |
| kubelet | Standalone, full feature gates | Embedded, same tracing capabilities |
| Container runtime | containerd or CRI-O (separate) | Embedded containerd (single process) |
| Network plugin | CNI (Calico, Cilium, etc.) | Flannel default; Cilium optional |
| Component logs | Separate journald units per component | Single k3s journald unit, multiplexed logs |
| kube-proxy | Separate, iptables/IPVS tracepoints | Embedded, same kernel tracepoints |
| Audit logging | Full audit policy support | Same, but often disabled by default |

k3s collapses multiple processes into one binary, so host-level tracing (perf, ftrace) captures all control plane activity in a single process — harder to attribute but lower per-component overhead.

---

## Timing Distortion from Pre-emption and Throttling

**This section is critical for interpreting any trace collected from or about containerized workloads.**

### CFS CPU Bandwidth Throttling

When a container's aggregate CPU usage hits its `cpu.cfs_quota_us` within the `cpu.cfs_period_us` window (default 100ms), the kernel throttles **all threads** in that cgroup. During throttling:

- The threads are removed from the runqueue and placed in a throttled list
- Wall-clock time passes, but no CPU time is consumed
- Application-level traces show latency gaps that are **NOT idle time** — the process was ready to run but the kernel refused to schedule it
- This happens at cgroup granularity — all containers in the pod share the quota

Observable from the host:

```bash
# Check throttling for a specific container
cat /sys/fs/cgroup/kubepods.slice/kubepods-burstable.slice/kubepods-burstable-pod${POD_UID}.slice/cri-containerd-${CID}.scope/cpu.stat
# Output:
# usage_usec 4523456789
# user_usec 3987654321
# system_usec 535802468
# nr_periods 12345
# nr_throttled 2341        ◄── throttled in 19% of periods
# throttled_usec 156780000 ◄── 156.78 seconds total throttled time

# bpftrace: catch throttle events in real-time
bpftrace -e 'kprobe:throttle_cfs_rq {
    $tg = ((struct cfs_rq *)arg0)->tg;
    printf("THROTTLED: cpu=%d\n", cpu);
}'
```

**Impact on traces**: A function that takes 2ms of CPU time may appear to take 102ms in wall-clock traces if throttling occurs mid-execution. The 100ms gap is invisible to application-level instrumentation.

### CPU Shares vs Limits (Proportional Pre-emption)

Containers configured with `cpu.weight` (mapped from `resources.requests.cpu`) get proportional CPU access under contention:

- Kubernetes maps `requests.cpu: 500m` → `cpu.weight: 19` (approximately)
- Under contention, a 500m container yields CPU to a 2000m neighbor at a 1:4 ratio
- Traces captured inside the container see **variable latencies** that depend entirely on co-located workload activity
- The same code path may take 5ms when the node is idle and 50ms under contention

```bash
# Show weight for a container's cgroup
cat /sys/fs/cgroup/kubepods.slice/.../cpu.weight
# 39 (maps from requests.cpu: 1000m)
```

### The Noisy Neighbor Problem

`sched_stat_wait` tracepoints expose runqueue wait time — how long a thread was runnable but not running:

```bash
# bpftrace: histogram of runqueue latency for a container
bpftrace -e 'tracepoint:sched:sched_stat_wait
    /cgroup == cgroupid("/sys/fs/cgroup/kubepods.slice/.../cri-containerd-${CID}.scope")/
{
    @wait_us = hist(args->delay / 1000);
}'
```

This wait time appears as execution time in application-level traces (OpenTelemetry spans, Langfuse traces) because those systems measure wall-clock time. A span showing 50ms may contain 30ms of runqueue wait caused by a noisy neighbor container.

**Correlation technique**: Compare `sched_stat_runtime` (actual CPU consumed) with wall-clock span duration. The difference is scheduling overhead:

```
scheduling_overhead = span_wall_clock - sum(sched_stat_runtime for span's threads)
```

### Memory Pressure and OOM

Cgroup memory limits (`memory.max`) cause kernel-level reclaim when usage approaches the limit:

- Direct reclaim: process's own allocation triggers page scanning — appears as slow `malloc()` / `mmap()` in traces
- kswapd reclaim: background scanning causes CPU contention
- OOM kill: catastrophic trace discontinuity — process is killed mid-execution

```bash
# Monitor memory pressure per container
cat /sys/fs/cgroup/kubepods.slice/.../memory.pressure
# some avg10=45.00 avg60=23.15 avg300=12.45 total=987654321

# Monitor OOM events
bpftrace -e 'kprobe:oom_kill_process {
    printf("OOM KILL: pid=%d comm=%s\n", pid, comm);
}'

# Memory events counter
cat /sys/fs/cgroup/kubepods.slice/.../memory.events
# low 0
# high 1234
# max 56
# oom 2
# oom_kill 1
```

### Network Namespace Overhead

Pod network namespaces introduce latency layers invisible to application traces:

1. **veth pair traversal**: Each packet crosses a virtual ethernet pair between pod namespace and host bridge — adds 2-5μs per packet
2. **iptables/nftables rules**: kube-proxy Service rules evaluate per-packet; O(n) rule count on iptables (IPVS is O(1))
3. **Overlay encapsulation**: VXLAN/Geneve adds encap/decap overhead (20-50μs per packet)
4. **Conntrack table**: Connection tracking per-flow overhead; table full → packet drops

```bash
# Trace network device transmit with namespace context
bpftrace -e 'tracepoint:net:net_dev_xmit {
    printf("dev=%s len=%d rc=%d netns=%d\n",
        args->name, args->len, args->rc, 
        curtask->nsproxy->net_ns->ns.inum);
}'

# Trace netfilter rule evaluation latency
bpftrace -e 'tracepoint:netfilter:nf_hook_slow {
    printf("hook=%d protocol=%d netns_inum=%d\n",
        args->hook, args->pf, args->indev ? args->indev->nd_net.net->ns.inum : 0);
}'
```

### Pod Scheduling Latency

Time between pod creation (API server accepts the Pod spec) and first application instruction executing includes:

| Phase | Typical Duration | Visible In |
|-------|-----------------|------------|
| Scheduling decision | 5-50ms | kube-scheduler OTel spans |
| Image pull (cached) | 100-500ms | kubelet spans, containerd events |
| Image pull (uncached) | 2-60s | kubelet spans, containerd events |
| Volume mount | 100ms-30s | kubelet spans (CSI calls) |
| Sandbox creation | 50-200ms | CRI CreatePodSandbox span |
| Container start | 10-50ms | CRI StartContainer span |
| Readiness probe pass | 0-30s | kubelet probe loop |

**None of this appears in application-level traces.** The application only sees time starting from its first instruction. Total pod startup can be 200ms to 60s+ depending on image size and volume type.

### Node-Level Pre-emption

Kubernetes priority/preemption (PriorityClasses) causes lower-priority pods to be evicted when higher-priority pods need scheduling:

- Pre-empted pods receive SIGTERM → graceful shutdown period → SIGKILL
- All in-flight traces from the pre-empted pod are truncated
- If trace data hasn't been flushed to an external collector, it is **lost**
- New pod on the same node may inherit the same cgroup path, causing trace correlation confusion

```bash
# Observe pre-emption events via Kubernetes audit
kubectl get events --field-selector reason=Preempted -w
```

### Mitigations for Timing Accuracy

| Mitigation | Effect | Configuration |
|------------|--------|---------------|
| **Guaranteed QoS** | `requests == limits` → no throttling variance | Set `resources.requests.cpu` = `resources.limits.cpu` |
| **CPU Manager static** | Exclusive CPU pinning for Guaranteed pods | kubelet `--cpu-manager-policy=static` |
| **Topology Manager** | NUMA-aligned CPU+memory allocation | kubelet `--topology-manager-policy=single-numa-node` |
| **isolcpus** | Kernel boot param excludes CPUs from general scheduling | `isolcpus=4-7` in GRUB, then CPU Manager assigns these |
| **CAP_PERFMON** | Enables in-container perf without full privileges | Pod securityContext capability |
| **Burstable with high limits** | Reduces throttling frequency | `limits.cpu` >> `requests.cpu` |
| **Pod anti-affinity** | Prevents noisy neighbor co-location | `podAntiAffinity` rules |
| **RuntimeClass** | Dedicated runtime with adjusted settings | Kata, gVisor for isolation; runc for performance |

```yaml
# Guaranteed QoS pod with CPU pinning
apiVersion: v1
kind: Pod
metadata:
  name: latency-critical
spec:
  containers:
  - name: app
    resources:
      requests:
        cpu: "4"          # Must equal limits for Guaranteed QoS
        memory: "8Gi"
      limits:
        cpu: "4"          # Guaranteed → CPU Manager pins 4 exclusive CPUs
        memory: "8Gi"
    securityContext:
      capabilities:
        add: ["CAP_PERFMON"]  # Enables perf inside container
```

---

## Instrumentation Walkthrough

### Step 1: Identify Container Cgroup Path

```bash
# From pod UID and container ID
POD_UID="a1b2c3d4-e5f6-7890-abcd-ef1234567890"
CID="abc123def456..."

# cgroup v2 path (Kubernetes standard layout)
CGROUP_PATH="/sys/fs/cgroup/kubepods.slice/kubepods-burstable.slice/kubepods-burstable-pod${POD_UID}.slice/cri-containerd-${CID}.scope"

# Verify
ls ${CGROUP_PATH}/cpu.stat
```

### Step 2: Enable Cgroup-Filtered Ftrace

```bash
# Create a dedicated ftrace instance
mkdir /sys/kernel/tracing/instances/k8s-trace

# Enable scheduler and cgroup events
echo 1 > /sys/kernel/tracing/instances/k8s-trace/events/sched/sched_switch/enable
echo 1 > /sys/kernel/tracing/instances/k8s-trace/events/sched/sched_stat_wait/enable
echo 1 > /sys/kernel/tracing/instances/k8s-trace/events/sched/sched_stat_runtime/enable
echo 1 > /sys/kernel/tracing/instances/k8s-trace/events/cgroup/enable

# Filter by cgroup (ftrace cgroup filtering requires set_event_pid with PIDs)
# Alternative: use perf with cgroup filter
PIDS=$(cat ${CGROUP_PATH}/cgroup.procs | tr '\n' ',')
echo ${PIDS%,} > /sys/kernel/tracing/instances/k8s-trace/set_event_pid

# Start tracing
echo 1 > /sys/kernel/tracing/instances/k8s-trace/tracing_on
```

### Step 3: Perf with Cgroup Filtering

```bash
# Record scheduling events for a specific container cgroup
perf record -e sched:sched_switch,sched:sched_stat_wait \
    --cgroup="kubepods.slice/kubepods-burstable.slice/kubepods-burstable-pod${POD_UID}.slice/cri-containerd-${CID}.scope" \
    -a --timeout 10000

# Analyze runqueue latency
perf script | awk '/sched_stat_wait/ {print $NF}' | sort -n | tail -20
```

### Step 4: BPF-Based Container-Aware Tracing

```bash
# bpftrace: comprehensive container scheduling profile
bpftrace -e '
tracepoint:sched:sched_switch
/cgroup == cgroupid("/sys/fs/cgroup/kubepods.slice/.../cri-containerd-${CID}.scope")/
{
    @off[args->prev_comm, args->prev_pid] = nsecs;
}

tracepoint:sched:sched_switch
/cgroup == cgroupid("/sys/fs/cgroup/kubepods.slice/.../cri-containerd-${CID}.scope")/
{
    $prev_off = @off[args->next_comm, args->next_pid];
    if ($prev_off > 0) {
        @runq_latency_us = hist((nsecs - $prev_off) / 1000);
    }
}
'
```

### Step 5: LTTng with Container Context

```bash
# Create LTTng session with PID tracking
lttng create k8s-trace --output=/tmp/k8s-trace
lttng enable-channel --kernel my-channel --subbuf-size=4M
lttng enable-event --kernel sched_switch,sched_stat_wait,sched_stat_runtime -c my-channel

# Track container PIDs
for p in $(cat ${CGROUP_PATH}/cgroup.procs); do
    lttng track --kernel --pid=$p
done

lttng start
sleep 10
lttng stop
lttng destroy

# Analyze with Trace Compass (correlates cgroup context)
```

---

## Sample Trace Output

### sched_switch with Cgroup Context (ftrace format)

```
# tracer: nop
#
#                              _-----=> irqs-off/BH-disabled
#                             / _----=> need-resched
#                            | / _---=> hardirq/softirq
#                            || / _--=> preempt-depth
#                            ||| / _-=> migrate-disable
#                            |||| /     delay
#           TASK-PID     CPU#|||||  TIMESTAMP  FUNCTION
#              | |         |  |||||     |         |
  python-ai-15432 [003] d..2. 91234.567890: sched_switch: prev_comm=python-ai prev_pid=15432 prev_prio=120 prev_state=R+ ==> next_comm=nginx-proxy next_pid=15500 next_prio=120
                                                          # ^^^ prev_state=R+ means RUNNABLE — forced pre-emption by CFS
  nginx-proxy-15500 [003] d..2. 91234.567901: sched_switch: prev_comm=nginx-proxy prev_pid=15500 prev_prio=120 prev_state=S ==> next_comm=python-ai next_pid=15432 next_prio=120
  python-ai-15432 [003] d..2. 91234.668234: sched_switch: prev_comm=python-ai prev_pid=15432 prev_prio=120 prev_state=R+ ==> next_comm=swapper/3 next_pid=0 next_prio=120
                                                          # ^^^ 100.344ms gap — CFS THROTTLE EVENT
                                                          # Container hit cpu.max quota; all threads blocked
  <idle>-0       [003] d..2. 91234.768234: sched_switch: prev_comm=swapper/3 prev_pid=0 prev_prio=120 prev_state=R ==> next_comm=python-ai next_pid=15432 next_prio=120
                                                          # ^^^ Exactly 100ms later — new CFS period began, quota replenished
```

### CFS Throttling Visible in cpu.stat

```bash
$ cat /sys/fs/cgroup/kubepods.slice/kubepods-burstable.slice/.../cpu.stat
usage_usec 892345678
user_usec 789012345
system_usec 103333333
core_sched.force_idle_usec 0
nr_periods 89234          # total scheduling periods
nr_throttled 17846        # throttled periods (20%!)
throttled_usec 1784600000 # 1784.6 seconds total throttled
nr_bursts 0
burst_usec 0
```

### sched_stat_wait Showing Runqueue Contention

```
# bpftrace output: runqueue latency histogram for container
@runq_latency_us:
[1]                 12345 |@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@                |
[2, 4)              18234 |@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@|
[4, 8)               9876 |@@@@@@@@@@@@@@@@@@@@@@@@@@@                     |
[8, 16)              4567 |@@@@@@@@@@@@                                    |
[16, 32)             2345 |@@@@@@                                          |
[32, 64)             1234 |@@@                                             |
[64, 128)             567 |@                                               |
[128, 256)            234 |                                                |  ◄── noisy neighbor
[256, 512)             89 |                                                |  ◄── severe contention
[512, 1K)              12 |                                                |  ◄── likely throttling
[1K, 2K)                3 |                                                |
```

---

## Cost Profile

### LLM Token Cost

**Not applicable.** Container orchestration tracing uses kernel-level instrumentation with no AI/LLM component.

### Compute/IO Overhead per Operation

| Method | Overhead | Notes |
|--------|----------|-------|
| ftrace sched events (filtered) | <0.5% CPU | Per-CPU ring buffers, text format |
| perf cgroup-filtered sampling | <1% CPU | Hardware counter + ring buffer |
| bpftrace one-liner | 1-3% CPU | BPF JIT, map operations |
| Inspektor Gadget (per-pod) | 1-5% CPU | BPF + userspace event processing |
| Hubble network flow export | 2-5% CPU | Per-packet BPF, ringbuf to userspace |
| LTTng kernel (sched tracepoints) | <0.3% CPU | CTF binary format, zero-copy |
| Kubernetes API server OTel | <1% latency | Span sampling reduces impact |
| containerd event subscription | negligible | Event-driven, no polling |
| cpu.stat polling (1s interval) | negligible | Single file read per container |

### Storage Growth Rate

| Method | Data Rate | Notes |
|--------|-----------|-------|
| ftrace sched events (busy node, 100 pods) | 10-100 MB/min | Text format, all CPUs |
| perf record (cgroup-filtered, 1 container) | 1-10 MB/min | Binary, depends on activity |
| LTTng CTF (sched tracepoints, full node) | 20-200 MB/min | Binary, compact |
| Inspektor Gadget export | 1-5 MB/min | JSON events per pod |
| Kubernetes audit log (full) | 50-500 MB/hour | JSON, API request/response bodies |
| Hubble flow logs | 10-100 MB/min | Protobuf flows, depends on traffic |

---

## Validation Criteria

### Smoke Tests

```bash
# 1. Verify cgroup v2 is active
stat /sys/fs/cgroup/cgroup.controllers && echo "cgroup v2 active"

# 2. Verify container cgroup hierarchy exists
ls /sys/fs/cgroup/kubepods.slice/ | grep -q burstable && echo "K8s cgroup layout present"

# 3. Verify scheduler tracepoints available
cat /sys/kernel/tracing/available_events | grep -c "sched:" 
# Expected: >= 20

# 4. Verify cgroup tracepoints available
cat /sys/kernel/tracing/available_events | grep -c "cgroup:"
# Expected: >= 4

# 5. Verify BPF cgroup filtering works
bpftrace -e 'tracepoint:sched:sched_switch { @[cgroup] = count(); exit(); }'
# Should show cgroup IDs

# 6. Verify perf cgroup filtering
perf stat -e sched:sched_switch --cgroup=kubepods.slice -- sleep 1
# Should show event count > 0

# 7. Verify cpu.stat is readable for a running container
POD=$(kubectl get pods -o jsonpath='{.items[0].metadata.uid}')
find /sys/fs/cgroup -path "*${POD}*" -name cpu.stat -exec cat {} \;
# Should show nr_periods, nr_throttled

# 8. Verify Kubernetes API server tracing (if enabled)
kubectl get --raw /metrics | grep -c apiserver_request_duration
# Should be > 0

# 9. Verify Inspektor Gadget (if installed)
kubectl gadget trace exec --timeout 5 2>/dev/null && echo "Gadget working"

# 10. End-to-end: create throttled pod and observe
kubectl run throttle-test --image=busybox --restart=Never \
    --overrides='{"spec":{"containers":[{"name":"throttle-test","image":"busybox","command":["yes"],"resources":{"limits":{"cpu":"100m"}}}]}}' 
sleep 5
CID=$(crictl ps --name throttle-test -q)
cat /sys/fs/cgroup/kubepods.slice/*/pod*/cri-containerd-${CID}.scope/cpu.stat | grep nr_throttled
# nr_throttled should be > 0 (container is throttled running 'yes' at 100m)
kubectl delete pod throttle-test
```

---

## Limitations / Out of Scope

| Item | Status |
|------|--------|
| Multi-cluster tracing correlation | Out of scope; requires distributed trace context propagation |
| Windows container tracing | Not covered; Linux-only |
| GPU scheduling inside containers (device plugin) | Covered in 03-hardware-accelerators/ |
| Application-level distributed tracing (OTel SDK) | Covered in 05-ai-agent-observability/ |
| Service mesh tracing (Istio, Linkerd) | L7 proxy tracing; partially overlaps with network namespace coverage |
| Rootless container tracing | Limited; many kernel tracepoints require CAP_SYS_ADMIN or CAP_PERFMON |
| Real-time scheduling (SCHED_FIFO/RR in containers) | Rare in practice; requires privileged pod |
| Trace context propagation across pod boundaries | Application-level concern; not kernel-observable |
| Encrypted container runtimes (Kata, gVisor) | Guest kernel provides separate tracing surface |
| Fargate/serverless containers | No host access; kernel tracing unavailable |
| Historical trace correlation (long-term storage) | Requires external pipeline (OTel Collector → backend) |

---

## Evaluation Assessment

### Observability

**Rating: Strong (with caveats)**

| Aspect | Assessment |
|--------|------------|
| **Strengths** | Full visibility into scheduling decisions, CFS throttling, memory pressure, and network namespace overhead from the host. Cgroup-filtered tracing scopes to individual containers. BPF-based tools (Inspektor Gadget, Hubble) provide Kubernetes-native ergonomics. Kubernetes API server and kubelet emit OpenTelemetry spans natively since 1.27+. The combination of host-level kernel tracing with Kubernetes-level metadata gives complete pod lifecycle observability. |
| **Gaps** | **Visibility boundary between host and container namespaces is fundamental.** Tracing from inside a container cannot see host scheduler decisions, other containers' activity, or the full cgroup hierarchy. Container-internal perf/ftrace requires privileged access or explicit capabilities. PID namespace translation requires host-side correlation. Overlay network tracing requires access to both pod and host network namespaces. |
| **Implementations must add** | Host-to-container trace correlation pipeline, PID namespace translation layer, automated cgroup path discovery from Kubernetes metadata, container-aware trace visualization (Trace Compass with container context). |

### Security

**Rating: Moderate**

| Aspect | Assessment |
|--------|------------|
| **Strengths** | Namespace isolation prevents containers from observing each other by default. CAP_PERFMON provides granular permission for in-container profiling without full root. Kubernetes RBAC controls access to API server audit logs. BPF programs require CAP_BPF (can be scoped). Cgroup hierarchy read access can be controlled via file permissions. |
| **Gaps** | Host-level tracing sees ALL containers — no tenant isolation at the tracing layer. A compromised tracing agent on the host can observe secrets in any container's memory/syscalls. tracefs mounted into a container exposes full kernel state. Inspektor Gadget requires cluster-admin. perf.data from host contains cross-container information. |
| **Implementations must add** | Per-tenant trace isolation, encrypted trace transport, RBAC for trace data access, audit logging of who traced what, node-level trace agent hardening. |

### Identity Management

**Rating: Moderate**

| Aspect | Assessment |
|--------|------------|
| **Strengths** | Kubernetes provides strong workload identity: pod UID, service account, namespace. Container IDs are unique and traceable to image SHA. Cgroup paths encode the full identity hierarchy (QoS class → pod → container). BPF cgroup IDs provide kernel-level identity for filtering. |
| **Gaps** | Kernel tracepoints report PIDs, not Kubernetes identities — translation required. No standard for embedding Kubernetes identity into kernel trace records. When a pod is rescheduled, its traces lose continuity (new PID, new node, new cgroup). AI agent identity (which model, which session) is not represented at this layer. |
| **Implementations must add** | PID→pod identity translation service, trace stitching across pod restarts, Kubernetes label enrichment of kernel traces, service mesh identity (SPIFFE) correlation. |

### Reliability

**Rating: Moderate**

| Aspect | Assessment |
|--------|------------|
| **Strengths** | Kernel tracepoints are stable ABI (guaranteed not to break between kernel versions). Ring buffer overflow is detectable. LTTng's flight recorder mode prevents data loss at the cost of overwriting old data. BPF maps persist across userspace restarts. Kubernetes audit log can be backed by webhook to external storage. |
| **Gaps** | Pod pre-emption and eviction cause trace data loss if not flushed to external storage. Node failure loses all buffered kernel traces. Ring buffer overflow under heavy load drops events silently (depending on configuration). cgroup path changes on pod restart break trace continuity. Container-internal trace agents are killed with the container. |
| **Implementations must add** | External trace collector with guaranteed delivery, trace buffer flush on SIGTERM, node-level persistent buffer (tmpfs → durable on shutdown), redundant collection paths for critical workloads. |

### Accuracy

**Rating: Moderate (fundamental distortion present)**

| Aspect | Assessment |
|--------|------------|
| **Strengths** | Kernel tracepoints report precise TSC-based timestamps at the point of scheduling decision. `sched_stat_runtime` gives exact CPU time consumed. `sched_stat_wait` gives exact runqueue wait time. `cpu.stat` provides authoritative throttling counts. Host-level tracing sees ground truth — no distortion from scheduling. |
| **Gaps** | **Timing accuracy is fundamentally distorted for any trace collected from INSIDE a container.** CFS throttling inserts wall-clock gaps (up to 100ms per period) that appear as execution time. CPU weight-based pre-emption causes variable latencies dependent on neighbor workload. Memory pressure causes syscall latency spikes misattributed to the application. Network namespace overhead is invisible to application traces. Application-level spans (OpenTelemetry, Langfuse) report wall-clock time that INCLUDES all scheduling distortion — they cannot distinguish 5ms of computation + 95ms of throttle from 100ms of computation. |
| **Implementations must add** | Wall-clock to CPU-clock reconciliation (subtract `throttled_usec` delta from span durations), runqueue wait compensation, mandatory `cpu.stat` correlation for any timing-sensitive trace analysis, distortion indicators in trace metadata. |

---

## Assessment Summary

| Dimension | Rating | Key Gap |
|-----------|--------|---------|
| Observability | Strong | Host/container namespace visibility boundary requires explicit bridging |
| Security | Moderate | Host-level tracing sees all tenants; no isolation at trace layer |
| Identity | Moderate | Kernel traces use PIDs; Kubernetes identity requires translation |
| Reliability | Moderate | Pod eviction/pre-emption causes trace data loss without external flush |
| Accuracy | Moderate | CFS throttling and pre-emption distort wall-clock timing inside containers |
