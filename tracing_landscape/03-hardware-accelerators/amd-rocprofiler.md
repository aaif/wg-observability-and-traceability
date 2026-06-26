# AAIF Reference Architecture: AMD roctracer / rocprofiler

| Field | Value |
|-------|-------|
| **Subject** | [AMD ROCm Profiling](https://rocm.docs.amd.com/) — roctracer, rocprofiler, rocprofiler-sdk |
| **Version** | ROCm 6.x (2024–2026) |
| **Date** | 2026-06-25 |

---

## Objective

Demonstrates how AMD's open-source ROCm profiling stack provides GPU kernel dispatch tracing (roctracer), hardware performance counter collection (rocprofiler), and unified next-generation instrumentation (rocprofiler-sdk) — enabling observation of HIP/HSA API calls, Matrix Core (MFMA) utilization, HBM bandwidth, and multi-GPU communication on AMD Instinct accelerators.

---

## Scope / Zoom Level

**Orchestration layer — from HIP runtime through kernel driver to CDNA hardware execution units.**

The ROCm profiling stack spans from application-level API tracing (HIP calls) through the HSA runtime to the amdgpu kernel driver and hardware performance counters. It covers compute dispatch, memory management, and matrix core instruction counting for AI/ML workloads on AMD Instinct (MI200/MI300) GPUs.

---

## Prerequisites

| Component | Version | Notes |
|-----------|---------|-------|
| ROCm | 6.x+ | Full stack: runtime, driver, tools |
| amdgpu kernel driver | Upstream Linux 6.x | Open-source, in mainline kernel |
| roctracer | Bundled with ROCm | HIP/HSA API tracing |
| rocprofiler-sdk | ROCm 6.0+ | New unified profiling API |
| rocprof CLI | ROCm 6.x+ | Counter collection CLI |
| ROCTX | Bundled with roctracer | User annotation API |
| KFD | Built into amdgpu | Kernel Fusion Driver for compute dispatch |
| GPU | MI200+ (CDNA2+) | MFMA counters require CDNA architecture |

Optional higher-level tools:
| Tool | Purpose |
|------|---------|
| Omniperf | Roofline analysis, kernel-level guidance |
| Omnitrace | Application timeline (like Nsight Systems) |
| ROCm SMI | System-level GPU monitoring |

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    Application + Framework                                    │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  PyTorch / TensorFlow / JAX (ROCm backend)                            │  │
│  │  + ROCTX annotations (training step, forward, backward)               │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  rocBLAS / MIOpen / RCCL                                              │  │
│  │  (MFMA kernel selection, collective communication)                    │  │
│  └────────────────────────────────────┬─────────────────────────────────┘  │
└───────────────────────────────────────┼─────────────────────────────────────┘
                                        │
┌───────────────────────────────────────▼─────────────────────────────────────┐
│                    HIP Runtime / HSA Runtime                                  │
│                                                                             │
│  hipLaunchKernel, hipMalloc, hipMemcpy, hipStreamSynchronize, ...          │
│  hsa_signal_*, hsa_queue_*, hsa_executable_*, ...                          │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  roctracer / rocprofiler-sdk (interception layer)                     │  │
│  │                                                                       │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐   │  │
│  │  │ Callback API │  │ Activity API │  │ Counter Collection Svc   │   │  │
│  │  │ (sync hooks) │  │ (async bufs) │  │ (HW PM counter read)     │   │  │
│  │  └──────┬───────┘  └──────┬───────┘  └────────────┬─────────────┘   │  │
│  └─────────┼──────────────────┼───────────────────────┼─────────────────┘  │
└────────────┼──────────────────┼───────────────────────┼─────────────────────┘
             │                  │                       │
┌────────────▼──────────────────▼───────────────────────▼─────────────────────┐
│                    Kernel Driver (amdgpu.ko + KFD)                            │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  Tracepoints: amdgpu_cs_ioctl, amdgpu_sched_run_job, amdgpu_vm_*    │  │
│  │  KFD: compute queue management, dispatch packets, XGMI routing       │  │
│  │  PM counter registers: direct read via KFD ioctl                     │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────┬───────────────────────────────────┘
                                          │
┌─────────────────────────────────────────▼───────────────────────────────────┐
│                    AMD GPU Hardware (CDNA)                                    │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  Compute Units (CUs)                                                  │  │
│  │  ┌────────────────────────────────────────────────────────────────┐  │  │
│  │  │  Matrix Cores (MFMA — Matrix Fused Multiply-Add)               │  │  │
│  │  │  v_mfma_f32_32x32x8_f16   (FP16 → FP32 accumulate)           │  │  │
│  │  │  v_mfma_f32_32x32x8_bf16  (BF16 → FP32 accumulate)           │  │  │
│  │  │  v_mfma_f32_32x32x16_i8   (INT8 → INT32 accumulate)          │  │  │
│  │  │  v_mfma_f32_32x32x16_fp8  (FP8 → FP32 accumulate)            │  │  │
│  │  └────────────────────────────────────────────────────────────────┘  │  │
│  │  HBM (High Bandwidth Memory)                                         │  │
│  │  XGMI / Infinity Fabric (inter-GPU links)                           │  │
│  │                                                                       │  │
│  │  PM Counters: SQ_INSTS_VALU_MFMA_*, TCC_*, FETCH_SIZE, WRITE_SIZE  │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Instrumentation Walkthrough

### What is captured

**roctracer (API-level tracing):**

| Domain | Events | Fields |
|--------|--------|--------|
| HIP API | hipLaunchKernel, hipMalloc, hipMemcpy, hipStreamSync | Function name, args, start_ns, end_ns, correlation_id |
| HSA API | hsa_signal_wait, hsa_queue_create, hsa_executable_load | Op type, signal handle, queue_id, timestamps |
| Activity | Kernel dispatch completion, memory copy completion | device_id, queue_id, begin_ns, end_ns, kernel_name, bytes |
| ROCTX | User-defined ranges and markers | text, begin_ns, end_ns, thread_id |

**rocprofiler / rocprofiler-sdk (hardware counters):**

| Counter Category | Key Counters | What They Measure |
|-----------------|--------------|-------------------|
| Matrix Core (MFMA) | `SQ_INSTS_VALU_MFMA_F16` | FP16 matrix multiply instructions executed |
| | `SQ_INSTS_VALU_MFMA_BF16` | BF16 matrix multiply instructions executed |
| | `SQ_INSTS_VALU_MFMA_F32` | FP32 matrix multiply instructions executed |
| | `SQ_INSTS_VALU_MFMA_I8` | INT8 matrix multiply instructions executed |
| | `SQ_INSTS_VALU_MFMA_F8` | FP8 matrix multiply instructions executed |
| Shader Sequencer | `SQ_WAVES` | Total wavefronts launched |
| | `SQ_INSTS_VALU` | Total VALU instructions |
| | `SQ_INSTS_SALU` | Total SALU instructions |
| | `SQ_WAIT_INST_ANY` | Cycles wavefronts stalled |
| L2 Cache (TCC) | `TCC_HIT_sum` | L2 cache hits |
| | `TCC_MISS_sum` | L2 cache misses |
| | `TCC_EA_RDREQ_sum` | Read requests to memory controller |
| Memory | `FETCH_SIZE` | Total bytes fetched from HBM |
| | `WRITE_SIZE` | Total bytes written to HBM |
| Utilization | `GRBM_GUI_ACTIVE` | GPU active cycles |
| | `GPU_UTIL` | Overall GPU utilization % |

### The mechanism

**roctracer (callback/activity model):**

1. **LD_PRELOAD injection**: roctracer interposes on HIP/HSA shared libraries
2. **Callback mode**: Synchronous hook fires before/after each API call; tool receives function ID + args
3. **Activity mode**: Asynchronous — after kernel/memcpy completes, an activity record (timestamps, device, queue, correlation_id) is written to a ring buffer
4. **Correlation**: Each API call gets a `correlation_id` linking the CPU-side API call to the GPU-side activity completion

**rocprofiler-sdk (counter collection):**

1. **Tool registration**: Tool implements `rocprofiler_tool_configure_result_t` and registers via `rocprofiler_configure()`
2. **Dispatch interception**: rocprofiler-sdk intercepts kernel dispatch at the HSA AQL packet level
3. **Counter configuration**: PM counter registers configured before dispatch
4. **Kernel execution**: Kernel runs with counters active
5. **Counter read**: After kernel completion, counter values read from hardware registers
6. **Multi-pass**: If requested counters exceed simultaneous hardware capacity, kernel re-dispatched with different counter set

**ROCTX (annotation):**

```c
#include <roctx.h>
roctxRangePush("forward_pass");
// ... HIP kernel launches ...
roctxRangePop();

roctxMark("epoch_boundary");
```

```python
# Python via PyTorch ROCm backend
from torch.cuda import nvtx  # Works on ROCm too via HIP translation
nvtx.range_push("training_step")
# ...
nvtx.range_pop()
```

### Data format produced

**roctracer output (text):**
```
HIP_API: hipLaunchKernel correlation=1234 beg=100000 end=100500
  kernel=mfma_gemm_4096x4096_f16 grid={128,1,1} block={256,1,1}
ACTIVITY: kernel correlation=1234 dev=0 queue=0 beg=100600 end=234500
  name=mfma_gemm_4096x4096_f16
```

**rocprof CSV output (per-kernel counters):**
```csv
Index,KernelName,gpu-id,queue-id,grd,wgr,lds,scr,vgpr,sgpr,SQ_INSTS_VALU_MFMA_F16,FETCH_SIZE,WRITE_SIZE
0,"mfma_gemm_4096x4096_f16",0,0,524288,256,65536,0,128,48,4194304,67108864,16777216
```

**rocprofiler-sdk (JSON via rocprofv2):**
```json
{
  "kernel_dispatch": {
    "kernel_name": "mfma_gemm_4096x4096_f16",
    "agent_id": 0,
    "queue_id": 0,
    "start_ns": 1750878545000100600,
    "end_ns": 1750878545000234500,
    "grid_size": [524288, 1, 1],
    "workgroup_size": [256, 1, 1],
    "counters": {
      "SQ_INSTS_VALU_MFMA_F16": 4194304,
      "SQ_INSTS_VALU_MFMA_BF16": 0,
      "SQ_WAVES": 2048,
      "FETCH_SIZE": 67108864,
      "WRITE_SIZE": 16777216,
      "TCC_HIT_sum": 8388608,
      "TCC_MISS_sum": 1048576
    }
  }
}
```

---

## Sample Trace Output

### roctracer text output (HIP API + Activity)

```
ROCTracer (pid=12345):
HIP_API 0:100000000 hipMalloc(ptr=0x7f..., size=67108864) = 0 :100002345
HIP_API 0:100100000 hipMemcpy(dst=0x7f..., src=0x..., size=67108864, kind=H2D) = 0 :100234567
HIP_API 0:100300000 hipLaunchKernel(fn=0x..., grid={128,1,1}, block={256,1,1}, shMem=65536, stream=0x...) :100300450
  correlation_id=1001
ACTIVITY: KERNEL dev=0 queue=0 correlation=1001 beg=100305000 end=100539000 dur=234000ns
  name="mfma_gemm_4096x4096x4096_f16" grid={128,1,1} block={256,1,1}
HIP_API 0:100600000 hipDeviceSynchronize() = 0 :100600123
```

### rocprof v1 CSV (counter output, multiple kernels)

```csv
Index,KernelName,gpu-id,queue-id,queue-index,pid,tid,grd,wgr,lds,scr,arch_vgpr,sgpr,fbar,sig,SQ_INSTS_VALU_MFMA_F16,SQ_INSTS_VALU_MFMA_BF16,SQ_WAVES,FETCH_SIZE,WRITE_SIZE
0,"mfma_gemm_4096x4096_f16",0,0,0,12345,12345,524288,256,65536,0,128,48,0,0x7f1234,4194304,0,2048,67108864,16777216
1,"mfma_gemm_4096x1024_bf16",0,0,1,12345,12345,131072,256,65536,0,96,32,0,0x7f5678,0,1048576,512,16777216,4194304
2,"elementwise_add_f16",0,0,2,12345,12345,16384,256,0,0,32,16,0,0x7f9abc,0,0,64,8388608,8388608
```

### Omnitrace timeline (Perfetto-compatible JSON)

```json
{
  "traceEvents": [
    {
      "name": "training_step",
      "cat": "roctx",
      "ph": "B",
      "ts": 1750878545000000,
      "pid": 12345,
      "tid": 1
    },
    {
      "name": "mfma_gemm_4096x4096_f16",
      "cat": "hip_kernel",
      "ph": "X",
      "ts": 1750878545000305,
      "dur": 234,
      "pid": 12345,
      "tid": 7,
      "args": {
        "device": 0,
        "queue": 0,
        "grid": [128, 1, 1],
        "block": [256, 1, 1],
        "lds": 65536,
        "vgpr": 128
      }
    },
    {
      "name": "rccl_allreduce_ring_bf16",
      "cat": "hip_kernel",
      "ph": "X",
      "ts": 1750878545001200,
      "dur": 1890,
      "pid": 12345,
      "tid": 7,
      "args": {
        "device": 0,
        "collective": "AllReduce",
        "bytes": 134217728
      }
    },
    {
      "name": "training_step",
      "cat": "roctx",
      "ph": "E",
      "ts": 1750878545005000,
      "pid": 12345,
      "tid": 1
    }
  ]
}
```

### amdgpu kernel tracepoint output (ftrace)

```
  python-12345  [004] .... 789.012345: amdgpu_cs_ioctl: ring=0 num_chunks=3
  python-12345  [004] .... 789.012367: amdgpu_sched_run_job: ring=0 job=5678 fence=0x7f...
  kworker/4:1-42 [004] .... 789.012601: amdgpu_sched_process_job: fence=0x7f... hw_fence=0x...
```

### ROCm SMI output (system monitoring)

```
$ rocm-smi --showuse --showmeminfo vram --showtemp --json
{
  "card0": {
    "GPU use (%)": "87",
    "GPU memory use (%)": "72",
    "VRAM Total Memory (B)": "68702699520",
    "VRAM Total Used Memory (B)": "49465614336",
    "Temperature (Sensor edge) (C)": "67",
    "Current Socket Graphics Package Power (W)": "285"
  },
  "card1": {
    "GPU use (%)": "84",
    "GPU memory use (%)": "71",
    "VRAM Total Memory (B)": "68702699520",
    "VRAM Total Used Memory (B)": "48792805376",
    "Temperature (Sensor edge) (C)": "65",
    "Current Socket Graphics Package Power (W)": "278"
  }
}
```

---

## Cost Profile

### LLM token cost

**Not directly applicable**, but ROCm profiling tools are essential for measuring inference throughput (tokens/sec) and training efficiency (samples/sec) on AMD Instinct GPUs.

### Compute/IO overhead per operation

| Tool/Mode | Overhead | Production Safe? |
|-----------|----------|-----------------|
| roctracer (HIP API trace) | 2–5% | Yes |
| roctracer (HSA + HIP combined) | 5–10% | Conditional |
| rocprof counters (single pass) | ~1 kernel re-execution | No (modifies timing) |
| rocprof counters (multi-pass) | N× kernel re-execution | No |
| rocprofiler-sdk (buffer mode) | 2–5% | Yes |
| rocprofiler-sdk (PC sampling) | 3–8% | Conditional |
| ROCTX annotation (no collector) | <0.01% | Yes |
| Omnitrace (full timeline) | 5–15% | No |
| ROCm SMI polling (1 Hz) | <0.1% | Yes |
| amdgpu kernel tracepoints | 40–100 ns/event | Yes (if bounded) |

### Storage growth rate

| Output | Size | Notes |
|--------|------|-------|
| roctracer text (60s, 1 GPU) | 10–100 MB | Proportional to API call rate |
| rocprof CSV (per-kernel) | 1–10 MB/min | One row per dispatch |
| Omnitrace trace (60s, 1 GPU) | 50–200 MB | Perfetto proto format |
| Omnitrace (8 GPUs, full) | 500 MB – 2 GB | Linear with GPU count |
| ROCm SMI JSON (1 Hz, 8 GPUs) | ~50 KB/min | Negligible |

---

## Validation Criteria

1. **roctracer captures**: `roctracer python -c "import torch; torch.mm(torch.randn(1024,1024,device='cuda'),torch.randn(1024,1024,device='cuda'))"` produces HIP API trace output
2. **Kernels named**: Trace output shows kernel names (e.g., `mfma_gemm_*`) not raw addresses
3. **MFMA counters fire**: `rocprof --input counters.txt` with `pmc: SQ_INSTS_VALU_MFMA_F16` shows > 0 for FP16 GEMM
4. **Correlation IDs link**: API call correlation_id matches activity record correlation_id
5. **Multi-GPU visible**: RCCL operations appear with device IDs and data sizes
6. **Kernel tracepoints work**: `echo 1 > /sys/kernel/tracing/events/amdgpu/amdgpu_cs_ioctl/enable` produces events during GPU activity
7. **Precision distinguished**: Different MFMA counters (F16 vs BF16 vs I8) correctly reflect the data type used

### Quick smoke test

```bash
# Verify roctracer captures HIP kernels
roctracer --hip-trace python -c "
import torch
a = torch.randn(4096, 4096, device='cuda', dtype=torch.float16)
b = torch.mm(a, a)
torch.cuda.synchronize()
" 2>&1 | grep -i "kernel\|mfma\|gemm"
# Should show hipLaunchKernel and ACTIVITY records with gemm/mfma kernel names

# Verify hardware counters
echo "pmc: SQ_INSTS_VALU_MFMA_F16 SQ_WAVES FETCH_SIZE" > /tmp/counters.txt
rocprof --input /tmp/counters.txt --timestamp on python -c "
import torch
a = torch.randn(4096, 4096, device='cuda', dtype=torch.float16)
for _ in range(10): torch.mm(a, a)
torch.cuda.synchronize()
"
cat results.csv | head -5
# Verify: SQ_INSTS_VALU_MFMA_F16 > 0, FETCH_SIZE matches expected HBM reads
```

---

## Limitations / Out of Scope

| Item | Status |
|------|--------|
| NVIDIA GPU support | ROCm tools are AMD-only; no cross-vendor |
| Persistent monitoring daemon | No equivalent to NVIDIA DCGM; rocm-smi is polling-only |
| Prometheus/metrics export | Not built-in; must wrap rocm-smi |
| Encrypted trace output | Not provided |
| Kernel replay isolation | Less mature than Nsight Compute's clock-locked replay |
| Tool transition (v1→v2) | Documentation confusion; legacy and new APIs coexist |
| Counter documentation | Scattered across XML files; less accessible than NVIDIA's |
| Multi-tenant isolation | No MIG equivalent until MI300 partitioning |
| Real-time streaming | No live trace streaming (batch only) |
| OpenTelemetry integration | None built-in |
| Job scheduler identity | No concept of Slurm/K8s job in traces |
| Windows support | Linux-only (ROCm is Linux-exclusive) |

---

## Evaluation Assessment

### Observability

**Rating: Strong**

| Aspect | Assessment |
|--------|------------|
| **Strengths** | Full-stack visibility: HIP API → HSA → kernel driver → hardware counters. MFMA-specific counters directly measure AI tensor utilization per precision type. Open-source (MIT license) — can be extended, embedded, or audited. Upstream kernel tracepoints integrate with ftrace/perf/LTTng. rocprofiler-sdk buffer model enables high-throughput collection. ROCTX annotations enable framework-level correlation. Omniperf provides roofline analysis. Omnitrace produces Perfetto-compatible timelines. |
| **Gaps** | No persistent monitoring daemon (must poll rocm-smi). No built-in Prometheus/metrics export. Tool transition (v1→v2) creates confusion. Counter documentation less accessible than NVIDIA's. No equivalent to Nsight Compute's rules/recommendations engine. |
| **Implementations must add** | Persistent GPU monitoring daemon with metrics export, unified documentation for counters, automated performance recommendations, OpenTelemetry bridge. |

### Security

**Rating: Partial**

| Aspect | Assessment |
|--------|------------|
| **Strengths** | Open-source allows full audit of what data is collected. KFD requires appropriate `/dev/kfd` permissions. Hardware counter access requires CAP_PERFMON or group membership. No telemetry or phone-home in any tool. Upstream kernel driver benefits from Linux security infrastructure. |
| **Gaps** | Profiling output (CSV, JSON) unencrypted, reveals kernel names and matrix dimensions. No access control beyond file permissions. No audit log of profiling sessions. `/dev/kfd` permissions model is coarse (all-or-nothing). Trace data in shared HPC environments accessible to other users if permissions misconfigured. |
| **Implementations must add** | Trace file encryption, fine-grained /dev/kfd access control per device, profiling session audit logging, kernel name obfuscation option, secure multi-tenant GPU sharing. |

### Identity Management

**Rating: Weak**

| Aspect | Assessment |
|--------|------------|
| **Strengths** | PID/TID in all trace records. External correlation IDs in rocprofiler-sdk allow custom identity injection. KFD tracks per-process GPU queue ownership. Device agent_id identifies specific GPU. |
| **Gaps** | No built-in job scheduler or container identity. No model/experiment identity concept. No multi-tenant identity isolation at the profiling level. External correlation IDs require tool code changes to propagate. No authenticated profiling sessions. |
| **Implementations must add** | Job scheduler identity integration (Slurm job ID → trace), model/experiment tagging via ROCTX conventions, per-tenant counter isolation, authenticated profiling access. |

### Reliability

**Rating: Moderate**

| Aspect | Assessment |
|--------|------------|
| **Strengths** | rocprofiler-sdk buffer overflow policy is configurable (DISCARD vs LOSSLESS). Ring-buffer model prevents unbounded memory growth. Kernel tracepoints use ftrace per-CPU ring buffers (lock-free). Thread-safe by design. Open-source means bugs can be fixed by users. |
| **Gaps** | Legacy rocprof v1 crashes on some multi-GPU configurations. Counter multiplexing requires kernel re-execution (non-determinism). No guaranteed delivery to external collectors. GPU reset loses in-flight profiling data. PC sampling can miss short-running kernels. Tool stability less validated than NVIDIA's mature ecosystem. |
| **Implementations must add** | Multi-GPU stability hardening, guaranteed delivery to external collectors, GPU reset recovery for in-flight traces, buffer overflow alerting, crash-resilient trace output. |

### Accuracy

**Rating: Moderate**

| Aspect | Assessment |
|--------|------------|
| **Strengths** | Hardware PM counters measure exact instruction counts (not estimates). GPU timestamp engine provides nanosecond resolution. MFMA counters distinguish exact precision types (F16/BF16/F32/I8/F8 separately). Memory bandwidth from hardware traffic counters (exact bytes). Open-source counter collection verifiable. |
| **Gaps** | Multi-pass counter collection means values from different kernel executions. CPU↔GPU clock domain correlation has microsecond-level error. Some counters aggregated across all CUs (cannot isolate per-CU). Derived metrics depend on normalization that varies by GPU SKU. Counter saturation behavior not always documented. Less validation tooling than NVIDIA's. |
| **Implementations must add** | Single-pass counter collection where hardware permits, per-CU counter isolation, clock domain calibration tooling, counter overflow/saturation detection, SKU-specific normalization documentation. |

---

## Assessment Summary

| Dimension | Rating | Key Gap |
|-----------|--------|---------|
| Observability | Strong | No persistent monitoring daemon; tool transition confusion |
| Security | Partial | Unencrypted output; coarse /dev/kfd permissions |
| Identity | Weak | No job/model/tenant identity; requires custom correlation injection |
| Reliability | Moderate | Multi-GPU stability; counter multiplexing non-determinism |
| Accuracy | Moderate | Multi-pass counters from different executions; clock domain error |

---

## Comparison with NVIDIA Nsight

| Aspect | AMD ROCm | NVIDIA Nsight |
|--------|----------|---------------|
| **License** | MIT (all open-source) | Proprietary |
| **Kernel driver** | amdgpu (upstream Linux) | nvidia.ko (proprietary, out-of-tree) |
| **ftrace integration** | Full tracepoints in mainline | None (proprietary driver) |
| **Timeline tool** | Omnitrace (Perfetto format) | Nsight Systems (.nsys-rep SQLite) |
| **Kernel profiler** | rocprof / Omniperf | Nsight Compute (.ncu-rep) |
| **Counter access** | Direct PM register via KFD ioctl | Abstracted via CUPTI/PerfWorks |
| **Annotation API** | ROCTX | NVTX |
| **Production monitoring** | rocm-smi (polling, no daemon) | DCGM (persistent daemon, Prometheus) |
| **Maturity** | Rapidly evolving (v1→v2) | Stable, mature, well-documented |
| **Documentation** | Counter docs in XML files | Rich web docs + in-tool guidance |
| **Recommendations engine** | Omniperf (separate tool) | Nsight Compute rules (built-in) |
| **Multi-tenant** | Limited | MIG hardware partitioning |
