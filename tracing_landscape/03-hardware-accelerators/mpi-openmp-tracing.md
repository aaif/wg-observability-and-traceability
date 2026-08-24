# AAIF Reference Architecture: MPI/OpenMP Tracing

| Field | Value |
|-------|-------|
| **Subject** | [Score-P](https://www.vi-hps.org/projects/score-p/) — Unified HPC Tracing for MPI + OpenMP |
| **Version** | MPI-4.1 / OpenMP 5.2 / Score-P 8.x / OTF2 3.x |
| **Date** | 2026-08-21 |

---

## Objective

Demonstrates how parallel computing workloads using MPI (inter-process communication) and OpenMP (intra-process shared-memory parallelism) are traced through standardized profiling interfaces — PMPI for message passing and OMPT for threading — unified by Score-P into OTF2 binary traces suitable for post-mortem performance analysis at scale (100k+ processes).

---

## Scope / Zoom Level

**System layer — HPC/parallel computing instrumentation across distributed processes and shared-memory threads.**

This assessment covers the instrumentation interfaces defined by the MPI and OpenMP standards, the Score-P measurement infrastructure that unifies them, and the OTF2 trace format that stores the results. The scope spans from application source code through compiler instrumentation, link-time wrapper interposition, and runtime callback registration to binary trace file output. Analysis/visualization tools (Vampir, Scalasca, Cube) are referenced but not assessed in depth.

---

## Prerequisites

| Component | Version | Notes |
|-----------|---------|-------|
| MPI Implementation | OpenMPI 5.x / MPICH 4.x / Intel MPI 2021+ / Cray MPICH | Must expose PMPI symbols; all major implementations do |
| OpenMP Runtime | LLVM/Clang 14+ / GCC 12+ / Intel oneAPI 2023+ | Must implement OMPT (OpenMP Tools Interface) |
| Score-P | 8.x+ | Measurement infrastructure; wraps PMPI, connects OMPT |
| OTF2 Library | 3.x+ | Trace format library; bundled with Score-P |
| C/C++/Fortran Compiler | GCC 12+ / Clang 14+ / Intel oneAPI | Score-P compiler wrapper instruments function entry/exit |
| PAPI (optional) | 7.x+ | Hardware counter access for CPU PMU metrics |
| Cube tools (optional) | 4.x+ | Profile analysis (aggregated metrics from CUBE format) |
| Vampir / Scalasca (optional) | — | OTF2 trace visualization and automated bottleneck analysis |

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    Application Source Code                                    │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  MPI_Init() ... MPI_Send/Recv/Allreduce/Barrier ... MPI_Finalize()   │  │
│  │  #pragma omp parallel for ... #pragma omp task ...                    │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────┬────────────────────────────────────────┘
                                     │ compiled with scorep-mpicc / scorep-mpicxx
                                     │ (compiler instrumentation + link wrapping)
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│              Instrumentation Layer (Standards-Based Interfaces)               │
│                                                                             │
│  ┌─────────────────────────────┐  ┌──────────────────────────────────────┐ │
│  │  PMPI Interposition         │  │  OMPT Callbacks                      │ │
│  │                             │  │                                      │ │
│  │  MPI_Send() → PMPI_Send()  │  │  ompt_callback_parallel_begin       │ │
│  │  MPI_Recv() → PMPI_Recv()  │  │  ompt_callback_parallel_end         │ │
│  │  MPI_Barrier()→PMPI_Barrier│  │  ompt_callback_task_create           │ │
│  │  MPI_Allreduce()→PMPI_...  │  │  ompt_callback_sync_region           │ │
│  │  MPI_Wait() → PMPI_Wait() │  │  ompt_callback_work                  │ │
│  │                             │  │  ompt_callback_target (GPU offload)  │ │
│  │  Tool wraps all ~450 MPI   │  │  Tool registers via                  │ │
│  │  functions at link time     │  │  ompt_start_tool() at load time      │ │
│  └──────────────┬──────────────┘  └────────────────────┬─────────────────┘ │
│                 │                                       │                    │
│  ┌──────────────▼──────────────┐                       │                    │
│  │  MPI_T Interface            │                       │                    │
│  │  Performance Variables      │                       │                    │
│  │  Control Variables          │                       │                    │
│  │  (runtime query/modify)     │                       │                    │
│  └──────────────┬──────────────┘                       │                    │
└─────────────────┼──────────────────────────────────────┼────────────────────┘
                  │                                       │
                  ▼                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│              Score-P Measurement Core                                         │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │  Event Processing Pipeline                                             │ │
│  │                                                                        │ │
│  │  ┌────────────┐  ┌────────────┐  ┌─────────────┐  ┌──────────────┐  │ │
│  │  │ Timestamp  │→ │ Filter     │→ │ Metric      │→ │ Buffer       │  │ │
│  │  │ (RDTSC /   │  │ (include/  │  │ Collection  │  │ Management   │  │ │
│  │  │  clock_get │  │  exclude   │  │ (PAPI HW    │  │ (per-thread  │  │ │
│  │  │  time)     │  │  regions)  │  │  counters)  │  │  ring buf)   │  │ │
│  │  └────────────┘  └────────────┘  └─────────────┘  └──────┬───────┘  │ │
│  └───────────────────────────────────────────────────────────┼───────────┘ │
│                                                               │             │
│  ┌─────────────────────────────┐  ┌──────────────────────────▼──────────┐ │
│  │  CUBE Profile Writer        │  │  OTF2 Trace Writer                   │ │
│  │  (aggregated statistics)    │  │  (per-process event streams)         │ │
│  │  → .cubex files             │  │  → .otf2 anchor + per-rank .evt     │ │
│  └─────────────────────────────┘  └─────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
                  │                              │
                  ▼                              ▼
┌──────────────────────────┐  ┌─────────────────────────────────────────────┐
│  CUBE Profile Files       │  │  OTF2 Trace Archive                         │
│                           │  │                                             │
│  scorep_sum/              │  │  scorep_trace/                              │
│  ├── summary.cubex        │  │  ├── traces.otf2          (anchor file)    │
│  └── (aggregated metrics) │  │  ├── traces/0.evt         (rank 0 events)  │
│                           │  │  ├── traces/1.evt         (rank 1 events)  │
│  Analysis: Cube GUI,      │  │  ├── ...                                   │
│  cube_stat, cube_diff     │  │  ├── traces/N.evt         (rank N events)  │
│                           │  │  └── traces.def           (global defs)    │
│                           │  │                                             │
│                           │  │  Analysis: Vampir, Scalasca, otf2-print    │
└──────────────────────────┘  └─────────────────────────────────────────────┘
```

---

## Instrumentation Walkthrough

### PMPI — MPI Profiling Interface

The MPI standard mandates that every public function `MPI_Xxx` has an identical entry point `PMPI_Xxx`. The MPI library itself implements the real logic at `PMPI_Xxx` and provides `MPI_Xxx` as a thin redirect. A profiling tool replaces `MPI_Xxx` at link time with its own implementation that records timestamps and then calls `PMPI_Xxx` to perform the actual operation.

**Mechanism:**

1. **Link-time interposition**: Score-P provides wrapper libraries containing all ~450 MPI function symbols. When the application is linked with `scorep-mpicc`, the linker resolves `MPI_Send` to Score-P's wrapper instead of the MPI library's.

2. **Wrapper structure** (conceptual):
```c
int MPI_Send(const void *buf, int count, MPI_Datatype dtype,
             int dest, int tag, MPI_Comm comm) {
    // Score-P: record enter event with timestamp
    scorep_enter_region(SCOREP_REGION_MPI_SEND);
    scorep_record_mpi_send(dest, tag, count * sizeof_datatype(dtype));

    // Call the real MPI implementation
    int ret = PMPI_Send(buf, count, dtype, dest, tag, comm);

    // Score-P: record exit event with timestamp
    scorep_exit_region(SCOREP_REGION_MPI_SEND);
    return ret;
}
```

3. **What is captured per MPI event**:

| Event Type | Recorded Data |
|-----------|---------------|
| Point-to-point (Send/Recv) | Timestamp, source rank, destination rank, tag, message size (bytes), communicator |
| Collective (Allreduce/Barrier/Bcast) | Timestamp, root rank, communicator, data volume (sent/received bytes) |
| Wait/Test | Timestamp, request handle, completion status |
| I/O (MPI-IO) | File handle, offset, bytes, operation type |
| One-sided (Put/Get) | Target rank, window, displacement, byte count |

4. **Zero overhead when disabled**: If the application is linked without Score-P wrappers (standard `mpicc`), no interposition exists. The PMPI mechanism adds zero overhead to uninstrumented builds.

### MPI_T — MPI Tools Information Interface

MPI-3.0 introduced `MPI_T` as a runtime query interface for MPI implementation internals:

```c
MPI_T_init_thread(MPI_THREAD_MULTIPLE, &provided);

// Enumerate performance variables
int num_pvars;
MPI_T_pvar_get_num(&num_pvars);
for (int i = 0; i < num_pvars; i++) {
    MPI_T_pvar_get_info(i, name, &name_len, &verbosity,
                        &var_class, &datatype, ...);
    // Examples: "unexpected_recvq_length", "posted_recvq_match_attempts"
}

// Start a performance variable session
MPI_T_pvar_session_create(&session);
MPI_T_pvar_handle_alloc(session, pvar_index, NULL, &handle, &count);
MPI_T_pvar_start(session, handle);
// ... application work ...
MPI_T_pvar_read(session, handle, &value);
```

Score-P queries MPI_T variables to capture internal MPI runtime metrics (queue depths, protocol thresholds, eager/rendezvous transitions) alongside application-level events.

### OMPT — OpenMP Tools Interface

OMPT (standardized in OpenMP 5.0) provides a callback-based mechanism for tools to observe OpenMP runtime behavior without modifying application code.

**Mechanism:**

1. **Tool registration**: The OpenMP runtime checks for an `ompt_start_tool()` function at load time. If found, it calls the tool's initialization function, passing a lookup function to register callbacks.

```c
ompt_start_tool_result_t *ompt_start_tool(
    unsigned int omp_version,
    const char *runtime_version) {
    // Return tool descriptor with initialize/finalize callbacks
    static ompt_start_tool_result_t tool = {
        .initialize = tool_initialize,
        .finalize = tool_finalize,
        .tool_data = {0}
    };
    return &tool;
}

void tool_initialize(ompt_function_lookup_t lookup,
                     int initial_device_num,
                     ompt_data_t *tool_data) {
    // Get the callback registration function
    ompt_set_callback_t set_callback =
        (ompt_set_callback_t)lookup("ompt_set_callback");

    // Register for events of interest
    set_callback(ompt_callback_parallel_begin, (ompt_callback_t)on_parallel_begin);
    set_callback(ompt_callback_parallel_end, (ompt_callback_t)on_parallel_end);
    set_callback(ompt_callback_task_create, (ompt_callback_t)on_task_create);
    set_callback(ompt_callback_sync_region, (ompt_callback_t)on_sync_region);
    set_callback(ompt_callback_work, (ompt_callback_t)on_work);
    set_callback(ompt_callback_target, (ompt_callback_t)on_target);
}
```

2. **Callback invocation**: The OpenMP runtime invokes registered callbacks at defined program points:

| Callback | Trigger | Data Provided |
|----------|---------|---------------|
| `ompt_callback_parallel_begin` | Fork (entering parallel region) | Requested parallelism, flags, parent task |
| `ompt_callback_parallel_end` | Join (exiting parallel region) | Parallel data, invoker task |
| `ompt_callback_task_create` | Explicit/implicit task creation | Task type, has_dependences, parent task |
| `ompt_callback_task_schedule` | Task switch (suspend/resume) | Prior task, next task, prior status |
| `ompt_callback_sync_region` | Barrier, taskwait, taskgroup entry/exit | Kind (barrier/taskwait/taskgroup), endpoint (begin/end) |
| `ompt_callback_work` | Worksharing (for/sections/single) entry/exit | Work type, count, endpoint |
| `ompt_callback_target` | GPU offload target region | Device number, target data |
| `ompt_callback_target_submit` | Kernel submission to device | Device, host_op_id, requested_num_teams |

3. **Thread identification**: OMPT provides `ompt_get_thread_data()` and `ompt_get_parallel_info()` for identifying the calling thread and its position in the parallel region hierarchy.

4. **Mutual exclusivity guarantee**: OMPT callbacks for a given thread are never invoked concurrently for that thread — no locking needed in tool callback implementations per thread.

### Score-P Unified Instrumentation

Score-P connects both interfaces into a single measurement system:

```bash
# Compile with Score-P compiler wrappers (instruments function entry/exit + MPI wrapping)
scorep-mpicc -fopenmp -o my_app my_app.c

# Run with tracing enabled
export SCOREP_ENABLE_TRACING=true
export SCOREP_ENABLE_PROFILING=true
export SCOREP_TOTAL_MEMORY=64MB          # per-process trace buffer
export SCOREP_FILTERING_FILE=filter.txt   # include/exclude regions

mpirun -np 64 ./my_app
```

**Filter file syntax** (controls instrumentation scope):
```
SCOREP_REGION_NAMES_BEGIN
  EXCLUDE
    *_init*         # exclude initialization functions
    *_cleanup*      # exclude teardown
    small_helper*   # exclude trivially short functions
  INCLUDE
    compute_*       # always trace compute kernels
    MPI_*           # always trace MPI (default anyway)
SCOREP_REGION_NAMES_END
```

**Instrumentation modes supported**:

| Mode | Mechanism | Overhead | Use Case |
|------|-----------|----------|----------|
| Compiler instrumentation | `-finstrument-functions` (GCC/Clang) | Medium (every function entry/exit) | Full call-path profiling |
| MPI library wrapping | PMPI link-time interposition | Low (MPI calls only) | Communication analysis |
| OMPT callbacks | Runtime callback registration | Low (OpenMP events only) | Thread/task analysis |
| User regions | `SCOREP_USER_REGION_BEGIN/END` macros | Negligible (manual placement) | Targeted instrumentation |
| Sampling | Timer-interrupt stack unwinding | Configurable (1ms–100ms period) | Statistical profiling |
| CUDA/HIP | CUPTI/roctracer integration | Medium | GPU kernel tracing |

---

## Sample Trace Output

### OTF2 Event Records (via `otf2-print`)

The following shows representative events from a 4-rank MPI+OpenMP application traced with Score-P:

```
$ otf2-print scorep_trace/traces.otf2

=== Global Definitions ===
CLOCK_PROPERTIES  0 1000000000 0   # 1 GHz clock (nanosecond resolution)
STRING            0 "MPI_Send"
STRING            1 "MPI_Recv"
STRING            2 "MPI_Allreduce"
STRING            3 "MPI_Barrier"
STRING            4 "!$omp parallel"
STRING            5 "!$omp for"
STRING            6 "compute_kernel"
REGION            0 "MPI_Send"      ROLE=MPI    PARADIGM=MPI
REGION            1 "MPI_Recv"      ROLE=MPI    PARADIGM=MPI
REGION            2 "MPI_Allreduce" ROLE=COLL   PARADIGM=MPI
REGION            3 "MPI_Barrier"   ROLE=BARRIER PARADIGM=MPI
REGION            4 "!$omp parallel" ROLE=PARALLEL PARADIGM=OPENMP
REGION            5 "!$omp for"      ROLE=LOOP   PARADIGM=OPENMP
REGION            6 "compute_kernel" ROLE=FUNCTION PARADIGM=USER
LOCATION          0 "Master thread" TYPE=CPU_THREAD  RANK=0
LOCATION          1 "OMP thread 1"  TYPE=CPU_THREAD  RANK=0
LOCATION          2 "OMP thread 2"  TYPE=CPU_THREAD  RANK=0
LOCATION          3 "OMP thread 3"  TYPE=CPU_THREAD  RANK=0
COMM              0 "MPI_COMM_WORLD" GROUP=0

=== Events (Rank 0, Master Thread) ===
ENTER       1000000000  Region: "compute_kernel"
ENTER       1000000100  Region: "!$omp parallel"
ENTER       1000000150  Region: "!$omp for"
LEAVE       1000450200  Region: "!$omp for"
LEAVE       1000450300  Region: "!$omp parallel"
LEAVE       1000450400  Region: "compute_kernel"
ENTER       1000450500  Region: "MPI_Allreduce"
MPI_COLLECTIVE_BEGIN
MPI_COLLECTIVE_END  1000470200  Root: NONE  Communicator: "MPI_COMM_WORLD"
                                Sent: 8192  Received: 8192
LEAVE       1000470300  Region: "MPI_Allreduce"
ENTER       1000470400  Region: "MPI_Send"
MPI_SEND    1000470450  Dest: 1  Communicator: "MPI_COMM_WORLD"
                        Tag: 42  Length: 65536
LEAVE       1000470600  Region: "MPI_Send"
ENTER       1000470700  Region: "MPI_Recv"
MPI_RECV    1000472100  Source: 3  Communicator: "MPI_COMM_WORLD"
                        Tag: 42  Length: 65536
LEAVE       1000472200  Region: "MPI_Recv"
ENTER       1000472300  Region: "MPI_Barrier"
MPI_COLLECTIVE_BEGIN
MPI_COLLECTIVE_END  1000475800  Root: NONE  Communicator: "MPI_COMM_WORLD"
                                Sent: 0  Received: 0
LEAVE       1000475900  Region: "MPI_Barrier"

=== Events (Rank 0, OMP Thread 1) ===
ENTER       1000000200  Region: "!$omp for"
LEAVE       1000448900  Region: "!$omp for"
THREAD_WAIT 1000449000  # implicit barrier at end of parallel region

=== Events (Rank 1, Master Thread) ===
ENTER       1000000000  Region: "compute_kernel"
ENTER       1000000100  Region: "!$omp parallel"
ENTER       1000000140  Region: "!$omp for"
LEAVE       1000460100  Region: "!$omp for"
LEAVE       1000460200  Region: "!$omp parallel"
LEAVE       1000460300  Region: "compute_kernel"
ENTER       1000460400  Region: "MPI_Allreduce"
MPI_COLLECTIVE_BEGIN
MPI_COLLECTIVE_END  1000470200  Root: NONE  Communicator: "MPI_COMM_WORLD"
                                Sent: 8192  Received: 8192
LEAVE       1000470300  Region: "MPI_Allreduce"
ENTER       1000470400  Region: "MPI_Recv"
MPI_RECV    1000471900  Source: 0  Communicator: "MPI_COMM_WORLD"
                        Tag: 42  Length: 65536
LEAVE       1000472000  Region: "MPI_Recv"
```

### CUBE Profile Summary (via `cube_stat`)

```
$ cube_stat scorep_sum/summary.cubex

Metric: Time (seconds)
+------------------------------------------+--------+--------+--------+--------+
| Region                                   | Rank 0 | Rank 1 | Rank 2 | Rank 3 |
+------------------------------------------+--------+--------+--------+--------+
| compute_kernel                           |  0.450 |  0.460 |  0.448 |  0.455 |
|   !$omp parallel                         |  0.450 |  0.460 |  0.448 |  0.455 |
|     !$omp for                            |  0.445 |  0.455 |  0.443 |  0.450 |
| MPI_Allreduce                            |  0.020 |  0.010 |  0.022 |  0.015 |
| MPI_Send                                 |  0.001 |  0.001 |  0.001 |  0.001 |
| MPI_Recv                                 |  0.002 |  0.001 |  0.003 |  0.002 |
| MPI_Barrier                              |  0.004 |  0.001 |  0.005 |  0.003 |
+------------------------------------------+--------+--------+--------+--------+
| TOTAL                                    |  0.477 |  0.473 |  0.479 |  0.476 |
+------------------------------------------+--------+--------+--------+--------+

Load Imbalance (compute_kernel): 2.7%
MPI Wait Time (total):           0.036s (7.6% of runtime)
OpenMP Idle Time (total):        0.012s (2.5% of runtime)
```

---

## Cost Profile

### Per-Event Instrumentation Overhead

| Instrumentation Type | Overhead per Event | Notes |
|---------------------|-------------------|-------|
| PMPI wrapper (Send/Recv) | 200–500 ns | Dominated by timestamp acquisition (RDTSC: ~20ns, clock_gettime: ~50ns); negligible vs. typical MPI latency (1–10 μs) |
| PMPI wrapper (Barrier/Allreduce) | 200–500 ns | Negligible vs. collective latency (10 μs – 10 ms) |
| OMPT callback (parallel begin/end) | 100–300 ns | Runtime invokes callback; tool records timestamp + thread ID |
| OMPT callback (work/sync) | 50–200 ns | Lightweight; no memory allocation in fast path |
| Compiler instrumentation (function entry/exit) | 50–150 ns | Most overhead source at scale due to high call frequency |
| User region (manual annotation) | 30–80 ns | Minimal; just timestamp + region ID |
| Sampling (stack unwinding) | 5–50 μs per sample | Configurable rate; 100 Hz typical (10ms period) |
| MPI_T variable read | 100–500 ns | Varies by implementation and variable complexity |

### Trace File Size at Scale

| Configuration | Per-Process Size | 1,000 Ranks | 100,000 Ranks |
|--------------|-----------------|-------------|---------------|
| MPI-only (communication tracing) | 5–50 MB/min | 5–50 GB/min | 500 GB – 5 TB/min |
| MPI + OpenMP (4 threads/rank) | 20–200 MB/min | 20–200 GB/min | 2–20 TB/min |
| Full instrumentation (all functions) | 100 MB – 1 GB/min | 100 GB – 1 TB/min | Impractical |
| Filtered (MPI + annotated regions) | 1–10 MB/min | 1–10 GB/min | 100 GB – 1 TB/min |
| Profile only (CUBE, no trace) | 1–5 MB total | 1–5 GB total | 100–500 GB total |

### Filtering Impact

| Strategy | Trace Size Reduction | Overhead Reduction |
|----------|---------------------|--------------------|
| Exclude trivially short functions (<1 μs) | 50–90% | 40–80% |
| MPI + user regions only (no compiler instrumentation) | 80–95% | 60–90% |
| Sampling instead of instrumentation | 95–99% | 90–99% (statistical) |
| Score-P runtime filtering (buffer flush suppression) | 30–60% | 0% (still measured) |

### Buffer Memory Requirements

| Configuration | Per-Process Memory | Notes |
|--------------|-------------------|-------|
| Default (`SCOREP_TOTAL_MEMORY=16MB`) | 16 MB | Sufficient for short runs or filtered traces |
| Heavy instrumentation | 64–256 MB | Needed for full compiler instrumentation |
| Circular buffer mode | Fixed (configurable) | Overwrites oldest events; keeps last N events |

---

## Validation Criteria

### Functional Validation

1. **Score-P installation complete**: `scorep-info --help` executes without error
2. **OTF2 tools available**: `otf2-print --version` returns version string
3. **Compiler wrapper functional**: `scorep-mpicc --version` shows underlying compiler + Score-P version
4. **OMPT support present**: `echo | scorep-gcc -fopenmp -dM -E - | grep _OPENMP` shows OpenMP version ≥ 201811 (5.0)
5. **Trace produced**: Running instrumented binary creates `scorep_*/traces.otf2`
6. **Profile produced**: Running instrumented binary creates `scorep_*/summary.cubex`
7. **Events readable**: `otf2-print scorep_*/traces.otf2 | head -50` shows ENTER/LEAVE/MPI events
8. **MPI communication recorded**: Trace contains `MPI_SEND` and `MPI_RECV` event types with matching pairs
9. **OpenMP regions recorded**: Trace contains `PARADIGM=OPENMP` regions with `ROLE=PARALLEL`
10. **Timestamp monotonicity**: All events per location have non-decreasing timestamps

### Quick Smoke Test

```bash
# 1. Verify Score-P installation
scorep-info config-summary | grep -E "MPI|OpenMP|OTF2"
# Expected: MPI support: yes, OpenMP support: yes, OTF2 version: 3.x

# 2. Compile a trivial MPI+OpenMP program
cat > test_scorep.c << 'EOF'
#include <mpi.h>
#include <omp.h>
#include <stdio.h>

int main(int argc, char **argv) {
    MPI_Init(&argc, &argv);
    int rank, size;
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    MPI_Comm_size(MPI_COMM_WORLD, &size);

    double local_sum = 0.0;
    #pragma omp parallel for reduction(+:local_sum)
    for (int i = 0; i < 1000000; i++) {
        local_sum += (double)i * (rank + 1);
    }

    double global_sum;
    MPI_Allreduce(&local_sum, &global_sum, 1, MPI_DOUBLE, MPI_SUM, MPI_COMM_WORLD);

    if (rank == 0) printf("Global sum: %e\n", global_sum);
    MPI_Finalize();
    return 0;
}
EOF

scorep-mpicc -fopenmp -O2 -o test_scorep test_scorep.c

# 3. Run with tracing
export SCOREP_ENABLE_TRACING=true
export SCOREP_ENABLE_PROFILING=true
export SCOREP_TOTAL_MEMORY=16MB
mpirun -np 4 ./test_scorep

# 4. Validate trace output
echo "--- Trace files ---"
ls -la scorep_*/traces*

echo "--- Trace events (first 30 lines) ---"
otf2-print scorep_*/traces.otf2 | head -30

echo "--- MPI events ---"
otf2-print scorep_*/traces.otf2 | grep -c "MPI_"

echo "--- OpenMP regions ---"
otf2-print scorep_*/traces.otf2 | grep -c "omp"

# 5. Validate profile
cube_stat scorep_*/summary.cubex 2>/dev/null || echo "cube_stat not available; profile file exists:"
ls -la scorep_*/summary.cubex

# Cleanup
rm -f test_scorep test_scorep.c
rm -rf scorep_*
```

---

## Limitations / Out of Scope

| Item | Status |
|------|--------|
| Real-time/streaming trace analysis | Not supported; OTF2 is post-mortem only; no live tail equivalent |
| GPU kernel-level profiling | Score-P records CUDA/HIP API calls and kernel timing; does not provide hardware PM counters (use Nsight Compute/rocprof) |
| Network-level protocol tracing | MPI message semantics only; no TCP/RDMA/InfiniBand packet capture |
| Application-layer semantics | Tool sees MPI/OpenMP primitives; cannot infer algorithmic intent |
| Security/access control | No trace encryption, signing, or access control mechanisms |
| Non-HPC runtimes | No native support for Node.js, JVM, Go, Python GIL-bound threads |
| Windows/macOS | Score-P targets Linux HPC systems; limited macOS support, no Windows |
| Trace compression at write time | OTF2 stores uncompressed events; compression is a post-processing step |
| Deterministic replay | Traces record timing and communication patterns but do not enable full replay |
| Overhead for latency-sensitive (<1 μs) functions | Compiler instrumentation overhead (50–150 ns) is significant for sub-microsecond functions; filtering required |
| Multi-tenant isolation | No concept of user/tenant separation in trace files |
| Integration with cloud-native observability (OpenTelemetry) | No native OTel exporter; traces exist in the HPC ecosystem only |

---

## Evaluation Assessment

### Observability

**Rating: Strong**

| Aspect | Assessment |
|--------|------------|
| **Strengths** | Complete visibility into MPI communication patterns (point-to-point, collective, one-sided, I/O), OpenMP parallel structure (fork/join, tasks, worksharing, synchronization), and their interaction. OTF2 provides nanosecond-resolution timestamps with per-thread event streams. CUBE profiles give instant aggregate views (time, visits, bytes transferred per region per rank). Score-P's unified approach correlates MPI waits with OpenMP load imbalance — critical for hybrid applications. MPI_T exposes internal runtime metrics not visible through any other interface. Scalable to 100k+ processes — proven in production on leadership-class supercomputers (ORNL Summit, NERSC Perlmutter). |
| **Gaps** | No real-time observation (post-mortem only). No streaming/push-based export to dashboards. No built-in anomaly detection. OTF2 files require specialized tools (Vampir, Scalasca) — not accessible via standard web UIs. No integration with cloud-native observability stacks (Prometheus, Grafana, OpenTelemetry). Profile summaries lose individual event timing. |
| **Implementations must add** | Live streaming trace export, OTel bridge, web-based trace viewer, automated bottleneck classification, trace-based alerting for regressions across runs. |

### Security

**Rating: Weak**

| Aspect | Assessment |
|--------|------------|
| **Strengths** | Instrumentation is opt-in (explicit recompilation with Score-P wrappers required). No daemon or always-on agent. Trace files are standard POSIX files subject to filesystem permissions. Filter files can exclude sensitive regions from tracing. |
| **Gaps** | No encryption of trace data at rest or in transit. No integrity checking (signatures/checksums) on trace files. No access control beyond filesystem permissions. Trace files expose full application communication topology, data volumes, and timing — sufficient to infer algorithm structure. No audit trail of who collected or accessed traces. No support for trace anonymization or redaction. HPC environments traditionally operate on shared filesystems with broad read access. MPI_T control variables allow runtime modification of MPI behavior — no authentication required. |
| **Implementations must add** | Trace encryption, integrity signing, role-based access to trace collection, MPI_T access control, trace redaction for multi-tenant environments, audit logging. |

### Identity

**Rating: Partial**

| Aspect | Assessment |
|--------|------------|
| **Strengths** | Every event is attributed to a specific MPI rank (process identity) and thread (via OTF2 Location). OMPT provides parallel region IDs, task IDs, and team structure. MPI communicators identify process groups. Score-P records hostname, process ID, and thread ID in trace metadata. OTF2 SystemTree captures node/socket/core topology. |
| **Gaps** | No concept of human user identity in traces. No experiment/job ID binding (Slurm job_id not recorded by default). No AI/ML model identity or training run correlation. Rank IDs are ephemeral — no persistent process identity across runs. No identity federation across trace files from different runs. No attribution to source code commits or build versions. |
| **Implementations must add** | Job scheduler identity binding (Slurm/PBS/LSF job_id), experiment tracking integration, source/build version recording, persistent workflow identity across restarts, user identity in trace metadata. |

### Reliability

**Rating: Moderate**

| Aspect | Assessment |
|--------|------------|
| **Strengths** | Per-process trace streams avoid single-point-of-failure (each rank writes independently). Buffer management prevents memory exhaustion (configurable limits, flush-on-full). Score-P gracefully degrades — if buffer fills, it either flushes to disk or switches to profiling-only mode. OTF2 anchor file + per-rank event files mean partial traces are still readable. SION parallel I/O library available for coordinated high-bandwidth writes. Proven reliable at 100k+ process scale on production supercomputers. |
| **Gaps** | Post-mortem design means trace data is lost if application crashes before finalize (no incremental safe-point). Buffer overflow discards events silently in some configurations. No delivery guarantees to external systems. Trace files can grow unbounded without filtering (disk exhaustion on shared filesystems). No replication or redundancy of trace data. Clock synchronization issues between nodes produce negative-duration events that confuse analysis tools. Application abort (MPI_Abort, SIGKILL) can leave corrupted partial traces. |
| **Implementations must add** | Periodic trace checkpointing, crash-safe incremental writes, buffer overflow alerting, disk space pre-flight checks, clock skew detection and correction, graceful handling of abnormal termination. |

### Accuracy

**Rating: Strong**

| Aspect | Assessment |
|--------|------------|
| **Strengths** | Hardware timestamp counters (RDTSC on x86, CNTVCT on ARM) provide sub-nanosecond resolution. OTF2 records exact byte counts for all MPI messages (not estimates). PMPI interposition captures every MPI call — no sampling, no missed events. OMPT callbacks are invoked by the runtime at exact program points — deterministic, not statistical. Score-P's clock synchronization (linear interpolation between MPI_Barrier timestamps) corrects inter-node clock drift. MPI communication events form verifiable pairs (every Send has a matching Recv). CUBE profiles maintain exact call-path attribution with visit counts. |
| **Gaps** | Clock synchronization adds 0.1–10 μs uncertainty at node boundaries (depends on synchronization frequency). Compiler instrumentation overhead (50–150 ns) shifts timestamps for very short functions. Filtering removes events that cannot be recovered — analysis of filtered traces is incomplete. Thread migration between cores can cause RDTSC drift on older hardware (mitigated by invariant TSC on modern CPUs). MPI_T variable semantics vary between implementations — same named variable may measure different things in OpenMPI vs. MPICH. |
| **Implementations must add** | Overhead-compensated timestamps, cross-implementation MPI_T semantics standardization, continuous clock synchronization (not just at barriers), trace completeness metadata (what was filtered). |

---

## Assessment Summary

| Dimension | Rating | Key Gap |
|-----------|--------|---------|
| Observability | Strong | Post-mortem only; no real-time streaming; no cloud-native integration |
| Security | Weak | No encryption, no access control beyond POSIX; HPC trust model assumes shared environment |
| Identity | Partial | Rank/thread IDs present; no user, job, or experiment identity binding |
| Reliability | Moderate | Crash before finalize loses data; buffer overflow silent; no incremental checkpointing |
| Accuracy | Strong | Sub-nanosecond timestamps; exact byte counts; deterministic event capture; clock sync adds μs uncertainty at boundaries |
