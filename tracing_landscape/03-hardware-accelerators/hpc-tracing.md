# AAIF Reference Architecture: HPC Tracing Tools (Vampir, Luthier, Intel PIN)

| Field | Value |
|-------|-------|
| **Subject** | [Vampir](https://vampir.eu/) / [Luthier (AMD)](https://github.com/ROCm/luthier) / [Intel PIN](https://www.intel.com/content/www/us/en/developer/articles/tool/pin-a-dynamic-binary-instrumentation-tool.html) |
| **Version** | Vampir 10.x / Luthier 0.x / PIN 3.x |
| **Date** | 2026-08-21 |

---

## Objective

Assess three complementary HPC tracing tools — Intel PIN (CPU instruction-level dynamic binary instrumentation), AMD Luthier (GPU ISA-level dynamic binary instrumentation), and Vampir (scalable post-mortem trace visualization) — as the deep hardware/instruction-level tracing layer for AI agent infrastructure, enabling deterministic replay, micro-architectural analysis, and performance visualization across CPU and GPU execution domains.

---

## Scope / Zoom Level

**Primitive layer — instruction-level and GPU kernel-level tracing with post-mortem visualization.**

These tools operate at the deepest instrumentation levels available:

- **Intel PIN**: Intercepts and re-compiles every CPU instruction at runtime via JIT, inserting arbitrary analysis callbacks. This is below kernel tracing (FTrace/LTTng observe function boundaries) and below hardware tracing (Intel PT records branches passively). PIN actively transforms the instruction stream.
- **AMD Luthier**: Performs the equivalent operation for AMD GPU ISA — intercepting, lifting, and patching GPU kernel binaries at the HSA AQL dispatch level. This is below rocprofiler (which observes API calls and hardware counters) and provides instruction-granularity GPU instrumentation.
- **Vampir**: Consumes OTF2 traces produced by Score-P, TAU, or custom collectors and renders them as interactive timelines, communication matrices, and statistical profiles. Handles billions of events across 100k+ processes. This is the visualization layer that makes the raw trace data comprehensible.

Together they form a complete pipeline: PIN/Luthier generate instruction-level traces → traces are written in standard formats → Vampir visualizes at scale.

---

## Prerequisites

| Component | Version / Pinned | Notes |
|-----------|-----------------|-------|
| **Intel PIN** | | |
| CPU | Intel x86/x86-64 | Works on Core/Xeon; limited AMD support for basic features |
| OS | Linux, Windows, macOS | Full support on Linux; most Pintools target Linux |
| PIN SDK | 3.x (latest: 3.28+) | Download from Intel; part of oneAPI toolkit |
| C++ compiler | GCC 7+ or MSVC 2019+ | Required to build Pintools |
| Target binary | Any x86/x86-64 ELF/PE | No recompilation needed; works on stripped binaries |
| **AMD Luthier** | | |
| GPU | AMD CDNA/RDNA (GFX9+) | MI100, MI200, MI250X, MI300X, RX 7000 series |
| ROCm | 6.x+ | Requires HSA runtime and amdgpu driver |
| OS | Linux (Ubuntu 22.04+, RHEL 9+) | ROCm-supported distributions only |
| Luthier | 0.x (GitHub main branch) | Early-stage; build from source |
| CMake | 3.21+ | Build system requirement |
| **Vampir** | | |
| Trace format | OTF2 (Open Trace Format 2) | Produced by Score-P, TAU, or direct OTF2 API |
| Score-P | 8.x+ (recommended collector) | Instruments MPI, OpenMP, CUDA, HIP, SYCL |
| Vampir GUI | 10.x | Commercial license; academic licenses available |
| VampirServer | 10.x (optional) | Parallel analysis for traces > 10 GB |
| MPI runtime | Any (for VampirServer) | Distributed trace analysis across cluster nodes |
| **Common** | | |
| Storage | Proportional to trace size | PIN: GB/min; Luthier: GB/min; Vampir reads OTF2 (GB-TB) |
| Memory | 8+ GB for analysis tools | VampirServer distributes memory across nodes |

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        APPLICATION LAYER                                     │
│                                                                             │
│   ┌──────────────────────┐          ┌──────────────────────┐               │
│   │  CPU Application     │          │  GPU Kernels         │               │
│   │  (x86/x86-64 code)  │          │  (AMD GCN/CDNA ISA)  │               │
│   └──────────┬───────────┘          └──────────┬───────────┘               │
│              │                                  │                           │
└──────────────┼──────────────────────────────────┼───────────────────────────┘
               │                                  │
               ▼                                  ▼
┌──────────────────────────────┐  ┌──────────────────────────────────────────┐
│  INTEL PIN (CPU DBI)         │  │  AMD LUTHIER (GPU DBI)                   │
│                              │  │                                          │
│  ┌────────────────────────┐  │  │  ┌────────────────────────────────────┐  │
│  │ JIT Engine             │  │  │  │ HSA Intercept Layer                │  │
│  │ ┌──────────────────┐   │  │  │  │ ┌────────────────────────────┐     │  │
│  │ │ Fetch original   │   │  │  │  │ │ Intercept AQL dispatch     │     │  │
│  │ │ instructions     │   │  │  │  │ │ packets                    │     │  │
│  │ ├──────────────────┤   │  │  │  │ ├────────────────────────────┤     │  │
│  │ │ Insert analysis  │   │  │  │  │ │ Lift GPU ISA to IR         │     │  │
│  │ │ callbacks        │   │  │  │  │ ├────────────────────────────┤     │  │
│  │ │ (INS_InsertCall) │   │  │  │  │ │ Inject instrumentation     │     │  │
│  │ ├──────────────────┤   │  │  │  │ │ (plugin callbacks)         │     │  │
│  │ │ Re-compile &     │   │  │  │  │ ├────────────────────────────┤     │  │
│  │ │ execute          │   │  │  │  │ │ Lower back to GPU ISA      │     │  │
│  │ └──────────────────┘   │  │  │  │ │ & dispatch to HW           │     │  │
│  └────────────────────────┘  │  │  │ └────────────────────────────┘     │  │
│                              │  │  └────────────────────────────────────┘  │
│  Granularity:                │  │                                          │
│  • Instruction               │  │  Granularity:                            │
│  • Basic block               │  │  • GPU ISA instruction                   │
│  • Routine / Image           │  │  • Kernel launch                         │
│  • Syscall / Thread          │  │  • Memory copy / Barrier                 │
│                              │  │                                          │
│  Output: Custom trace files  │  │  Output: Plugin-defined trace data       │
│  (text, binary, CTF, etc.)   │  │  (counters, memory traces, etc.)         │
└──────────────┬───────────────┘  └──────────────────┬───────────────────────┘
               │                                      │
               ▼                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         TRACE DATA LAYER                                     │
│                                                                             │
│   ┌─────────────────┐  ┌──────────────┐  ┌────────────────────────────┐    │
│   │ PIN trace files │  │ Luthier data │  │ Score-P / TAU collectors   │    │
│   │ (custom format) │  │ (plugin fmt) │  │ (MPI, OpenMP, CUDA, HIP)  │    │
│   └────────┬────────┘  └──────┬───────┘  └─────────────┬──────────────┘    │
│            │                   │                        │                   │
│            ▼                   ▼                        ▼                   │
│   ┌────────────────────────────────────────────────────────────────┐        │
│   │                    OTF2 (Open Trace Format 2)                  │        │
│   │         Unified trace format for HPC performance data          │        │
│   └───────────────────────────────┬────────────────────────────────┘        │
│                                   │                                         │
└───────────────────────────────────┼─────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  VAMPIR (Visualization & Analysis)                                           │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  VampirServer (distributed analysis engine)                           │  │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐    │  │
│  │  │  Worker 0   │ │  Worker 1   │ │  Worker 2   │ │  Worker N   │    │  │
│  │  │  (rank 0)   │ │  (rank 1)   │ │  (rank 2)   │ │  (rank N)   │    │  │
│  │  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘    │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  GUI Displays:                                                              │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐      │
│  │  Master      │ │ Communication│ │  Function    │ │  Call Tree   │      │
│  │  Timeline    │ │  Matrix      │ │  Summary     │ │  Profile     │      │
│  │  (Gantt)     │ │  (P2P msgs)  │ │  (% time)   │ │  (hierarchy) │      │
│  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘      │
│  ┌──────────────┐ ┌──────────────┐                                         │
│  │  Counter     │ │  I/O View    │                                         │
│  │  Data        │ │  (file ops)  │                                         │
│  └──────────────┘ └──────────────┘                                         │
│                                                                             │
│  Scale: billions of events, 100k+ processes                                 │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Instrumentation Walkthrough

### Intel PIN: JIT-Based Dynamic Binary Instrumentation

PIN operates as a process-level virtual machine that intercepts, decompiles, instruments, and re-executes every instruction in the target application:

**1. Process Attach / Launch**

```bash
# PIN launches or attaches to target process
$ pin -t my_pintool.so -- ./target_application --args
```

PIN takes control before `_start` executes. The application never runs natively — every instruction passes through PIN's JIT engine.

**2. JIT Compilation Pipeline**

```
Original code       PIN JIT              Instrumented code (code cache)
─────────────       ───────              ───────────────────────────────
mov rax, [rbx]  →  Fetch trace      →   [analysis call: RecordMemRead(rbx)]
add rax, rcx       (basic block)        mov rax, [rbx]
cmp rax, 0         Insert callbacks     add rax, rcx
jz  target         Re-encode            cmp rax, 0
                                        [analysis call: RecordBranch(target)]
                                        jz  instrumented_target
```

**3. Pintool Registration (C++ API)**

```cpp
#include "pin.H"

// Called for every instruction in the binary
VOID Instruction(INS ins, VOID *v) {
    // Insert call before every memory read
    if (INS_IsMemoryRead(ins)) {
        INS_InsertCall(ins, IPOINT_BEFORE,
            (AFUNPTR)RecordMemRead,
            IARG_INST_PTR,           // instruction address
            IARG_MEMORYREAD_EA,      // effective address
            IARG_MEMORYREAD_SIZE,    // access size
            IARG_END);
    }
}

// Called for every routine (function)
VOID Routine(RTN rtn, VOID *v) {
    RTN_Open(rtn);
    RTN_InsertCall(rtn, IPOINT_BEFORE,
        (AFUNPTR)RecordFunctionEntry,
        IARG_ADDRINT, RTN_Address(rtn),
        IARG_PTR, RTN_Name(rtn).c_str(),
        IARG_END);
    RTN_Close(rtn);
}

int main(int argc, char *argv[]) {
    PIN_Init(argc, argv);
    INS_AddInstrumentFunction(Instruction, 0);
    RTN_AddInstrumentFunction(Routine, 0);
    PIN_AddSyscallEntryFunction(SyscallEntry, 0);
    PIN_StartProgram();  // Never returns
    return 0;
}
```

**4. Callback Granularity Levels**

| Level | API | Frequency | Use Case |
|-------|-----|-----------|----------|
| Instruction | `INS_InsertCall` | Every instruction | Cache simulation, taint analysis |
| Basic block | `TRACE_InsertCall` | Every BBL entry | Coverage, hot path detection |
| Routine | `RTN_InsertCall` | Function entry/exit | Call graph, function timing |
| Image | `IMG_AddInstrumentFunction` | Library load/unload | Module tracking |
| Syscall | `PIN_AddSyscallEntryFunction` | Every syscall | I/O tracing, security monitoring |
| Thread | `PIN_AddThreadStartFunction` | Thread create/exit | Concurrency analysis |
| Context switch | `PIN_AddContextChangeFunction` | Signal delivery | Signal handling analysis |

---

### AMD Luthier: GPU ISA Dynamic Binary Instrumentation

Luthier performs for AMD GPUs what PIN does for CPUs — intercepting and instrumenting GPU kernel code at the ISA level:

**1. Plugin Architecture**

```
┌─────────────────────────────────────────────────────────┐
│  HIP Application                                        │
│  hipLaunchKernelGGL(myKernel, grid, block, ...)         │
└──────────────────────────┬──────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│  Luthier HSA Intercept Layer                            │
│  ┌───────────────────────────────────────────────────┐  │
│  │ 1. Intercept hsa_queue_submit (AQL packet)        │  │
│  │ 2. Extract kernel code object from dispatch       │  │
│  │ 3. Lift GPU ISA → Luthier IR                      │  │
│  │ 4. Call plugin instrumentation hooks               │  │
│  │ 5. Lower Luthier IR → patched GPU ISA             │  │
│  │ 6. Submit patched kernel to hardware queue        │  │
│  └───────────────────────────────────────────────────┘  │
└──────────────────────────┬──────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│  AMD GPU Hardware (GFX9/GFX10/GFX11)                    │
│  Executes instrumented kernel ISA                       │
└─────────────────────────────────────────────────────────┘
```

**2. Plugin API (Conceptual)**

```cpp
#include "luthier/luthier.h"

class MemoryTracer : public luthier::InstrumentationPlugin {
public:
    void instrument_kernel(luthier::KernelIR &kernel) override {
        for (auto &bb : kernel.basic_blocks()) {
            for (auto &inst : bb.instructions()) {
                // Instrument every global memory access
                if (inst.is_global_load() || inst.is_global_store()) {
                    // Insert callback before the memory operation
                    bb.insert_before(inst,
                        luthier::make_callback(
                            &MemoryTracer::on_memory_access,
                            inst.address(),
                            inst.memory_operand(),
                            inst.is_global_store()
                        ));
                }
            }
        }
    }

    void on_memory_access(uint64_t pc, uint64_t addr, bool is_write) {
        // Record to per-wavefront trace buffer
        trace_buffer_->record(pc, addr, is_write, get_wavefront_id());
    }
};

LUTHIER_REGISTER_PLUGIN(MemoryTracer);
```

**3. HSA/AQL Level Operation**

| Stage | What Happens | Technical Detail |
|-------|-------------|-----------------|
| Intercept | Luthier hooks `hsa_queue_submit` | Interposes on HSA runtime API |
| Extract | Reads kernel code object from AQL dispatch packet | Accesses `kernel_object` field in `hsa_kernel_dispatch_packet_t` |
| Lift | Disassembles GCN/CDNA ISA into Luthier IR | Handles VALU, SALU, VMEM, SMEM, DS, EXP instructions |
| Instrument | Plugin callbacks modify IR | Can insert counters, memory traces, divergence tracking |
| Lower | Re-assembles patched IR to GPU ISA | Manages register allocation for instrumentation overhead |
| Dispatch | Submits patched kernel to HW queue | Transparent to application; same AQL queue mechanism |

---

### Vampir: Post-Mortem OTF2 Trace Visualization

Vampir does not generate traces — it consumes and visualizes them. The collection pipeline uses Score-P:

**1. Trace Collection with Score-P**

```bash
# Instrument and run MPI+OpenMP application
$ scorep-gcc -o my_app my_app.c -lm -fopenmp
$ export SCOREP_ENABLE_TRACING=true
$ export SCOREP_TOTAL_MEMORY=256MB
$ export SCOREP_EXPERIMENT_DIRECTORY=trace_output
$ mpirun -np 64 ./my_app

# Produces: trace_output/traces.otf2 + per-rank trace files
$ ls trace_output/
traces.otf2           # anchor file (metadata + definitions)
traces/               # per-rank trace data files
  0.evt               # events for rank 0
  1.evt               # events for rank 1
  ...
  63.evt              # events for rank 63
```

**2. Vampir GUI Load and Exploration**

```
File → Open: trace_output/traces.otf2

Vampir Display Panels:
┌────────────────────────────────────────────────────────────────┐
│ Master Timeline (Gantt chart - all processes)                  │
│ ┌──────────────────────────────────────────────────────────┐   │
│ │ Rank 0  ████████░░░████████████░░░████████░░░████        │   │
│ │ Rank 1  ░░░████████████░░░████████░░░████████████        │   │
│ │ Rank 2  ████░░░████████████░░░████████░░░████████        │   │
│ │ Rank 3  ░░░████████░░░████████████░░░████████████        │   │
│ │         ↕ message arrows between ranks                   │   │
│ └──────────────────────────────────────────────────────────┘   │
│ Legend: ████ = compute  ░░░ = MPI wait  ─── = message          │
├────────────────────────────────────────────────────────────────┤
│ Communication Matrix          │ Function Summary               │
│ ┌─────────────────────────┐   │ ┌───────────────────────────┐ │
│ │   0  1  2  3            │   │ │ matmul()        42.3%     │ │
│ │ 0 ·  █  ░  ░            │   │ │ MPI_Allreduce() 23.1%     │ │
│ │ 1 █  ·  █  ░            │   │ │ attention()     18.7%     │ │
│ │ 2 ░  █  ·  █            │   │ │ MPI_Wait()      12.4%     │ │
│ │ 3 ░  ░  █  ·            │   │ │ other            3.5%     │ │
│ └─────────────────────────┘   │ └───────────────────────────┘ │
│ (msg volume between ranks)    │ (exclusive time per function)  │
└────────────────────────────────────────────────────────────────┘
```

**3. VampirServer for Large-Scale Traces**

```bash
# Launch parallel analysis engine on cluster
$ mpirun -np 16 vampirserver start
VampirServer listening on node01:30000

# Connect GUI to distributed backend
# File → Open Remote: node01:30000 → trace_output/traces.otf2
# VampirServer distributes OTF2 reading across 16 MPI ranks
# GUI requests only visible time ranges (lazy loading)
```

| VampirServer Feature | What It Does |
|---------------------|--------------|
| Distributed I/O | Each worker reads a subset of OTF2 per-rank files |
| Parallel statistics | Function summaries computed in parallel |
| Lazy loading | Only reads trace data for visible zoom level |
| Progressive rendering | GUI updates as workers complete |
| Multi-TB traces | Handles traces too large for single-node memory |

---

## Sample Trace Output

### Intel PIN: Instruction-Level Memory Trace

```
# Pintool output: memory access trace for inference workload
# Format: Thread IP Operation Address Size Value
# ─────────────────────────────────────────────────────────────────────
T0 0x55a4e4001a20 R 0x7f3c8a000040 8    0x00000000deadbeef
T0 0x55a4e4001a28 R 0x7f3c8a000048 8    0x000000000000003f
T0 0x55a4e4001a30 W 0x7ffd8bc00120 8    0x00000000deadbeef
T0 0x55a4e4001a38 R 0x7f3c8a000050 32   [AVX256 load]
T0 0x55a4e4001a40 R 0x7f3c8a200000 32   [AVX256 load]
T0 0x55a4e4001a48 W 0x7f3c8a400000 32   [AVX256 store - matmul result]
T1 0x55a4e4003b10 R 0x7f3c8b000000 64   [AVX512 load - weights]
T1 0x55a4e4003b18 R 0x7f3c8b000040 64   [AVX512 load - activations]
T1 0x55a4e4003b20 W 0x7f3c8b100000 64   [AVX512 store - output]
# ...
# Total: 847,293,102 memory accesses in 12.4s (68M accesses/sec)
# Cache miss rate (simulated L1): 3.2%
# Cache miss rate (simulated L2): 0.8%
```

### Intel PIN: Branch Trace

```
# Pintool output: branch prediction analysis
# Format: IP Target Taken Mispredicted Context
# ─────────────────────────────────────────────────────────────────────
0x55a4e4002100 0x55a4e4002180 T  N  matmul_inner_loop (iteration 1)
0x55a4e4002100 0x55a4e4002180 T  N  matmul_inner_loop (iteration 2)
0x55a4e4002100 0x55a4e4002180 T  N  matmul_inner_loop (iteration 3)
...
0x55a4e4002100 0x55a4e4002108 NT Y  matmul_inner_loop (exit - mispredicted)
0x55a4e4002200 0x55a4e4002400 T  N  attention_head_select (head 0)
0x55a4e4002200 0x55a4e4002500 T  Y  attention_head_select (head 1 - mispredicted)
# ...
# Branch misprediction rate: 2.1% (1,247,891 / 59,423,471)
# Indirect branch mispredictions: 8.3% (most from vtable calls)
```

### AMD Luthier: GPU Kernel Instrumentation Events

```
# Luthier plugin output: GPU memory access trace
# Format: Wavefront KernelPC SIMD_Lane GlobalAddr AccessType Latency
# ─────────────────────────────────────────────────────────────────────
WF[0,0,0]  0x7f0000001200  lane_0   0x00007f2000000000  LOAD   142cy
WF[0,0,0]  0x7f0000001200  lane_1   0x00007f2000000040  LOAD   142cy
WF[0,0,0]  0x7f0000001200  lane_2   0x00007f2000000080  LOAD   145cy
...
WF[0,0,0]  0x7f0000001200  lane_63  0x00007f2000000fc0  LOAD   148cy
WF[0,0,0]  0x7f0000001240  lane_0   0x00007f2001000000  STORE  89cy
WF[0,0,1]  0x7f0000001200  lane_0   0x00007f2000001000  LOAD   38cy  [L2 hit]
WF[0,0,1]  0x7f0000001200  lane_1   0x00007f2000001040  LOAD   38cy  [L2 hit]

# Kernel: gemm_fp16_256x256
# Total wavefronts: 4096
# Global loads: 1,847,392,256
# Global stores: 268,435,456
# Avg load latency: 127 cycles (67% L2 hit, 33% HBM)
# Occupancy: 8 wavefronts / CU (limited by VGPR usage: 128 VGPRs)
```

### AMD Luthier: Kernel Launch Events

```
# Luthier HSA intercept log
# Format: Timestamp QueueID KernelName Grid Block Event
# ─────────────────────────────────────────────────────────────────────
1723456789.001234  Q0  gemm_fp16_256x256        [128,128,1] [256,1,1]  DISPATCH
1723456789.001235  Q0  gemm_fp16_256x256        [128,128,1] [256,1,1]  KERNEL_START
1723456789.004567  Q0  gemm_fp16_256x256        [128,128,1] [256,1,1]  KERNEL_END    dur=3.333ms
1723456789.004600  Q0  softmax_f32              [512,1,1]   [256,1,1]  DISPATCH
1723456789.004601  Q0  softmax_f32              [512,1,1]   [256,1,1]  KERNEL_START
1723456789.004890  Q0  softmax_f32              [512,1,1]   [256,1,1]  KERNEL_END    dur=0.290ms
1723456789.004900  Q0  flash_attention_v2_fp16  [64,32,1]   [128,1,1]  DISPATCH
1723456789.004901  Q0  flash_attention_v2_fp16  [64,32,1]   [128,1,1]  KERNEL_START
1723456789.012345  Q0  flash_attention_v2_fp16  [64,32,1]   [128,1,1]  KERNEL_END    dur=7.444ms
1723456789.012400  Q1  memcpy_d2h               4096 bytes              COPY_START
1723456789.012456  Q1  memcpy_d2h               4096 bytes              COPY_END     dur=0.056ms
```

### Vampir: OTF2 Timeline Representation

```
# OTF2 trace content (as printed by otf2-print)
# Score-P collected MPI+CUDA application, visualized in Vampir

ENTER     0  2.345678901  "main"
ENTER     0  2.345679012  "load_model"
ENTER     0  2.345680123  "mmap_weights"
LEAVE     0  2.346234567  "mmap_weights"
LEAVE     0  2.346234890  "load_model"

ENTER     0  2.346235000  "train_step"
ENTER     0  2.346235100  "forward_pass"
METRIC    0  2.346235100  "GPU_Utilization" 0.0
ENTER     0  2.346235200  "cuda_memcpy_h2d"       # Score-P CUDA wrapper
LEAVE     0  2.346340000  "cuda_memcpy_h2d"

# GPU stream (Score-P device trace)
ENTER     GPU:0:S0  2.346340500  "gemm_fp16_nn_128x128"
METRIC    GPU:0:S0  2.346340500  "SM_Active" 98.2
METRIC    GPU:0:S0  2.346340500  "DRAM_BW_GB/s" 1247.3
LEAVE     GPU:0:S0  2.346890000  "gemm_fp16_nn_128x128"

# MPI communication (recorded by Score-P MPI wrapper)
ENTER     0  2.346900000  "MPI_Allreduce"
MPI_SEND  0  2.346900100  dest=1  tag=42  bytes=4194304
MPI_RECV  0  2.347200000  src=1   tag=42  bytes=4194304
LEAVE     0  2.347200500  "MPI_Allreduce"

METRIC    0  2.347200500  "GPU_Utilization" 94.7

# Vampir renders this as:
# - Gantt bars colored by function (compute=blue, MPI=red, memcpy=yellow)
# - Arrows between ranks showing message flow
# - Counter timeline graphs below (GPU util, bandwidth)
# - Click any region to drill into call tree
```

---

## Cost Profile

### Runtime Overhead

| Scenario | Intel PIN | AMD Luthier | Notes |
|----------|-----------|-------------|-------|
| Instruction counting only | 2-3x | 1.5-3x | Minimal per-instruction callback |
| Memory access tracing | 5-8x | 3-6x | Callback on every load/store |
| Full cache simulation | 8-10x | 5-10x | Complex analysis per access |
| Branch tracing only | 2-4x | 2-4x | Conditional branch callbacks |
| Routine-level profiling | 1.5-2x | 1.5-2x | Function entry/exit only |
| Syscall tracing only | 1.1-1.5x | N/A | Minimal (syscalls are infrequent) |

**Overhead model:**
- **Intel PIN**: JIT recompilation is the dominant cost. Each basic block is compiled once into PIN's code cache, so steady-state overhead comes from analysis callbacks, not JIT. Hot loops approach native speed for lightweight instrumentation.
- **AMD Luthier**: Kernel patching overhead is per-dispatch (amortized across wavefronts). Instrumentation code runs on GPU compute units alongside original kernel, competing for VGPR/SGPR resources and reducing occupancy.

### Vampir / Score-P Collection Overhead

| Collection Mode | Overhead | Notes |
|-----------------|----------|-------|
| Function entry/exit (compiler instrumentation) | 2-5% | Score-P `-finstrument-functions` |
| MPI wrapper only | 1-3% | PMPI interposition; low-overhead |
| CUDA/HIP API wrapping | 2-5% | Score-P GPU support |
| Hardware counters (PAPI) | <1% | Counter read at function boundaries |
| Full instrumentation (all of above) | 5-15% | Combined overhead |
| Filtering (Score-P filter file) | 1-3% | Exclude high-frequency short functions |

### Storage Costs

| Trace Source | Typical Size (60s capture) | Notes |
|-------------|---------------------------|-------|
| PIN instruction trace (all memory accesses) | 10-100 GB | Every load/store recorded |
| PIN branch trace | 2-20 GB | Every taken/not-taken branch |
| PIN routine-level only | 50-500 MB | Function entry/exit timestamps |
| Luthier GPU memory trace | 5-50 GB | Per-lane, per-wavefront accesses |
| Luthier kernel-level events | 10-100 MB | Dispatch/start/end per kernel |
| Score-P OTF2 (64-rank MPI job) | 1-10 GB | Function + MPI + counters |
| Score-P OTF2 (4096-rank job) | 50-500 GB | Requires VampirServer |

### Visualization Cost (Vampir)

| Trace Size | Vampir (single node) | VampirServer (cluster) |
|-----------|---------------------|----------------------|
| < 1 GB | Interactive (< 1s load) | Not needed |
| 1-10 GB | Interactive (5-30s load) | Optional (faster zoom) |
| 10-100 GB | Slow / may OOM | 4-16 workers recommended |
| 100 GB - 1 TB | Not feasible | 16-64 workers required |
| > 1 TB | Not feasible | 64-256 workers required |

### Licensing

| Tool | License | Cost |
|------|---------|------|
| Intel PIN | Free (non-commercial); Intel EULA | $0 for research/academic |
| AMD Luthier | MIT (open source) | $0 |
| Score-P | BSD (open source) | $0 |
| Vampir (GUI) | Commercial | Academic licenses available; contact TU Dresden |
| VampirServer | Commercial | Per-node licensing |

---

## Validation Criteria

### Quick Smoke Test (Intel PIN)

```bash
# 1. Verify PIN installation
$ pin -version
Pin: pin-3.28-98749-g6643ecee5
# Expected: version string with build number

# 2. Run built-in instruction count tool
$ pin -t $PIN_ROOT/source/tools/ManualExamples/obj-intel64/inscount0.so -- /bin/ls
# Expected: "Count 782345" (instruction count varies)

# 3. Build custom Pintool
$ cd $PIN_ROOT/source/tools/ManualExamples
$ make obj-intel64/inscount0.so
# Expected: successful compilation

# 4. Verify thread-safe operation
$ pin -t $PIN_ROOT/source/tools/ManualExamples/obj-intel64/inscount2.so \
    -- ./multi_threaded_app
# Expected: per-thread instruction counts without crashes

# 5. Verify memory trace capability
$ pin -t $PIN_ROOT/source/tools/ManualExamples/obj-intel64/pinatrace.so \
    -- /bin/ls /tmp
$ head -20 pinatrace.out
# Expected: lines with instruction pointer + memory address + R/W
```

### Quick Smoke Test (AMD Luthier)

```bash
# 1. Verify ROCm installation
$ rocm-smi --showproductname
# Expected: GPU product name (e.g., "AMD Instinct MI250X")

$ hipcc --version
# Expected: HIP version 6.x+

# 2. Build Luthier from source
$ git clone https://github.com/ROCm/luthier.git
$ cd luthier && mkdir build && cd build
$ cmake .. -DCMAKE_PREFIX_PATH=/opt/rocm
$ make -j$(nproc)
# Expected: successful build

# 3. Run example plugin (if available)
$ ./luthier --plugin=examples/kernel_trace.so -- ./hip_matmul
# Expected: kernel launch/end events printed to stdout

# 4. Verify HSA intercept
$ HSA_TOOLS_LIB=./libluthier.so ./hip_app
# Expected: Luthier intercepts HSA dispatches (visible in output)

# 5. Verify GPU ISA instrumentation
$ ./luthier --plugin=examples/instruction_count.so -- ./hip_vectoradd
# Expected: per-kernel instruction counts
```

### Quick Smoke Test (Vampir + Score-P)

```bash
# 1. Verify Score-P installation
$ scorep --version
# Expected: Score-P 8.x

# 2. Instrument and run simple MPI program
$ scorep-mpicc -o hello_mpi hello_mpi.c
$ export SCOREP_ENABLE_TRACING=true
$ export SCOREP_EXPERIMENT_DIRECTORY=test_trace
$ mpirun -np 4 ./hello_mpi
# Expected: test_trace/ directory created with traces.otf2

# 3. Verify OTF2 trace validity
$ otf2-print test_trace/traces.otf2 | head -30
# Expected: ENTER/LEAVE events with timestamps and function names

# 4. Open in Vampir (GUI)
$ vampir test_trace/traces.otf2
# Expected: timeline displays with colored function bars for 4 ranks

# 5. VampirServer (for large traces)
$ mpirun -np 4 vampirserver start
# Expected: "VampirServer listening on <host>:<port>"
$ vampir --server=<host>:<port> large_trace/traces.otf2
# Expected: remote trace opens with distributed analysis
```

---

## Limitations / Out of Scope

| Limitation | Affected Tool | Impact | Workaround |
|-----------|--------------|--------|------------|
| High overhead (2-10x slowdown) | Intel PIN | Cannot use in production; timing distortion invalidates real-time analysis | Use Intel PT for low-overhead tracing; PIN for offline analysis |
| x86/x86-64 only | Intel PIN | No ARM/RISC-V support | Use DynamoRIO for ARM; Valgrind for portability |
| AMD GPU only | Luthier | No NVIDIA or Intel GPU support | Use CUPTI/Nsight for NVIDIA; oneAPI for Intel |
| Early-stage / research quality | Luthier | API instability, limited documentation, potential crashes | Pin to specific commits; contribute upstream fixes |
| ROCm 6.x+ required | Luthier | Older ROCm installations unsupported | Upgrade ROCm or use roctracer for stable API-level tracing |
| GPU occupancy reduction | Luthier | Instrumentation consumes VGPRs/SGPRs, reducing active wavefronts | Minimize instrumentation; target specific kernels |
| No real-time visualization | Vampir | Post-mortem only; cannot observe running application | Use Score-P online access interface or Grafana for live metrics |
| Commercial license required | Vampir | Cost barrier for non-academic users | Use alternative: Trace Compass (free, open-source OTF2 support) |
| OTF2 format dependency | Vampir | Cannot read arbitrary formats directly | Convert via OTF2 API or use Score-P as intermediary |
| No kernel-space instrumentation | Intel PIN | Cannot instrument OS kernel code | Use FTrace/eBPF/LTTng for kernel; combine with PIN for userspace |
| Single-process model | Intel PIN | Multi-process requires separate PIN instances | Use PIN's follow-fork mode; correlate traces externally |
| No integrated collection+visualization pipeline | All three | Three separate tools must be assembled | Build pipeline: PIN/Luthier → OTF2 writer → Vampir |

---

## Evaluation Assessment

### Observability

**Rating: Strong**

| Aspect | Assessment |
|--------|------------|
| **Strengths** | Instruction-level granularity (PIN): every load, store, branch, and syscall observable. GPU ISA-level granularity (Luthier): per-lane, per-wavefront memory access and instruction execution traces. Vampir handles billions of events across 100k+ processes with interactive exploration. Combined pipeline provides full-stack visibility from individual x86 instructions through GPU kernel ISA to distributed MPI communication patterns. Score-P captures MPI, OpenMP, CUDA, HIP, SYCL, and I/O events. Vampir's communication matrix reveals inter-process data flow. PIN's JIT model means zero blind spots — every instruction passes through instrumentation. |
| **Gaps** | No unified single-tool solution — requires assembly of separate tools. No real-time/streaming observation (all are batch/post-mortem). PIN cannot observe kernel-space. Luthier lacks stable API documentation. Vampir requires commercial license for full functionality. No built-in OpenTelemetry or Prometheus export. No automatic anomaly detection (manual visual inspection in Vampir). |
| **Implementations must add** | Unified pipeline tooling (PIN/Luthier → OTF2 → Vampir automation), real-time streaming mode, OpenTelemetry bridge for integration with cloud-native observability, automatic performance regression detection, kernel-space correlation via eBPF/LTTng sidecar. |

### Security

**Rating: Partial**

| Aspect | Assessment |
|--------|------------|
| **Strengths** | PIN operates in same privilege as target process (no elevation required). Luthier is open-source (MIT) — full audit trail. Score-P/OTF2 are open-source (BSD). No telemetry or phone-home in any tool. PIN's JIT sandbox isolates analysis code from target. Vampir is local GUI — no cloud data exfiltration. |
| **Gaps** | PIN can inspect all process memory (powerful attack vector if misused). Trace files are unencrypted — contain instruction pointers, memory addresses, function names that reveal binary internals. No access control on trace files beyond filesystem permissions. PIN's `IARG_MEMORYREAD_EA` exposes all memory access patterns (side-channel risk). Luthier's HSA interposition could be used maliciously. No audit logging of instrumentation sessions. Vampir commercial license requires license server communication. |
| **Implementations must add** | Trace file encryption at rest, signed instrumentation plugins, audit logging of PIN/Luthier sessions, memory address anonymization option, secure multi-user access control for VampirServer, integrity verification of Pintool binaries. |

### Identity Management

**Rating: Weak**

| Aspect | Assessment |
|--------|------------|
| **Strengths** | PIN records PID/TID for all events. Score-P embeds MPI rank, OpenMP thread ID, and CUDA stream/device in OTF2. Luthier identifies wavefront and CU. Vampir correlates events by rank/thread/device identity. Score-P supports custom region annotations via SCOREP_USER_REGION. |
| **Gaps** | No concept of human operator identity (who initiated the trace). No AI model identity (which model version produced which behavior). No experiment/run identity beyond filesystem directory naming. No authenticated sessions for PIN/Luthier. No job scheduler integration (Slurm job ID not automatically embedded). No container or Kubernetes pod identity. No correlation ID linking CPU trace (PIN) to GPU trace (Luthier) to distributed trace (Score-P/Vampir). |
| **Implementations must add** | Operator identity in trace metadata, AI model version tagging, Slurm/PBS job identity embedding, cross-tool correlation IDs (PIN↔Luthier↔Score-P), experiment tracking integration (MLflow/W&B run ID), container identity in OTF2 metadata. |

### Reliability

**Rating: Moderate**

| Aspect | Assessment |
|--------|------------|
| **Strengths** | PIN's code cache provides deterministic instrumented execution (same trace for same input). Score-P's ring buffer model with configurable overflow policy (flush/wrap/abort). OTF2 format includes checksums and anchor file for trace integrity. VampirServer distributes analysis across nodes — single-node failure doesn't lose trace data. PIN's JIT engine is mature (20+ years of development) with extensive testing. Score-P's filtering mechanism prevents trace explosion for high-frequency functions. |
| **Gaps** | PIN's 2-10x overhead means timing-sensitive bugs (races, deadlocks) may not reproduce. Luthier's early-stage status means potential crashes during instrumentation. GPU occupancy changes from Luthier instrumentation alter kernel execution timing (probe effect). Score-P can exhaust memory with dense tracing (must configure SCOREP_TOTAL_MEMORY). No guaranteed delivery from collection to storage under memory pressure. Multi-GPU Luthier instrumentation stability unproven at scale. Signal handling under PIN is complex and may alter program behavior. |
| **Implementations must add** | Probe-effect quantification tooling (measure overhead introduced), graceful degradation under memory pressure, Luthier crash recovery without losing partial traces, PIN signal-safe mode validation, distributed trace consistency verification, automatic Score-P memory tuning. |

### Accuracy

**Rating: Strong**

| Aspect | Assessment |
|--------|------------|
| **Strengths** | PIN captures deterministic, complete instruction traces (not statistical sampling). Every branch, every memory access, every function call is recorded exactly. Luthier instruments at GPU ISA level — exact instruction execution counts per wavefront. Score-P function entry/exit timestamps use hardware cycle counters (rdtsc/cntvct). OTF2 preserves nanosecond-resolution timestamps. Vampir's timeline rendering is pixel-accurate to trace data. No sampling bias — complete execution record (PIN/Luthier). Cache simulation (PIN) produces exact hit/miss counts given the cache model. |
| **Gaps** | PIN's overhead distorts wall-clock timing (accurate instruction sequence, inaccurate timing). Luthier's added VGPRs change kernel scheduling — measured latencies include instrumentation overhead. Cross-domain clock synchronization (CPU timestamps vs GPU timestamps) has microsecond-level error. Score-P's compiler instrumentation may miss inlined functions. OTF2 timestamp resolution limited by clock source granularity. Vampir's statistical views (function summary) are exact but aggregated — may hide variance. |
| **Implementations must add** | Overhead compensation models (subtract known instrumentation cost from timing), CPU↔GPU clock calibration tooling, Score-P inline-aware instrumentation (-finline-tracking), per-sample confidence intervals for timing data, trace completeness verification (no dropped events). |

---

## Assessment Summary

| Dimension | Rating | Key Gap |
|-----------|--------|---------|
| Observability | Strong | No unified pipeline; post-mortem only; no real-time streaming |
| Security | Partial | Unencrypted traces expose binary internals; no audit logging; no signed plugins |
| Identity | Weak | No operator/model/experiment identity; no cross-tool correlation IDs |
| Reliability | Moderate | Probe effect distorts timing; Luthier stability unproven; memory pressure risks |
| Accuracy | Strong | Deterministic capture but timing distorted by overhead; clock domain sync gaps |

---

## References

| Resource | URL |
|----------|-----|
| Vampir (TU Dresden) | https://vampir.eu/ |
| AMD Luthier (ROCm) | https://github.com/ROCm/luthier |
| Intel PIN | https://www.intel.com/content/www/us/en/developer/articles/tool/pin-a-dynamic-binary-instrumentation-tool.html |
| Score-P | https://www.vi-hps.org/projects/score-p/ |
| OTF2 specification | https://www.vi-hps.org/projects/score-p/otf2.html |
| PIN User Guide | https://software.intel.com/sites/landingpage/pintool/docs/98749/Pin/html/ |
| ROCm documentation | https://rocm.docs.amd.com/ |
| VampirTrace → Score-P migration | https://vampir.eu/tutorial/manual/score-p_migration |
