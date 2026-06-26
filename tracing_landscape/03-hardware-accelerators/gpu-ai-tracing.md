# AAIF Reference Architecture: GPU Driver Tracing for AI Acceleration

| Field | Value |
|-------|-------|
| **Subject** | GPU Driver Tracing for AI/Tensor Operations |
| **Vendors** | [NVIDIA CUPTI](https://developer.nvidia.com/cupti) / [AMD ROCm](https://rocm.docs.amd.com) / [Intel oneAPI](https://www.intel.com/content/www/us/en/developer/tools/oneapi/overview.html) |
| **Date** | 2026-06-25 |

---

## Objective

Demonstrates how GPU drivers expose tensor core utilization, compute kernel dispatch, memory management, and multi-GPU communication through vendor-specific tracing APIs and hardware performance counters — enabling observation of AI/ML workload execution from framework-level dispatch through driver submission to hardware execution unit activity.

---

## Scope / Zoom Level

**System layer — from AI framework dispatch through GPU driver to hardware tensor execution units.**

This spans the full AI compute path: framework (PyTorch/TensorFlow) → vendor runtime (CUDA/HIP/Level Zero) → kernel driver (nvidia/amdgpu/i915) → hardware (Tensor Cores/Matrix Cores/XMX units). The focus is on observing tensor operations, mixed-precision compute, memory transfers, and multi-GPU coordination at the driver and hardware level.

---

## Prerequisites

| Component | Version | Notes |
|-----------|---------|-------|
| **NVIDIA** | | |
| CUDA Toolkit | 12.x+ | Includes CUPTI, Nsight tools |
| NVIDIA driver | 535+ | Exposes PM counters, CUPTI backend |
| DCGM | 3.x | Data center monitoring |
| Nsight Systems | 2024.x+ | Timeline tracing |
| Nsight Compute | 2024.x+ | Kernel profiling |
| **AMD** | | |
| ROCm | 6.x+ | Includes roctracer, rocprof |
| amdgpu driver | 6.x kernel module | Kernel tracepoints |
| rocprof | 2.x | Hardware counter profiling |
| roctracer | Bundled with ROCm | API tracing |
| **Intel** | | |
| oneAPI | 2024.x+ | Level Zero, VTune |
| i915/xe driver | 6.x kernel | OA counter interface |
| intel_gpu_top | Bundled with intel-gpu-tools | Real-time monitoring |
| **Cross-vendor** | | |
| PyTorch | 2.x+ | torch.profiler with CUDA/ROCm/XPU |
| TensorFlow | 2.x+ | TF Profiler, XLA tracing |

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    AI Framework Layer                                         │
│                                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                     │
│  │   PyTorch    │  │ TensorFlow   │  │    JAX       │                     │
│  │  torch.profiler│  │  TF Profiler │  │  XLA trace  │                     │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘                     │
│         │ NVTX/ROCTX annotations            │                               │
│         ▼                  ▼                  ▼                               │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  Math Libraries: cuBLAS/cuDNN | rocBLAS/MIOpen | oneMKL/oneDNN      │   │
│  │  (Kernel selection: GEMM algorithm, precision, fusion decisions)     │   │
│  └──────────────────────────────┬──────────────────────────────────────┘   │
└─────────────────────────────────┼───────────────────────────────────────────┘
                                  │
┌─────────────────────────────────▼───────────────────────────────────────────┐
│                    Vendor Runtime Layer                                       │
│                                                                             │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐         │
│  │  CUDA Runtime    │  │  HIP Runtime     │  │  Level Zero      │         │
│  │  + CUPTI hooks   │  │  + roctracer     │  │  + ze_tracer     │         │
│  │                  │  │                  │  │                  │         │
│  │  cuLaunchKernel  │  │  hipLaunchKernel │  │  zeCommandList   │         │
│  │  cuMemAlloc      │  │  hipMalloc       │  │  ExecuteAppend   │         │
│  │  cuMemcpy*       │  │  hipMemcpy       │  │  zeMemAlloc*     │         │
│  └────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘         │
└───────────┼──────────────────────┼──────────────────────┼───────────────────┘
            │                      │                      │
┌───────────▼──────────────────────▼──────────────────────▼───────────────────┐
│                    Kernel Driver Layer                                        │
│                                                                             │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐         │
│  │  nvidia.ko       │  │  amdgpu.ko       │  │  i915.ko / xe.ko │         │
│  │                  │  │                  │  │                  │         │
│  │  • GPU scheduler │  │  • amdgpu_cs_*   │  │  • i915_request_*│         │
│  │  • Channel mgmt  │  │  • KFD dispatch  │  │  • xe_exec       │         │
│  │  • VRAM/BAR mgmt │  │  • BO create/move│  │  • xe_bo_create  │         │
│  │  • NVLink ctrl   │  │  • XGMI routing  │  │  • EU scheduling │         │
│  └────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘         │
└───────────┼──────────────────────┼──────────────────────┼───────────────────┘
            │                      │                      │
┌───────────▼──────────────────────▼──────────────────────▼───────────────────┐
│                    GPU Hardware                                               │
│                                                                             │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐         │
│  │  NVIDIA          │  │  AMD             │  │  Intel           │         │
│  │  Tensor Cores    │  │  Matrix Cores    │  │  XMX Units       │         │
│  │  (WMMA/MMA)     │  │  (MFMA)          │  │  (DPAS)          │         │
│  │                  │  │                  │  │                  │         │
│  │  SM units        │  │  Compute Units   │  │  Execution Units │         │
│  │  HBM/GDDR       │  │  HBM             │  │  HBM/GDDR       │         │
│  │  NVLink/PCIe    │  │  XGMI/PCIe       │  │  Xe Link/PCIe   │         │
│  │                  │  │                  │  │                  │         │
│  │  PM Counters:    │  │  PM Counters:    │  │  OA Counters:    │         │
│  │  tensor_active   │  │  SQ_INSTS_MFMA  │  │  XMX_active      │         │
│  │  sm_active       │  │  CU_occupancy   │  │  EU_active       │         │
│  │  dram_bw         │  │  HBM_bw         │  │  L3_bandwidth    │         │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘         │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Instrumentation Walkthrough

### Observation Model: Tensor Operations

GPU driver tracing for AI uses three complementary observation models:

| Model | What It Answers | Mechanism |
|-------|----------------|-----------|
| **Kernel dispatch events** | "What tensor op ran, when, for how long?" | CUPTI Activity / roctracer / Level Zero timestamps |
| **Hardware counters** | "How efficiently did tensor cores execute?" | PM counters: tensor pipe active %, occupancy, memory BW |
| **Memory events** | "Where did data move, how much, at what bandwidth?" | DtoH/HtoD/DtoD memcpy tracing, page migration, P2P transfers |

### NVIDIA: Tensor Core Tracing

**Key metrics for AI workloads:**

| Metric | What It Measures |
|--------|-----------------|
| `sm__pipe_tensor_cycles_active` | Cycles where Tensor Cores are actively computing |
| `sm__inst_executed_pipe_tensor` | Tensor Core instructions executed |
| `sm__pipe_tensor_cycles_active.avg.pct_of_peak_sustained_active` | Tensor Core utilization % |
| `dram__bytes_read.sum` + `dram__bytes_write.sum` | HBM bandwidth consumed |
| `sm__warps_active.avg.pct_of_peak_sustained_active` | SM occupancy |
| `gpu__time_duration.sum` | Kernel execution time |
| `lts__t_bytes.sum` | L2 cache throughput |

**CUPTI Activity API (kernel dispatch tracing):**

```c
// Each completed kernel produces a CUpti_ActivityKernel record:
typedef struct {
    CUpti_ActivityKind kind;         // CUPTI_ACTIVITY_KIND_KERNEL
    uint64_t start;                  // GPU timestamp (ns)
    uint64_t end;                    // GPU timestamp (ns)
    uint32_t deviceId;
    uint32_t contextId;
    uint32_t streamId;
    int32_t  gridX, gridY, gridZ;   // Grid dimensions
    int32_t  blockX, blockY, blockZ; // Block dimensions
    uint32_t dynamicSharedMemory;
    uint32_t staticSharedMemory;
    const char *name;                // Kernel name (e.g., "volta_fp16_s884gemm_128x128_ldg8_f2f_tn")
} CUpti_ActivityKernel;
```

**Nsight Systems CLI (full AI training trace):**

```bash
# Trace PyTorch training with CUDA kernels, NVTX annotations, cuDNN/cuBLAS, NCCL
nsys profile \
  --trace=cuda,nvtx,cudnn,cublas,osrt \
  --cuda-memory-usage=true \
  --gpuctxsw=true \
  python train.py

# Tensor core specific metrics via Nsight Compute
ncu --metrics \
  sm__pipe_tensor_cycles_active.avg.pct_of_peak_sustained_active,\
  sm__inst_executed_pipe_tensor,\
  dram__bytes_read.sum,\
  dram__bytes_write.sum \
  python -c "import torch; a=torch.randn(4096,4096,device='cuda',dtype=torch.float16); torch.mm(a,a)"
```

**DCGM for production monitoring:**

```bash
# Key AI metrics via DCGM
dcgmi dmon -e 1004,1005,1009,1010,1011,1012
# Fields:
#   1004: SM_ACTIVE (%)
#   1005: SM_OCCUPANCY (%)
#   1009: TENSOR_ACTIVE (%)     ← Primary AI utilization metric
#   1010: DRAM_ACTIVE (%)
#   1011: PCIE_TX_BYTES
#   1012: PCIE_RX_BYTES
```

### AMD: Matrix Core (MFMA) Tracing

**Key metrics for AI workloads:**

| Metric | What It Measures |
|--------|-----------------|
| `SQ_INSTS_VALU_MFMA_F16` | FP16 matrix multiply-add instructions |
| `SQ_INSTS_VALU_MFMA_BF16` | BF16 matrix multiply-add instructions |
| `SQ_INSTS_VALU_MFMA_F32` | FP32 matrix multiply-add instructions |
| `SQ_INSTS_VALU_MFMA_I8` | INT8 matrix multiply-add instructions |
| `SQ_INSTS_VALU_MFMA_F8` | FP8 matrix multiply-add instructions |
| `TCC_HIT_sum` / `TCC_MISS_sum` | L2 cache hit/miss (memory efficiency) |
| `FETCH_SIZE` / `WRITE_SIZE` | HBM read/write bytes |
| `GPU_UTIL` | Overall GPU utilization |

**rocprof (hardware counter profiling):**

```bash
# Profile matrix core utilization for a training script
cat > counters.txt << 'EOF'
pmc: SQ_INSTS_VALU_MFMA_F16 SQ_INSTS_VALU_MFMA_BF16 SQ_INSTS_VALU_MFMA_I8
pmc: FETCH_SIZE WRITE_SIZE GPU_UTIL
EOF

rocprof --input counters.txt python train.py
# Output: results.csv with per-kernel counter values
```

**roctracer (API-level dispatch tracing):**

```bash
# Trace HIP API calls and kernel dispatches
roctracer --hip-trace --hsa-trace python train.py

# Output (text):
# HIP_API: hipLaunchKernel(fn=0x7f..., grid={128,1,1}, block={256,1,1}, shMem=0, stream=0x...)
#   start=1234567890 end=1234568000 dur=110ns
# HSA_API: hsa_signal_wait_scacquire(signal=0x..., value=0)
#   start=1234568100 end=1234569500 dur=1400ns
```

**amdgpu kernel tracepoints:**

```bash
# Enable AMD GPU compute dispatch tracing
echo 1 > /sys/kernel/tracing/events/amdgpu/amdgpu_cs_ioctl/enable
echo 1 > /sys/kernel/tracing/events/amdgpu/amdgpu_sched_run_job/enable
echo 1 > /sys/kernel/tracing/events/amdgpu/amdgpu_vm_bo_map/enable

cat /sys/kernel/tracing/trace_pipe
# amdgpu_cs_ioctl: ring=0, num_chunks=3
# amdgpu_sched_run_job: ring=0, job=1234, fence=0x...
```

### Intel: XMX (Xe Matrix Extensions) Tracing

**Key metrics for AI workloads:**

| Metric | What It Measures |
|--------|-----------------|
| `XMX Pipe Active` | Cycles XMX systolic array is computing |
| `EU Active` | Execution Unit active cycles |
| `EU Stall` | Execution Unit stalled (waiting for data) |
| `L3 Bandwidth` | L3 cache throughput |
| `GTI Read/Write Bandwidth` | Memory controller throughput |
| `Compute Engine Busy` | Overall compute utilization |

**Level Zero tracing:**

```bash
# Trace all Level Zero API calls
ze_tracer python train.py

# Programmatic kernel timestamp collection:
# zeCommandListAppendLaunchKernel timestamps in command list
# zeEventQueryKernelTimestamp retrieves GPU execution time per kernel
```

**i915_perf / OA counters:**

```bash
# Intel GPU top with JSON output (for AI workload monitoring)
intel_gpu_top -J -s 100

# Output:
# {"period":{"duration":100.00},
#  "engines":{"Compute/0":{"busy":87.3},
#             "Render":{"busy":2.1},
#             "Copy/0":{"busy":45.2}}}

# Detailed OA metrics via VTune
vtune -collect gpu-hotspots -- python train.py
```

### Cross-Vendor: PyTorch Profiler Integration

```python
import torch
from torch.profiler import profile, ProfilerActivity, tensorboard_trace_handler

with profile(
    activities=[ProfilerActivity.CPU, ProfilerActivity.CUDA],  # or ProfilerActivity.XPU
    with_stack=True,
    record_shapes=True,
    profile_memory=True,
    on_trace_ready=tensorboard_trace_handler("./log/traces"),
) as prof:
    for step in range(10):
        output = model(input_batch)
        loss = criterion(output, target)
        loss.backward()
        optimizer.step()
        prof.step()

# Key trace output includes:
# - Kernel name (e.g., "volta_fp16_s884gemm_128x128_ldg8_f2f_tn")
# - GPU time (μs)
# - CPU time (μs)
# - Input shapes (e.g., [4096, 4096] × [4096, 4096])
# - Memory allocated/freed
# - NCCL operations (for distributed training)
```

---

## Sample Trace Output

### NVIDIA: Nsight Systems export (JSON, one kernel)

```json
{
  "traceEvents": [
    {
      "name": "volta_fp16_s884gemm_128x128_ldg8_f2f_tn",
      "cat": "cuda",
      "ph": "X",
      "ts": 1750878545123456,
      "dur": 234,
      "pid": 1,
      "tid": 7,
      "args": {
        "device": 0,
        "stream": 13,
        "context": 1,
        "grid": [32, 32, 1],
        "block": [128, 1, 1],
        "shared_memory": 49152,
        "registers_per_thread": 128,
        "tensor_core_utilization_pct": 78.4,
        "dram_read_bytes": 67108864,
        "dram_write_bytes": 16777216,
        "precision": "FP16",
        "operation": "GEMM",
        "m": 4096, "n": 4096, "k": 4096
      }
    },
    {
      "name": "ncclAllReduceRingLLKernel_sum_fp16",
      "cat": "cuda",
      "ph": "X",
      "ts": 1750878545123690,
      "dur": 1450,
      "pid": 1,
      "tid": 7,
      "args": {
        "device": 0,
        "stream": 15,
        "collective": "AllReduce",
        "data_bytes": 134217728,
        "nvlink_bandwidth_gbps": 42.3,
        "num_ranks": 8
      }
    }
  ]
}
```

### AMD: rocprof CSV output (per-kernel counters)

```csv
Index,KernelName,gpu-id,queue-id,queue-index,pid,tid,grd,wgr,lds,scr,vgpr,sgpr,fbar,sig,SQ_INSTS_VALU_MFMA_F16,SQ_INSTS_VALU_MFMA_BF16,FETCH_SIZE,WRITE_SIZE
0,"mfma_gemm_4096x4096x4096_f16",0,0,0,12345,12345,524288,256,65536,0,128,48,0,0x7f...,4194304,0,67108864,16777216
1,"mfma_gemm_4096x1024x4096_bf16",0,0,1,12345,12345,131072,256,65536,0,96,32,0,0x7f...,0,1048576,16777216,4194304
```

### PyTorch Profiler output (Chrome trace format)

```json
{
  "name": "aten::mm",
  "cat": "cpu_op",
  "ph": "X",
  "ts": 1750878545000000,
  "dur": 45,
  "args": {
    "Input Dims": [[4096, 4096], [4096, 4096]],
    "Input type": ["Float16", "Float16"],
    "Concrete Inputs": "",
    "Fwd thread id": 1
  }
},
{
  "name": "ampere_fp16_s1688gemm_fp16_128x256_ldg8_f2f_stages_32x5_tn",
  "cat": "kernel",
  "ph": "X",
  "ts": 1750878545000012,
  "dur": 218,
  "args": {
    "device": 0,
    "stream": 7,
    "grid": [16, 32, 1],
    "block": [128, 1, 1],
    "est. achieved occupancy %": 75,
    "shared memory": 99328,
    "memory bandwidth (GB/s)": 1842.5
  }
}
```

### DCGM Prometheus metrics (production monitoring)

```
# HELP DCGM_FI_PROF_PIPE_TENSOR_ACTIVE Tensor Core pipe active ratio
# TYPE DCGM_FI_PROF_PIPE_TENSOR_ACTIVE gauge
DCGM_FI_PROF_PIPE_TENSOR_ACTIVE{gpu="0",UUID="GPU-abc123"} 0.784
DCGM_FI_PROF_PIPE_TENSOR_ACTIVE{gpu="1",UUID="GPU-def456"} 0.791

# HELP DCGM_FI_PROF_DRAM_ACTIVE HBM bandwidth utilization ratio
# TYPE DCGM_FI_PROF_DRAM_ACTIVE gauge
DCGM_FI_PROF_DRAM_ACTIVE{gpu="0",UUID="GPU-abc123"} 0.623
DCGM_FI_PROF_DRAM_ACTIVE{gpu="1",UUID="GPU-def456"} 0.618

# HELP DCGM_FI_DEV_POWER_USAGE Current power draw (W)
# TYPE DCGM_FI_DEV_POWER_USAGE gauge
DCGM_FI_DEV_POWER_USAGE{gpu="0",UUID="GPU-abc123"} 312.5
DCGM_FI_DEV_POWER_USAGE{gpu="1",UUID="GPU-def456"} 308.2
```

---

## Cost Profile

### LLM token cost

**Not directly applicable**, but GPU tracing is essential for measuring token/sec throughput and identifying bottlenecks in LLM inference/training.

### Compute/IO overhead per operation

| Mechanism | Overhead | Notes |
|-----------|----------|-------|
| CUPTI Activity API (kernel trace) | 2–5% GPU throughput | Serialization overhead on kernel launch |
| CUPTI hardware counters (per-pass) | 1 replay per counter group | Kernel re-execution for each counter set |
| Nsight Systems (timeline) | 1–3% | Low-overhead event recording |
| Nsight Compute (detailed) | 10–100× slower | Full kernel replay with isolation |
| DCGM polling (1 Hz) | <0.1% | Reads hardware registers periodically |
| roctracer (API trace) | 2–5% | Callback overhead per API call |
| rocprof (hardware counters) | 1 pass per counter group | Similar to CUPTI replay model |
| Level Zero timestamps | <1% | Kernel timestamps in command list |
| i915_perf OA counters | 1–3% | OA buffer DMA + interrupt |
| PyTorch profiler | 3–10% | CPU-side recording + CUPTI overhead |

### Storage growth rate

| Tracing Mode | Growth Rate | Notes |
|--------------|-------------|-------|
| DCGM metrics (1 Hz, 8 GPUs) | ~50 KB/min | Prometheus export; bounded |
| Nsight Systems timeline (training) | 50–500 MB/hour | Depends on kernel launch rate |
| Nsight Compute (full kernel profile) | 10–100 MB per kernel | One kernel at a time |
| PyTorch profiler (per-step) | 1–10 MB/step | Chrome trace JSON; grows fast |
| rocprof CSV | 1–10 MB/min | One row per kernel dispatch |
| Production monitoring (DCGM + alerts) | Negligible | Aggregated metrics only |

---

## Validation Criteria

1. **Tensor core utilization visible**: DCGM field 1009 (`TENSOR_ACTIVE`) reports > 0% during matrix multiply
2. **Kernel names resolved**: Nsight/rocprof output shows human-readable kernel names (e.g., `volta_fp16_s884gemm_*`) not addresses
3. **Mixed precision tracked**: Counter distinguishes FP16/BF16/TF32/INT8/FP8 paths (NVIDIA: separate tensor pipe metrics; AMD: separate MFMA counters per type)
4. **Memory bandwidth measured**: HBM read/write bytes per kernel correlate with expected data movement
5. **Multi-GPU visible**: NCCL/RCCL operations appear in trace with inter-GPU data size and bandwidth
6. **Framework ↔ GPU correlated**: PyTorch profiler shows both CPU op (aten::mm) and corresponding GPU kernel with matched timestamps
7. **No silent drops**: Profiler reports if events were lost due to buffer overflow

### Quick smoke test

```bash
# NVIDIA: Verify tensor cores are being used
dcgmi dmon -e 1009 -d 1000 &  # Monitor tensor active %
python -c "
import torch
a = torch.randn(4096, 4096, device='cuda', dtype=torch.float16)
for _ in range(100): torch.mm(a, a)
torch.cuda.synchronize()
"
# DCGM output should show TENSOR_ACTIVE > 50%

# AMD: Verify matrix core instructions
echo "pmc: SQ_INSTS_VALU_MFMA_F16" > /tmp/counters.txt
rocprof --input /tmp/counters.txt python -c "
import torch
a = torch.randn(4096, 4096, device='cuda', dtype=torch.float16)
for _ in range(100): torch.mm(a, a)
torch.cuda.synchronize()
"
# results.csv should show SQ_INSTS_VALU_MFMA_F16 > 0
```

---

## Limitations / Out of Scope

| Item | Status |
|------|--------|
| Cross-vendor unified trace format | Does not exist; NVIDIA (CUPTI/Nsight), AMD (rocprof), Intel (OA) all different |
| Model architecture inference from traces | Kernel names may reveal layer shapes; no built-in obfuscation |
| Unified tensor core utilization metric | Each vendor uses different counters; no abstraction layer |
| Multi-node distributed training tracing | NCCL/RCCL traces are per-node; cross-node correlation requires external tooling |
| Firmware-level GPU tracing | Internal GPU microcontroller behavior not exposed to host |
| Kernel fusion internals | Fused kernels appear as single unit; individual op attribution lost |
| Real-time alerting on tensor underutilization | Must build on top of DCGM/prometheus; not built-in |
| Energy per token measurement | Power (watts) available; per-token attribution requires manual calculation |
| Training job identity binding | GPU traces have no concept of job scheduler job ID or user identity |
| Encrypted trace export | No vendor provides encrypted profiling output |
| Historical comparison (regression detection) | Must be built externally; no built-in baseline comparison |

---

## Evaluation Assessment

### Observability

**Rating: Strong**

| Aspect | Assessment |
|--------|------------|
| **Strengths** | Full visibility from framework dispatch to hardware execution. Tensor core utilization directly measurable (NVIDIA DCGM field 1009 is the gold standard). Kernel-level timing with nanosecond precision. Memory bandwidth measurement identifies data movement bottlenecks. Multi-GPU communication traceable (NCCL/RCCL). PyTorch/TensorFlow profilers provide framework-level correlation. Mixed precision path identification (which kernels use FP16 vs BF16 vs TF32). Production monitoring via DCGM/Prometheus without overhead. |
| **Gaps** | No cross-vendor unified format — comparing NVIDIA vs AMD workloads requires different tools. Kernel fusion makes individual op attribution impossible. Counter multiplexing requires kernel replay (Nsight Compute) which is impractical in production. No standard for correlating GPU traces with CPU/network traces. Framework-level overhead may distort timing. |
| **Implementations must add** | Cross-vendor trace normalization layer, production-safe counter collection without replay, automatic kernel-to-op attribution through fusion, unified monitoring dashboards across GPU vendors. |

### Security

**Rating: Partial**

| Aspect | Assessment |
|--------|------------|
| **Strengths** | CUPTI requires explicit opt-in (admin privilege or environment variable). DCGM access controllable via systemd/permissions. Hardware counter access requires root or CAP_PERFMON equivalent. Nsight tools require explicit attachment. |
| **Gaps** | Trace data reveals model architecture (kernel names contain matrix dimensions: `gemm_4096x4096`). GPU memory contents accessible via debugfs on some drivers. No encryption of profiling output files. DCGM Prometheus endpoint exposes GPU utilization to anyone with network access. Shared GPU environments (MIG, time-slicing) may leak cross-tenant utilization patterns. No audit trail of profiling sessions. |
| **Implementations must add** | Kernel name obfuscation options, encrypted trace export, per-tenant GPU isolation verification, profiling session audit logging, network-level access control for DCGM, trace data classification (sensitive model IP). |

### Identity Management

**Rating: Weak**

| Aspect | Assessment |
|--------|------------|
| **Strengths** | CUDA context ID identifies a process's GPU context. NVIDIA MIG (Multi-Instance GPU) partitions have unique IDs. PID available in some trace formats. DCGM can report per-process GPU usage. AMD KFD tracks per-process queues. |
| **Gaps** | No binding between GPU trace and training job identity (Slurm job ID, Kubernetes pod, user). No AI model identity (which model is running). No session correlation across multi-node training. No tenant identity in shared GPU environments beyond MIG partition. GPU performance counters are system-wide, not per-process. NCCL traces have no concept of training run identity. |
| **Implementations must add** | Job scheduler → GPU trace identity binding, model/experiment identity tagging (via NVTX/ROCTX), per-tenant counter isolation, training run correlation across nodes, authenticated profiling sessions with operator identity. |

### Reliability

**Rating: Moderate**

| Aspect | Assessment |
|--------|------------|
| **Strengths** | DCGM is production-grade (runs as systemd service, survives GPU resets). Hardware counters are non-intrusive at low polling rates. CUPTI buffer overflow reporting. Nsight Systems ring-buffer mode bounds memory. GPU driver tracepoints use ftrace ring buffer (lock-free, per-CPU). |
| **Gaps** | CUPTI activity buffer can overflow silently, losing kernel records. Hardware counter multiplexing means not all metrics are simultaneously available. Nsight Compute kernel replay can hang on synchronization-dependent kernels. rocprof crashes on some multi-GPU configurations. GPU driver bugs can crash the tracing subsystem. No guaranteed delivery of GPU metrics to external collectors. Clock synchronization between CPU and GPU has microsecond-level error. |
| **Implementations must add** | Overflow alerting, redundant metric collection paths, graceful degradation when GPU tracing subsystem fails, validated clock synchronization, multi-GPU profiling stability testing. |

### Accuracy

**Rating: Moderate**

| Aspect | Assessment |
|--------|------------|
| **Strengths** | Hardware performance counters measure exact instruction counts (MFMA/WMMA/DPAS dispatched). GPU timestamps from dedicated timestamp engines (nanosecond resolution). Tensor core utilization directly measured at hardware level (not inferred). Memory bandwidth from hardware traffic counters (exact bytes). |
| **Gaps** | CPU↔GPU clock synchronization error (1–10 μs) makes cross-domain correlation imprecise. Kernel replay for counters changes execution behavior (warmed caches, different scheduling). Tensor core utilization % can be misleading (high utilization ≠ efficient computation if doing redundant work). Fused kernels attribute all time to a single entry point. Counter multiplexing means metrics are from different kernel executions (not simultaneous). AMD/Intel counter documentation less precise than NVIDIA. |
| **Implementations must add** | Clock correlation calibration, simultaneous multi-counter collection (hardware support dependent), per-op attribution within fused kernels, efficiency metrics (useful FLOPS vs theoretical peak), counter documentation validation. |

---

## Assessment Summary

| Dimension | Rating | Key Gap |
|-----------|--------|---------|
| Observability | Strong | No cross-vendor unified format; kernel fusion hides individual op timing |
| Security | Partial | Traces expose model architecture; no encrypted export; no audit trail |
| Identity | Weak | No job/model/tenant identity binding in GPU traces |
| Reliability | Moderate | CUPTI buffer overflow; counter multiplexing; clock sync error |
| Accuracy | Moderate | CPU↔GPU clock skew; kernel replay changes behavior; fused op attribution |

---

## Vendor Maturity Comparison

| Capability | NVIDIA | AMD | Intel |
|-----------|--------|-----|-------|
| Tensor/Matrix core utilization metric | ★★★★★ | ★★★★ | ★★★ |
| Production monitoring (daemon) | ★★★★★ (DCGM) | ★★★ (ROCm SMI) | ★★ (intel_gpu_top) |
| Framework integration (PyTorch) | ★★★★★ | ★★★★ | ★★★ |
| Kernel-level profiling | ★★★★★ (Nsight) | ★★★★ (rocprof) | ★★★ (VTune) |
| Multi-GPU tracing | ★★★★★ (NCCL+NVLink) | ★★★★ (RCCL+XGMI) | ★★ (oneCCL+Xe Link) |
| Documentation quality | ★★★★★ | ★★★ | ★★★ |
| Open-source tooling | ★★★ (mostly proprietary) | ★★★★★ (ROCm is open) | ★★★★ (Level Zero is open) |
| Linux kernel integration | ★★ (nvidia.ko is proprietary) | ★★★★★ (amdgpu upstream) | ★★★★★ (i915/xe upstream) |
