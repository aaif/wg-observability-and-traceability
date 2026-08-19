# AAIF Reference Architecture: Linux Driver Tracing

| Field | Value |
|-------|-------|
| **Subject** | [Linux Device Driver Tracing](https://www.kernel.org/doc/html/latest/driver-api/basics.html) |
| **Version** | Linux kernel 6.x |
| **Date** | 2026-06-25 |

---

## Objective

Demonstrates the complete set of mechanisms available to Linux device driver developers and system administrators for tracing, debugging, and observing driver behavior — from structured logging (dev_dbg) through dynamic debug, custom tracepoints, bus-specific tracers, devcoredump, and debugfs interfaces.

---

## Scope / Zoom Level

**System layer — driver/subsystem instrumentation and observability.**

This document covers the tracing surface exposed by and for Linux device drivers. It sits between the generic kernel tracing infrastructure (ftrace/perf/LTTng — covered in separate documents) and hardware-specific diagnostic tools. The focus is on what a driver developer instruments, what a sysadmin enables at runtime, and how the data flows to analysis tools.

---

## Prerequisites

| Component | Version / Pinned | Notes |
|-----------|-----------------|-------|
| Linux kernel | ≥ 4.19 (6.x recommended) | `CONFIG_DYNAMIC_DEBUG=y`, `CONFIG_DEBUG_FS=y`, `CONFIG_TRACEPOINTS=y` |
| debugfs | Mounted | `/sys/kernel/debug/` (mount -t debugfs none /sys/kernel/debug) |
| tracefs | Mounted | `/sys/kernel/tracing/` |
| Root / CAP_SYS_ADMIN | — | Required for debugfs/tracefs access |
| trace-cmd | 3.x (optional) | CLI wrapper for ftrace tracepoint consumption |
| perf | matching kernel | `linux-tools-$(uname -r)` package |
| blktrace | 2.x (optional) | Block device tracing |
| usbmon | built-in | `CONFIG_USB_MON=y` |
| wireshark | 4.x (optional) | USB/network packet analysis with usbmon |

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              Linux Kernel                                         │
│                                                                                  │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │  Device Drivers                                                          │    │
│  │                                                                          │    │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐    │    │
│  │  │  USB     │ │  Network │ │  Block   │ │  GPU/DRM │ │  I2C/SPI │    │    │
│  │  │  drivers │ │  drivers │ │  drivers │ │  drivers │ │  drivers │    │    │
│  │  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘    │    │
│  │       │             │             │             │             │          │    │
│  └───────┼─────────────┼─────────────┼─────────────┼─────────────┼──────────┘    │
│          │             │             │             │             │               │
│  ┌───────▼─────────────▼─────────────▼─────────────▼─────────────▼──────────┐   │
│  │  Instrumentation Mechanisms                                               │   │
│  │                                                                           │   │
│  │  ┌─────────────┐ ┌──────────────┐ ┌────────────┐ ┌───────────────────┐  │   │
│  │  │ dev_dbg()   │ │ TRACE_EVENT()│ │ debugfs    │ │ devcoredump       │  │   │
│  │  │ dev_info()  │ │ tracepoints  │ │ files      │ │ (crash dumps)     │  │   │
│  │  │ dev_err()   │ │              │ │            │ │                   │  │   │
│  │  └──────┬──────┘ └──────┬───────┘ └─────┬──────┘ └────────┬──────────┘  │   │
│  │         │               │               │                  │             │   │
│  └─────────┼───────────────┼───────────────┼──────────────────┼─────────────┘   │
│            │               │               │                  │                  │
│            ▼               ▼               ▼                  ▼                  │
│  ┌──────────────┐ ┌────────────────┐ ┌──────────┐ ┌────────────────────┐       │
│  │ Ring Buffer  │ │ Per-CPU trace  │ │ debugfs  │ │ /sys/class/        │       │
│  │ (printk)    │ │ ring buffers   │ │ VFS      │ │  devcoredump/      │       │
│  │ → dmesg     │ │ → tracefs      │ │          │ │                    │       │
│  │ → syslog    │ │ → perf_events  │ │          │ │                    │       │
│  └──────────────┘ └────────────────┘ └──────────┘ └────────────────────┘       │
│                                                                                  │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │  Bus-Specific Tracers                                                     │   │
│  │  usbmon | blktrace | i2c tracepoints | pci tracepoints | regmap           │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
│                                                                                  │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │  Dynamic Debug (dyndbg)                                                   │   │
│  │  Runtime enable/disable of dev_dbg() and pr_debug() — no recompile       │   │
│  │  /sys/kernel/debug/dynamic_debug/control                                  │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────┘

         Userspace Consumers
         ═══════════════════
┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐
│  dmesg   │ │trace-cmd │ │  perf    │ │ wireshark│ │  babeltrace2 │
│  journald│ │ ftrace   │ │          │ │          │ │  (LTTng)     │
└──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────────┘
```

---

## Instrumentation Walkthrough

### 1. Structured Device Logging (dev_dbg / dev_info / dev_err / dev_warn)

**What it is:** The `<linux/device.h>` family of logging macros that automatically prefix messages with the device name and bus position, providing structured context without manual string formatting.

**Mechanism:**

```c
#include <linux/device.h>

/* In a probe function: */
static int my_driver_probe(struct platform_device *pdev)
{
    struct device *dev = &pdev->dev;

    dev_info(dev, "probing device (firmware rev %d)\n", fw_rev);
    dev_dbg(dev, "register base: %pa, irq: %d\n", &res->start, irq);

    if (error_condition)
        dev_err(dev, "failed to initialize DMA: %d\n", ret);

    dev_warn(dev, "deprecated feature X used, migrate to Y\n");
    return 0;
}
```

**Output format (in dmesg):**

```
[  12.345678] my_driver 0000:03:00.0: probing device (firmware rev 42)
[  12.345700] my_driver 0000:03:00.0: register base: 0xfe000000, irq: 27
```

The prefix `my_driver 0000:03:00.0:` is automatically generated from `dev_name(dev)` — includes driver name and bus address (PCI BDF, USB bus/port, platform device name, etc.).

**Hierarchy:**

| Macro | Log Level | Compiled when | Typical use |
|-------|-----------|---------------|-------------|
| `dev_emerg()` | KERN_EMERG | Always | System unusable |
| `dev_crit()` | KERN_CRIT | Always | Critical failure |
| `dev_alert()` | KERN_ALERT | Always | Immediate action needed |
| `dev_err()` | KERN_ERR | Always | Error conditions |
| `dev_warn()` | KERN_WARNING | Always | Warning conditions |
| `dev_notice()` | KERN_NOTICE | Always | Normal significant events |
| `dev_info()` | KERN_INFO | Always | Informational |
| `dev_dbg()` | KERN_DEBUG | Only with DEBUG or CONFIG_DYNAMIC_DEBUG | Debug messages |

**Control mechanisms:**

```bash
# View current kernel log level
cat /proc/sys/kernel/printk
# 4    4    1    7
# current | default | minimum | boot-time-default

# Set console log level to see all messages
echo 8 > /proc/sys/kernel/printk

# Filter dmesg by driver
dmesg | grep "my_driver"

# Follow new messages
dmesg -w | grep "my_driver"
```

**Key property:** `dev_dbg()` compiles to nothing unless either:
- `#define DEBUG` is set before `#include <linux/device.h>` in the source file
- `CONFIG_DYNAMIC_DEBUG=y` is set in the kernel config (in which case the call site exists but is disabled by default)


---

### 2. Dynamic Debug (dyndbg)

**What it is:** A runtime mechanism to enable/disable `pr_debug()` and `dev_dbg()` call sites without recompiling the kernel or modules. Each call site is registered in a table and can be toggled per-file, per-function, per-module, or per-line-number.

**Control interface:** `/sys/kernel/debug/dynamic_debug/control`

**Querying available debug sites:**

```bash
# List all debug call sites (thousands of entries)
cat /sys/kernel/debug/dynamic_debug/control | head -20
# drivers/usb/core/hub.c:1234 [usbcore]hub_port_connect_change =_ "port %d..."

# Count debug sites per module
cat /sys/kernel/debug/dynamic_debug/control | awk '{print $3}' | sort | uniq -c | sort -rn | head

# Find all debug sites in a specific driver
grep "i915" /sys/kernel/debug/dynamic_debug/control | wc -l
```

**Enabling/disabling debug output:**

```bash
# Enable all dev_dbg in USB core
echo "file drivers/usb/core/* +p" > /sys/kernel/debug/dynamic_debug/control

# Enable by module name
echo "module i915 +p" > /sys/kernel/debug/dynamic_debug/control

# Enable by function name
echo "func hub_port_connect_change +p" > /sys/kernel/debug/dynamic_debug/control

# Enable specific line
echo "file drivers/gpu/drm/i915/i915_gem.c line 450 +p" > /sys/kernel/debug/dynamic_debug/control

# Disable
echo "module i915 -p" > /sys/kernel/debug/dynamic_debug/control

# Enable with extra decorations
echo "module usbcore +pflmt" > /sys/kernel/debug/dynamic_debug/control
```

**Flags:**

| Flag | Meaning | Effect on output |
|------|---------|-----------------|
| `p` | Print | Enable the pr_debug/dev_dbg call site |
| `f` | Function | Prepend function name |
| `l` | Line | Prepend file:line |
| `m` | Module | Prepend module name |
| `t` | Thread ID | Prepend thread ID |
| `_` | No flags | Disable printing (default state) |

**Output with all flags enabled:**

```
[  45.123456] usbcore:hub_port_connect_change:hub.c:1234: [task:1523] usb 2-1: port 1 status 0501 change 0001
```

**Boot-time activation:**

```bash
# In kernel command line (GRUB)
dyndbg="module usbcore +p" dyndbg="file drivers/mmc/* +p"

# Or per-module when loading
modprobe i915 dyndbg="+p"
```

**Integration with systemd/journald:**

```bash
# Dynamic debug output goes through printk → ring buffer → journald
journalctl -k | grep "usbcore"
journalctl -k -f --grep="i915"  # follow with filter
```

**Performance impact:** Enabled dev_dbg() calls have the same cost as dev_info() (~1-5 µs depending on message complexity and console/log targets). When disabled, the overhead is a single static branch test (~1-3 ns).

---

### 3. TRACE_EVENT() in Drivers

**What it is:** The `TRACE_EVENT()` macro allows drivers to define custom tracepoints — typed, structured events that are exposed through tracefs and consumable by ftrace, perf, LTTng, and BPF programs.

**Defining a tracepoint in a driver:**

```c
/* include/trace/events/my_driver.h */
#undef TRACE_SYSTEM
#define TRACE_SYSTEM my_driver

#if !defined(_TRACE_MY_DRIVER_H) || defined(TRACE_HEADER_MULTI_READ)
#define _TRACE_MY_DRIVER_H

#include <linux/tracepoint.h>

TRACE_EVENT(my_driver_dma_transfer,
    TP_PROTO(struct device *dev, dma_addr_t addr, size_t len, int direction),

    TP_ARGS(dev, addr, len, direction),

    TP_STRUCT__entry(
        __string(devname, dev_name(dev))
        __field(u64, dma_addr)
        __field(size_t, length)
        __field(int, direction)
    ),

    TP_fast_assign(
        __assign_str(devname, dev_name(dev));
        __entry->dma_addr = addr;
        __entry->length = len;
        __entry->direction = direction;
    ),

    TP_printk("dev=%s addr=0x%llx len=%zu dir=%s",
        __get_str(devname),
        __entry->dma_addr,
        __entry->length,
        __entry->direction ? "FROM_DEVICE" : "TO_DEVICE"
    )
);

#endif /* _TRACE_MY_DRIVER_H */

#undef TRACE_INCLUDE_PATH
#define TRACE_INCLUDE_PATH .
#define TRACE_INCLUDE_FILE my_driver_trace
#include <trace/define_trace.h>
```

**Using the tracepoint in driver code:**

```c
#include "my_driver_trace.h"

static int my_driver_submit_dma(struct my_device *mdev, dma_addr_t addr, size_t len)
{
    trace_my_driver_dma_transfer(mdev->dev, addr, len, DMA_TO_DEVICE);
    /* ... actual DMA submission ... */
    return 0;
}
```

**Consuming with ftrace:**

```bash
# List available driver tracepoints
ls /sys/kernel/tracing/events/my_driver/
# my_driver_dma_transfer  enable  filter

# Enable the tracepoint
echo 1 > /sys/kernel/tracing/events/my_driver/my_driver_dma_transfer/enable

# Read trace output
cat /sys/kernel/tracing/trace_pipe
# my_app-1234  [003] .... 123.456789: my_driver_dma_transfer: dev=0000:03:00.0 addr=0x7f000000 len=4096 dir=TO_DEVICE

# Filter events
echo "length > 65536" > /sys/kernel/tracing/events/my_driver/my_driver_dma_transfer/filter

# Trigger actions
echo "hist:keys=direction:vals=length:sort=length.desc" > /sys/kernel/tracing/events/my_driver/my_driver_dma_transfer/trigger
```

**Consuming with perf:**

```bash
# Record tracepoint events
perf record -e my_driver:my_driver_dma_transfer -a -- sleep 10

# List and report
perf script
perf stat -e my_driver:my_driver_dma_transfer -a -- sleep 5
```

**Consuming with BPF (bpftrace):**

```bash
# Count DMA transfers by direction
bpftrace -e 'tracepoint:my_driver:my_driver_dma_transfer { @[args->direction] = count(); }'

# Histogram of DMA sizes
bpftrace -e 'tracepoint:my_driver:my_driver_dma_transfer { @size = hist(args->length); }'
```

**Key examples of driver tracepoints in mainline kernel:**

| Subsystem | Tracepoint prefix | Example events |
|-----------|-------------------|----------------|
| DRM | `drm:` | `drm_vblank_event`, `drm_vblank_event_delivered` |
| i915 (Intel GPU) | `i915:` | `i915_request_queue`, `i915_request_retire` |
| amdgpu | `amdgpu:` | `amdgpu_cs_ioctl`, `amdgpu_vm_bo_map` |
| Block | `block:` | `block_rq_issue`, `block_rq_complete` |
| USB | `xhci-hcd:` | `xhci_urb_enqueue`, `xhci_urb_giveback` |
| I2C | `i2c:` | `i2c_read`, `i2c_write`, `i2c_result` |
| SPI | `spi:` | `spi_transfer_start`, `spi_transfer_stop` |
| regmap | `regmap:` | `regmap_reg_read`, `regmap_reg_write` |
| GPIO | `gpio:` | `gpio_value`, `gpio_direction` |
| RPM | `rpm:` | `rpm_suspend`, `rpm_resume`, `rpm_idle` |
| Clock | `clk:` | `clk_enable`, `clk_disable`, `clk_set_rate` |
| Regulator | `regulator:` | `regulator_enable`, `regulator_set_voltage` |
| Thermal | `thermal:` | `thermal_zone_trip`, `cdev_update` |


---

### 4. DRM/GPU Driver Tracing

**What it is:** The DRM (Direct Rendering Manager) subsystem and GPU drivers provide extensive tracing for command submission, memory management, fence signaling, display mode setting, and vblank events.

**DRM subsystem tracepoints:**

```bash
# List all DRM tracepoints
ls /sys/kernel/tracing/events/drm/
# drm_vblank_event  drm_vblank_event_delivered  drm_vblank_event_queued

# Enable all DRM tracing
echo 1 > /sys/kernel/tracing/events/drm/enable
```

**Intel i915 tracepoints:**

```bash
# List i915 tracepoints (typically 50+)
ls /sys/kernel/tracing/events/i915/
# i915_request_queue  i915_request_submit  i915_request_retire
# i915_request_wait_begin  i915_request_wait_end
# i915_gem_object_create  i915_gem_object_destroy
# i915_gem_evict  i915_gem_evict_vm
# i915_pipe_update_start  i915_pipe_update_end

# Trace GPU command submission latency
echo 1 > /sys/kernel/tracing/events/i915/i915_request_queue/enable
echo 1 > /sys/kernel/tracing/events/i915/i915_request_retire/enable
cat /sys/kernel/tracing/trace_pipe

# With perf
perf record -e i915:i915_request_queue -e i915:i915_request_retire -a -- sleep 5
perf script  # shows submission-to-retirement timeline
```

**AMD GPU tracepoints:**

```bash
# List amdgpu tracepoints
ls /sys/kernel/tracing/events/amdgpu/
# amdgpu_cs_ioctl  amdgpu_sched_run_job  amdgpu_vm_bo_map
# amdgpu_vm_bo_unmap  amdgpu_bo_create  amdgpu_ttm_bo_move

# Trace command submission
perf stat -e amdgpu:amdgpu_cs_ioctl -a -- glmark2
```

**DRM DebugFS:**

```bash
# Per-card debug information
ls /sys/kernel/debug/dri/0/
# clients  gem_names  name  framebuffer  state  ...

# GPU client list
cat /sys/kernel/debug/dri/0/clients
# command   pid  dev master  auth  uid  magic
# Xorg      1234 0   y       y     0    0
# firefox   5678 0   n       y     1000 1

# i915-specific debugfs
cat /sys/kernel/debug/dri/0/i915_gem_objects
cat /sys/kernel/debug/dri/0/i915_frequency_info
cat /sys/kernel/debug/dri/0/i915_engine_info

# amdgpu-specific
cat /sys/kernel/debug/dri/0/amdgpu_gpu_recover
cat /sys/kernel/debug/dri/0/amdgpu_fence_info
cat /sys/kernel/debug/dri/0/amdgpu_pm_info
```

**GPU hang debugging with devcoredump (see section 10):**

```bash
# After GPU hang, firmware state is dumped
ls /sys/class/devcoredump/devcd*/
cat /sys/devices/.../devcoredump/data > gpu_crash_dump.bin
# Decode with vendor tools (intel_error_decode, umr for AMD)
```

---

### 5. USB Tracing (usbmon)

**What it is:** `usbmon` is a kernel facility that captures USB Request Blocks (URBs) as they pass between USB device drivers and host controller drivers. It provides complete bus-level visibility of USB transactions.

**Prerequisites:**

```bash
# Ensure usbmon is loaded
modprobe usbmon
# Or verify it's built-in
ls /sys/kernel/debug/usb/usbmon/
# 0s  0u  1s  1t  1u  2s  2t  2u  ...
# 0 = all buses, 1/2/... = specific bus numbers
```

**Text interface (human-readable):**

```bash
# Monitor all USB buses
cat /sys/kernel/debug/usb/usbmon/0u

# Monitor specific bus (bus 2)
cat /sys/kernel/debug/usb/usbmon/2u

# Output format:
# URB_TAG TIMESTAMP EVENT_TYPE ADDRESS STATUS LENGTH DATA
# ffff8881a0b0c000 3052826780 S Ci:2:003:0 s 80 06 0100 0000 0040 64 <
# ffff8881a0b0c000 3052826900 C Ci:2:003:0 0 18 = 12010002 00000040 6d041e00 00020102 0301

# Fields:
# S = Submit, C = Callback (completion)
# Ci = Control In, Co = Control Out, Bi = Bulk In, Bo = Bulk Out
# Ii = Interrupt In, Io = Interrupt Out, Zi = Isochronous In
# 2:003:0 = bus:device:endpoint
```

**Binary interface (for tools):**

```bash
# Binary format for efficient capture
cat /sys/kernel/debug/usb/usbmon/2t > capture.mon
# Or use the character device
cat /dev/usbmon2 > capture.bin
```

**Wireshark integration:**

```bash
# Capture USB traffic with dumpcap (wireshark's capture engine)
# Requires usbmon module loaded
dumpcap -i usbmon2 -w usb_capture.pcapng

# Or directly in wireshark
wireshark -i usbmon2

# Filter in wireshark:
# usb.device_address == 3
# usb.endpoint_address == 0x81
# usb.transfer_type == URB_BULK
```

**USB device topology inspection:**

```bash
# View USB device tree
lsusb -t
# /:  Bus 02.Port 1: Dev 1, Class=root_hub, Driver=xhci_hcd/4p, 5000M
#     |__ Port 1: Dev 2, If 0, Class=Mass Storage, Driver=uas, 5000M

# Detailed device info
lsusb -v -d 046d:c52b

# sysfs USB device attributes
cat /sys/bus/usb/devices/2-1/idVendor
cat /sys/bus/usb/devices/2-1/idProduct
cat /sys/bus/usb/devices/2-1/manufacturer
cat /sys/bus/usb/devices/2-1/speed
```

**USB tracepoints (xHCI layer):**

```bash
# xHCI host controller tracepoints
ls /sys/kernel/tracing/events/xhci-hcd/
# xhci_urb_enqueue  xhci_urb_dequeue  xhci_urb_giveback
# xhci_address_device  xhci_alloc_dev

echo 1 > /sys/kernel/tracing/events/xhci-hcd/enable
cat /sys/kernel/tracing/trace_pipe
```

---

### 6. Network Driver Tracing

**What it is:** Network drivers expose tracing through per-device statistics, NAPI tracepoints, ethtool diagnostics, XDP/BPF hooks, and the devlink subsystem.

**Per-device statistics:**

```bash
# ethtool driver statistics (hardware-specific counters)
ethtool -S eth0
# NIC statistics:
#      rx_packets: 1234567
#      tx_packets: 987654
#      rx_bytes: 1234567890
#      rx_crc_errors: 0
#      rx_missed_errors: 0
#      tx_timeout_count: 0
#      rx_queue_0_packets: 456789
#      tx_queue_0_packets: 321456

# Kernel-level interface statistics
cat /sys/class/net/eth0/statistics/rx_packets
cat /sys/class/net/eth0/statistics/tx_dropped
cat /sys/class/net/eth0/statistics/rx_errors

# Driver info
ethtool -i eth0
# driver: i40e
# version: 2.8.20-k
# firmware-version: 7.10 0x800075e8 19.5.12
```

**NAPI tracing:**

```bash
# NAPI (New API) polling tracepoints
ls /sys/kernel/tracing/events/napi/
# napi_poll

echo 1 > /sys/kernel/tracing/events/napi/napi_poll/enable
cat /sys/kernel/tracing/trace_pipe
# <idle>-0  [002] ..s. 1234.567890: napi_poll: napi poll on napi struct 0xffff... for device eth0 work 16 budget 64

# Measure NAPI poll efficiency with bpftrace
bpftrace -e 'tracepoint:napi:napi_poll { @work = hist(args->work); }'
```

**Network tracepoints:**

```bash
# Net device tracepoints
ls /sys/kernel/tracing/events/net/
# net_dev_queue  net_dev_xmit  netif_receive_skb  netif_rx

# Trace packet path
echo 1 > /sys/kernel/tracing/events/net/net_dev_xmit/enable
echo "name == \"eth0\"" > /sys/kernel/tracing/events/net/net_dev_xmit/filter
```

**XDP/BPF-based driver tracing:**

```bash
# Attach BPF to XDP hook for per-packet driver visibility
bpftrace -e '
tracepoint:xdp:xdp_bulk_tx_err {
    @drops[args->ifindex] = count();
}'

# perf trace of network syscalls hitting driver
perf trace -e sendmsg,recvmsg -p $(pidof my_app) -- sleep 10
```

**devlink (netdev subsystem debugging):**

```bash
# List devlink devices
devlink dev show
# pci/0000:03:00.0
# pci/0000:03:00.1

# Health reporters (driver error reporting)
devlink health show pci/0000:03:00.0
# reporter fw_fatal
#   state healthy error 0 recover 0

# Dump device health info
devlink health dump show pci/0000:03:00.0 reporter fw_fatal

# Device parameters
devlink dev param show pci/0000:03:00.0

# Port info
devlink port show
```


---

### 7. Block Device Tracing

**What it is:** Block device tracing captures I/O requests as they flow through the block layer — from filesystem/application submission through the I/O scheduler to driver completion. This reveals driver queue depths, latencies, merges, and error handling.

**blktrace / blkparse:**

```bash
# Trace all I/O on /dev/sda (writes to current directory)
blktrace -d /dev/sda -o trace_sda &
# ... run workload ...
kill %1
blkparse -i trace_sda -o trace_sda.txt

# Shorthand: btrace combines blktrace + blkparse for live output
btrace /dev/nvme0n1

# Output format:
#  8,0  1  1  0.000000000  1234  A  WS 123456 + 8 <- (8,1) 123400
#  8,0  1  2  0.000001234  1234  Q  WS 123456 + 8 [dd]
#  8,0  1  3  0.000002345  1234  G  WS 123456 + 8 [dd]
#  8,0  1  4  0.000003456  1234  I  WS 123456 + 8 [dd]
#  8,0  1  5  0.000010000  1234  D  WS 123456 + 8 [dd]
#  8,0  1  6  0.000250000     0  C  WS 123456 + 8 [0]
#
# Actions: A=remap, Q=queue, G=get_request, I=insert, D=dispatch, C=complete
# WS = Write Sync, R = Read
```

**Block layer tracepoints:**

```bash
# List block tracepoints
ls /sys/kernel/tracing/events/block/
# block_bio_backmerge  block_bio_bounce  block_bio_complete
# block_bio_frontmerge  block_bio_queue  block_bio_remap
# block_dirty_buffer  block_getrq  block_plug  block_unplug
# block_rq_complete  block_rq_insert  block_rq_issue
# block_rq_merge  block_rq_remap  block_rq_requeue
# block_split  block_touch_buffer

# Trace I/O issue and completion for latency analysis
echo 1 > /sys/kernel/tracing/events/block/block_rq_issue/enable
echo 1 > /sys/kernel/tracing/events/block/block_rq_complete/enable

# Filter to specific device (major 259 = nvme, minor 0 = nvme0n1)
echo "dev == 259*65536+0" > /sys/kernel/tracing/events/block/block_rq_issue/filter
```

**I/O latency histograms with BPF:**

```bash
# biolatency from bcc-tools — measures time from submission to completion
biolatency -D  # per-disk histogram

# bpftrace version
bpftrace -e '
tracepoint:block:block_rq_issue { @start[args->dev, args->sector] = nsecs; }
tracepoint:block:block_rq_complete /@start[args->dev, args->sector]/ {
    @usecs = hist((nsecs - @start[args->dev, args->sector]) / 1000);
    delete(@start[args->dev, args->sector]);
}'
```

**debugfs block interface:**

```bash
# Per-device block debug info (when available)
ls /sys/kernel/debug/block/sda/
# Usually contains scheduler-specific debug files

# NVMe-specific debug
cat /sys/kernel/debug/nvme0/
# nvme-specific I/O queue information
```

---

### 8. PCI/PCIe Tracing

**What it is:** PCI/PCIe tracing covers device enumeration, configuration space access, error reporting (AER), and power management transitions for PCI-attached devices.

**PCI tracepoints:**

```bash
# List PCI tracepoints
ls /sys/kernel/tracing/events/pci/ 2>/dev/null || echo "May not exist on all kernels"

# Intel IOMMU / DMAR tracepoints
ls /sys/kernel/tracing/events/intel_iommu/
# map  unmap  dmar_map  dmar_unmap

# Trace config space reads (via ftrace function tracing)
echo pci_read_config_byte > /sys/kernel/tracing/set_ftrace_filter
echo function > /sys/kernel/tracing/current_tracer
echo 1 > /sys/kernel/tracing/tracing_on
cat /sys/kernel/tracing/trace_pipe
```

**PCIe AER (Advanced Error Reporting):**

```bash
# Check AER status for a device
lspci -vvv -s 03:00.0 | grep -A 20 "Advanced Error Reporting"
#   UESta:  DLP- SDES- TLP- FCP- CmpltTO- CmpltAbrt- ...
#   UEMsk:  DLP- SDES- TLP- FCP- CmpltTO- CmpltAbrt- ...
#   CESta:  RxErr- BadTLP- BadDLLP- Rollover- Timeout- ...

# AER events appear in dmesg
dmesg | grep -i "aer"
# [  100.234567] pcieport 0000:00:1c.0: AER: Corrected error received: 0000:03:00.0
# [  100.234568] my_driver 0000:03:00.0: PCIe Bus Error: severity=Corrected, type=Data Link Layer

# sysfs AER attributes
cat /sys/bus/pci/devices/0000:03:00.0/aer_dev_correctable
cat /sys/bus/pci/devices/0000:03:00.0/aer_dev_fatal
```

**PCI device sysfs inspection:**

```bash
# Complete device information
lspci -vvv -s 0000:03:00.0

# sysfs attributes
cat /sys/bus/pci/devices/0000:03:00.0/vendor      # 0x8086
cat /sys/bus/pci/devices/0000:03:00.0/device      # 0x1533
cat /sys/bus/pci/devices/0000:03:00.0/class       # 0x020000
cat /sys/bus/pci/devices/0000:03:00.0/irq         # MSI/MSI-X IRQ number
cat /sys/bus/pci/devices/0000:03:00.0/resource    # BAR addresses
cat /sys/bus/pci/devices/0000:03:00.0/driver      # -> ../../../bus/pci/drivers/i40e
cat /sys/bus/pci/devices/0000:03:00.0/link/       # PCIe link speed/width

# Read raw config space
hexdump -C /sys/bus/pci/devices/0000:03:00.0/config | head -20

# PCIe link state
cat /sys/bus/pci/devices/0000:03:00.0/current_link_speed   # 8.0 GT/s PCIe
cat /sys/bus/pci/devices/0000:03:00.0/current_link_width   # 4
```

**Power management tracing for PCI:**

```bash
# PCI device power state
cat /sys/bus/pci/devices/0000:03:00.0/power_state  # D0, D1, D2, D3hot, D3cold

# Runtime PM statistics
cat /sys/bus/pci/devices/0000:03:00.0/power/runtime_status     # active/suspended
cat /sys/bus/pci/devices/0000:03:00.0/power/runtime_active_time
cat /sys/bus/pci/devices/0000:03:00.0/power/runtime_suspended_time
```

---

### 9. I2C/SPI Tracing

**What it is:** I2C and SPI bus tracing captures individual register reads/writes between the CPU and peripheral devices (sensors, EEPROMs, touchscreens, PMICs). The `regmap` abstraction layer provides unified tracing for any device using regmap-based register access.

**I2C tracepoints:**

```bash
# List I2C tracepoints
ls /sys/kernel/tracing/events/i2c/
# i2c_read  i2c_write  i2c_reply  i2c_result

# Enable I2C tracing
echo 1 > /sys/kernel/tracing/events/i2c/enable
cat /sys/kernel/tracing/trace_pipe

# Output:
# sensors-1234 [001] .... 45.678901: i2c_write: i2c-3 #0 a=048 f=0000 l=2 [0b00]
# sensors-1234 [001] .... 45.678950: i2c_read: i2c-3 #1 a=048 f=0001 l=2
# sensors-1234 [001] .... 45.679010: i2c_reply: i2c-3 #1 a=048 f=0001 l=2 [1a2b]
# sensors-1234 [001] .... 45.679015: i2c_result: i2c-3 n=2 ret=0
#
# a=048 : slave address 0x48
# f=0000 : flags (0x0001 = I2C_M_RD)
# l=2   : message length in bytes
```

**SPI tracepoints:**

```bash
# List SPI tracepoints
ls /sys/kernel/tracing/events/spi/
# spi_transfer_start  spi_transfer_stop  spi_message_start
# spi_message_done  spi_message_submit

# Enable SPI tracing
echo 1 > /sys/kernel/tracing/events/spi/enable
cat /sys/kernel/tracing/trace_pipe

# Output:
# irq/47-spi0-789 [000] .... 67.890123: spi_transfer_start: spi0.0 len=4 tx=[ff010000] rx=[00000000]
# irq/47-spi0-789 [000] .... 67.890200: spi_transfer_stop: spi0.0 len=4 tx=[ff010000] rx=[00abcdef]
```

**Regmap tracing (unified register access layer):**

```bash
# regmap tracepoints — THE most useful for debugging register-mapped devices
ls /sys/kernel/tracing/events/regmap/
# regmap_reg_read  regmap_reg_write  regmap_hw_read_start
# regmap_hw_read_done  regmap_hw_write_start  regmap_hw_write_done
# regmap_cache_only  regmap_cache_bypass  regmap_cache_sync

# Enable regmap tracing
echo 1 > /sys/kernel/tracing/events/regmap/regmap_reg_write/enable
echo 1 > /sys/kernel/tracing/events/regmap/regmap_reg_read/enable
cat /sys/kernel/tracing/trace_pipe

# Output:
# my_codec-1234 [002] .... 89.012345: regmap_reg_write: 0-0034 reg=0x0f val=0x80
# my_codec-1234 [002] .... 89.012456: regmap_reg_read: 0-0034 reg=0x10 val=0x42
#
# 0-0034 = regmap name (typically bus_id-slave_addr)

# Filter to specific device
echo "name == \"0-0034\"" > /sys/kernel/tracing/events/regmap/regmap_reg_write/filter
```

**I2C debugfs:**

```bash
# I2C adapter information
ls /sys/kernel/debug/i2c/
# Not always populated; depends on adapter driver

# Regmap debugfs (if CONFIG_REGMAP_DEBUGFS=y)
ls /sys/kernel/debug/regmap/
# 0-0034/  1-001a/  spi0.0/  ...

cat /sys/kernel/debug/regmap/0-0034/registers
# 00: 01
# 01: ff
# 02: 42
# ...

cat /sys/kernel/debug/regmap/0-0034/access
# Shows register access permissions (RW/RO/WO/Volatile)

cat /sys/kernel/debug/regmap/0-0034/cache
# Shows cached vs hardware register values
```


---

### 10. devcoredump

**What it is:** The devcoredump framework allows drivers to dump device/firmware state when a critical error occurs (GPU hang, WiFi firmware crash, etc.). The dump is exposed through sysfs and can be collected by userspace tools for offline analysis.

**How it works:**

```c
/* In driver error handler: */
#include <linux/devcoredump.h>

static void my_driver_handle_fw_crash(struct my_device *mdev)
{
    void *dump_data;
    size_t dump_size;

    /* Collect device state */
    dump_size = my_driver_collect_crash_state(mdev, &dump_data);

    /* Submit to devcoredump framework
     * Data will appear at /sys/class/devcoredump/devcdN/data
     * Framework auto-frees after 5 minutes (configurable)
     */
    dev_coredumpv(mdev->dev, dump_data, dump_size, GFP_KERNEL);

    dev_err(mdev->dev, "firmware crash — coredump submitted\n");
}
```

**Accessing dumps:**

```bash
# List available devcoredumps
ls /sys/class/devcoredump/
# devcd0  devcd1

# Read crash dump data (binary, driver-specific format)
cat /sys/class/devcoredump/devcd0/data > crash_dump.bin

# Or via the device path
cat /sys/devices/pci0000:00/0000:00:02.0/devcoredump/data > gpu_crash.bin

# Delete dump (frees kernel memory)
echo 1 > /sys/class/devcoredump/devcd0/data

# Check dump timestamp
stat /sys/class/devcoredump/devcd0/data
```

**Real-world examples:**

```bash
# Intel WiFi (iwlwifi) firmware crash
dmesg | grep "iwlwifi.*firmware"
# [  300.123456] iwlwifi 0000:02:00.0: Firmware error detected, restarting
cat /sys/class/devcoredump/devcd0/data > iwlwifi_dump.bin
# Analyze with iwlwifi debug tools

# AMD GPU hang
dmesg | grep "amdgpu.*reset"
# [  500.234567] amdgpu 0000:06:00.0: amdgpu: GPU reset begin!
cat /sys/class/devcoredump/devcd0/data > amdgpu_dump.bin
# Analyze with umr (AMD GPU debugger)

# Intel GPU hang
cat /sys/class/devcoredump/devcd0/data | intel_error_decode
# Provides human-readable GPU state at time of hang
```

**Configuration:**

```bash
# Auto-delete timeout (default 300 seconds)
# Set via module parameter or at compile time
# Drivers can call dev_coredumpv() with custom timeout

# Disable devcoredump collection entirely
echo 0 > /sys/class/devcoredump/disabled  # if available
```

---

### 11. DebugFS for Drivers

**What it is:** DebugFS (`/sys/kernel/debug/`) provides a simple filesystem interface for drivers to expose arbitrary debug information — register dumps, internal state, statistics, tuning knobs. Unlike sysfs (which has strict one-value-per-file rules), debugfs has no ABI stability guarantees and can expose complex, multi-value data.

**Creating debugfs entries in a driver:**

```c
#include <linux/debugfs.h>

struct my_device {
    struct dentry *debugfs_root;
    u32 error_count;
    u64 bytes_transferred;
    bool turbo_mode;
};

static int my_driver_probe(struct platform_device *pdev)
{
    struct my_device *mdev = /* ... */;

    /* Create directory: /sys/kernel/debug/my_driver/<device_name>/ */
    mdev->debugfs_root = debugfs_create_dir(dev_name(&pdev->dev),
                                             debugfs_lookup("my_driver", NULL));

    /* Simple value files */
    debugfs_create_u32("error_count", 0444, mdev->debugfs_root, &mdev->error_count);
    debugfs_create_u64("bytes_transferred", 0444, mdev->debugfs_root, &mdev->bytes_transferred);
    debugfs_create_bool("turbo_mode", 0644, mdev->debugfs_root, &mdev->turbo_mode);

    /* Custom file with seq_file for complex output */
    debugfs_create_file("registers", 0444, mdev->debugfs_root, mdev, &my_reg_fops);

    return 0;
}

/* seq_file operations for complex debug output */
static int my_reg_show(struct seq_file *s, void *data)
{
    struct my_device *mdev = s->private;

    seq_printf(s, "REG_STATUS:  0x%08x\n", readl(mdev->base + REG_STATUS));
    seq_printf(s, "REG_CONTROL: 0x%08x\n", readl(mdev->base + REG_CONTROL));
    seq_printf(s, "REG_INTR:    0x%08x\n", readl(mdev->base + REG_INTR));
    seq_printf(s, "DMA_PTR:     0x%08x\n", readl(mdev->base + REG_DMA_PTR));
    return 0;
}
DEFINE_SHOW_ATTRIBUTE(my_reg);
```

**Accessing debugfs:**

```bash
# Requires root or CAP_SYS_ADMIN (or mount with access options)
mount -t debugfs none /sys/kernel/debug  # usually already mounted

# Browse driver debug entries
ls /sys/kernel/debug/my_driver/
# 0000:03:00.0/

ls /sys/kernel/debug/my_driver/0000:03:00.0/
# error_count  bytes_transferred  turbo_mode  registers

cat /sys/kernel/debug/my_driver/0000:03:00.0/error_count
# 42

cat /sys/kernel/debug/my_driver/0000:03:00.0/registers
# REG_STATUS:  0x00000001
# REG_CONTROL: 0x00000100
# REG_INTR:    0x00000000
# DMA_PTR:     0x7f000000

# Write to writable debug knobs
echo 1 > /sys/kernel/debug/my_driver/0000:03:00.0/turbo_mode
```

**Real-world debugfs examples:**

```bash
# Intel Wi-Fi driver (iwlwifi)
ls /sys/kernel/debug/iwlwifi/
# 0000:02:00.0/

ls /sys/kernel/debug/iwlwifi/0000:02:00.0/
# stations  fw_dbg_conf  fw_nvm  fw_rx_stats  fw_tx_stats
# sar_geo_profile  inject_beacon_ie  inject_packet

# DRM/i915
ls /sys/kernel/debug/dri/0/
# i915_capabilities  i915_engine_info  i915_frequency_info
# i915_gem_objects  i915_gpu_info  i915_sr_status

# Network driver (i40e)
ls /sys/kernel/debug/i40e/
# 0000:03:00.0/
cat /sys/kernel/debug/i40e/0000:03:00.0/command  # admin command interface

# MMC/SD card
ls /sys/kernel/debug/mmc0/
# clock  ios  registers
```

---

### 12. GPIO/Pinctrl Tracing

**What it is:** GPIO and pin control tracing captures digital I/O state changes and pin muxing configuration, critical for embedded/SoC driver development where GPIO interactions drive device behavior.

**GPIO tracepoints:**

```bash
# List GPIO tracepoints
ls /sys/kernel/tracing/events/gpio/
# gpio_direction  gpio_value

# Enable GPIO tracing
echo 1 > /sys/kernel/tracing/events/gpio/enable
cat /sys/kernel/tracing/trace_pipe

# Output:
# my_driver-1234 [000] .... 12.345678: gpio_value: 42 set 1
# my_driver-1234 [000] .... 12.345700: gpio_direction: 42 out 1
# irq/23-gpio-5678 [001] ..s. 12.346000: gpio_value: 17 get 0
#
# Fields: gpio_number direction/set/get value
```

**GPIO debugfs:**

```bash
# Complete GPIO state dump
cat /sys/kernel/debug/gpio
# gpiochip0: GPIOs 0-31, parent: platform/fe200000.gpio, pinctrl-bcm2835:
#  gpio-5   (                    |led0                ) out hi
#  gpio-6   (                    |spi0 CS0            ) out lo ACTIVE LOW
#  gpio-17  (                    |button              ) in  hi IRQ ACTIVE LOW
#  gpio-18  (                    |pwm0                ) out lo
#  gpio-27  (                    |my_device reset     ) out hi
#
# gpiochip1: GPIOs 128-143, parent: i2c/1-0020, pca9555:
#  gpio-128 (                    |relay0              ) out lo
#  gpio-129 (                    |relay1              ) out hi

# Shows: chip, GPIO number, consumer label, direction, value, flags
```

**Pinctrl debugfs:**

```bash
# Pin controller state
ls /sys/kernel/debug/pinctrl/
# fe200000.gpio/  (BCM2835 example)

cat /sys/kernel/debug/pinctrl/fe200000.gpio/pins
# pin 0 (GPIO0) function alt0 (I2C0 SDA)
# pin 1 (GPIO1) function alt0 (I2C0 SCL)
# pin 2 (GPIO2) function alt4 (SPI0 CE0)
# ...

cat /sys/kernel/debug/pinctrl/fe200000.gpio/pinmux-pins
# pin 14 (GPIO14): my_driver (group GPIO14 function alt0)
# pin 15 (GPIO15): my_driver (group GPIO15 function alt0)

cat /sys/kernel/debug/pinctrl/fe200000.gpio/pingroups
# group: gpio0  pins: 0
# group: gpio1  pins: 1
# group: uart0  pins: 14, 15
# group: spi0   pins: 7, 8, 9, 10, 11
```

**Tracing GPIO in BPF:**

```bash
# Track GPIO toggles per pin
bpftrace -e '
tracepoint:gpio:gpio_value {
    @toggles[args->gpio] = count();
}

END { print(@toggles); }'

# Measure time between GPIO transitions (useful for timing-sensitive protocols)
bpftrace -e '
tracepoint:gpio:gpio_value /args->gpio == 42/ {
    @last = nsecs;
    if (@prev > 0) { @interval_us = hist((nsecs - @prev) / 1000); }
    @prev = nsecs;
}'
```


---

### 13. Power Management / Runtime PM Tracing

**What it is:** Runtime PM tracing captures device power state transitions (active → suspended → idle), revealing power management bugs, spurious wakeups, and devices that fail to suspend properly.

**Runtime PM tracepoints:**

```bash
# List RPM tracepoints
ls /sys/kernel/tracing/events/rpm/
# rpm_idle  rpm_suspend  rpm_resume  rpm_return_int

# Enable runtime PM tracing
echo 1 > /sys/kernel/tracing/events/rpm/enable
cat /sys/kernel/tracing/trace_pipe

# Output:
# kworker/2:1-89 [002] .... 234.567890: rpm_suspend: 0000:03:00.0 flags-4 cnt-0 dep-0 allow-1
#  irq/47-my_dev-123 [001] .... 234.890123: rpm_resume: 0000:03:00.0 flags-4 cnt-1 dep-0 allow-1
# kworker/2:1-89 [002] .... 235.567890: rpm_idle: 0000:03:00.0 flags-4 cnt-0 dep-0 allow-1
#
# cnt = usage_count, dep = child_count, allow = runtime_auto enabled
```

**System-wide PM tracepoints:**

```bash
# Device PM callbacks (suspend/resume path)
ls /sys/kernel/tracing/events/power/
# cpu_idle  cpu_frequency  device_pm_callback_start
# device_pm_callback_end  suspend_resume  wakeup_source_activate
# wakeup_source_deactivate  clock_enable  clock_disable

# Trace system suspend/resume timeline
echo 1 > /sys/kernel/tracing/events/power/device_pm_callback_start/enable
echo 1 > /sys/kernel/tracing/events/power/device_pm_callback_end/enable
echo 1 > /sys/kernel/tracing/events/power/suspend_resume/enable

# Trigger suspend
echo mem > /sys/power/state
# ... system suspends and resumes ...

cat /sys/kernel/tracing/trace
# shows exact order and timing of every driver's suspend/resume callback
```

**sysfs runtime PM statistics:**

```bash
# Per-device runtime PM stats
cat /sys/devices/pci0000:00/0000:00:1f.3/power/runtime_status
# active | suspended | suspending | resuming

cat /sys/devices/pci0000:00/0000:00:1f.3/power/runtime_active_time
# 1234567  (milliseconds in active state)

cat /sys/devices/pci0000:00/0000:00:1f.3/power/runtime_suspended_time
# 9876543  (milliseconds in suspended state)

cat /sys/devices/pci0000:00/0000:00:1f.3/power/runtime_active_kids
# 2  (number of active children)

# Autosuspend delay
cat /sys/devices/pci0000:00/0000:00:1f.3/power/autosuspend_delay_ms
# 2000  (wait 2 seconds before autosuspending)

# Control runtime PM
echo auto > /sys/devices/.../power/control   # enable runtime PM
echo on   > /sys/devices/.../power/control   # force always-on
```

**Wakeup source debugging:**

```bash
# List all wakeup sources
cat /sys/kernel/debug/wakeup_sources
# name          active_count  event_count  wakeup_count  expire_count
# 0000:00:1f.3  12           15           2             0
# rtc0          1            1            1             0

# Trace wakeup events
echo 1 > /sys/kernel/tracing/events/power/wakeup_source_activate/enable
echo 1 > /sys/kernel/tracing/events/power/wakeup_source_deactivate/enable
```

---

### 14. Thermal/Clock/Regulator Tracing

**What it is:** These subsystem tracepoints capture hardware resource management events — thermal throttling, clock frequency changes, and voltage regulator state transitions that directly affect driver behavior and device performance.

**Thermal tracepoints:**

```bash
# List thermal tracepoints
ls /sys/kernel/tracing/events/thermal/
# thermal_temperature  thermal_zone_trip  thermal_power_allocator
# thermal_power_actor  cdev_update

# Trace thermal throttling
echo 1 > /sys/kernel/tracing/events/thermal/enable
cat /sys/kernel/tracing/trace_pipe

# Output:
# thermal-daemon-456 [000] .... 300.123: thermal_temperature: thermal_zone=cpu-thermal id=0 temp_input=72000 temp=72000
# thermal-daemon-456 [000] .... 300.124: thermal_zone_trip: thermal_zone=cpu-thermal id=0 trip=1 trip_type=passive temp=72000
# thermal-daemon-456 [000] .... 300.125: cdev_update: type=cpu-freq target=2
#
# temp in millidegrees Celsius (72000 = 72.0°C)

# Thermal zone sysfs
cat /sys/class/thermal/thermal_zone0/type    # cpu-thermal
cat /sys/class/thermal/thermal_zone0/temp    # 65000 (65.0°C)
cat /sys/class/thermal/thermal_zone0/trip_point_0_temp   # 80000
cat /sys/class/thermal/thermal_zone0/trip_point_0_type   # passive
```

**Clock tracepoints:**

```bash
# List clock tracepoints
ls /sys/kernel/tracing/events/clk/
# clk_enable  clk_disable  clk_prepare  clk_unprepare
# clk_set_rate  clk_set_rate_complete  clk_set_parent

# Trace clock changes
echo 1 > /sys/kernel/tracing/events/clk/enable
cat /sys/kernel/tracing/trace_pipe

# Output:
# my_driver-1234 [001] .... 100.456789: clk_enable: uart_clk
# my_driver-1234 [001] .... 100.456800: clk_set_rate: uart_clk rate=115200
# my_driver-1234 [001] .... 100.456820: clk_set_rate_complete: uart_clk rate=115200

# Clock tree debugfs
cat /sys/kernel/debug/clk/clk_summary
# Name               Enable_cnt  Prepare_cnt  Rate        Accuracy
# pll_cpu            1           1            1800000000  0
#   cpu_clk          1           1            1800000000  0
# pll_periph0        1           1            600000000   0
#   ahb_clk          1           1            200000000   0
#   apb1_clk         1           1            100000000   0
#     uart0_clk      1           1            24000000    0
```

**Regulator tracepoints:**

```bash
# List regulator tracepoints
ls /sys/kernel/tracing/events/regulator/
# regulator_enable  regulator_disable  regulator_bypass_enable
# regulator_set_voltage  regulator_set_voltage_complete

# Trace voltage regulator changes
echo 1 > /sys/kernel/tracing/events/regulator/enable
cat /sys/kernel/tracing/trace_pipe

# Output:
# my_driver-1234 [002] .... 200.789012: regulator_enable: name=vdd_3v3
# my_driver-1234 [002] .... 200.789100: regulator_set_voltage: name=vdd_core min=900000 max=1100000
# my_driver-1234 [002] .... 200.790000: regulator_set_voltage_complete: name=vdd_core val=950000
#
# Voltage in microvolts (950000 = 0.95V)

# Regulator debugfs
cat /sys/kernel/debug/regulator/regulator_summary
# regulator             use  open  bypass  voltage  current  min_uV  max_uV
# vdd_core               2     2       0   950000        0  800000  1100000
# vdd_3v3                3     3       0  3300000        0 3300000  3300000
# vdd_io                 1     1       0  1800000        0 1800000  1800000
```

---

### 15. Device Tree / Platform Bus Debugging

**What it is:** Device Tree (DT) debugging helps verify that hardware descriptions are correctly parsed and matched to drivers, critical for embedded/ARM/RISC-V platforms where device enumeration is DT-driven rather than PCI/USB discovery.

**Device Tree sysfs interface:**

```bash
# Complete device tree as parsed by kernel
ls /sys/firmware/devicetree/base/
# #address-cells  #size-cells  compatible  model  chosen/  memory/  soc/  ...

# Read properties
cat /sys/firmware/devicetree/base/model
# Raspberry Pi 4 Model B Rev 1.4

cat /sys/firmware/devicetree/base/compatible
# raspberrypi,4-model-b brcm,bcm2711

# Navigate device nodes
ls /sys/firmware/devicetree/base/soc/
# #address-cells  #size-cells  compatible  ranges
# gpio@7e200000/  serial@7e201000/  i2c@7e804000/  spi@7e204000/

# Check a device node's properties
cat /sys/firmware/devicetree/base/soc/serial@7e201000/compatible
# arm,pl011 arm,primecell

cat /sys/firmware/devicetree/base/soc/serial@7e201000/status
# okay

hexdump -C /sys/firmware/devicetree/base/soc/serial@7e201000/reg
# Shows register base address and size (big-endian u32/u64)
```

**Platform device binding tracing:**

```bash
# See which drivers matched which DT nodes
ls /sys/bus/platform/devices/
# fe200000.gpio  fe201000.serial  fe804000.i2c  ...

# Check driver binding
cat /sys/bus/platform/devices/fe201000.serial/driver
# → ../../bus/platform/drivers/uart-pl011

cat /sys/bus/platform/devices/fe201000.serial/of_node/compatible
# arm,pl011 arm,primecell

# Trace driver binding events
echo 1 > /sys/kernel/tracing/events/bus/bus_probe_device/enable 2>/dev/null
# Or use dynamic debug on the driver core:
echo "file drivers/base/dd.c +p" > /sys/kernel/debug/dynamic_debug/control
# Produces messages like:
# [  1.234567] bus: 'platform': driver_probe_device: matched device fe201000.serial with driver uart-pl011
```

**DT overlay debugging (runtime device tree changes):**

```bash
# List applied overlays
ls /sys/kernel/config/device-tree/overlays/
# my_overlay/

cat /sys/kernel/config/device-tree/overlays/my_overlay/status
# applied

# Trace overlay application with dynamic debug
echo "file drivers/of/overlay.c +p" > /sys/kernel/debug/dynamic_debug/control
echo "file drivers/of/dynamic.c +p" > /sys/kernel/debug/dynamic_debug/control
```


---

## Sample Trace Output

### Combined driver tracing session (real-world workflow)

A system administrator investigating intermittent I2C sensor failures on an embedded device:

```
# Step 1: Enable relevant tracing
echo "module my_sensor_driver +p" > /sys/kernel/debug/dynamic_debug/control
echo 1 > /sys/kernel/tracing/events/i2c/enable
echo 1 > /sys/kernel/tracing/events/regmap/regmap_reg_read/enable
echo 1 > /sys/kernel/tracing/events/regmap/regmap_reg_write/enable
echo 1 > /sys/kernel/tracing/events/rpm/enable

# Step 2: Capture output (trace_pipe merges all enabled events by timestamp)
cat /sys/kernel/tracing/trace_pipe
```

**Merged output:**

```
# tracer: nop
#
#                                _-----=> irqsoff
#                               / _----=> need-resched
#                              | / _---=> hardirq/softirq
#                              || / _--=> preempt-depth
#                              ||| /     delay
#           TASK-PID     CPU#  ||||   TIMESTAMP  FUNCTION
#              | |         |   ||||      |         |
 kworker/0:1-45  [000] ....  1234.567890: rpm_resume: 1-0048 flags-4 cnt-1 dep-0 allow-1
     my_app-1234 [000] ....  1234.568000: regmap_reg_write: 1-0048 reg=0x0b val=0x80
     my_app-1234 [000] ....  1234.568010: i2c_write: i2c-1 #0 a=048 f=0000 l=2 [0b80]
     my_app-1234 [000] ....  1234.568050: i2c_result: i2c-1 n=1 ret=0
     my_app-1234 [000] ....  1234.568100: regmap_reg_read: 1-0048 reg=0x0c val=0x00
     my_app-1234 [000] ....  1234.568110: i2c_read: i2c-1 #0 a=048 f=0001 l=2
     my_app-1234 [000] ....  1234.568200: i2c_reply: i2c-1 #0 a=048 f=0001 l=2 [1a2b]
     my_app-1234 [000] ....  1234.568210: i2c_result: i2c-1 n=2 ret=0
     my_app-1234 [000] ....  1234.568300: regmap_reg_read: 1-0048 reg=0x0d val=0xff
     my_app-1234 [000] ....  1234.568310: i2c_read: i2c-1 #0 a=048 f=0001 l=2
     my_app-1234 [000] ....  1234.568900: i2c_reply: i2c-1 #0 a=048 f=0001 l=2 [ffff]
     my_app-1234 [000] ....  1234.568910: i2c_result: i2c-1 n=2 ret=-110
     # ^^^ ret=-110 is -ETIMEDOUT! The I2C bus timed out on the second read.
     # The 600µs gap (568310→568900) vs 90µs for successful read confirms bus hang.
 kworker/0:1-45  [000] ....  1234.569000: rpm_idle: 1-0048 flags-4 cnt-0 dep-0 allow-1
 kworker/0:1-45  [000] ....  1234.571000: rpm_suspend: 1-0048 flags-4 cnt-0 dep-0 allow-1
```

### perf script output for block I/O latency

```
dd       1234 [002] 567890.123456: block:block_rq_issue: 259,0 W 4096 () 123456 + 8 [dd]
dd       1234 [002] 567890.123706: block:block_rq_complete: 259,0 W () 123456 + 8 [0]
# ^ 250µs latency for this write I/O
dd       1234 [002] 567890.124000: block:block_rq_issue: 259,0 W 4096 () 123464 + 8 [dd]
dd       1234 [002] 567890.135000: block:block_rq_complete: 259,0 W () 123464 + 8 [0]
# ^ 11ms latency! This I/O hit a garbage collection stall on the NVMe device.
```

---

## Developer Workflow: Adding Tracing to a New Driver

### Step 1: Start with dev_dbg() / dev_info() / dev_err()

```c
/* my_new_driver.c */
#include <linux/device.h>
#include <linux/platform_device.h>

static int my_driver_probe(struct platform_device *pdev)
{
    struct device *dev = &pdev->dev;

    dev_info(dev, "probing\n");

    /* Use dev_dbg for high-frequency paths (disabled by default) */
    dev_dbg(dev, "reading config register: 0x%08x\n", val);

    /* Use dev_err for failures */
    if (ret)
        dev_err(dev, "firmware load failed: %d\n", ret);

    return 0;
}
```

### Step 2: Add TRACE_EVENT() for performance-critical paths

```c
/* include/trace/events/my_new_driver.h */
TRACE_EVENT(my_new_driver_xfer,
    TP_PROTO(struct device *dev, u32 addr, u32 len, int dir),
    TP_ARGS(dev, addr, len, dir),
    TP_STRUCT__entry(
        __string(devname, dev_name(dev))
        __field(u32, addr)
        __field(u32, len)
        __field(int, dir)
    ),
    TP_fast_assign(
        __assign_str(devname, dev_name(dev));
        __entry->addr = addr;
        __entry->len = len;
        __entry->dir = dir;
    ),
    TP_printk("dev=%s addr=0x%x len=%u dir=%d",
        __get_str(devname), __entry->addr, __entry->len, __entry->dir)
);
```

### Step 3: Add debugfs for state inspection

```c
static int my_driver_probe(...)
{
    /* ... */
    mdev->debugfs = debugfs_create_dir("my_new_driver", NULL);
    debugfs_create_file("status", 0444, mdev->debugfs, mdev, &status_fops);
    debugfs_create_u32("error_count", 0444, mdev->debugfs, &mdev->err_count);
}
```

### Step 4: Add devcoredump for crash analysis

```c
static void my_driver_handle_error(struct my_device *mdev)
{
    void *dump = kmalloc(DUMP_SIZE, GFP_KERNEL);
    if (dump) {
        my_driver_collect_state(mdev, dump);
        dev_coredumpv(mdev->dev, dump, DUMP_SIZE, GFP_KERNEL);
    }
}
```

### Step 5: Validate tracing works

```bash
# After loading driver:
# 1. Check dev_dbg works via dynamic debug
echo "module my_new_driver +p" > /sys/kernel/debug/dynamic_debug/control
dmesg -w | grep my_new_driver

# 2. Verify tracepoints are registered
cat /sys/kernel/tracing/available_events | grep my_new_driver

# 3. Confirm debugfs is accessible
ls /sys/kernel/debug/my_new_driver/

# 4. Test devcoredump (trigger error path)
echo 1 > /sys/kernel/debug/my_new_driver/inject_error
ls /sys/class/devcoredump/
```

---

## Cost Profile

| Mechanism | Overhead when disabled | Overhead when enabled | Storage/Memory |
|-----------|----------------------|---------------------|----------------|
| dev_dbg() (dyndbg) | 1–3 ns (static branch) | 1–5 µs per message | Ring buffer (configurable, default 256KB) |
| TRACE_EVENT() | ~0 ns (static key) | 50–150 ns per event | Per-CPU ring buffers (default 1408 KB/CPU) |
| debugfs files | 0 (passive) | µs per read (register access) | Negligible (VFS dentries) |
| devcoredump | 0 (triggered on error) | ms–s (state collection) | Dump size (KB to MB, freed after 5min) |
| usbmon | 0 if no readers | ~200 ns per URB | Ring buffer per bus |
| blktrace | 0 if not active | ~100 ns per I/O | Per-CPU buffers (default 512KB/CPU) |
| regmap tracing | ~0 ns (static key) | 50–100 ns per register access | Shared ftrace ring buffer |
| debugfs regmap | 0 (passive) | µs per read | Register cache memory |

**Key insight:** All mechanisms are designed for zero (or near-zero) overhead when disabled. The Linux tracing philosophy is "always compiled in, never active unless explicitly enabled."

---

## Validation Criteria

### Smoke test: Verify driver tracing is functional

```bash
#!/bin/bash
# Quick validation that driver tracing infrastructure is working

set -e

echo "=== Testing Dynamic Debug ==="
if [ -f /sys/kernel/debug/dynamic_debug/control ]; then
    echo "  [OK] dyndbg control file exists"
    COUNT=$(wc -l < /sys/kernel/debug/dynamic_debug/control)
    echo "  [OK] $COUNT debug call sites registered"
else
    echo "  [FAIL] CONFIG_DYNAMIC_DEBUG not enabled"
fi

echo "=== Testing tracefs ==="
if [ -d /sys/kernel/tracing/events ]; then
    echo "  [OK] tracefs mounted"
    EVENTS=$(find /sys/kernel/tracing/events -name "enable" | wc -l)
    echo "  [OK] $EVENTS traceable events available"
else
    echo "  [FAIL] tracefs not mounted"
fi

echo "=== Testing driver-specific subsystems ==="
for subsys in i2c spi regmap gpio rpm block drm; do
    if [ -d "/sys/kernel/tracing/events/$subsys" ]; then
        echo "  [OK] $subsys tracepoints available"
    fi
done

echo "=== Testing debugfs ==="
if [ -d /sys/kernel/debug ]; then
    echo "  [OK] debugfs mounted"
    ls /sys/kernel/debug/ | head -5 | sed 's/^/  [OK] driver: /'
fi

echo "=== Testing devcoredump ==="
if [ -d /sys/class/devcoredump ]; then
    echo "  [OK] devcoredump class exists"
    DUMPS=$(ls /sys/class/devcoredump/ 2>/dev/null | wc -l)
    echo "  [INFO] $DUMPS pending dumps"
fi
```

---

## Security Considerations

### Access Control

| Interface | Default permissions | Required capability | Risk |
|-----------|-------------------|-------------------|------|
| `/sys/kernel/debug/` (debugfs) | root-only (0700) | CAP_SYS_ADMIN | Register dumps, device state, write knobs |
| `/sys/kernel/tracing/` (tracefs) | root-only (0700) | CAP_SYS_ADMIN | Function arguments, data flow, timing |
| `/sys/kernel/debug/dynamic_debug/` | root-only (0700) | CAP_SYS_ADMIN | Enable verbose logging |
| `/sys/class/devcoredump/` | root-only (0600) | CAP_SYS_ADMIN | Firmware state, memory contents |
| `dmesg` / ring buffer | Restricted (since 4.9) | CAP_SYSLOG | Kernel addresses, device info |
| `/dev/usbmon*` | root-only (0600) | CAP_NET_RAW or root | USB traffic (may include sensitive data) |
| sysfs statistics | world-readable (0444) | None | Low-sensitivity counters |

### Information Exposure Risks

1. **debugfs register dumps** can expose cryptographic keys stored in hardware registers (e.g., TPM, crypto accelerators)
2. **devcoredump** may contain memory contents from DMA buffers (user data, network packets, GPU framebuffer content)
3. **usbmon** captures raw USB traffic including keyboard input, authentication tokens on USB security keys
4. **blktrace** reveals I/O patterns that can fingerprint application behavior
5. **dev_dbg messages** may log sensitive data passed to driver interfaces (e.g., WiFi keys during association)

### Hardening Recommendations

```bash
# Restrict dmesg access (prevent unprivileged users from reading kernel logs)
echo 1 > /proc/sys/kernel/dmesg_restrict

# Disable kptr_restrict to prevent kernel address leaks
echo 2 > /proc/sys/kernel/kptr_restrict

# Mount debugfs with restricted access (or don't mount in production)
mount -t debugfs none /sys/kernel/debug -o mode=0700,uid=0,gid=0

# Lock down tracefs
chmod 0700 /sys/kernel/tracing

# Auto-delete devcoredumps quickly in production
# (configure driver-specific timeouts or systemd timer to clean)

# On lockdown (SecureBoot) systems:
# - debugfs may be entirely disabled
# - BPF may be restricted (kernel.unprivileged_bpf_disabled=1)
# - kprobes may be blocked
# - tracefs writes may be blocked

# SELinux/AppArmor policies should restrict:
# - /sys/kernel/debug/** read/write
# - /sys/kernel/tracing/** read/write
# - /sys/class/devcoredump/** read
```

### Production vs Development Tradeoff

| Environment | Recommended configuration |
|-------------|--------------------------|
| Development | Full debugfs, tracefs, dyndbg, devcoredump. Mount everything. |
| Staging | debugfs mounted but restricted. Tracepoints compiled in. devcoredump enabled. |
| Production | debugfs unmounted or locked. `CONFIG_DYNAMIC_DEBUG=y` but disabled. devcoredump with short timeout. dmesg_restrict=1. |
| Secure/Lockdown | `CONFIG_DEBUG_FS=n`, `CONFIG_KPROBES=n` (or lockdown mode). Only built-in tracepoints via authorized tooling. |

---

## Limitations / Out of Scope

| Limitation | Impact | Workaround |
|-----------|--------|------------|
| debugfs is not ABI-stable | Scripts break between kernel versions | Check kernel version; use tracepoints for stable interfaces |
| dev_dbg() is text-only | Cannot do structured queries on output | Use TRACE_EVENT() for queryable structured data |
| No cross-device correlation ID | Cannot link USB URB to block I/O to network packet | Manual timestamp correlation or BPF programs |
| devcoredump format is driver-specific | Each driver's dump needs its own decoder | Vendor tools required (intel_error_decode, umr, etc.) |
| usbmon misses early boot USB | Monitoring starts after usbmon module loads | Use `usbmon` built-in + early printk |
| No standard "driver health" API | Each driver invents its own debugfs layout | devlink health reporters (network only currently) |
| Ring buffer overflow under load | Events lost when production rate > consumption | Increase buffer size or use snapshot triggers |
| Requires root for most interfaces | Cannot delegate to non-root operators easily | cgroups + BPF (restricted), or relay via systemd-journal |
| No remote trace streaming built-in | Cannot stream traces off-box natively | LTTng relay daemon, or perf + ssh pipe |
| GPIO tracing high-overhead at MHz rates | Cannot trace bit-banged protocols at full speed | Use hardware logic analyzer; tracepoints for low-rate GPIO |
| Thermal/clock events are subsystem-wide | Cannot filter to single device easily | Use ftrace filter expressions on device name field |


---

## AAIF Evaluation Assessment

### Observability — Strong

**Strengths:**
- Every major bus subsystem has dedicated tracepoints (I2C, SPI, USB, PCI, block, network, GPIO, clk, regulator, thermal, RPM)
- Dynamic debug enables runtime verbosity without recompile
- TRACE_EVENT() provides structured, typed, filterable events
- Multiple consumption backends (ftrace, perf, LTTng, BPF) allow different analysis modes from same instrumentation
- Per-CPU lock-free ring buffers ensure low overhead

**Gaps:**
- No unified "driver health dashboard" — each subsystem has its own tools and interfaces
- No standardized structured logging format (dev_dbg is free-form text; only TRACE_EVENT is structured)
- No built-in distributed tracing / correlation IDs across subsystem boundaries
- devcoredump lacks standardized format — each driver invents its own binary layout

### Security — Moderate

**Strengths:**
- All debug interfaces require root/CAP_SYS_ADMIN by default
- Kernel lockdown mode can disable debugfs, kprobes, and tracefs writes entirely
- dmesg_restrict and kptr_restrict prevent information leakage to unprivileged users
- debugfs is explicitly documented as "not for production" with no ABI guarantees

**Gaps:**
- No fine-grained access control (all-or-nothing root access to debugfs)
- devcoredump may expose sensitive memory contents without sanitization
- usbmon captures all USB traffic including authentication data
- No audit trail of who enabled what tracing (no logging of debugfs/tracefs writes)
- Many drivers expose write knobs in debugfs that can alter hardware state (potential DoS vector if debugfs mounted)

### Identity Management — Minimal

**Strengths:**
- Trace events include PID/TID of triggering process
- Device identity is well-established (bus address, driver name, device name)

**Gaps:**
- No concept of "who requested this trace" — all root access is equivalent
- No session/token binding for trace collection
- No cryptographic identity for trace data (unsigned, unauthenticated)
- No user-level attribution for driver operations (which user's I/O hit this driver path)

### Reliability — Strong

**Strengths:**
- Per-CPU ring buffers are lock-free — tracing cannot deadlock the system
- Tracepoints have near-zero overhead when disabled (static keys/branches)
- Overflow is handled gracefully (events dropped, counter incremented, no crash)
- Dynamic debug can be enabled/disabled at any time without module reload
- devcoredump auto-expires (5-minute default) to prevent memory exhaustion

**Gaps:**
- Ring buffer overflow loses events silently (only a count is recorded)
- No delivery guarantees — if userspace doesn't read fast enough, data is lost
- No ordering guarantees across CPUs without timestamp correlation
- blktrace/usbmon can create backpressure if consumer stalls (blocking reads)

### Accuracy — Strong

**Strengths:**
- TRACE_EVENT() records typed, structured data directly from kernel data structures (no serialization ambiguity)
- Timestamps are TSC-based with nanosecond resolution
- regmap tracing records actual hardware register values (ground truth)
- I2C/SPI tracing captures raw bus transactions (wire-level accuracy)
- dev_dbg() messages are generated at the exact code point (no deferred/batched reporting)

**Gaps:**
- dev_dbg() text messages can be ambiguous or out-of-date if format strings aren't maintained
- Timestamp accuracy depends on TSC synchronization across CPUs (rare issues on NUMA)
- debugfs register reads can have side effects on hardware (read-to-clear registers)
- usbmon may miss split-transaction details on some host controllers

---

## Summary Assessment

| Dimension | Rating | Key Gap |
|-----------|--------|---------|
| Observability | **Strong** | No unified cross-subsystem correlation; no standard driver health API |
| Security | **Moderate** | All-or-nothing root access; no audit trail; devcoredump data exposure |
| Identity | **Minimal** | No operator identity, no signed traces, no per-user attribution |
| Reliability | **Strong** | Silent event loss on overflow; no delivery guarantees to userspace |
| Accuracy | **Strong** | Text-based dev_dbg prone to staleness; register reads may have HW side effects |

---

## Integration Matrix: How Driver Tracing Connects to Generic Tracers

| Driver mechanism | ftrace | perf | LTTng | BPF/bpftrace | Wireshark |
|-----------------|--------|------|-------|-------------|-----------|
| dev_dbg() / dyndbg | — (dmesg only) | — | — | — | — |
| TRACE_EVENT() tracepoints | ✓ (native) | ✓ (perf record -e) | ✓ (lttng enable-event -k) | ✓ (tracepoint:*) | — |
| debugfs files | — | — | — | — | — |
| devcoredump | — | — | — | — | — |
| usbmon | — | — | — | — | ✓ (usbmon interface) |
| blktrace | ✓ (via tracepoints) | ✓ (block:* events) | ✓ | ✓ (tracepoint:block:*) | — |
| ethtool -S | — | — | — | — | — |
| devlink health | — | — | — | — | — |
| regmap tracepoints | ✓ | ✓ | ✓ | ✓ | — |
| GPIO tracepoints | ✓ | ✓ | ✓ | ✓ | — |
| RPM/power tracepoints | ✓ | ✓ | ✓ | ✓ | — |
| thermal/clk/regulator | ✓ | ✓ | ✓ | ✓ | — |

**Key insight:** TRACE_EVENT()-based tracepoints are the universal integration point. Any driver mechanism that uses TRACE_EVENT() is automatically consumable by all four major tracing backends. Mechanisms that don't (dev_dbg, debugfs, devcoredump, ethtool) exist in their own siloes.
