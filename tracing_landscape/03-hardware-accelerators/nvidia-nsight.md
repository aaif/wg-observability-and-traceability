# AAIF Reference Architecture: NVIDIA Nsight

| Field | Value |
|-------|-------|
| **Subject** | [NVIDIA Nsight Systems](https://developer.nvidia.com/nsight-systems) / [Nsight Compute](https://developer.nvidia.com/nsight-compute) |
| **Version** | 2024.x (bundled with CUDA Toolkit 12.x) |
| **Date** | 2026-06-25 |

---

## Objective

Demonstrates how NVIDIA Nsight provides two complementary GPU profiling tools — Nsight Systems for system-wide timeline tracing (kernel launches, memory transfers, multi-GPU communication) and Nsight Compute for per-kernel hardware counter analysis (tensor core utilization, memory throughput, occupancy) — both built on the CUPTI instrumentation API and the NVTX annotation framework.

---

## Scope / Zoom Level

**Orchestration layer — from application framework dispatch through CUDA runtime to GPU hardware execution.**

Nsight operates between the AI framework (PyTorch/TensorFlow) and the GPU hardware. Nsight Systems captures the timeline of all GPU operations across the system. Nsight Compute drills into individual kernels with hardware counter replay. Together they cover the full observability stack for CUDA-accelerated AI workloads.

---

## Prerequisites

| Component | Version | Notes |
|-----------|---------|-------|
| CUDA Toolkit | 12.x+ | Includes CUPTI, nsys, ncu |
| NVIDIA Driver | 535+ | Exposes CUPTI backend and PM counters |
| Nsight Systems (nsys) | 2024.x+ | Timeline tracer |
| Nsight Compute (ncu) | 2024.x+ | Kernel profiler |
| NVTX | Bundled with CUDA | User annotation API |
| GPU | Volta+ (SM 7.0+) | Tensor Core metrics require Volta or newer |
| CAP_SYS_ADMIN or --target-processes | — | Required for hardware counter access in containers |

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    Application + Framework                                    │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  PyTorch / TensorFlow / JAX                                           │  │
│  │  + NVTX annotations (training step, forward, backward, optimizer)     │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  cuDNN / cuBLAS / NCCL / Transformer Engine                           │  │
│  │  (emit NVTX ranges internally for layer-level visibility)             │  │
│  └────────────────────────────────────┬─────────────────────────────────┘  │
└───────────────────────────────────────┼─────────────────────────────────────┘
                                        │
┌───────────────────────────────────────▼─────────────────────────────────────┐
│                    CUDA Runtime / Driver API                                  │
│                                                                             │
│  cuLaunchKernel, cuMemAlloc, cuMemcpy*, cuStreamSynchronize, ...           │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  CUPTI (CUDA Profiling Tools Interface)                               │  │
│  │                                                                       │  │
│  │  ┌─────────────┐ ┌──────────────┐ ┌─────────────┐ ┌─────────────┐  │  │
│  │  │ Activity API│ │ Callback API │ │ Event API   │ │Profiling API│  │  │
│  │  │ (async buf) │ │ (sync hooks) │ │ (PM counter)│ │(replay+ctr) │  │  │
│  │  └──────┬──────┘ └──────┬───────┘ └──────┬──────┘ └──────┬──────┘  │  │
│  │         │               │                │               │           │  │
│  └─────────┼───────────────┼────────────────┼───────────────┼───────────┘  │
└────────────┼───────────────┼────────────────┼───────────────┼───────────────┘
             │               │                │               │
    ┌────────▼───────┐ ┌────▼────────┐ ┌─────▼──────┐ ┌─────▼──────┐
    │ Nsight Systems │ │Nsight Systems│ │Nsight Compute│ │Nsight Compute│
    │ (kernel timing)│ │ (API trace) │ │(raw counters)│ │(derived met.)│
    └────────┬───────┘ └─────┬───────┘ └─────┬──────┘ └─────┬──────┘
             │               │                │               │
             ▼               ▼                ▼               ▼
    ┌─────────────────────────────┐  ┌───────────────────────────────┐
    │  .nsys-rep (SQLite-based)   │  │  .ncu-rep (proprietary)       │
    │  Exportable: JSON, SQLite,  │  │  Exportable: CSV, stdout      │
    │  text, Chrome trace         │  │  Rules/Recommendations        │
    └─────────────────────────────┘  └───────────────────────────────┘
```

### Data Flow: Nsight Systems (Timeline)

```
Kernel launch → CUPTI Activity buffer → nsys reads buffer → .nsys-rep file
NVTX push/pop → CUPTI NVTX callback → nsys records range → .nsys-rep file
cuMemcpy call → CUPTI Activity record → nsys records transfer → .nsys-rep file
OS thread → CPU sampling (backtrace) → nsys records sample → .nsys-rep file
```

### Data Flow: Nsight Compute (Kernel Profiling)

```
Kernel launch → ncu intercepts → REPLAYS kernel N times with different counter sets
  Pass 1: SM pipe metrics (tensor_active, fp32_active, fp16_active)
  Pass 2: Memory metrics (dram_bytes, l2_hit_rate, shared_efficiency)
  Pass 3: Scheduler metrics (warp_stall_*, eligible_warps)
  ...
Each pass → hardware PM counters read → aggregated into .ncu-rep
```

---

## Instrumentation Walkthrough

### What is captured

**Nsight Systems (timeline):**

| Data Category | Events | Fields |
|---------------|--------|--------|
| CUDA kernels | Launch, start, end | Name, grid/block dims, stream, duration, shared mem, registers |
| Memory operations | cuMemcpy*, cuMemAlloc/Free | Bytes, direction (H2D/D2H/D2D), source/dest device, bandwidth |
| NVTX annotations | Push/Pop ranges, markers | User-defined text, domain, category, color |
| cuDNN/cuBLAS | Algorithm selection, execution | Operation type, dimensions, data type, algorithm ID |
| NCCL | Collective operations | Type (AllReduce/Broadcast/...), data size, ranks, ring/tree topology |
| NVLink | Bandwidth counters | Bytes TX/RX per link, utilization % |
| PCIe | Transfer bandwidth | Bytes, direction, device pair |
| OS runtime | Thread scheduling | CPU migrations, context switches, POSIX sync |
| CPU sampling | Backtraces at configured frequency | IP, call stack, thread, process |

**Nsight Compute (per-kernel hardware):**

| Metric Section | Key Metrics | What They Answer |
|----------------|------------|------------------|
| Speed Of Light (SOL) | Compute %, Memory % of peak | Is kernel compute- or memory-bound? |
| Tensor Core | `sm__pipe_tensor_cycles_active.avg.pct_of_peak_sustained_active` | Are Tensor Cores being used efficiently? |
| Compute | `sm__inst_executed_pipe_tensor`, `sm__inst_executed_pipe_fp16`, `sm__inst_executed_pipe_fp32` | What instruction types dominate? |
| Memory | `dram__bytes_read.sum`, `dram__bytes_write.sum`, `lts__t_bytes.sum` | HBM and L2 throughput |
| Occupancy | `sm__warps_active.avg.pct_of_peak_sustained_active` | SM utilization |
| Scheduler | `smsp__warps_eligible.avg`, stall reasons | Why are warps waiting? |
| Roofline | FLOPS vs bytes | Arithmetic intensity vs hardware limits |

### The mechanism

**CUPTI Activity API (Nsight Systems backend):**
- CUPTI maintains per-context ring buffers
- After kernel completion, activity records (struct with timestamps, grid dims, etc.) are written to buffer
- nsys polls/drains buffers and writes to .nsys-rep
- Overhead: 2–5% (buffer management + serialization)

**CUPTI Profiling API (Nsight Compute backend):**
- Intercepts kernel launch
- Configures hardware PM counter set for this pass
- Re-executes kernel with clock isolation (fixed frequency, no other kernels)
- Reads PM counters after completion
- Repeats for each counter group that doesn't fit simultaneously
- Overhead: 10–100× slower (kernel replayed N times)

**NVTX (annotation mechanism):**
```c
#include <nvtx3/nvtx3.hpp>
// C++ RAII range
{
    nvtx3::scoped_range r{"forward_pass"};
    model.forward(input);
}
// C API
nvtxRangePushA("backward_pass");
loss.backward();
nvtxRangePop();
```

```python
# Python
import nvtx
with nvtx.annotate("training_step", color="blue"):
    output = model(batch)
    loss.backward()
```

### Data format produced

**Nsight Systems (.nsys-rep):**
- SQLite database with schema: CUPTI_ACTIVITY_KIND_KERNEL, NVTX_EVENTS, CUPTI_ACTIVITY_KIND_MEMCPY, etc.
- Exportable: `nsys export --type=json`, `nsys export --type=sqlite`, `nsys stats`
- Chrome trace format (JSON) for visualization in chrome://tracing or Perfetto

**Nsight Compute (.ncu-rep):**
- Proprietary binary containing per-kernel metric collections
- Exportable: `ncu --csv`, `ncu --page raw` for text output
- Includes rules engine output (performance recommendations)

---

## Sample Trace Output

### nsys stats (kernel summary)

```
CUDA Kernel Statistics:

 Time (%)  Total Time (ns)  Instances  Avg (ns)   Med (ns)   Min (ns)   Max (ns)   Name
 --------  ---------------  ---------  ---------  ---------  ---------  ---------   ----
     45.2      234567890        128     1832561    1789234    1654321    2345678     volta_fp16_s884gemm_128x128_ldg8_f2f_tn
     23.1      119876543         64     1873071    1834567    1723456    2123456     ncclAllReduceRingLL_sum_fp16
     12.4       64234567        256      250916     234567     198765     345678     vectorized_elementwise_kernel<4, ...>
      8.7       45123456        128      352527     334567     298765     456789     bn_fw_tr_kernel<float, float16>

CUDA Memory Operation Statistics:

 Time (%)  Total Time (ns)  Count   Avg (ns)   Operations    Bytes       Bandwidth
 --------  ---------------  ------  ---------  ----------  ----------  -----------
     67.3      345678901       512    675154   DtoH        2147483648  6.2 GB/s
     28.4      145678901       256    569058   HtoD        1073741824  7.4 GB/s
      4.3       22345678       128    174575   DtoD         536870912  24.0 GB/s
```

### nsys export JSON (Chrome trace format, one kernel)

```json
{
  "traceEvents": [
    {
      "name": "volta_fp16_s884gemm_128x128_ldg8_f2f_tn",
      "cat": "cuda",
      "ph": "X",
      "ts": 1750878545123456,
      "dur": 1832,
      "pid": 1,
      "tid": 7,
      "args": {
        "device": 0,
        "stream": 13,
        "context": 1,
        "gridX": 32, "gridY": 32, "gridZ": 1,
        "blockX": 128, "blockY": 1, "blockZ": 1,
        "sharedMemory": 49152,
        "registersPerThread": 128,
        "correlationId": 45678
      }
    },
    {
      "name": "forward_pass",
      "cat": "nvtx",
      "ph": "B",
      "ts": 1750878545120000,
      "pid": 1,
      "tid": 1,
      "args": { "domain": "pytorch", "category": "training" }
    },
    {
      "name": "forward_pass",
      "cat": "nvtx",
      "ph": "E",
      "ts": 1750878545200000,
      "pid": 1,
      "tid": 1
    }
  ]
}
```

### ncu CSV output (per-kernel metrics)

```csv
"Kernel Name","Metric Name","Metric Unit","Metric Value"
"volta_fp16_s884gemm_128x128","sm__pipe_tensor_cycles_active.avg.pct_of_peak_sustained_active","%","78.4"
"volta_fp16_s884gemm_128x128","sm__inst_executed_pipe_tensor.sum","inst","4194304"
"volta_fp16_s884gemm_128x128","dram__bytes_read.sum","byte","67108864"
"volta_fp16_s884gemm_128x128","dram__bytes_write.sum","byte","16777216"
"volta_fp16_s884gemm_128x128","sm__warps_active.avg.pct_of_peak_sustained_active","%","75.3"
"volta_fp16_s884gemm_128x128","gpu__time_duration.sum","nsecond","1832561"
"volta_fp16_s884gemm_128x128","lts__t_bytes.sum","byte","83886080"
"volta_fp16_s884gemm_128x128","sm__sass_thread_inst_executed_op_hmma_pred_on.sum","inst","8388608"
```

### ncu Rules/Recommendations output

```
---- Speed Of Light ----
  Compute (SM) Throughput: 34.5% of peak
  Memory Throughput: 78.2% of peak
  → This kernel is MEMORY BOUND

---- Tensor Core Utilization ----
  Tensor pipe active: 78.4%
  FP16 instructions: 4,194,304
  Tensor operations: HMMA (Half-precision Matrix Multiply-Accumulate)

---- Recommendation ----
  Memory is more heavily utilized than Compute (78.2% vs 34.5%).
  Consider:
  - Increasing arithmetic intensity (more compute per byte)
  - Using shared memory tiling to reduce DRAM pressure
  - L2 cache hit rate is 45.2% — investigate access patterns
```

---

## Cost Profile

### LLM token cost

**Not directly applicable**, but Nsight is the primary tool for measuring LLM inference throughput (tokens/sec) and identifying bottlenecks in transformer execution.

### Compute/IO overhead per operation

| Tool/Mode | Overhead | Production Safe? |
|-----------|----------|-----------------|
| nsys `--trace=cuda` | 1–3% | Yes |
| nsys `--trace=cuda,nvtx,cudnn,cublas` | 3–8% | Conditional (time-limited) |
| nsys with Python backtrace | 5–15% | No |
| ncu `--set basic` (single kernel) | 10–30× | No |
| ncu `--set full` (single kernel) | 50–100× | No |
| NVTX annotation (no collector) | <0.01% | Yes (always safe) |
| NVTX annotation (nsys collecting) | 0.1–1% | Yes |
| CUPTI Activity API (programmatic) | 2–5% | Yes |

### Storage growth rate

| Output | Size | Notes |
|--------|------|-------|
| .nsys-rep (60s trace, 1 GPU) | 50–200 MB | Proportional to kernel launch rate |
| .nsys-rep (60s, 8 GPUs, full) | 500 MB – 2 GB | Linear with GPU count |
| .ncu-rep (one kernel, full metrics) | 10–50 MB | N replay passes |
| JSON export (Chrome trace) | 2–5× .nsys-rep | Text encoding overhead |

---

## Validation Criteria

1. **nsys collects**: `nsys profile -o test python -c "import torch; torch.mm(torch.randn(1024,1024,device='cuda'),torch.randn(1024,1024,device='cuda'))"` produces .nsys-rep without error
2. **Kernels visible**: `nsys stats test.nsys-rep` shows kernel names and timing
3. **NVTX ranges**: User annotations appear in timeline aligned with GPU kernels
4. **ncu metrics**: `ncu --metrics sm__pipe_tensor_cycles_active.avg.pct_of_peak_sustained_active` reports >0% for FP16 GEMM
5. **Tensor Cores active**: FP16 matrix multiply shows tensor pipe utilization >50%
6. **Memory bandwidth**: dram bytes matches expected data movement (M×K×sizeof(fp16) + K×N×sizeof(fp16))
7. **Multi-GPU**: NCCL operations visible with ring/tree topology and per-link bandwidth

### Quick smoke test

```bash
nsys profile --trace=cuda,nvtx --output=smoke \
  python -c "
import torch, nvtx
with nvtx.annotate('gemm_test'):
    a = torch.randn(4096, 4096, device='cuda', dtype=torch.float16)
    b = torch.mm(a, a)
    torch.cuda.synchronize()
"
nsys stats smoke.nsys-rep
# Verify: kernel name contains 'gemm' or 'hmma'; NVTX range 'gemm_test' present
```

---

## Limitations / Out of Scope

| Item | Status |
|------|--------|
| Open-source | Proprietary; .nsys-rep and .ncu-rep formats not publicly documented |
| Real-time streaming | Batch collection only; no live metrics stream |
| OpenTelemetry integration | None built-in; no OTLP export |
| Non-NVIDIA GPUs | CUDA/CUPTI only; no AMD/Intel support |
| Kernel fusion internals | Fused kernels appear as single unit; individual op timing lost |
| Production continuous profiling | Not designed for always-on; time-limited sessions |
| Multi-node distributed | Per-node collection; cross-node correlation requires external tooling |
| Model architecture protection | Kernel names expose matrix dimensions (e.g., `gemm_4096x4096`) |
| Encrypted trace export | Not provided |
| Job scheduler identity | No concept of Slurm job ID or K8s pod in traces |
| Counter simultaneous collection | Requires kernel replay (counters from different executions) |

---

## Evaluation Assessment

### Observability

**Rating: Strong**

| Aspect | Assessment |
|--------|------------|
| **Strengths** | Complete GPU execution visibility from API call to hardware counter. Nanosecond kernel timing via dedicated GPU timestamp engine. NVTX provides semantic correlation (training step → layer → kernel). cuDNN/cuBLAS/NCCL emit NVTX automatically. Two zoom levels: system-wide timeline (nsys) + per-kernel hardware analysis (ncu). SQLite export enables custom analysis. Roofline analysis built-in. Rules engine provides actionable recommendations. |
| **Gaps** | Proprietary formats require NVIDIA tools. No real-time streaming. No OpenTelemetry bridge. Counter collection requires kernel replay (not representative of production). No cross-node correlation for distributed training. |
| **Implementations must add** | OTLP export, real-time metrics streaming, cross-node trace correlation, production-safe continuous profiling, open trace format support. |

### Security

**Rating: Partial**

| Aspect | Assessment |
|--------|------------|
| **Strengths** | Profiling requires explicit invocation. Admin privileges required for hardware counters. CUPTI can be disabled via environment variables. No always-on telemetry. |
| **Gaps** | Trace files reveal model architecture (kernel names contain dimensions). No encryption of output files. No access control on trace contents. Container profiling requires `--cap-add=SYS_ADMIN` (broad privilege). No audit trail of profiling sessions. Remote profiling relies solely on SSH security. |
| **Implementations must add** | Encrypted trace export, kernel name obfuscation, per-trace access control, profiling session audit log, fine-grained container capabilities. |

### Identity Management

**Rating: Weak**

| Aspect | Assessment |
|--------|------------|
| **Strengths** | PID/TID in trace records. NVTX domains/categories allow user-defined identity. CUDA context ID per process. MIG GPU Instance UUIDs provide hardware partition identity. |
| **Gaps** | No built-in user, job, or model identity. Must manually annotate via NVTX. No Slurm/K8s/scheduler integration. Multi-tenant MPS conflates process identities. No authentication for profiling sessions. |
| **Implementations must add** | Job scheduler identity binding (Slurm job → trace), model/experiment tagging, authenticated profiling sessions, per-tenant trace isolation. |

### Reliability

**Rating: Moderate**

| Aspect | Assessment |
|--------|------------|
| **Strengths** | CUPTI Activity buffers are configurable (overflow detectable). nsys bounds collection with `--duration` and `--buffer-size`. GPU hardware timestamp engine is stable and monotonic. Partial .nsys-rep files recoverable. |
| **Gaps** | CUPTI buffer overflow drops events silently (only OVERHEAD records signal loss). ncu kernel replay hangs on synchronization-dependent kernels. GPU driver bugs can crash profiling. No guaranteed delivery to external systems. Large traces can exceed disk without warning. |
| **Implementations must add** | Buffer overflow alerting, replay hang detection/timeout, disk space pre-check, guaranteed delivery to collectors, graceful degradation under pressure. |

### Accuracy

**Rating: Strong**

| Aspect | Assessment |
|--------|------------|
| **Strengths** | Hardware PM counters measure exact instruction/cycle counts. GPU timestamp engine provides nanosecond resolution. ncu kernel replay with clock locking ensures reproducible measurements. Roofline uses measured values vs architectural peaks. PC sampling provides instruction-level attribution. |
| **Gaps** | Kernel replay changes execution context (warm caches, isolated scheduling). CPU↔GPU clock correlation has 1–10 μs error. Counter multiplexing means metrics from different executions. Very short kernels (<1 μs) have measurement uncertainty. NVTX annotation overhead perturbs timing. |
| **Implementations must add** | Production-representative counter collection (no replay), clock correlation calibration, sub-microsecond cross-domain synchronization, annotation overhead compensation. |

---

## Assessment Summary

| Dimension | Rating | Key Gap |
|-----------|--------|---------|
| Observability | Strong | Proprietary formats; no real-time streaming or OTLP export |
| Security | Partial | Traces expose model architecture; no encryption or audit trail |
| Identity | Weak | No job/model/tenant identity; requires manual NVTX annotation |
| Reliability | Moderate | Buffer overflow silent; kernel replay can hang |
| Accuracy | Strong | Replay context differs from production; CPU↔GPU clock skew |
