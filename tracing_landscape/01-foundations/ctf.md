# AAIF Reference Architecture: Common Trace Format (CTF)

| Field | Value |
|-------|-------|
| **Subject** | [Common Trace Format](https://diamon.org/ctf/) |
| **Version** | 1.8.3 (stable); 2.0 (draft) |
| **Date** | 2026-06-25 |

---

## Objective

Demonstrates how the Common Trace Format (CTF) specification defines a self-describing binary trace encoding optimized for zero-copy write paths, enabling producers to record high-frequency events at nanosecond precision with minimal overhead by writing native-endian, bit-packed data described by an embedded TSDL metadata stream.

---

## Scope / Zoom Level

**Data format specification — the wire/storage encoding layer beneath tracing infrastructure.**

CTF is not a tool or a runtime; it is the binary format that tracers (LTTng, barectf) produce and readers (babeltrace2, Trace Compass) consume. It defines how trace data is laid out on disk or in ring buffers, how events are typed and packed, and how a reader self-discovers the schema from the trace itself.

---

## Prerequisites

| Component | Version / Pinned | Notes |
|-----------|-----------------|-------|
| CTF specification | 1.8.3 | https://diamon.org/ctf/v1.8.3/ |
| babeltrace2 | 2.0.x | Reference reader/converter |
| Trace producer | Any (LTTng 2.13+, barectf 3.x, custom) | Writes CTF binary |
| Trace Compass | 9.x+ (optional) | GUI analysis |
| barectf | 3.1+ (optional) | Bare-metal CTF code generator |

No runtime dependencies — CTF is a specification. A conforming producer needs only the ability to write binary data.

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         CTF Trace (directory)                             │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  metadata (TSDL text stream)                                     │   │
│  │                                                                  │   │
│  │  • trace { major = 1; minor = 8; uuid = "..."; byte_order = le } │   │
│  │  • clock { name = monotonic; freq = 1000000000; ... }            │   │
│  │  • env { hostname = "..."; tracer_name = "..."; }                │   │
│  │  • stream { id = 0; packet.context := struct { ... }; }          │   │
│  │  • event { name = "sched_switch"; id = 0; fields := struct {...}}│   │
│  │  • event { name = "sys_write"; id = 1; fields := struct {...} }  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────┐      │
│  │  channel0_0 (binary data stream — CPU 0)                      │      │
│  │                                                               │      │
│  │  ┌─────────────────────────────────────────────────────────┐ │      │
│  │  │ Packet 0                                                 │ │      │
│  │  │  ┌─────────────────────────────────────────────────┐    │ │      │
│  │  │  │ Packet Header                                    │    │ │      │
│  │  │  │  magic: 0xC1FC1FC1                               │    │ │      │
│  │  │  │  uuid[16]: trace identity                        │    │ │      │
│  │  │  │  stream_id: 0                                    │    │ │      │
│  │  │  ├─────────────────────────────────────────────────┤    │ │      │
│  │  │  │ Packet Context                                   │    │ │      │
│  │  │  │  timestamp_begin: 1750878545000000000             │    │ │      │
│  │  │  │  timestamp_end:   1750878545105000000             │    │ │      │
│  │  │  │  content_size: 2048000 (bits)                    │    │ │      │
│  │  │  │  packet_size:  2097152 (bits = 256KB)            │    │ │      │
│  │  │  │  events_discarded: 0                             │    │ │      │
│  │  │  │  cpu_id: 0                                       │    │ │      │
│  │  │  ├─────────────────────────────────────────────────┤    │ │      │
│  │  │  │ Event Records (packed binary)                    │    │ │      │
│  │  │  │  [hdr|ctx|payload][hdr|ctx|payload][...]         │    │ │      │
│  │  │  ├─────────────────────────────────────────────────┤    │ │      │
│  │  │  │ Zero-padding to packet_size                      │    │ │      │
│  │  │  └─────────────────────────────────────────────────┘    │ │      │
│  │  ├─────────────────────────────────────────────────────────┤ │      │
│  │  │ Packet 1                                                 │ │      │
│  │  │  [header][context][events...][padding]                   │ │      │
│  │  ├─────────────────────────────────────────────────────────┤ │      │
│  │  │ ...                                                      │ │      │
│  │  └─────────────────────────────────────────────────────────┘ │      │
│  └──────────────────────────────────────────────────────────────┘      │
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────┐      │
│  │  channel0_1 (binary data stream — CPU 1)                      │      │
│  │  [packets...]                                                 │      │
│  └──────────────────────────────────────────────────────────────┘      │
│  ...                                                                    │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                         Producers → CTF                                   │
│                                                                         │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌───────────────┐    │
│  │ LTTng      │  │ LTTng-UST  │  │ barectf    │  │ Custom writer │    │
│  │ (kernel)   │  │ (userspace)│  │ (bare-metal)│  │ (any lang)   │    │
│  └─────┬──────┘  └─────┬──────┘  └─────┬──────┘  └──────┬────────┘    │
│        └────────────────┴───────────────┴─────────────────┘             │
│                                  │                                       │
│                    memcpy native types → ring buffer → CTF files         │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                         CTF → Consumers                                   │
│                                                                         │
│  ┌────────────┐  ┌────────────────┐  ┌───────────────────────────┐    │
│  │ babeltrace2│  │ Trace Compass  │  │ Custom (libbabeltrace2 /  │    │
│  │ (CLI/API)  │  │ (GUI analysis) │  │  Python bt2 bindings)     │    │
│  └────────────┘  └────────────────┘  └───────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Instrumentation Walkthrough

### What is captured (by the format specification)

CTF defines the encoding, not the instrumentation. It specifies how to represent:

| Element | CTF Encoding |
|---------|-------------|
| **Event identity** | Integer `id` in event header; name in metadata only |
| **Timestamps** | Integer fields mapped to declared clocks; arbitrary bit-width (e.g., 27-bit deltas) |
| **Typed payloads** | Integers (1–64 bit), floats, strings, enums, arrays, sequences, structs, variants |
| **Stream identity** | `stream_id` in packet header; one file per stream |
| **Trace identity** | 128-bit UUID in every packet header |
| **Loss detection** | `events_discarded` counter in packet context |
| **Time ranges** | `timestamp_begin`/`timestamp_end` per packet (enables random access) |
| **Environment** | Key-value strings/integers (hostname, tracer, domain) |

### The mechanism (TSDL metadata)

TSDL is a C-like declarative language that describes the binary layout:

```c
/* CTF 1.8 */
typealias integer { size = 32; align = 8; signed = false; } := uint32_t;
typealias integer { size = 64; align = 8; signed = false; } := uint64_t;
typealias integer { size = 27; align = 1; signed = false;
                    map = clock.monotonic.value; } := uint27_clock_t;

clock {
    name = monotonic;
    freq = 1000000000;
    offset_s = 1750000000;
    precision = 0;
    absolute = true;
};

trace {
    major = 1;
    minor = 8;
    uuid = "a1b2c3d4-e5f6-7890-abcd-ef0123456789";
    byte_order = le;
    packet.header := struct {
        uint32_t magic;
        uint8_t  uuid[16];
        uint32_t stream_id;
    };
};

env {
    hostname = "prod-web-01";
    domain = "ust";
    tracer_name = "lttng-ust";
    tracer_major = 2;
    tracer_minor = 13;
};

stream {
    id = 0;
    event.header := struct {
        enum : uint16_t { compact = 0 ... 65534, extended = 65535 } id;
        variant <id> {
            struct { uint27_clock_t timestamp; } compact;
            struct { uint32_t id; uint64_t timestamp; } extended;
        } v;
    } align(8);
    packet.context := struct {
        uint64_t timestamp_begin;
        uint64_t timestamp_end;
        uint64_t content_size;
        uint64_t packet_size;
        uint64_t events_discarded;
        uint32_t cpu_id;
    } align(8);
};

event {
    name = "my_app:request_start";
    id = 0;
    stream_id = 0;
    fields := struct {
        int32_t id;
        string endpoint;
    };
};

event {
    name = "my_app:request_end";
    id = 1;
    stream_id = 0;
    fields := struct {
        int32_t id;
        int32_t status;
        int64_t duration_ns;
    };
};
```

### Data format produced

**Binary, bit-packed, native-endian event records** within self-delimiting packets:

```
Byte offset   Field                    Bits    Encoding
──────────────────────────────────────────────────────────
0x0000        magic                    32      LE uint32: 0xC1FC1FC1
0x0004        uuid                     128     Raw bytes
0x0014        stream_id                32      LE uint32
0x0018        timestamp_begin          64      LE uint64 (ns)
0x0020        timestamp_end            64      LE uint64 (ns)
0x0028        content_size             64      LE uint64 (bits)
0x0030        packet_size              64      LE uint64 (bits)
0x0038        events_discarded         64      LE uint64 (cumulative)
0x0040        cpu_id                   32      LE uint32
──── Event records (bit-packed) ──────────────────────────
0x0044        event[0].header.id       16      enum/uint16 (compact)
0x0046        event[0].header.ts       27 bits delta from timestamp_begin
              event[0].payload         varies  per TSDL event definition
              event[1].header...       ...     ...
──── Padding ─────────────────────────────────────────────
              zeros                    to packet_size boundary
```

---

## Sample Trace Output

### Raw metadata file (TSDL)

```c
/* CTF 1.8 */

typealias integer { size = 8; align = 8; signed = false; } := uint8_t;
typealias integer { size = 16; align = 8; signed = false; } := uint16_t;
typealias integer { size = 32; align = 8; signed = false; } := uint32_t;
typealias integer { size = 64; align = 8; signed = false; } := uint64_t;
typealias integer { size = 32; align = 8; signed = true; } := int32_t;
typealias integer { size = 64; align = 8; signed = true; } := int64_t;

clock {
    name = monotonic;
    freq = 1000000000;
    offset_s = 1750878545;
    offset = 0;
    precision = 0;
    absolute = true;
};

trace {
    major = 1;
    minor = 8;
    uuid = "b2e4f691-3a1c-4e7d-8f0b-1c2d3e4a5b6c";
    byte_order = le;
    packet.header := struct {
        uint32_t magic;
        uint8_t  uuid[16];
        uint32_t stream_id;
    };
};

env {
    hostname = "prod-web-01";
    domain = "ust";
    tracer_name = "lttng-ust";
    tracer_major = 2;
    tracer_minor = 13;
};

stream {
    id = 0;
    event.header := struct {
        enum : uint16_t { compact = 0 ... 65534, extended = 65535 } id;
        variant <id> {
            struct {
                integer { size = 27; map = clock.monotonic.value; } timestamp;
            } compact;
            struct {
                uint32_t id;
                uint64_t timestamp;
            } extended;
        } v;
    } align(8);
    packet.context := struct {
        uint64_t timestamp_begin;
        uint64_t timestamp_end;
        uint64_t content_size;
        uint64_t packet_size;
        uint64_t events_discarded;
        uint32_t cpu_id;
    } align(8);
    event.context := struct {
        int32_t _vpid;
        int32_t _vtid;
        uint8_t _procname[17];
    } align(8);
};

event {
    name = "sched_switch";
    id = 0;
    stream_id = 0;
    fields := struct {
        uint8_t _prev_comm[16];
        int32_t _prev_tid;
        int32_t _prev_prio;
        int64_t _prev_state;
        uint8_t _next_comm[16];
        int32_t _next_tid;
        int32_t _next_prio;
    };
};
```

### babeltrace2 decoded output (text)

```
[14:29:05.847291532] (+0.000012843) prod-web-01 sched_switch: { cpu_id = 0 }, { vpid = 4521, vtid = 4521, procname = "nginx" }, { prev_comm = "nginx", prev_tid = 4521, prev_prio = 20, prev_state = 1, next_comm = "kworker/0:1", next_tid = 42, next_prio = 20 }
```

### Packet-level decoded view (JSON representation)

```json
{
  "packet": {
    "header": {
      "magic": "0xC1FC1FC1",
      "uuid": "b2e4f691-3a1c-4e7d-8f0b-1c2d3e4a5b6c",
      "stream_id": 0
    },
    "context": {
      "timestamp_begin": 1750878545847000000,
      "timestamp_end": 1750878545952000000,
      "content_size_bits": 2048000,
      "packet_size_bits": 2097152,
      "events_discarded": 0,
      "cpu_id": 0
    },
    "events": [
      {
        "header": { "id": 0, "timestamp_delta_27bit": 291532 },
        "stream_event_context": { "vpid": 4521, "vtid": 4521, "procname": "nginx" },
        "payload": {
          "prev_comm": "nginx",
          "prev_tid": 4521,
          "prev_prio": 20,
          "prev_state": 1,
          "next_comm": "kworker/0:1",
          "next_tid": 42,
          "next_prio": 20
        }
      }
    ]
  }
}
```

---

## Cost Profile

### LLM token cost

**Not applicable.** CTF is a binary trace format specification with no AI/LLM component.

### Compute/IO overhead per operation

| Operation | Cost | Notes |
|-----------|------|-------|
| **Write one event** | ~50–150 ns | memcpy of native types; no formatting, no syscalls |
| **Read one event (babeltrace2)** | ~10–50 ns | Binary decode; field offsets precomputed from metadata |
| **Seek to timestamp** | O(log N) | Binary search over packet timestamp_begin fields |
| **Full trace decode** | Multi-GB/s | I/O-bound; decode is trivial pointer arithmetic |
| **Metadata parse (TSDL)** | One-time; <1 ms | Parsed once at trace open |

### Storage efficiency (comparative)

| Format | 1M sched_switch events (~10 fields each) | Ratio vs CTF |
|--------|------------------------------------------|--------------|
| **CTF** | ~50–80 MB | 1× |
| **Protobuf** | ~100–200 MB | 2–3× |
| **JSON (OTLP)** | ~2–5 GB | 40–100× |
| **Text log (formatted)** | ~500 MB – 2 GB | 10–40× |

Key efficiency factors:
- **No field names in data stream** — names exist only in metadata
- **Bit-packing** — a 27-bit timestamp uses 27 bits, not 32 or 64
- **No per-record delimiters** — events are packed sequentially with computed offsets
- **Compact event headers** — variant type allows 27-bit delta timestamps for most events, reserving full 64-bit only when needed

### Storage growth rate (as format)

CTF adds ~50–80 bytes per typical kernel event (including header overhead). At 100K events/sec, growth is ~5–8 MB/sec. The format itself imposes no minimum overhead beyond the data actually captured.

---

## Validation Criteria

1. **Magic number**: First 4 bytes of each data packet are `0xC1FC1FC1`
2. **UUID consistency**: UUID in every packet header matches the trace's declared UUID
3. **Metadata parseable**: `babeltrace2 <trace-dir>` successfully reads without parse errors
4. **Content size ≤ packet size**: `content_size` never exceeds `packet_size` in any packet context
5. **Timestamp monotonicity**: Within a stream, `timestamp_begin` of packet N+1 ≥ `timestamp_end` of packet N
6. **Event count**: Actual events decoded from a packet match the space between context end and `content_size`
7. **Type consistency**: All event payloads conform to their TSDL-declared field types (no truncation, no overflow)
8. **events_discarded monotonic**: Counter is non-decreasing across packets in a stream
9. **Byte order match**: Integer values decode correctly only when using the declared `byte_order`

### Quick smoke test

```bash
# Verify a CTF trace is valid and readable
babeltrace2 /path/to/trace-dir/ | head -5
# Should output decoded event lines with timestamps and field values

# Verify metadata
cat /path/to/trace-dir/metadata | head -3
# Should show "/* CTF 1.8 */" or packetized metadata header

# Verify packet magic (hex dump first 4 bytes of a stream file)
xxd -l 4 /path/to/trace-dir/channel0_0
# Expected: c1fc 1fc1
```

---

## Limitations / Out of Scope

| Item | Status |
|------|--------|
| Instrumentation / tracing runtime | Not in scope — CTF is a format, not a tracer |
| Checksums / data integrity | Not included; relies on transport/filesystem |
| Encryption | Not included; plaintext binary |
| Compression | Not part of spec; can layer gzip/zstd externally |
| Schema evolution / versioning | No formal migration mechanism; metadata is per-trace |
| Query language | Not included; linear scan or external indexing |
| Distributed trace correlation | No trace-context propagation (single-node format) |
| Nested/hierarchical events | Flat event model; no parent-child spans |
| String length prefix | Strings are null-terminated only (CTF 1.8); CTF 2.0 adds length-prefixed |
| JSON metadata | CTF 1.8 uses TSDL only; JSON metadata is CTF 2.0 (draft, not yet ratified) |
| Windows native support | No OS restriction, but tooling is Linux-centric |
| Network transport protocol | Not defined; streaming semantics are implementation-specific (e.g., LTTng relayd) |
| Sampling / filtering | Not part of format; producer-side concern |
| Real-time alerting | Not applicable — CTF is a storage/encoding format |

---

## Evaluation Assessment

### Observability

**Rating: Moderate**

| Aspect | Assessment |
|--------|------------|
| **Strengths** | Self-describing: any CTF trace can be decoded without external schema. Packet-level timestamp ranges enable efficient temporal navigation. `events_discarded` provides explicit loss signal. Rich type system captures full-fidelity event data. Environment block provides trace provenance. Multiple tooling options (babeltrace2, Trace Compass). |
| **Gaps** | CTF is a storage format, not an observability system. No metrics, no alerting, no dashboards. No built-in indexing or query capability. No correlation primitives (no trace IDs, no span links). Requires external tooling for any operational observability use case. |
| **Implementations must add** | Indexing layers, query engines, metrics derivation, alerting pipelines, distributed trace ID support in event payloads. |

### Security

**Rating: Minimal**

| Aspect | Assessment |
|--------|------------|
| **Strengths** | Binary format is not trivially human-readable (slight obscurity). UUID identifies trace provenance. |
| **Gaps** | No encryption defined by specification. No checksums or integrity validation. No signing mechanism. No access control model. No field-level redaction. Trace data is fully exposed to anyone with file access. No authentication for metadata or data streams. |
| **Implementations must add** | Filesystem-level encryption, transport-layer TLS, signed metadata for integrity, field-level access control, data classification/redaction policies. |

### Identity Management

**Rating: None**

| Aspect | Assessment |
|--------|------------|
| **Strengths** | Trace UUID uniquely identifies a trace instance. `env` block can carry hostname and tracer identity. Stream event context can carry PID/TID (implementation-defined, not spec-mandated). |
| **Gaps** | No concept of human, machine, or AI identity in the specification. No session binding. No principal attribution. No authentication of trace producers. UUID identifies a trace, not a person or agent. Identity fields are entirely implementation-defined — the spec provides the type system but mandates no identity semantics. |
| **Implementations must add** | Identity context fields (operator, tenant, service), producer authentication, trace provenance chain, cryptographic binding of trace to authenticated principal. |

### Reliability

**Rating: Moderate**

| Aspect | Assessment |
|--------|------------|
| **Strengths** | Packet-based design enables atomic units of data (complete packet or nothing). `events_discarded` counter allows precise loss quantification. `content_size`/`packet_size` fields enable truncation detection. Packet timestamp ranges enable gap detection between packets. Self-describing metadata means no external dependency for trace recovery. |
| **Gaps** | No checksums — bit rot or corruption undetectable by format alone. No error correction. No redundancy encoding. Ordering is stream-local only; cross-stream ordering requires reader-side merge by timestamp. No delivery guarantees (format has no transport semantics). No deduplication mechanism. |
| **Implementations must add** | Checksums per packet, filesystem/transport integrity verification, cross-stream timestamp synchronization validation, delivery acknowledgment protocols. |

### Accuracy

**Rating: Strong**

| Aspect | Assessment |
|--------|------------|
| **Strengths** | Bit-exact representation: integers of any width stored at declared precision with no rounding or truncation. Clock declarations with explicit frequency and offset enable nanosecond-precise timestamp reconstruction. Typed fields prevent type confusion — metadata declares exact sizes and signedness. Variant types eliminate ambiguity in polymorphic data. Self-describing metadata guarantees reader interprets data exactly as producer intended. No text formatting step that could lose precision. |
| **Gaps** | Clock accuracy depends on hardware/producer — CTF encodes whatever the producer writes. No built-in validation that field values are semantically correct (only structurally correct). TSDL parser implementations may have subtle divergences. Bit-packing across byte boundaries is error-prone to implement. |
| **Implementations must add** | Semantic validation of field ranges, clock calibration verification, conformance test suites for TSDL parsers, producer-side value validation. |

---

## Assessment Summary

| Dimension | Rating | Key Gap |
|-----------|--------|---------|
| Observability | Moderate | Storage format only; no querying, indexing, or alerting |
| Security | Minimal | No encryption, checksums, signing, or access control in spec |
| Identity | None | No identity concepts; UUID identifies traces not principals |
| Reliability | Moderate | No checksums; loss detection via counters but no correction |
| Accuracy | Strong | Bit-exact typed encoding; precision limited only by producer's clock |
