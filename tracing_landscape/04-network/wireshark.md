# AAIF Reference Architecture: Wireshark

| Field | Value |
|-------|-------|
| **Subject** | [Wireshark](https://www.wireshark.org) |
| **Version** | 4.4.x (stable) |
| **Date** | 2026-06-25 |

---

## Objective

Demonstrates how Wireshark provides deep packet inspection and network protocol analysis through a privilege-separated capture engine (dumpcap), a modular dissector framework (3000+ protocols), and structured export capabilities (PCAPNG/JSON/PDML), enabling both real-time network observation and forensic offline analysis.

---

## Scope / Zoom Level

**System layer — network wire capture through protocol dissection to structured output.**

Wireshark captures raw network frames from kernel packet sockets, dissects them through layered protocol parsers, and presents structured field-level data. It operates at the network infrastructure level — observing traffic between systems rather than within them.

---

## Prerequisites

| Component | Version / Pinned | Notes |
|-----------|-----------------|-------|
| Wireshark/TShark | 4.4.x | Core tools |
| dumpcap | 4.4.x (bundled) | Capture engine; requires CAP_NET_RAW |
| libpcap | 1.10+ (Linux/macOS) | Kernel packet capture interface |
| Npcap | 1.70+ (Windows) | Windows capture driver |
| Qt6 | 6.x | GUI only; TShark has no GUI dependency |
| Lua | 5.x (embedded) | For custom dissectors/scripts |
| CAP_NET_RAW or `wireshark` group | — | Required for live capture |

Optional for decryption:
| Component | Purpose |
|-----------|---------|
| SSLKEYLOGFILE | TLS 1.2/1.3 session key log |
| RSA private key | TLS 1.2 (non-DHE only) |
| WPA passphrase | WiFi decryption |
| Keytab | Kerberos decryption |

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          Network                                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                             │
│  │ Ethernet │  │  WiFi    │  │   USB    │  ... (any interface)         │
│  └─────┬────┘  └─────┬────┘  └─────┬────┘                             │
└────────┼──────────────┼─────────────┼───────────────────────────────────┘
         │              │             │
         ▼              ▼             ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    Kernel (AF_PACKET / BPF)                               │
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────┐      │
│  │  PACKET_MMAP ring buffer (zero-copy to userspace)             │      │
│  │  + BPF capture filter (compiled from tcpdump syntax)          │      │
│  └──────────────────────────────────────────────────────────────┘      │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │ mmap read
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│              dumpcap (privilege-separated capture)                        │
│                                                                         │
│  • Runs with CAP_NET_RAW (minimal privilege)                           │
│  • No dissection — only raw packet capture                             │
│  • Ring buffer rotation (-b filesize/duration/files)                   │
│  • Writes PCAPNG to disk or pipe to parent process                     │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │ pipe / file
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│              Wiretap Library (file format abstraction)                    │
│                                                                         │
│  Reads/writes: pcapng, pcap, snoop, ERF, Network Monitor, ~50 formats  │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│              EPAN (Enhanced Packet ANalyzer)                              │
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────┐      │
│  │  Dissector Framework                                          │      │
│  │                                                               │      │
│  │  Frame → Ethernet → IP → TCP → HTTP → ...                   │      │
│  │         (registered dissector tables by port/ethertype/etc.)  │      │
│  │         + Heuristic dissectors (pattern matching)             │      │
│  │         + Lua/C plugin dissectors                             │      │
│  │         3000+ protocol dissectors                             │      │
│  └──────────────────────────────────────────────────────────────┘      │
│                                                                         │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────────┐      │
│  │ Display Filter  │  │ Reassembly      │  │ Expert Info      │      │
│  │ Engine          │  │ Engine          │  │ System           │      │
│  │ (bytecode VM)   │  │ (TCP, IP frag)  │  │ (error/warn/note)│      │
│  └─────────────────┘  └─────────────────┘  └──────────────────┘      │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
                    ┌────────────────┬┼────────────────┐
                    ▼                ▼│                ▼
┌──────────────────┐  ┌─────────────┐│  ┌─────────────────────────────┐
│ Wireshark (GUI)  │  │ TShark (CLI)││  │ Export: JSON / PDML / CSV   │
│ • Packet list    │  │ • Batch     ││  │ • tshark -T json            │
│ • Dissection tree│  │ • Streaming ││  │ • tshark -T pdml            │
│ • Hex dump       │  │ • Statistics││  │ • tshark -T fields -e ...   │
│ • I/O graphs     │  │ • Field ext.││  └─────────────────────────────┘
│ • Flow graphs    │  └─────────────┘│
│ • Stream follow  │                  │
└──────────────────┘                  │
                                      ▼
                              ┌──────────────────┐
                              │ PCAPNG on disk   │
                              │ (ring buffer)    │
                              └──────────────────┘
```

---

## Instrumentation Walkthrough

### What is captured

| Layer | Data | Examples |
|-------|------|----------|
| Link (L2) | Frame headers | Ethernet src/dst MAC, VLAN tags, 802.11 headers |
| Network (L3) | Packet headers | IP src/dst, TTL, DSCP, fragmentation |
| Transport (L4) | Segment headers + state | TCP flags, seq/ack, window, retransmissions, UDP |
| Session/Application (L5-7) | Protocol payloads | HTTP requests/responses, DNS queries, TLS handshakes, SMTP |
| Expert analysis | Inferred state | Retransmissions, out-of-order, window problems, malformed packets |

### The mechanism

1. **Kernel capture**: AF_PACKET socket in promiscuous mode with PACKET_MMAP provides zero-copy ring buffer. BPF filter (compiled from capture filter expression) runs in kernel to pre-filter.

2. **dumpcap extraction**: Reads raw frames from PACKET_MMAP, writes PCAPNG blocks (Enhanced Packet Blocks with timestamps and interface metadata).

3. **Dissector chain**: Each dissector examines its layer, extracts fields into the dissection tree, then calls the next dissector based on type/port lookups in dissector tables.

4. **Display filter evaluation**: After full dissection, display filter bytecode evaluates against the dissection tree to determine visibility.

5. **Reassembly**: TCP reassembly collects segments into a stream; IP fragment reassembly reconstitutes original datagrams. Reassembled data is passed to higher-layer dissectors.

6. **Expert info**: During dissection, anomalies are flagged (retransmissions, checksum errors, protocol violations).

### Data format produced

**PCAPNG** (default) — block-based binary format:
- Section Header Block: byte order, version, options (hardware, OS, tool)
- Interface Description Block: link type, snap length, interface name
- Enhanced Packet Block: timestamp (ns), captured length, original length, raw bytes
- Optional: Decryption Secrets Block, Name Resolution Block, Interface Statistics Block

**Export formats**: JSON (full dissection tree), PDML (XML), CSV (flat fields), C arrays.

---

## Sample Trace Output

### TShark JSON output (one packet)

```json
{
  "_index": "packets-2026-06-25",
  "_source": {
    "layers": {
      "frame": {
        "frame.time": "Jun 25, 2026 14:29:05.123456789 EDT",
        "frame.time_epoch": "1750878545.123456789",
        "frame.len": "583",
        "frame.protocols": "eth:ethertype:ip:tcp:tls:http2"
      },
      "eth": {
        "eth.dst": "00:1a:2b:3c:4d:5e",
        "eth.src": "aa:bb:cc:dd:ee:ff",
        "eth.type": "0x0800"
      },
      "ip": {
        "ip.version": "4",
        "ip.src": "192.168.1.42",
        "ip.dst": "93.184.216.34",
        "ip.proto": "6",
        "ip.ttl": "64",
        "ip.len": "569"
      },
      "tcp": {
        "tcp.srcport": "48210",
        "tcp.dstport": "443",
        "tcp.seq_raw": "1234567890",
        "tcp.ack_raw": "987654321",
        "tcp.flags": "0x0018",
        "tcp.flags.push": "1",
        "tcp.flags.ack": "1",
        "tcp.stream": "5",
        "tcp.len": "517"
      },
      "tls": {
        "tls.record.content_type": "23",
        "tls.record.version": "0x0303",
        "tls.record.length": "512"
      },
      "http2": {
        "http2.stream": "1",
        "http2.type": "1",
        "http2.header.name": ":method",
        "http2.header.value": "GET",
        "http2.header.name": ":path",
        "http2.header.value": "/api/v1/users"
      }
    }
  }
}
```

### TShark field extraction

```
$ tshark -r capture.pcapng -T fields -e frame.time_epoch -e ip.src -e ip.dst -e tcp.dstport -e http.request.uri -Y "http.request"
1750878545.123456789  192.168.1.42  93.184.216.34  80  /index.html
1750878545.234567890  192.168.1.42  93.184.216.34  80  /api/v1/users
1750878546.345678901  192.168.1.100 10.0.0.5       8080  /health
```

### Expert info summary

```
$ tshark -r capture.pcapng -q -z expert
Errors (3)
   Frequency  Group    Protocol  Summary
          2   Malformed TCP      TCP segment with invalid checksum
          1   Protocol  HTTP     Content-Length mismatch

Warnings (45)
   Frequency  Group      Protocol  Summary
         32   Sequence   TCP       Out-Of-Order segment
         13   Sequence   TCP       Retransmission

Notes (1234)
   Frequency  Group      Protocol  Summary
        890   Sequence   TCP       ACKed unseen segment
        344   Chat       HTTP      GET /api/v1/users
```

### PCAPNG block structure (hex dump of Enhanced Packet Block header)

```
06 00 00 00   Block Type: Enhanced Packet Block (0x00000006)
4B 02 00 00   Block Total Length: 587 bytes
00 00 00 00   Interface ID: 0
A5 C3 17 00   Timestamp (High): 0x0017C3A5
7B 2E 59 07   Timestamp (Low):  0x07592E7B → epoch ns
47 02 00 00   Captured Packet Length: 583
47 02 00 00   Original Packet Length: 583
[583 bytes of packet data]
[padding to 32-bit boundary]
4B 02 00 00   Block Total Length (repeated)
```

---

## Cost Profile

### LLM token cost

**Not applicable.** Wireshark is a network protocol analyzer with no AI/LLM component.

### Compute/IO overhead per operation

| Operation | Cost | Notes |
|-----------|------|-------|
| Kernel capture (BPF filter) | Near-zero per packet | Runs in kernel; PACKET_MMAP is zero-copy |
| dumpcap write to disk | I/O-bound | Line-rate at 10Gbps+ with adequate storage |
| Full dissection (per packet) | 1–50 μs | Depends on protocol depth and reassembly state |
| Display filter evaluation | 0.1–5 μs per packet | Bytecode VM; complexity-dependent |
| TCP reassembly | Amortized ~1 μs | Hash table lookup + buffer append |
| JSON export (per packet) | 10–100 μs | String formatting of all fields |

**CPU**: TShark can dissect 200K–1M packets/sec on modern hardware (single-threaded dissection). Capture itself is nearly costless.

### Storage growth rate

| Traffic | Capture Rate | Disk Growth |
|---------|-------------|-------------|
| Idle office network | 100–1000 pps | 1–10 MB/min |
| Web server (100 Mbps) | 10–50K pps | 50–500 MB/min |
| Database traffic (1 Gbps) | 100–500K pps | 500 MB–5 GB/min |
| Full 10 Gbps link | 1–10M pps | 5–60 GB/min |
| Headers only (96-byte snap) | × 0.1–0.2 | Reduces by 5–10× |

Ring buffer mode bounds disk usage: `-b filesize:102400 -b files:10` = max 1 GB.

---

## Validation Criteria

1. **Capture works**: `dumpcap -i eth0 -c 10 -w /tmp/test.pcapng` captures 10 packets without error
2. **Permissions correct**: Non-root user in `wireshark` group can capture (`dumpcap -D` lists interfaces)
3. **Dissection correct**: `tshark -r file.pcapng -Y "tcp"` shows TCP fields; protocol hierarchy makes sense
4. **Display filters work**: `tshark -r file.pcapng -Y "ip.addr == 10.0.0.1"` filters correctly
5. **Expert info populated**: `tshark -r file.pcapng -q -z expert` shows detected anomalies
6. **JSON export valid**: `tshark -r file.pcapng -T json -c 1 | python3 -m json.tool` parses cleanly
7. **TLS decryption**: With SSLKEYLOGFILE set, encrypted traffic shows decrypted HTTP/2 fields

### Quick smoke test

```bash
# Capture 100 packets, then verify dissection
tshark -i eth0 -c 100 -w /tmp/smoke.pcapng
tshark -r /tmp/smoke.pcapng -q -z io,phs
# Verify: protocol hierarchy tree shows expected layers (ETH > IP > TCP/UDP > ...)

# Verify JSON export
tshark -r /tmp/smoke.pcapng -T json -c 1 | python3 -c "import json,sys; json.load(sys.stdin); print('OK')"
```

---

## Limitations / Out of Scope

| Item | Status |
|------|--------|
| Encrypted payload inspection (without keys) | Cannot dissect; shows TLS record layer only |
| Real-time alerting/IDS | Not a security tool; no alert/block capability (use Suricata/Snort) |
| Distributed capture correlation | No built-in multi-probe aggregation (use Arkime/Moloch) |
| Continuous monitoring | Designed for capture-and-analyze, not long-term monitoring |
| Application-layer tracing | Observes network; no process/kernel internal visibility |
| Performance metrics/dashboards | No built-in monitoring (use ntopng/Grafana for that) |
| Large-scale storage | Single file / ring buffer; no built-in indexed storage (use Arkime) |
| Modification/injection | Read-only analysis; cannot modify or inject packets |
| Kernel/system tracing | Network only; no CPU/scheduler/disk visibility |
| AI/ML analysis | No built-in anomaly detection or ML |
| Non-Linux embedded capture | Limited to OS with libpcap/Npcap support |
| Container-native capture | No special container awareness; captures at host NIC level |

---

## Evaluation Assessment

### Observability

**Rating: Strong**

| Aspect | Assessment |
|--------|------------|
| **Strengths** | Deepest possible network visibility — full packet payloads dissected to individual fields. 3000+ protocol dissectors cover virtually all network protocols. Expert info automatically detects anomalies (retransmissions, malformed packets, protocol violations). Rich statistics: conversations, endpoints, I/O graphs, response times. Live capture + offline analysis. JSON/PDML export enables toolchain integration. |
| **Gaps** | Single-node capture only (no distributed correlation). No real-time alerting. No metrics export to monitoring systems. GUI limited to ~1-2M packets. No long-term retention/indexing built-in. |
| **Implementations must add** | Multi-probe correlation (Arkime), metrics export (Prometheus), alerting integration, long-term indexed storage, distributed capture management. |

### Security

**Rating: Moderate**

| Aspect | Assessment |
|--------|------------|
| **Strengths** | Privilege separation: dumpcap runs with minimal CAP_NET_RAW; dissection is unprivileged. Group-based access control for capture. No network services exposed by default. Capture filters reduce data exposure. PCAPNG supports embedded decryption secrets (controlled sharing). |
| **Gaps** | Dissector code is a historical CVE source (complex C parsers). Capture files contain sensitive cleartext data (passwords, tokens, PII) with no built-in redaction. No encryption of PCAPNG files at rest. No audit trail of who captured what. Malicious PCAPNG files can crash dissectors. |
| **Implementations must add** | Capture file encryption, automated PII redaction, dissector sandboxing (process isolation), capture audit logging, malicious pcap detection. |

### Identity Management

**Rating: Weak**

| Aspect | Assessment |
|--------|------------|
| **Strengths** | Network traffic inherently contains identity signals (IP addresses, MAC addresses, HTTP headers, TLS certificates, Kerberos principals). Wireshark makes these visible and filterable. Name resolution maps IPs to hostnames. |
| **Gaps** | No concept of operator identity (who captured/analyzed). No binding between capture session and authenticated user. Identity information in packets is observed, not managed. No session correlation across captures. No AI/agent identity concept. |
| **Implementations must add** | Capture session metadata (operator, purpose, authorization), chain-of-custody for forensic captures, integration with identity management systems for packet-level attribution. |

### Reliability

**Rating: Moderate**

| Aspect | Assessment |
|--------|------------|
| **Strengths** | Ring buffer mode enables continuous bounded capture without disk exhaustion. dumpcap is simple and stable (minimal code). PCAPNG Interface Statistics Block records dropped packet counts. BPF filters reduce load. PACKET_MMAP provides reliable kernel-to-userspace delivery at high rates. |
| **Gaps** | Packet drops at extreme rates (kernel ring buffer overflow) with only statistical reporting. No guaranteed delivery to external systems. Dissector crashes can lose analysis (not capture data). No redundancy or replication. Single-process TShark can't scale beyond one CPU for dissection. No capture resumption after crash. |
| **Implementations must add** | Multi-process capture scaling, redundant capture probes, guaranteed delivery to collection infrastructure, crash-resilient capture state, packet drop alerting. |

### Accuracy

**Rating: Strong**

| Aspect | Assessment |
|--------|------------|
| **Strengths** | Bit-perfect packet capture — raw bytes exactly as on wire. Nanosecond timestamp resolution (PCAPNG). Dissectors maintained by protocol experts — highly accurate parsing. TCP reassembly reconstructs exact byte streams. Expert info detects protocol violations that indicate inaccurate/corrupted data. Checksum verification for IP, TCP, UDP. Two-pass analysis for stateful correctness. |
| **Gaps** | Heuristic dissectors can misidentify protocols (false positive dissection). Truncated captures (snap length) lose payload accuracy. Timestamp accuracy depends on OS clock (not hardware-stamped without special NICs). Tap/mirror port may drop or reorder packets. Encrypted traffic shows only record boundaries, not content. |
| **Implementations must add** | Hardware timestamping (PTP-synchronized NICs), dissector confidence scoring, capture completeness validation, packet reordering detection and correction. |

---

## Assessment Summary

| Dimension | Rating | Key Gap |
|-----------|--------|---------|
| Observability | Strong | Single-node only; no distributed correlation or real-time alerting |
| Security | Moderate | Dissector CVE history; no capture file encryption or PII redaction |
| Identity | Weak | Observes network identity but has no operator/session identity |
| Reliability | Moderate | Packet drops at extreme rates; no redundancy; single-threaded dissection |
| Accuracy | Strong | Heuristic dissector misidentification; timestamp accuracy depends on OS |
