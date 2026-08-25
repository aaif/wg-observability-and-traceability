# AAIF Reference Architecture: PyTorch Profiler

| Field | Value |
|-------|-------|
| **Subject** | [PyTorch Profiler](https://pytorch.org/docs/stable/profiler.html) |
| **Version** | PyTorch 2.x+ |
| **Date** | 2026-06-25 |

---

## Objective

Demonstrates how PyTorch's built-in profiler captures the full execution path of tensor operations — from Python-level op dispatch through C++ ATen backend to GPU kernel execution — producing Chrome Trace JSON for timeline visualization and enabling correlation between framework-level semantics (model layers, optimizer steps) and hardware execution (CUDA/HIP kernels, memory transfers, collective communication).

---

## Scope / Zoom Level

**Orchestration layer — from Python model code through framework dispatch to GPU execution.**

PyTorch Profiler bridges the gap between AI framework semantics (which layer, which op, which tensor shape) and hardware execution (which GPU kernel, how long, how much memory). It produces standardized Chrome Trace Format JSON consumable by chrome://tracing, Perfetto, TensorBoard, and Holistic Trace Analysis (HTA).

---

## Prerequisites

| Component | Version | Notes |
|-----------|---------|-------|
| PyTorch | 2.x+ | `torch.profiler` module |
| CUDA Toolkit | 12.x+ (NVIDIA) | For CUDA activity tracing via CUPTI |
| ROCm | 6.x+ (AMD) | For HIP activity tracing via roctracer |
| TensorBoard | 2.x+ (optional) | For visualization via `tensorboard_trace_handler` |
| Kineto | Bundled with PyTorch | Underlying tracing library (wraps CUPTI/roctracer) |
| GPU | Any CUDA/ROCm-supported | CPU-only profiling also supported |

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    Python User Code                                           │
│                                                                             │
│  with torch.profiler.profile(...) as prof:                                  │
│      output = model(input)       # forward                                  │
│      loss.backward()             # backward                                 │
│      optimizer.step()            # optimizer                                │
│      prof.step()                 # marks iteration boundary                 │
└────────────────────────────────────┬────────────────────────────────────────┘
                                     │
┌────────────────────────────────────▼────────────────────────────────────────┐
│                    PyTorch Dispatcher (ATen)                                  │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  RecordFunction callbacks (profiler hooks at every op dispatch)        │  │
│  │  Captures: op name, input shapes, input dtypes, stack trace          │  │
│  └──────────────────────────────┬───────────────────────────────────────┘  │
│                                 │                                            │
│  ┌──────────────┐  ┌───────────▼──────────┐  ┌──────────────────────┐    │
│  │ CPU ops      │  │ GPU kernel launch    │  │ Memory allocator     │    │
│  │ (aten::mm,   │  │ (cuLaunchKernel /    │  │ (CUDACachingAlloc)   │    │
│  │  aten::add)  │  │  hipLaunchKernel)    │  │                      │    │
│  └──────┬───────┘  └───────────┬──────────┘  └──────────┬───────────┘    │
└─────────┼───────────────────────┼────────────────────────┼──────────────────┘
          │                       │                        │
┌─────────▼───────────────────────▼────────────────────────▼──────────────────┐
│                    Kineto (Tracing Backend)                                   │
│                                                                             │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────┐    │
│  │ CPU events       │  │ GPU events       │  │ Memory events        │    │
│  │ (start/end ts,   │  │ (CUPTI Activity  │  │ (alloc/free,         │    │
│  │  thread, stack)  │  │  or roctracer)   │  │  bytes, device)      │    │
│  └────────┬─────────┘  └────────┬─────────┘  └──────────┬───────────┘    │
│           │                     │                        │                  │
│  ┌────────▼─────────────────────▼────────────────────────▼───────────────┐ │
│  │  Correlation Engine                                                    │ │
│  │  Links CPU op → GPU kernel via CUPTI correlation_id                   │ │
│  │  Links op → memory allocation via pointer tracking                    │ │
│  │  Links NCCL call → collective GPU kernel                              │ │
│  └────────────────────────────────┬──────────────────────────────────────┘ │
└───────────────────────────────────┼─────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    Output (Chrome Trace JSON)                                 │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │  { "traceEvents": [                                                    │ │
│  │    { "name": "aten::mm", "cat": "cpu_op", "ph": "X", ... },           │ │
│  │    { "name": "volta_fp16_s884gemm_...", "cat": "kernel", "ph":"X"..}, │ │
│  │    { "name": "[memory]", "cat": "gpu_mem", ... },                      │ │
│  │    { "name": "nccl:allReduce", "cat": "gpu_op", ... }                 │ │
│  │  ] }                                                                   │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│  Consumers: chrome://tracing, Perfetto, TensorBoard, HTA                   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Instrumentation Walkthrough

### What is captured

| Category | Events | Fields |
|----------|--------|--------|
| **CPU ops** | Every ATen operation (aten::mm, aten::add, aten::linear, ...) | Name, start/end μs, thread, input shapes, input dtypes, call stack |
| **GPU kernels** | Every launched kernel | Name, start/end μs (GPU clock), device, stream, grid/block dims, shared mem, registers |
| **Memory** | CUDA/HIP allocations and frees | Bytes, device, address, allocator (caching vs raw) |
| **Communication** | NCCL/RCCL/Gloo collectives | Op type (AllReduce/Broadcast/...), data size, ranks |
| **User annotations** | `record_function` / `torch.profiler.record_function` | User-defined name, start/end |
| **Module hierarchy** | `nn.Module` forward calls (with `with_modules=True`) | Module class name, parameter count |
| **Flops** | Estimated FLOPs per op (with `with_flops=True`) | FLOPs count per operation |

### The mechanism

1. **RecordFunction hooks**: PyTorch's dispatcher calls registered `RecordFunction` callbacks at every op entry/exit. The profiler registers hooks that capture: op name, input tensor metadata (shapes, dtypes, device), and wall-clock timestamps.

2. **Kineto (CUPTI/roctracer backend)**: When `ProfilerActivity.CUDA` is enabled, Kineto activates CUPTI Activity API (NVIDIA) or roctracer (AMD) to collect GPU-side kernel execution timestamps asynchronously.

3. **Correlation**: CUPTI/roctracer provide `correlation_id` linking each GPU kernel back to the CPU-side launch call. Kineto uses this to connect `aten::mm` (CPU) → `volta_fp16_s884gemm_*` (GPU).

4. **Memory tracking**: The CUDA Caching Allocator reports allocation/free events with size and address.

5. **Export**: All events are serialized to Chrome Trace Format JSON — an array of `traceEvents` objects with standard fields (`name`, `cat`, `ph`, `ts`, `dur`, `pid`, `tid`, `args`).

### The profiler API

```python
import torch
from torch.profiler import profile, ProfilerActivity, schedule, tensorboard_trace_handler

# Full-featured profiling with schedule
with profile(
    activities=[ProfilerActivity.CPU, ProfilerActivity.CUDA],
    schedule=schedule(wait=1, warmup=1, active=3, repeat=2),
    on_trace_ready=tensorboard_trace_handler("./log/profiler"),
    record_shapes=True,
    profile_memory=True,
    with_stack=True,
    with_flops=True,
    with_modules=True,
) as prof:
    for step in range(20):
        train_step(model, batch)
        prof.step()

# Simple one-shot profiling
with profile(activities=[ProfilerActivity.CPU, ProfilerActivity.CUDA]) as prof:
    model(input)

# Export to Chrome trace JSON
prof.export_chrome_trace("trace.json")

# Print summary table
print(prof.key_averages().table(sort_by="cuda_time_total", row_limit=10))

# Print with input shapes
print(prof.key_averages(group_by_input_shape=True).table(sort_by="cuda_time_total"))
```

### Data format produced

**Chrome Trace Format JSON** — the standard format for chrome://tracing and Perfetto UI:

```json
{
  "schemaVersion": 1,
  "traceEvents": [
    {"ph": "X", "cat": "cpu_op", "name": "...", "ts": ..., "dur": ..., "pid": ..., "tid": ..., "args": {...}},
    {"ph": "X", "cat": "kernel", "name": "...", "ts": ..., "dur": ..., "pid": ..., "tid": ..., "args": {...}},
    ...
  ]
}
```

Event phases: `X` (complete event with duration), `B`/`E` (begin/end pair), `i` (instant), `M` (metadata).

---

## Sample Trace Output

### Chrome Trace JSON (complete example)

```json
{
  "schemaVersion": 1,
  "traceEvents": [
    {
      "ph": "X",
      "cat": "cpu_op",
      "name": "aten::linear",
      "pid": 12345,
      "tid": 1,
      "ts": 1000000,
      "dur": 85,
      "args": {
        "Input Dims": [[32, 4096], [4096, 4096], [4096]],
        "Input type": ["Float16", "Float16", "Float16"],
        "Concrete Inputs": "",
        "Fwd thread id": 1
      }
    },
    {
      "ph": "X",
      "cat": "cpu_op",
      "name": "aten::mm",
      "pid": 12345,
      "tid": 1,
      "ts": 1000012,
      "dur": 45,
      "args": {
        "Input Dims": [[32, 4096], [4096, 4096]],
        "Input type": ["Float16", "Float16"],
        "Ev Idx": 42
      }
    },
    {
      "ph": "X",
      "cat": "kernel",
      "name": "ampere_fp16_s1688gemm_fp16_128x256_ldg8_f2f_stages_32x5_tn",
      "pid": 12345,
      "tid": 7,
      "ts": 1000025,
      "dur": 218,
      "args": {
        "device": 0,
        "stream": 7,
        "grid": [16, 1, 1],
        "block": [128, 1, 1],
        "shared memory": 99328,
        "registers per thread": 128,
        "est. achieved occupancy %": 75,
        "correlation": 42,
        "external id": 42
      }
    },
    {
      "ph": "X",
      "cat": "gpu_memcpy",
      "name": "Memcpy HtoD (Pageable -> Device)",
      "pid": 12345,
      "tid": 8,
      "ts": 999000,
      "dur": 1200,
      "args": {
        "device": 0,
        "stream": 7,
        "bytes": 67108864,
        "bandwidth (GB/s)": 12.4
      }
    },
    {
      "ph": "X",
      "cat": "kernel",
      "name": "ncclKernel_AllReduce_RING_LL_Sum_fp16",
      "pid": 12345,
      "tid": 9,
      "ts": 1001000,
      "dur": 1450,
      "args": {
        "device": 0,
        "stream": 15,
        "grid": [108, 1, 1],
        "block": [512, 1, 1],
        "correlation": 45
      }
    },
    {
      "ph": "i",
      "cat": "gpu_mem",
      "name": "[memory]",
      "pid": 12345,
      "tid": 0,
      "ts": 1000000,
      "s": "g",
      "args": {
        "Device Type": 1,
        "Device Id": 0,
        "Bytes": 67108864,
        "Total Allocated": 2147483648,
        "Total Reserved": 4294967296
      }
    },
    {
      "ph": "X",
      "cat": "user_annotation",
      "name": "training_step",
      "pid": 12345,
      "tid": 1,
      "ts": 999500,
      "dur": 5000
    }
  ]
}
```

### prof.key_averages() table output

```
---------------------------------  ------------  ------------  ------------  ------------  ------------
                             Name    Self CPU %      Self CPU   CPU total %     CPU total  CUDA total
---------------------------------  ------------  ------------  ------------  ------------  ------------
                      aten::linear         0.5%      45.000us        35.2%       3.200ms       3.100ms
                          aten::mm         0.3%      28.000us        12.8%       1.164ms       1.090ms
          aten::native_batch_norm         0.2%      18.000us         8.4%     764.000us     712.000us
                    aten::addmm            0.2%      15.000us         6.2%     564.000us     534.000us
               aten::_log_softmax         0.1%       9.000us         3.1%     282.000us     267.000us
    autograd::engine::evaluate_f…         2.1%     191.000us        24.5%       2.228ms       2.100ms
               ncclKernel_AllRed…         0.0%       0.000us         0.0%       0.000us       1.450ms
---------------------------------  ------------  ------------  ------------  ------------  ------------
Self CPU time total: 9.091ms
Self CUDA time total: 8.543ms
```

### prof.key_averages(group_by_input_shape=True) output

```
-------  -------  --------  ------------------  -------  ----------
   Name  CPU tot  CUDA tot  Input Shapes        # Calls  FLOPS
-------  -------  --------  ------------------  -------  ----------
aten::mm  1.16ms   1.09ms  [[32,4096],[4096,4096]]  10  10737418240
aten::mm  0.58ms   0.54ms  [[32,4096],[4096,1024]]   5   1342177280
aten::mm  0.29ms   0.27ms  [[32,1024],[1024,4096]]   5   1342177280
aten::add  0.12ms  0.11ms  [[32,4096],[32,4096]]     10   262144
-------  -------  --------  ------------------  -------  ----------
```

---

## Cost Profile

### LLM token cost

**Not directly applicable**, but PyTorch Profiler is the standard tool for measuring LLM training throughput (tokens/sec), identifying bottlenecks in transformer attention/FFN, and quantifying NCCL communication overhead in distributed training.

### Compute/IO overhead per operation

| Configuration | Overhead | Production Safe? |
|--------------|----------|-----------------|
| CPU ops only (`ProfilerActivity.CPU`) | 3–8% | Conditional |
| CPU + CUDA (`ProfilerActivity.CUDA`) | 5–12% | Time-limited only |
| + `record_shapes=True` | +1–3% | Yes (small tensors add overhead) |
| + `with_stack=True` | +5–15% | No (Python stack unwinding expensive) |
| + `profile_memory=True` | +1–2% | Yes |
| + `with_flops=True` | +0.5% | Yes |
| + `with_modules=True` | +1% | Yes |
| Schedule (wait/warmup/active) | Active period only | Yes (designed for production) |

### Storage growth rate

| Configuration | Size per Step | Notes |
|--------------|--------------|-------|
| Basic (CPU+CUDA, 1 GPU) | 0.5–2 MB/step | Depends on model op count |
| Full (shapes+stack+memory, 1 GPU) | 2–10 MB/step | Stack traces dominate size |
| Distributed (8 GPUs, full) | 10–50 MB/step | Linear with rank count |
| Typical training run (100 steps profiled) | 50–500 MB | Bounded by schedule |

---

## Validation Criteria

1. **Trace produced**: `prof.export_chrome_trace("trace.json")` creates valid JSON file
2. **CPU ops present**: Trace contains `"cat": "cpu_op"` events with `aten::` names
3. **GPU kernels present**: Trace contains `"cat": "kernel"` events with GPU kernel names
4. **Correlation works**: CPU op's `"Ev Idx"` matches GPU kernel's `"correlation"` field
5. **Shapes captured**: With `record_shapes=True`, `"Input Dims"` shows tensor dimensions
6. **Memory tracked**: With `profile_memory=True`, `"[memory]"` events show allocation bytes
7. **Timeline valid**: Opening `trace.json` in chrome://tracing shows CPU and GPU rows with aligned events
8. **NCCL visible**: In distributed training, collective kernels (ncclKernel_*) appear in GPU timeline

### Quick smoke test

```bash
python -c "
import torch
from torch.profiler import profile, ProfilerActivity

model = torch.nn.Linear(4096, 4096).cuda().half()
x = torch.randn(32, 4096, device='cuda', dtype=torch.float16)

with profile(activities=[ProfilerActivity.CPU, ProfilerActivity.CUDA], record_shapes=True) as prof:
    for _ in range(5):
        y = model(x)
    torch.cuda.synchronize()

prof.export_chrome_trace('/tmp/pytorch_trace.json')
print(prof.key_averages().table(sort_by='cuda_time_total', row_limit=5))
"
# Verify: table shows aten::mm/aten::linear with CUDA time > 0
# Verify: /tmp/pytorch_trace.json is valid JSON with traceEvents array
python -c "import json; d=json.load(open('/tmp/pytorch_trace.json')); print(f'{len(d[\"traceEvents\"])} events')"
```

---

## Limitations / Out of Scope

| Item | Status |
|------|--------|
| Hardware PM counters (tensor utilization %) | Not captured; use Nsight Compute / rocprof for that |
| Kernel-level roofline analysis | Not provided; use Nsight Compute / Omniperf |
| Always-on production profiling | Not designed for continuous use; schedule API bounds collection |
| Non-PyTorch frameworks | PyTorch-specific; TensorFlow has its own profiler |
| Cross-node distributed correlation | Per-rank traces; must merge externally (HTA does this) |
| Binary/compact format | JSON only (large files); no binary equivalent |
| Real-time streaming | Batch export only; no live trace viewing |
| Op-level GPU counter attribution | Cannot attribute hardware counters to individual ops (only kernel timing) |
| Custom kernel internals | Fused/compiled kernels (TorchInductor/Triton) appear as opaque blocks |
| Model architecture protection | Trace exposes full op graph, tensor shapes, and layer structure |
| Encrypted export | Not provided |

---

## Evaluation Assessment

### Observability

**Rating: Strong**

| Aspect | Assessment |
|--------|------------|
| **Strengths** | Unique ability to correlate framework semantics (model layers, op names, tensor shapes) with GPU execution (kernel names, timing). Chrome Trace JSON is a standard format viewable in multiple tools (chrome://tracing, Perfetto, TensorBoard). Schedule API enables bounded profiling of production training. Input shape grouping identifies which tensor dimensions drive compute cost. FLOPS estimation per op. Memory tracking identifies allocation patterns. NCCL/RCCL collectives visible for distributed training analysis. Module hierarchy shows model structure. |
| **Gaps** | No hardware PM counters (can't see tensor core utilization %). No roofline analysis. JSON format is verbose and large. No real-time streaming. Fused kernels (TorchInductor) obscure individual op timing. No built-in anomaly detection or regression alerts. |
| **Implementations must add** | Hardware counter integration (combine with Nsight/rocprof), compact binary trace format, real-time streaming, automatic performance regression detection, kernel fusion transparency. |

### Security

**Rating: Weak**

| Aspect | Assessment |
|--------|------------|
| **Strengths** | Profiling requires explicit code instrumentation (opt-in). Schedule API limits collection window. No daemon or always-on collection. |
| **Gaps** | Trace JSON exposes complete model architecture: every op, every tensor shape, every layer name. This is the full model graph in readable form. No encryption of trace files. No access control. No redaction of sensitive shapes/names. Any user with file access can reconstruct model architecture. Stack traces expose source file paths. |
| **Implementations must add** | Trace encryption, shape/name redaction options, access-controlled trace storage, model IP classification of trace data, secure trace sharing (strip sensitive fields). |

### Identity Management

**Rating: Weak**

| Aspect | Assessment |
|--------|------------|
| **Strengths** | PID/TID in every event. User annotations (`record_function`) can encode arbitrary identity. `prof.step()` marks iteration boundaries. Module names provide model structure identity. |
| **Gaps** | No concept of training job identity, user identity, or experiment identity in the trace format. No binding to Slurm/K8s job. No model version or experiment tracking integration. No multi-user awareness. Distributed traces have no cross-rank correlation ID built-in. |
| **Implementations must add** | Experiment/run ID in trace metadata, job scheduler identity binding, model version tagging, cross-rank correlation IDs, integration with experiment tracking (MLflow/W&B). |

### Reliability

**Rating: Moderate**

| Aspect | Assessment |
|--------|------------|
| **Strengths** | Schedule API (wait/warmup/active/repeat) prevents unbounded collection. `on_trace_ready` callback enables streaming export per window. CUPTI buffer management handled by Kineto. Partial traces still valid JSON. Profiler errors don't crash training (graceful degradation). |
| **Gaps** | Large models can produce multi-GB traces that exhaust memory/disk. CUPTI buffer overflow drops GPU events silently. No built-in compression. No delivery guarantee to external systems. Long training runs with always-active profiling will degrade throughput and storage. JSON serialization is single-threaded and can stall. |
| **Implementations must add** | Compressed trace output, buffer overflow alerting, disk space pre-check, async JSON serialization, guaranteed delivery to trace collectors, automatic trace rotation. |

### Accuracy

**Rating: Moderate**

| Aspect | Assessment |
|--------|------------|
| **Strengths** | CPU timestamps from `clock_gettime` (nanosecond precision). GPU timestamps from hardware timestamp engines via CUPTI/roctracer. Correlation IDs provide exact CPU→GPU linkage. Input shapes are exact (not estimated). FLOPS calculated from known op semantics + shapes. |
| **Gaps** | CPU↔GPU clock synchronization has 1–10 μs error (cross-domain correlation imprecise for short ops). Profiling overhead distorts timing of very short ops. `with_stack=True` adds latency that shifts timestamps. FLOPS are theoretical (don't account for padding, alignment, or actual hardware efficiency). Fused kernels attribute all time to a single op. Memory events may miss sub-allocator activity (caching allocator batches). |
| **Implementations must add** | Clock domain calibration, overhead-compensated timestamps, actual (not theoretical) FLOPS measurement, per-op attribution within fused kernels, sub-allocator tracking. |

---

## Assessment Summary

| Dimension | Rating | Key Gap |
|-----------|--------|---------|
| Observability | Strong | No hardware counters; JSON verbose; no real-time streaming |
| Security | Weak | Trace fully exposes model architecture and tensor shapes |
| Identity | Weak | No job/experiment/user identity in trace format |
| Reliability | Moderate | Multi-GB traces possible; CUPTI buffer overflow silent |
| Accuracy | Moderate | CPU↔GPU clock skew; profiling overhead distorts short ops |
