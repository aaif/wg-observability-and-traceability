# AAIF Reference Architecture: Virtualization Tracing

| Field | Value |
|-------|-------|
| **Subject** | Hypervisor Tracing (KVM, VirtualBox, VMware, Xen, Hyper-V) |
| **Version** | Multi-platform |
| **Date** | 2026-08-12 |

---

## Objective

Demonstrates how virtualization hypervisors fundamentally affect trace accuracy through vCPU pre-emption, stolen time, and timer virtualization — creating systematic timestamp distortion in guest traces — and how host-level OS tracepoints (KVM tracepoints via ftrace/perf, xentrace, vmkernel events) expose the hypervisor's scheduling decisions that are otherwise invisible to the guest.

---

## Scope / Zoom Level

**Infrastructure layer — between physical hardware and guest OS kernel tracing.**

Virtualization inserts a scheduling layer between physical CPUs and guest kernels. This layer pre-empts vCPUs, virtualizes timers, and intercepts hardware access — all of which distort the timestamps and performance counters that tracing tools rely on. This document covers tracepoints exposing hypervisor behavior from the host side, and the timing distortions affecting tracing inside guests.

---

## Prerequisites

| Component | Version / Pinned | Notes |
|-----------|-----------------|-------|
| Linux kernel (host) | ≥ 5.4 (6.x recommended) | `CONFIG_KVM=m`, `CONFIG_KVM_INTEL=m` or `CONFIG_KVM_AMD=m` |
| QEMU | ≥ 7.0 | KVM acceleration; device emulation |
| VirtualBox | ≥ 7.0 | `VBoxManage metrics` for host-side counters |
| VMware ESXi | ≥ 7.0 / Workstation ≥ 17 | `esxtop`, `vscsiStats`, vpxd event logging |
| Xen | ≥ 4.16 | `xentrace` for hypervisor-level event capture |
| Hyper-V | Server 2022+ / WSL2 | ETW with Microsoft-Windows-Hyper-V-* providers |
| perf | ≥ 5.4 (matching kernel) | `perf kvm stat`, `perf trace -e kvm:*` |
| ftrace / tracefs | Mounted at `/sys/kernel/tracing` | KVM tracepoints under `events/kvm/` |
| LTTng | 2.13+ with lttng-modules | Kernel tracepoint subscription for KVM events |
| trace-cmd | ≥ 3.x | CLI recording of KVM tracepoints |
| Root / CAP_SYS_ADMIN | — | Required on host for all hypervisor tracing |

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│  Guest VM                                                               │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │  Guest Kernel (ftrace, perf inside guest)                         │  │
│  │  ⚠ Timestamps subject to stolen-time distortion                   │  │
│  │  ⚠ Hardware counters stop during pre-emption                      │  │
│  │  ⚠ TSC may be offset/scaled by hypervisor                         │  │
│  │                                                                   │  │
│  │  Paravirtual interfaces:                                          │  │
│  │    • kvmclock / pvclock (corrected time source)                   │  │
│  │    • steal_time (MSR 0x4b564d03 → /proc/stat)                    │  │
│  │    • pv_sched_yield, pv_kick_cpu (scheduling hints)               │  │
│  └───────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │ VM Exit / VM Entry (hardware trap)
┌────────────────────────────────────▼────────────────────────────────────┐
│  Hypervisor Layer                                                       │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │  KVM (kernel module)                                              │  │
│  │  Tracepoints: kvm_entry, kvm_exit, kvm_mmu_page_fault,           │  │
│  │    kvm_pio, kvm_mmio, kvm_halt_poll_ns, kvm_nested_vmexit,       │  │
│  │    kvm_inj_virq, kvm_apicv_*, kvm_steal_time                     │  │
│  │  Exposed via: /sys/kernel/tracing/events/kvm/                     │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │  QEMU (userspace device emulation)                                │  │
│  │  Trace backend: --trace events=file (ftrace, dtrace, log)         │  │
│  └───────────────────────────────────────────────────────────────────┘  │
├─────────────────────────────────────────────────────────────────────────┤
│  Host Kernel                                                            │
│  CFS schedules vCPU threads like any process                            │
│  sched:sched_switch, sched:sched_wakeup (vCPU thread context)           │
│  perf PMU counters reflect true physical CPU activity                   │
└────────────────────────────────────┬────────────────────────────────────┘
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  Physical Hardware                                                       │
│  CPU: VT-x/AMD-V, TSC, PMU | VMCS/VMCB: exit reasons, TSC offset       │
│  APIC: interrupt virtualization, posted interrupts                       │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Tracepoint Coverage at the OS Level

### KVM Tracepoints (Linux host)

KVM exposes 50+ tracepoints in the `kvm:` subsystem, accessible via ftrace, perf, and LTTng.

#### Core Exit/Entry

| Tracepoint | Fires When | Key Fields |
|------------|-----------|------------|
| `kvm_entry` | vCPU enters guest (VMRESUME) | vcpu_id, guest_rip |
| `kvm_exit` | VM exit occurs | exit_reason, guest_rip, info1, info2 |
| `kvm_userspace_exit` | Exit needs QEMU handling | reason |
| `kvm_nested_vmexit` | Nested exit (L2→L1) | rip, exit_reason |

#### Memory Management

| Tracepoint | Fires When | Key Fields |
|------------|-----------|------------|
| `kvm_mmu_page_fault` | Guest page fault trapped | addr, error_code, is_write |
| `kvm_mmu_get_page` | Shadow page allocation | gfn, role |
| `kvm_mmu_set_spte` | Shadow PTE written | gfn, spte, level |

#### I/O and Interrupts

| Tracepoint | Fires When | Key Fields |
|------------|-----------|------------|
| `kvm_pio` | Port I/O instruction | port, size, direction, val |
| `kvm_mmio` | MMIO access | gpa, val, len, is_write |
| `kvm_inj_virq` | Virtual IRQ injected | irq |
| `kvm_msi_set_irq` | MSI interrupt delivery | addr, data |

#### Scheduling and Halt

| Tracepoint | Fires When | Key Fields |
|------------|-----------|------------|
| `kvm_halt_poll_ns` | Halt-poll duration change | vcpu_id, new, old, grow |
| `kvm_vcpu_wakeup` | vCPU resumes from halt | ns, waited |
| `kvm_steal_time` | Steal-time update | vcpu_id, steal |

#### Enabling and Consuming

```bash
# ftrace (direct, zero-install)
echo 1 > /sys/kernel/tracing/events/kvm/enable
cat /sys/kernel/tracing/trace_pipe

# perf (recording with timestamps)
perf record -e 'kvm:*' -a sleep 10
perf script

# perf kvm stat (aggregated view)
perf kvm stat live
perf kvm stat record && perf kvm stat report

# trace-cmd (structured recording with scheduler correlation)
trace-cmd record -e kvm -e sched:sched_switch sleep 10
trace-cmd report

# LTTng (CTF binary, long-running, low-overhead)
lttng create kvm-session
lttng enable-event -k 'kvm_entry,kvm_exit,kvm_halt_poll_ns'
lttng start && sleep 60 && lttng stop && lttng destroy
babeltrace2 ~/lttng-traces/kvm-session*

# bpftrace (programmable aggregation)
bpftrace -e 'tracepoint:kvm:kvm_exit { @reasons[args->exit_reason] = count(); }'
```

### VirtualBox Tracepoints

**DTrace probes** (Solaris, macOS, FreeBSD with DTrace support):
- `vboxvmm:::guest-entry` / `vboxvmm:::guest-exit`
- `vboxvmm:::r0-hmvmx-vmexit` — Intel VT-x exit handler
- `vboxvmm:::r0-hmsvm-vmexit` — AMD SVM exit handler

**VBoxManage metrics**:
```bash
VBoxManage metrics setup --period 1 --samples 60 '*' 'MyVM'
VBoxManage metrics query 'MyVM' 'CPU/Load/User,CPU/Load/Kernel,Guest/CPU/Load/Idle'
VBoxManage metrics query 'MyVM' 'RAM/Usage/Used'
```

**VBox.log**: Per-VM log files with exit-reason statistics, VMCS dumps, and timing data. No Linux DTrace probes — limited to metrics + log parsing on Linux hosts.

### VMware (ESXi / Workstation)

**esxtop** (ESXi) — critical fields per vCPU:
- `%RDY` — ready time: runnable but waiting for pCPU (**= pre-emption/steal**)
- `%CSTP` — co-stop: SMP VMs waiting for simultaneous scheduling
- `%USED` / `%RUN` — actual execution time
- `%SWPWT` — swap wait time

```bash
esxtop -b -d 2 -n 100 > esxtop_output.csv
```

**vscsiStats**: `vscsiStats -s -w <worldID>` enables per-VM storage I/O latency histograms.

**vmkernel tracepoints**: `vmkernel.log` records scheduler swaps (`SchedSwap`), NUMA migrations, balloon events. Not user-accessible as tracefs-style tracepoints.

**vpxd events**: vCenter event stream via vSphere API `EventManager` / `PerformanceManager`.

### Xen Tracepoints (xentrace)

```bash
xentrace -D -e 0xffff /tmp/xentrace.bin
xentrace_format /tmp/xentrace.bin /usr/share/xen/formats
```

Key event classes: `TRC_SCHED_SWITCH` (vCPU→pCPU mapping), `TRC_SCHED_BLOCK` (domain halted), `TRC_HVM_VMEXIT`/`TRC_HVM_VMENTRY`, `TRC_HVM_IO_ASSIST`, `TRC_MEM_*` (p2m, grant tables).

### VFIO (Virtual Function I/O) — Device Passthrough

VFIO provides direct device assignment to VMs, bypassing the hypervisor's emulation layer. This creates a **tracing blind spot**: the host loses visibility into device interactions once the guest owns the IOMMU mapping.

#### Architecture

```
┌────────────────────────────────────────────────────────────────────┐
│  Guest VM                                                          │
│  ┌────────────────────────────────────────────────────────────┐   │
│  │  Guest driver (native, no paravirt)                        │   │
│  │  • Direct MMIO to device BARs (no VM exit)                 │   │
│  │  • DMA via guest-physical addresses (IOMMU-translated)     │   │
│  │  • MSI/MSI-X interrupts posted directly (no host trap)     │   │
│  └────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────┬─────────────────────────────────┘
                                   │ (No VM exits for device access)
┌──────────────────────────────────▼─────────────────────────────────┐
│  Host VFIO Layer                                                   │
│  ┌────────────────────────────────────────────────────────────┐   │
│  │  IOMMU (VT-d / AMD-Vi)                                    │   │
│  │  • DMA remapping: guest phys → host phys                  │   │
│  │  • Interrupt remapping: device MSI → guest vector          │   │
│  │  • Isolation: device cannot DMA outside assigned region    │   │
│  └────────────────────────────────────────────────────────────┘   │
│  ┌────────────────────────────────────────────────────────────┐   │
│  │  VFIO driver (/dev/vfio/*)                                 │   │
│  │  • Group/container management                              │   │
│  │  • IOMMU mapping setup (VFIO_IOMMU_MAP_DMA)               │   │
│  │  • Device reset, config space access                       │   │
│  └────────────────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌────────────────────────────────────────────────────────────────────┐
│  Physical Device (GPU, NIC, NVMe, FPGA)                           │
│  • Device operates at native speed                                │
│  • No hypervisor interception of MMIO/DMA/interrupts              │
└────────────────────────────────────────────────────────────────────┘
```

#### VFIO Tracepoints

| Tracepoint | Fires When | Key Fields |
|------------|-----------|------------|
| `vfio_iommu_map_dma` | Guest maps DMA region | iova, size, flags |
| `vfio_iommu_unmap_dma` | Guest unmaps DMA region | iova, size |
| `vfio_pci_intx_mask` | Legacy INTx masked | devname |
| `vfio_pci_intx_unmask` | Legacy INTx unmasked | devname |
| `vfio_platform_irq_enable` | Platform IRQ enabled | index |
| `vfio_platform_irq_disable` | Platform IRQ disabled | index |

```bash
# Enable VFIO tracepoints
echo 1 > /sys/kernel/tracing/events/vfio/enable
cat /sys/kernel/tracing/trace_pipe

# IOMMU fault tracing (AMD-Vi / Intel VT-d)
echo 1 > /sys/kernel/tracing/events/iommu/enable
# io_page_fault: fires on DMA remapping failures
# map / unmap: IOMMU table modifications
```

#### IOMMU Tracepoints (Intel VT-d / AMD-Vi)

| Tracepoint | Fires When | Key Fields |
|------------|-----------|------------|
| `iommu:io_page_fault` | Device DMA hits unmapped address | dev, iova, flags |
| `iommu:map` | IOMMU mapping created | iova, paddr, size |
| `iommu:unmap` | IOMMU mapping removed | iova, size |
| `iommu:attach_device_to_domain` | Device assigned to domain | dev |
| `iommu:detach_device_from_domain` | Device removed from domain | dev |

#### Timing Implications for VFIO

VFIO passthrough fundamentally changes the tracing picture:

**What becomes invisible to the host:**
- Device register reads/writes (MMIO mapped directly, no VM exits)
- DMA transfers (IOMMU translates without host CPU involvement)
- Posted MSI-X interrupts (delivered to guest without host trap)
- Device command queues and completions (NVMe, GPU command rings)

**What remains visible:**
- Initial VFIO setup: group attachment, DMA mapping establishment
- IOMMU faults (misconfigurations, out-of-bounds DMA)
- Device reset events
- PCI config space access (still trapped for safety)
- Interrupt routing changes

**Timing accuracy for passed-through devices:**
- MMIO operations: **Near-native latency** — no VM exit means no hypervisor distortion
- DMA completions: **Native** — IOMMU translation adds <100ns, not visible in traces
- Interrupt delivery: **Native with posted interrupts** — no VM exit; without posted interrupts, MSI delivery causes VM exit adding 1–3μs
- **Net effect**: GPU/NIC/NVMe operations traced from inside the guest are **more timing-accurate** than with emulated devices (no VM exit delays), but **still subject to vCPU pre-emption** for the CPU-side of the driver

```bash
# Verify VFIO assignment
ls /sys/bus/pci/drivers/vfio-pci/
# 0000:03:00.0 → device bound to VFIO

# Check IOMMU groups
find /sys/kernel/iommu_groups/ -type l | sort

# Monitor IOMMU faults
perf record -e 'iommu:io_page_fault' -a -- sleep 60
perf script  # Any events = DMA misconfiguration

# GPU passthrough: guest-side tracing works natively
# (CUPTI, rocprofiler work as on bare metal since device is unmediated)
```

#### SR-IOV with VFIO

Single Root I/O Virtualization creates hardware-partitioned Virtual Functions (VFs):

```bash
# Create VFs on host (before VM assignment)
echo 4 > /sys/class/net/ens1f0/device/sriov_numvfs

# Each VF is independently assignable via VFIO
# VF tracepoints: same as PF but per-function
# Network VFs: guest sees native NIC; tcpdump/XDP work at line rate
# NVMe VFs: guest sees native NVMe namespace; blktrace works natively
```

**Tracing implication**: With SR-IOV, the guest has a real hardware device. Host-side network/block tracepoints don't fire for VF traffic — you must trace inside the guest or at the physical switch/controller.

### Hyper-V (ETW Providers)

Key providers: `Microsoft-Windows-Hyper-V-Hypervisor`, `Microsoft-Windows-Hyper-V-Worker`, `Microsoft-Windows-Hyper-V-VmSwitch`, `Microsoft-Windows-Hyper-V-StorageVSP`. Captured via `logman create trace` or `xperf`.

---

## ⚠ CRITICAL: Timing Distortion from Pre-emption

### vCPU Scheduling and Pre-emption

A vCPU is a host-kernel thread scheduled by CFS. When the host pre-empts a vCPU thread:

1. Guest execution halts at an arbitrary instruction
2. Guest **does not know** it has been pre-empted
3. Time perception depends on clock source (kvmclock vs raw TSC)
4. When rescheduled, guest resumes as if nothing happened

```
Guest trace (kvmclock — steal-aware):
  [t=0.000ms] function_entry: process_request
  [t=0.050ms] function_exit: process_request    ← shows 50μs (includes stolen)

Guest trace (raw TSC — CPU-only):
  [t=0.000ms] function_entry: process_request
  [t=0.015ms] function_exit: process_request    ← shows 15μs (excludes stolen)

Reality: 15μs CPU work + 35μs stolen = 50μs wall-clock.
Neither trace mode shows the complete picture without host correlation.
```

### Stolen Time Accounting

Linux guests expose stolen time through the paravirtual steal-time interface (KVM MSR `0x4b564d03`):

```bash
# /proc/stat — 8th per-CPU field is steal (in jiffies)
cat /proc/stat
# cpu  12345 0 6789 98765 0 123 0 4567 0 0
#                                      ^^^^ steal time

# Per-CPU steal percentage
mpstat -P ALL 1
# %steal column shows hypervisor-stolen time

# perf: task-clock < wall-clock when steal occurs
perf stat -e cycles,instructions,task-clock sleep 1
# task-clock will be < 1000ms if stolen time > 0
```

**Paravirtual clock sources**:

| Clock Source | Mechanism | Steal-Aware | Accuracy |
|-------------|-----------|-------------|----------|
| `kvmclock` | Shared memory page, host TSC + offset | Yes | Wall-clock (steal included) |
| `tsc` passthrough | Raw hardware TSC, `-cpu host,+invtsc` | No | CPU-clock only |
| `acpi_pm` | Emulated ACPI timer (3.58 MHz) | Wall-clock | 280ns resolution |
| `hpet` | Emulated HPET | Wall-clock | High VM-exit cost |

```bash
# Check guest clock source
cat /sys/devices/system/clocksource/clocksource0/current_clocksource
# kvm-clock (default, steal-aware)
```

### Timer Virtualization

**TSC Offsetting**: VMCS/VMCB `TSC_OFFSET` field. `guest_tsc = host_tsc + TSC_OFFSET`. Rate matches host but pre-emption creates invisible time gaps.

**TSC Scaling** (AMD-V, newer Intel): `guest_tsc = (host_tsc × TSC_MULTIPLIER) >> 48 + TSC_OFFSET`. Enables live migration across different TSC frequencies; introduces nanosecond-scale rounding errors.

**VMX Preemption Timer**: Hardware timer decrementing only while guest executes. KVM uses this for lapic timer emulation. Creates divergence: timer counts CPU-time, not wall-time.

### Impact on Tracing

**ftrace inside guest**: `function_graph` duration values include stolen time (kvmclock) or exclude wall-clock gaps (TSC passthrough). Gaps in trace output may be real idle time OR invisible pre-emption — indistinguishable from guest perspective.

**perf inside guest**: Hardware PMU counters **stop during pre-emption** because the physical PMU serves whatever runs on the pCPU. Therefore:
- `cycles` ≠ `wall_time × frequency`
- `task-clock` < `wall-clock` by exactly the steal amount
- IPC remains valid (numerator and denominator both pause)
- Cache-miss counts elevated: cache evicted during pre-emption, invisible to guest

**Latency measurements are UNRELIABLE**: `measured_latency = actual + stolen`. Pre-emption creates artificial p99 spikes. A 50μs operation appears as 5ms if vCPU stolen for 4.95ms. Real from application perspective, not caused by application.

### Halt Polling Optimization

When vCPU executes HLT, KVM has two options: schedule out (high wakeup latency, 1–10ms) or spin-poll (low wakeup latency, burns host CPU).

```bash
cat /sys/module/kvm/parameters/halt_poll_ns       # Default: 200000 (200μs)
cat /sys/module/kvm/parameters/halt_poll_ns_grow   # Default: 2 (double on success)
cat /sys/module/kvm/parameters/halt_poll_ns_shrink # Default: 0 (reset on failure)
```

**Trade-off**: Halt polling burns host CPU to reduce the gap between "guest halted" and "guest resumes." This improves timestamp accuracy for latency-sensitive transitions at cost of host efficiency. Traced via `kvm_halt_poll_ns`.

### Nested Virtualization Compounding

With L0 → L1 → L2: both L0 and L1 schedulers can independently pre-empt. TSC offsetting applied twice. Two steal-time sources compound with no correction mechanism. `kvm_nested_vmexit` on L0 captures double-exit events. **Traces inside L2 are subject to two independent distortion sources.**

### Mitigations

| Mitigation | Mechanism | Effect on Tracing |
|-----------|-----------|-------------------|
| CPU pinning | `isolcpus=4-7` + `virsh vcpupin` | Eliminates pre-emption; timestamps accurate |
| NOHZ_FULL | `nohz_full=4-7` on host kernel cmdline | Removes timer ticks from isolated CPUs |
| TSC passthrough | `-cpu host,+invtsc` | No offset jitter; raw CPU-time visible |
| Posted interrupts | Hardware APIC virtualization | Fewer VM exits → fewer timing gaps |
| SCHED_FIFO | `chrt -f -p 99 <vcpu_pid>` | Prevents CFS pre-emption |
| kvmclock correction | Paravirt clock deducts steal | `clock_gettime()` reflects wall-clock |
| Disable C-states | `processor.max_cstate=0` on host | No exit latency from deep idle |

```bash
# Full isolation for accurate guest tracing:
# Host cmdline: isolcpus=4-7 nohz_full=4-7 rcu_nocbs=4-7
virsh vcpupin myvm 0 4
virsh vcpupin myvm 1 5
virsh vcpupin myvm 2 6
virsh vcpupin myvm 3 7
# Set SCHED_FIFO for vCPU threads:
for pid in $(ps -eLo pid,comm | grep qemu | awk '{print $1}'); do
    chrt -f -p 99 $pid 2>/dev/null
done
# Verify in guest: mpstat shows %steal = 0.00
```

---

## Instrumentation Walkthrough

| Layer | What | How | Overhead |
|-------|------|-----|----------|
| Host: VM exits | Every exit reason, guest RIP | `kvm:kvm_exit` tracepoint | ~100ns/exit |
| Host: vCPU scheduling | Pre-emption start/end | `sched:sched_switch` filtered by QEMU PIDs | ~80ns/switch |
| Host: Halt polling | Poll duration, growth | `kvm:kvm_halt_poll_ns` | Negligible |
| Host: Memory | EPT/NPT violations | `kvm:kvm_mmu_*` tracepoints | ~150ns/fault |
| Host: Interrupts | IRQ injection timing | `kvm:kvm_inj_virq` | ~100ns/injection |
| Guest: Steal time | Cumulative stolen CPU | `/proc/stat`, `mpstat` | Zero (paravirt MSR) |
| Guest: Clock source | Time correction metadata | `/sys/devices/system/clocksource/` | Zero |

### Correlating Host and Guest Traces

```bash
# Host: record exits + scheduler context switches
trace-cmd record -e kvm:kvm_exit -e kvm:kvm_entry \
  -e sched:sched_switch -P $(pgrep -d, qemu-system) sleep 30

# Analysis: each sched_switch AWAY from vCPU = pre-emption start
#           each sched_switch TO vCPU = pre-emption end
#           duration = stolen time for that interval
# Overlay stolen windows onto guest trace timeline
trace-cmd report | grep -E 'kvm_exit|sched_switch'
```

---

## Sample Trace Output

### KVM Exit/Entry Pairs (host ftrace)

```
    qemu-system-4521  [004] d..1.  1842.563201: kvm_exit: vcpu 0 reason EPT_VIOLATION rip 0xffffffff81a03c20 info1 0x00000000b83183 info2 0x0
    qemu-system-4521  [004] d..1.  1842.563205: kvm_mmu_page_fault: addr 0xb83000 err 0x183
    qemu-system-4521  [004] d..1.  1842.563208: kvm_entry: vcpu 0
    qemu-system-4521  [004] d..1.  1842.563894: kvm_exit: vcpu 0 reason IO_INSTRUCTION rip 0xffffffff81632a10 info1 0x00000cf900040008 info2 0x0
    qemu-system-4521  [004] d..1.  1842.563895: kvm_pio: pio_read at 0xcf9 size 4 count 1 val 0x0
    qemu-system-4521  [004] d..1.  1842.563897: kvm_entry: vcpu 0
    qemu-system-4521  [004] d..1.  1842.570412: kvm_exit: vcpu 0 reason HLT rip 0xffffffff81e0115a info1 0x0 info2 0x0
    qemu-system-4521  [004] d..1.  1842.570413: kvm_halt_poll_ns: vcpu 0 new 400000 old 200000 grow 1
    qemu-system-4521  [004] d..1.  1842.570590: kvm_vcpu_wakeup: poll time 176841 ns wakeup
    qemu-system-4521  [004] d..1.  1842.570591: kvm_entry: vcpu 0
    qemu-system-4521  [004] d..1.  1842.583102: kvm_exit: vcpu 0 reason EXTERNAL_INTERRUPT rip 0xffffffff81a01234 info1 0xfe info2 0x0
    qemu-system-4521  [004] d..1.  1842.583103: kvm_entry: vcpu 0
```

### Stolen Time Visible (host sched_switch)

```
# vCPU pre-empted — 4.5ms stolen from guest
    qemu-system-4521  [004] d..1.  1842.590000: sched_switch: prev_comm=qemu-system prev_pid=4521 prev_prio=120 prev_state=R ==> next_comm=stress-ng next_pid=8901 next_prio=120
    stress-ng-8901    [004] d..1.  1842.594523: sched_switch: prev_comm=stress-ng prev_pid=8901 prev_prio=120 prev_state=S ==> next_comm=qemu-system next_pid=4521 next_prio=120
# ↑ 4.523ms stolen: guest traces show inflated latency during this window
```

### perf kvm stat

```
$ perf kvm stat report

Analyze events for all VMs, all VCPUs:

    VM-EXIT       Samples   Pct%    Avg t (ns)    Min t     Max t
 EPT_VIOLATION      8921   32.1%      14000        800      89000
 EXTERNAL_INTER    12045   43.4%        700        500       3200
 HLT                4521   16.3%     150200       1200    8900000
 IO_INSTRUCTION     1523    5.5%      60000       2100      95000
 MSR_WRITE           412    1.5%       4000        400       8000
 CPUID               334    1.2%       3200        500       5000

Total Samples:27756, Total events handled time:1006657000ns
```

---

## Cost Profile

| Scenario | Overhead | Notes |
|----------|----------|-------|
| Host: all KVM tracepoints enabled | 2–5% guest throughput | ~100ns added per exit (exits already cost 500–2000ns) |
| Host: kvm_exit + sched_switch only | 1–3% | Minimal beyond intrinsic exit cost |
| Host: `perf kvm stat live` | <1% | Aggregation only, no per-event storage |
| Guest: ftrace function_graph | 15–30% | Bare-metal overhead + stolen-time distortion |
| Guest: perf hardware counters | 1–3% + inaccuracy | PMU overflow generates extra VM exits |
| Guest: LTTng kernel tracing | 3–8% + timing inaccuracy | High throughput but timestamps unreliable |
| Host+Guest combined | 5–15% | Dual recording compounds perturbation |

---

## Validation Criteria

```bash
# 1. KVM tracepoints exist
ls /sys/kernel/tracing/events/kvm/ | wc -l  # ≥ 20

# 2. KVM module loaded
lsmod | grep -E 'kvm_intel|kvm_amd'

# 3. Record exits while VM runs
perf record -e kvm:kvm_exit -a -- sleep 5
perf script | head -20  # Should show exit events with reasons

# 4. perf kvm stat works
perf kvm stat live  # Real-time exit table (Ctrl+C to stop)

# 5. Halt-polling active
cat /sys/module/kvm/parameters/halt_poll_ns  # Non-zero (default 200000)

# 6. Steal time visible in guest (under host CPU contention)
# In guest: mpstat -P ALL 1  →  %steal > 0

# 7. Guest clock source is paravirtual
# In guest: cat /sys/devices/system/clocksource/clocksource0/current_clocksource
# Expected: kvm-clock

# 8. CPU pinning eliminates steal
virsh vcpupin myvm 0 4
# In guest: mpstat shows %steal = 0.00 after pinning
```

---

## Limitations / Out of Scope

| Item | Status |
|------|--------|
| Guest-side timestamp accuracy | Fundamentally compromised without CPU pinning |
| Cross-hypervisor trace format | No unified format; each hypervisor uses different output |
| Live migration tracing | TSC offset changes during migration; traces discontinuous |
| GPU passthrough tracing | VFIO bypasses hypervisor — host blind to device ops; trace from guest side |
| Windows guest steal time | No paravirtual steal-time interface for Windows on KVM |
| Nested virt timing correction | No known mitigation for double-steal distortion |
| VirtualBox on Linux | No DTrace probes; limited to VBoxManage metrics + logs |
| Encrypted VMs (SEV/TDX) | Memory encryption prevents host memory introspection |
| ARM virtualization | Different trap mechanism (EL2); tracepoint names differ |
| Proprietary hypervisor internals | VMware/Hyper-V don't expose kernel-level tracepoints |
| Real-time guarantees | Virtualization inherently conflicts with hard real-time |

---

## Evaluation Assessment

### Observability

**Rating: Strong (host-side) / Compromised (guest-side)**

| Aspect | Assessment |
|--------|------------|
| **Strengths** | 50+ KVM tracepoints covering exits, MMU, I/O, scheduling. `perf kvm stat` provides zero-setup visibility. Host traces show the complete picture: when vCPUs run, why they exit, when pre-empted. Combined host+guest traces can reconstruct true execution timeline. |
| **Gaps** | Guest traces blind to pre-emption. No unified cross-hypervisor format. VirtualBox/VMware expose less granularity than KVM. Host/guest trace correlation requires manual timestamp alignment. No automatic stolen-time annotation of guest traces. |
| **Implementations must add** | Automatic host/guest correlation, stolen-time overlay on guest traces, cross-hypervisor abstraction. |

### Security

**Rating: Partial**

| Aspect | Assessment |
|--------|------------|
| **Strengths** | Host tracing requires root — guests cannot observe each other. SEV/TDX encrypted VMs prevent host memory introspection. KVM tracepoints expose exit reasons without guest memory contents. |
| **Gaps** | Host root can profile any VM without consent (multi-tenant risk). Guest RIP in `kvm_exit` leaks kernel addresses. No trace encryption at rest. Timing side-channels through halt-poll patterns. |
| **Implementations must add** | Per-VM trace ACLs, RIP anonymization, trace encryption, guest consent for profiling. |

### Identity Management

**Rating: Minimal**

| Aspect | Assessment |
|--------|------------|
| **Strengths** | vCPU ID in every event. QEMU PID identifies VM. `virsh` domain names for human-readable identity. |
| **Gaps** | No tenant identity in tracepoints. No cross-boundary correlation IDs. No AI agent identity propagation through virtualization layer. No authentication of trace consumers. |
| **Implementations must add** | Tenant/workload identity tagging, cross-boundary trace correlation, AI agent identity propagation. |

### Reliability

**Rating: Strong (host-side) / Moderate (guest-side)**

| Aspect | Assessment |
|--------|------------|
| **Strengths** | In-kernel tracepoints — no daemon to crash. Ring buffer survives guest crashes. `perf kvm stat` is lock-free. Host tracing unaffected by guest state. |
| **Gaps** | Guest traces lost on crash without flush. High exit rates can overflow ring buffer. Live migration breaks trace continuity. Overflow during exit storms silently drops events. |
| **Implementations must add** | Remote trace streaming, cross-host continuity through migration, overflow alerting. |

### Accuracy

**Rating: Compromised (guest-side) / Strong (host-side)**

| Aspect | Assessment |
|--------|------------|
| **Strengths** | Host tracepoints capture exact VM exit/entry timestamps at TSC precision. Exit counts and categorization are accurate. Halt-poll duration measured in nanoseconds. Host scheduler tracepoints precisely identify stolen-time windows. |
| **Gaps** | **Guest-side timing accuracy is fundamentally compromised by pre-emption.** Timestamps include stolen time (kvmclock) or exclude wall-clock gaps (TSC passthrough) — neither reflects true application behavior alone. Hardware counters stop during pre-emption (cycles ≠ wall time). Cache metrics degraded by invisible eviction. Nested virtualization compounds with no correction. |
| **Implementations must add** | Mandatory CPU pinning for timing-sensitive tracing, automatic stolen-time deduction, host-assisted timestamp correction, warnings on guest traces without isolation. |

---

## Assessment Summary

| Dimension | Rating | Key Gap |
|-----------|--------|---------|
| Observability | Strong / Compromised | Guest traces blind to pre-emption; no cross-hypervisor format |
| Security | Partial | Host can observe all guests; RIP leakage; no trace encryption |
| Identity | Minimal | vCPU/PID only; no tenant, workload, or AI agent identity |
| Reliability | Strong / Moderate | Guest crash loses traces; live migration breaks continuity |
| Accuracy | **Compromised** / Strong | **Guest timing fundamentally unreliable without CPU pinning; pre-emption creates systematic measurement error** |
