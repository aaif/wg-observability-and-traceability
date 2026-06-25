# AAIF Reference Architecture: Linux Driver Tracing Mechanisms

| Field | Value |
|-------|-------|
| **Subject** | [Linux Driver Tracing](https://www.kernel.org/doc/html/latest/driver-api/tracing.html) |
| **Version** | Linux 6.x (kernel-integrated) |
| **Date** | 2026-06-25 |

---

## Objective

Demonstrates how Linux provides a layered set of tracing, debugging, and observability mechanisms specifically for device drivers — from structured logging (dev_dbg) through dynamic debug, custom tracepoints, subsystem-specific tracers (usbmon, blktrace), debugfs inspection, and devcoredump — enabling driver developers and system administrators to observe hardware interaction without modifying or recompiling driver code.

---

## Scope / Zoom Level

**System layer — kernel driver subsystem instrumentation and hardware interaction observation.**

This covers the mechanisms available for observing device driver behavior: how drivers communicate with hardware, how I/O requests flow through subsystem layers, and how driver state can be inspected at runtime. It spans from compile-time instrumentation (TRACE_EVENT) to runtime-enabled logging (dynamic debug) to post-mortem analysis (devcoredump).

---

## Prerequisites

| Component | Version / Pinned | Notes |
|-----------|-----------------|-------|
| Linux kernel | ≥ 4.x (6.x recommended) | `CONFIG_DYNAMIC_DEBUG=y`, `CONFIG_FTRACE=y`, `CONFIG_DEBUG_FS=y` |
| debugfs | Mounted at `/sys/kernel/debug/` | Required for dynamic debug, driver debug files |
| tracefs | Mounted at `/sys/kernel/tracing/` | Required for tracepoints |
| Root / CAP_SYS_ADMIN | — | Required for all driver tracing mechanisms |
| blktrace | 2.x (optional) | Block device tracing |
| usbmon | Built-in (optional) | USB traffic tracing |
| trace-cmd | 3.x (optional) | Tracepoint recording |
| perf | Matches kernel | Alternative tracepoint consumer |

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Hardware Devices                                      │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────────┐    │
│  │  USB    │  │  NVMe   │  │  GPU    │  │  NIC    │  │  I2C/SPI    │    │
│  │ devices │  │  drives │  │  (DRM)  │  │         │  │  sensors    │    │
│  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘  └──────┬──────┘    │
└───────┼─────────────┼───────────┼───────────┼────────────────┼────────────┘
        │             │           │           │                │
┌───────▼─────────────▼───────────▼───────────▼────────────────▼────────────┐
│                     Linux Kernel Driver Subsystems                          │
│                                                                            │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │  Driver Code (e.g., drivers/usb/*, drivers/gpu/drm/*, etc.)         │  │
│  │                                                                      │  │
│  │  Instrumentation points:                                             │  │
│  │  ┌────────────┐ ┌──────────────┐ ┌────────────────┐ ┌───────────┐  │  │
│  │  │ dev_dbg()  │ │ TRACE_EVENT()│ │ debugfs files  │ │devcoredump│  │  │
│  │  │ dev_info() │ │ trace_*()    │ │ custom attrs   │ │ (on crash)│  │  │
│  │  │ dev_err()  │ │              │ │                │ │           │  │  │
│  │  └─────┬──────┘ └──────┬───────┘ └───────┬────────┘ └─────┬─────┘  │  │
│  └────────┼────────────────┼─────────────────┼────────────────┼────────┘  │
│           │                │                 │                │            │
│           ▼                ▼                 ▼                ▼            │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │ Kernel Log  │  │ Ring Buffers │  │   debugfs    │  │/sys/class/   │  │
│  │ (printk)    │  │ (per-CPU)    │  │ /sys/kernel/ │  │devcoredump/  │  │
│  │ + dyndbg    │  │              │  │ debug/<drv>/ │  │              │  │
│  └──────┬──────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  │
│         │                │                 │                │            │
│  ┌──────▼──────┐  ┌──────▼───────┐  ┌──────▼───────┐  ┌──────▼───────┐  │
│  │  dmesg /    │  │ tracefs /    │  │ cat/echo     │  │ Read dump    │  │
│  │  journalctl │  │ perf / LTTng │  │ direct I/O   │  │ for analysis │  │
│  └─────────────┘  └──────────────┘  └──────────────┘  └──────────────┘  │
│                                                                            │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │  Subsystem-Specific Tracers                                          │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌───────────────────┐   │  │
│  │  │ usbmon   │  │ blktrace │  │ DRM debug│  │ regmap trace      │   │  │
│  │  │ (USB URB)│  │(block IO)│  │ (GPU)    │  │ (register access) │   │  │
│  │  └──────────┘  └──────────┘  └──────────┘  └───────────────────┘   │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────────┘
```

---

## Instrumentation Walkthrough

### 1. Structured Device Logging (dev_dbg / dev_info / dev_err)

**Mechanism**: `<linux/device.h>` macros that automatically prefix messages with device identity (bus/address).

```c
/* In driver code */
dev_info(&pdev->dev, "device initialized, firmware v%d.%d\n", major, minor);
dev_dbg(&pdev->dev, "register 0x%04x = 0x%08x\n", reg, val);
dev_err(&pdev->dev, "timeout waiting for hardware response\n");
dev_warn(&pdev->dev, "unexpected status 0x%x, retrying\n", status);
```

**Output** (dmesg):
```
[  123.456789] my_driver 0000:03:00.0: device initialized, firmware v2.1
[  123.456800] my_driver 0000:03:00.0: register 0x0010 = 0x0000cafe
[  124.567890] my_driver 0000:03:00.0: timeout waiting for hardware response
```

**Control**: `dev_dbg()` is compiled out unless `DEBUG` defined or dynamic debug enabled. Zero overhead in production.

### 2. Dynamic Debug (dyndbg)

**Mechanism**: Runtime enable/disable of `pr_debug()` and `dev_dbg()` calls without recompilation.

```bash
# List all debug callsites
cat /sys/kernel/debug/dynamic_debug/control | head

# Enable all debug messages in a driver
echo "module i915 +p" > /sys/kernel/debug/dynamic_debug/control

# Enable with function name and line number decoration
echo "module my_driver +pflmt" > /sys/kernel/debug/dynamic_debug/control

# Enable specific function
echo "func my_driver_probe +p" > /sys/kernel/debug/dynamic_debug/control

# Enable specific file
echo "file drivers/usb/core/hub.c +p" > /sys/kernel/debug/dynamic_debug/control

# Disable
echo "module i915 -p" > /sys/kernel/debug/dynamic_debug/control
```

**Flags**: `p` (print), `f` (include function name), `l` (include line number), `m` (include module name), `t` (include thread ID).

### 3. Custom Tracepoints in Drivers (TRACE_EVENT)

**Mechanism**: Drivers define structured tracepoints using the `TRACE_EVENT()` macro. These appear in tracefs and can be consumed by ftrace, perf, LTTng, or BPF.

```c
/* In include/trace/events/my_driver.h */
TRACE_EVENT(my_driver_cmd_submit,
    TP_PROTO(struct my_device *dev, u32 cmd_id, u64 addr, u32 len),
    TP_ARGS(dev, cmd_id, addr, len),
    TP_STRUCT__entry(
        __string(devname, dev_name(&dev->pdev->dev))
        __field(u32, cmd_id)
        __field(u64, addr)
        __field(u32, len)
    ),
    TP_fast_assign(
        __assign_str(devname, dev_name(&dev->pdev->dev));
        __entry->cmd_id = cmd_id;
        __entry->addr = addr;
        __entry->len = len;
    ),
    TP_printk("dev=%s cmd=%u addr=0x%llx len=%u",
        __get_str(devname), __entry->cmd_id, __entry->addr, __entry->len)
);
```

**Real-world driver tracepoint examples**:

| Subsystem | Tracepoint Category | Example Events |
|-----------|-------------------|----------------|
| DRM/GPU | `drm`, `i915`, `amdgpu` | `drm_vblank_event`, `i915_request_submit`, `amdgpu_cs_ioctl` |
| Block | `block` | `block_rq_issue`, `block_rq_complete`, `block_bio_queue` |
| USB | `xhci-hcd` | `xhci_urb_enqueue`, `xhci_cmd_completion` |
| Network | `net`, `napi` | `napi_poll`, `netif_receive_skb`, `net_dev_xmit` |
| I2C | `i2c` | `i2c_read`, `i2c_write`, `i2c_result` |
| SPI | `spi` | `spi_transfer_start`, `spi_transfer_stop` |
| Regmap | `regmap` | `regmap_reg_read`, `regmap_reg_write`, `regmap_cache_sync` |
| Power | `rpm` | `rpm_suspend`, `rpm_resume`, `rpm_idle` |
| Clock | `clk` | `clk_enable`, `clk_disable`, `clk_set_rate` |
| Regulator | `regulator` | `regulator_enable`, `regulator_set_voltage` |
| Thermal | `thermal` | `thermal_zone_trip`, `thermal_temperature` |
| GPIO | `gpio` | `gpio_value`, `gpio_direction` |

### 4. Subsystem-Specific Tracers

#### usbmon (USB traffic)

```bash
# Load usbmon (if not built-in)
modprobe usbmon

# List USB buses
ls /sys/kernel/debug/usb/usbmon/

# Capture USB bus 1 text format
cat /sys/kernel/debug/usb/usbmon/1t

# Output format:
# TIMESTAMP EVENT_TYPE ADDRESS STATUS LENGTH DATA
# ffff8801 4294967 S Ci:1:001:0 s 80 06 0100 0000 0040 64 <
# ffff8801 4294968 C Ci:1:001:0 0 18 = 12010002 00000040 6b1d0002 0200 0301 ...
```

Wireshark can capture via usbmon (Linux) using `extcap` for USB protocol analysis.

#### blktrace (Block I/O)

```bash
# Trace block device for 10 seconds
blktrace -d /dev/sda -o - | blkparse -i - | head -20

# Output:
#   8,0    1      1     0.000000000  4521  Q  RS 2048000 + 8 [nginx]
#   8,0    1      2     0.000001234  4521  G  RS 2048000 + 8 [nginx]
#   8,0    1      3     0.000005678  4521  I  RS 2048000 + 8 [nginx]
#   8,0    1      4     0.000010234  4521  D  RS 2048000 + 8 [nginx]
#   8,0    1      5     0.000234567  4521  C  RS 2048000 + 8 [0]

# Or use trace events directly:
echo 1 > /sys/kernel/tracing/events/block/enable
cat /sys/kernel/tracing/trace_pipe
```

#### DRM/GPU debugging

```bash
# DRM debugfs (per-GPU)
ls /sys/kernel/debug/dri/0/
# Output: clients  gem_names  i915_*  name  ...

# i915 specific
cat /sys/kernel/debug/dri/0/i915_frequency_info
cat /sys/kernel/debug/dri/0/i915_gem_objects

# DRM tracepoints
echo 1 > /sys/kernel/tracing/events/drm/drm_vblank_event/enable
echo 1 > /sys/kernel/tracing/events/i915/i915_request_submit/enable
```

#### regmap (register I/O abstraction)

```bash
# Trace all register reads/writes for a device
echo 1 > /sys/kernel/tracing/events/regmap/enable
cat /sys/kernel/tracing/trace_pipe

# Output:
# my_codec 1-001a: regmap_reg_write: reg=0x0010 val=0x00ff
# my_codec 1-001a: regmap_reg_read: reg=0x0020 val=0x1234
```

### 5. debugfs Driver Files

Drivers create custom files in `/sys/kernel/debug/<driver>/` for state inspection:

```bash
# Intel WiFi (iwlwifi)
ls /sys/kernel/debug/iwlwifi/
# Output: 0000:00:14.3/  stations/  fw_dbg_*  ...

# Network interface ring buffer state
cat /sys/kernel/debug/netdev/eth0/queues

# AMD GPU
ls /sys/kernel/debug/amdgpu/0000:03:00.0/
# Output: amdgpu_firmware_info  amdgpu_pm_info  amdgpu_ring_gfx  ...
```

### 6. devcoredump (Post-Mortem)

When a device firmware crashes, drivers can generate a core dump:

```bash
# List available devcoredumps
ls /sys/class/devcoredump/

# Read firmware crash dump (e.g., WiFi or GPU)
cat /sys/class/devcoredump/devcd0/data > firmware_crash.bin

# Dumps auto-delete after 5 minutes or manual:
echo 1 > /sys/class/devcoredump/devcd0/failing_device/delete
```

Used by: `iwlwifi`, `amdgpu`, `qcom`, `ath10k`, `mediatek` and other drivers for firmware crash analysis.

---

## Sample Trace Output

### Dynamic debug output (dmesg)

```
[  456.123456] i915 0000:00:02.0: [drm:intel_dp_aux_xfer [i915]] dp_aux_ch timeout status 0x7145003e
[  456.123460] i915 0000:00:02.0: [drm:intel_dp_link_training [i915]] clock recovery OK
[  456.234567] iwlwifi 0000:00:14.3: loaded firmware version 77.2df8986f.0 ty-a0-gf-a0-77.ucode
[  456.345678] nvme 0000:01:00.0: allocated 64 MiB host memory buffer
```

### Tracepoint output (regmap register access)

```
# tracer: nop
#
#           TASK-PID    CPU#  ||||   TIMESTAMP  FUNCTION
#              | |       |   ||||      |         |
     irq/31-i2c-187    [001] ....  456.789012: regmap_reg_write: codec 1-001a reg=00000010 val=000000ff
     irq/31-i2c-187    [001] ....  456.789015: regmap_reg_read: codec 1-001a reg=00000020 val=00001234
        kworker/0:1-42  [000] ....  456.789100: regmap_cache_sync: codec 1-001a type=flat status=start
        kworker/0:1-42  [000] ....  456.789200: regmap_cache_sync: codec 1-001a type=flat status=end
```

### blktrace output (block I/O request lifecycle)

```
  8,0    1      1     0.000000000  4521  Q  RS 2048000 + 8 [nginx]
  8,0    1      2     0.000001234  4521  G  RS 2048000 + 8 [nginx]
  8,0    1      3     0.000005678  4521  I  RS 2048000 + 8 [nginx]
  8,0    1      4     0.000010234  4521  D  RS 2048000 + 8 [nginx]
  8,0    1      5     0.000234567     0  C  RS 2048000 + 8 [0]
```

Actions: Q=queued, G=get request, I=inserted, D=dispatched to device, C=completed.

### GPU tracepoint (i915 request submission)

```
     Xorg-1234   [002] .... 789.012345: i915_request_submit: dev=0000:00:02.0, engine=rcs0, ctx=5, seqno=1024, tail=0x1a00
     Xorg-1234   [002] .... 789.012400: i915_request_in: dev=0000:00:02.0, engine=rcs0, ctx=5, seqno=1024, port=0
     kworker/2:1-42 [002] .... 789.015678: i915_request_out: dev=0000:00:02.0, engine=rcs0, ctx=5, seqno=1024, completed
```

### usbmon text output (USB control transfer)

```
ffff88810a3 3456789012 S Ci:1:004:0 s 80 06 0100 0000 0012 18 <
ffff88810a3 3456789100 C Ci:1:004:0 0 18 = 12011001 00000008 6b1d0002 0200 0301 0100 01
ffff88810a3 3456789200 S Co:1:004:0 s 00 09 0001 0000 0000 0
ffff88810a3 3456789250 C Co:1:004:0 0 0
```

### devcoredump metadata

```
$ cat /sys/class/devcoredump/devcd0/data | head -c 128 | xxd
00000000: 4957 4c20 4657 2044 554d 5020 5632 0000  IWL FW DUMP V2..
00000010: 0100 0000 0000 0000 4357 4649 0000 0000  ........CWFI....
00000020: 0800 0000 0000 0000 0001 0000 0000 0000  ................
```

---

## Cost Profile

### LLM token cost

**Not applicable.** These are kernel infrastructure mechanisms with no AI/LLM component.

### Compute/IO overhead per operation

| Mechanism | Overhead | Notes |
|-----------|----------|-------|
| dev_dbg (disabled) | 0 ns | Compiled out or dyndbg branch not taken |
| dev_dbg (enabled) | 500 ns – 2 μs | printk formatting + ring buffer write |
| Dynamic debug toggle | One-time ~1 μs | Patches static branch |
| TRACE_EVENT (disabled) | 1–3 ns | Static branch (jump label) |
| TRACE_EVENT (enabled) | 40–100 ns | Serialization + ring buffer write |
| usbmon capture | ~1 μs per URB | Copies URB metadata; minimal for USB speeds |
| blktrace (enabled) | 100–300 ns per I/O | Per-request overhead in block layer |
| debugfs file read | 1–100 μs | Depends on data collected; on-demand |
| devcoredump write | ms–seconds | One-time on device crash; copies firmware state |
| regmap trace (enabled) | 50–150 ns per reg access | Tracepoint overhead on I/O path |

### Storage growth rate

| Mechanism | Growth | Notes |
|-----------|--------|-------|
| dmesg (dev_dbg enabled) | 10–100 KB/min | Ring buffer bounded (default 256 KB–8 MB) |
| Tracepoints (driver events) | 1–50 MB/min | Depends on hardware activity |
| blktrace | 10–500 MB/min | Proportional to I/O rate |
| usbmon | 1–10 MB/min | Low data rate (USB bus speed) |
| debugfs | 0 (on-demand read) | No persistent storage; generated on read |
| devcoredump | 1–100 MB per crash | One-time; auto-deleted after 5 min |

---

## Validation Criteria

1. **Dynamic debug works**: `echo "module <driver> +p" > /sys/kernel/debug/dynamic_debug/control` followed by driver activity shows messages in `dmesg`
2. **Tracepoints available**: `ls /sys/kernel/tracing/events/<subsystem>/` shows driver tracepoint events
3. **Tracepoints fire**: Enable event, trigger driver activity, `cat trace` shows entries
4. **debugfs populated**: `/sys/kernel/debug/<driver>/` contains driver-specific files readable with `cat`
5. **usbmon captures**: `cat /sys/kernel/debug/usb/usbmon/0u` shows USB traffic when device active
6. **blktrace works**: `blktrace -d /dev/sda -o - | blkparse -i -` shows I/O requests during disk activity
7. **devcoredump present**: After driver-triggered crash, `/sys/class/devcoredump/devcd0/data` is readable

### Quick smoke test

```bash
# Enable dynamic debug for a loaded driver and verify output
DRIVER=$(lsmod | awk 'NR==2{print $1}')
echo "module $DRIVER +p" > /sys/kernel/debug/dynamic_debug/control
dmesg -w &  # watch for new messages
# Trigger driver activity (plug USB device, do disk I/O, etc.)
echo "module $DRIVER -p" > /sys/kernel/debug/dynamic_debug/control

# Verify tracepoints exist for block subsystem
ls /sys/kernel/tracing/events/block/
echo 1 > /sys/kernel/tracing/events/block/block_rq_issue/enable
dd if=/dev/sda of=/dev/null bs=4k count=10 2>/dev/null
cat /sys/kernel/tracing/trace | tail -5
echo 0 > /sys/kernel/tracing/events/block/block_rq_issue/enable
```

---

## Limitations / Out of Scope

| Item | Status |
|------|--------|
| Userspace driver tracing | Not covered; use LTTng-UST or eBPF for userspace drivers (DPDK, FUSE) |
| Hardware protocol analyzers | Physical bus analyzers (USB, PCIe, I2C) are out of scope |
| Firmware internals | devcoredump captures state but firmware execution tracing requires vendor tools |
| JTAG/SWD debugging | Hardware debug interfaces not covered |
| Windows/macOS drivers | Linux-specific mechanisms |
| Real-time alerting | No built-in notification; must be layered externally |
| Encryption of trace data | None provided |
| Remote driver debugging | No built-in remote access (SSH + tracefs is the workaround) |
| Driver fuzzing/fault injection | Separate mechanism (fault injection framework); not tracing |
| ABI stability | debugfs interfaces are explicitly non-ABI-stable |
| Multi-device correlation | No built-in mechanism to correlate events across different device drivers |
| Timestamped register dumps | debugfs reads are point-in-time; no automatic time-series |

---

## Evaluation Assessment

### Observability

**Rating: Strong**

| Aspect | Assessment |
|--------|------------|
| **Strengths** | Multiple complementary mechanisms cover different observation needs: structured logging (dev_dbg), event tracing (TRACE_EVENT), register-level I/O (regmap), protocol-level (usbmon, blktrace), state inspection (debugfs), crash analysis (devcoredump). Dynamic debug enables production systems to activate logging without recompilation. Tracepoints integrate with ftrace/perf/LTTng ecosystem. Subsystem tracers (blktrace, usbmon) provide domain-specific visibility. |
| **Gaps** | No unified view across all driver subsystems. Each mechanism has its own interface and output format. No built-in dashboards or aggregation. debugfs is unstructured (driver-specific). No automatic anomaly detection. No cross-driver event correlation. |
| **Implementations must add** | Unified driver observability dashboard, structured debugfs schemas, cross-subsystem event correlation, anomaly detection on driver behavior. |

### Security

**Rating: Partial**

| Aspect | Assessment |
|--------|------------|
| **Strengths** | All mechanisms require root/CAP_SYS_ADMIN. debugfs explicitly non-ABI-stable (discourages reliance from non-root tools). Dynamic debug has zero overhead when disabled (no information leakage path). devcoredumps auto-delete after 5 minutes. |
| **Gaps** | debugfs exposes raw hardware state (register values, firmware internals). devcoredumps may contain sensitive device memory (encryption keys, DMA buffers). No encryption of any output. No audit trail of debug operations. usbmon captures all USB traffic including HID keystrokes. blktrace reveals file access patterns. No per-driver access granularity. |
| **Implementations must add** | Encrypted devcoredumps, sanitization of sensitive register fields, per-subsystem access control, audit logging of debug access, USB traffic filtering for sensitive devices (HID). |

### Identity Management

**Rating: Minimal**

| Aspect | Assessment |
|--------|------------|
| **Strengths** | PID/process name in tracepoint events identifies which process triggered driver activity. Device identity (bus/address) is embedded in all dev_* messages and tracepoints. |
| **Gaps** | No concept of operator identity for debug sessions. No binding between debug access and authenticated user beyond root UID. No device ownership or tenancy model. No correlation between driver events and application-layer identity. |
| **Implementations must add** | Debug session identity (who enabled tracing, when, why), device-to-tenant mapping in multi-tenant environments, correlation with application identity. |

### Reliability

**Rating: Moderate**

| Aspect | Assessment |
|--------|------------|
| **Strengths** | Dynamic debug and tracepoints have zero overhead when disabled — safe to leave compiled in. devcoredump captures crash state even when system is partially failed. Built-in mechanisms (no external daemon to crash). Per-CPU ring buffers for tracepoints are lock-free. blktrace survives high I/O load (uses same ftrace ring buffer infrastructure). |
| **Gaps** | dmesg ring buffer overflow loses old messages. debugfs reads may race with driver state changes (no consistency guarantee). devcoredump data lost if system hard-crashes before dump completes. usbmon can drop URBs under heavy traffic. No guaranteed delivery of driver events to external systems. No redundancy or replication. |
| **Implementations must add** | Persistent driver event logging, guaranteed delivery to external collectors, debugfs snapshot consistency, driver event buffering during high-activity periods. |

### Accuracy

**Rating: Strong**

| Aspect | Assessment |
|--------|------------|
| **Strengths** | Tracepoints capture exact values at execution point — no sampling. Register reads via regmap tracepoints show exact hardware state. blktrace captures complete I/O lifecycle with nanosecond timestamps. usbmon captures full URB content (exact bytes on the wire). devcoredump preserves complete device state at crash time. Dynamic debug shows exact code path with function/line attribution. |
| **Gaps** | Tracing overhead can perturb timing-sensitive hardware interactions (race conditions may disappear when traced). debugfs reads may show inconsistent state if device is active. Register reads for tracing may have side effects on some hardware (status-clear-on-read). dev_dbg formatting introduces latency that may mask timing bugs. |
| **Implementations must add** | Non-intrusive hardware tracing alternatives (hardware trace buffers), atomic debugfs snapshot mechanisms, side-effect-free register read paths for tracing. |

---

## Assessment Summary

| Dimension | Rating | Key Gap |
|-----------|--------|---------|
| Observability | Strong | No unified cross-subsystem view; each mechanism is independent |
| Security | Partial | debugfs/devcoredump expose sensitive hardware state unencrypted |
| Identity | Minimal | PID/device-level only; no operator or tenant identity |
| Reliability | Moderate | dmesg overflow; debugfs consistency races; no guaranteed delivery |
| Accuracy | Strong | Tracing overhead may perturb timing-sensitive driver behavior |
