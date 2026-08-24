# AAIF Reference Architecture: MQTT

| Field | Value |
|-------|-------|
| **Subject** | [MQTT](https://mqtt.org) |
| **Version** | 5.0 (OASIS Standard, 2019) |
| **Date** | 2026-08-12 |

---

## Objective

Demonstrates how MQTT provides lightweight publish/subscribe messaging for AI agent infrastructure through a broker-mediated topic hierarchy, QoS delivery guarantees, session persistence, and minimal wire overhead — enabling telemetry collection, command distribution, and inter-agent communication in bandwidth-constrained and high-fan-out environments.

---

## Scope / Zoom Level

**System layer — application-level messaging protocol between agents, sensors, and backends.**

MQTT operates at the application layer (TCP/TLS transport), providing structured message routing between publishers and subscribers via a central broker. It sits above the wire-level capture that Wireshark observes and below the agent-level orchestration frameworks.

---

## Prerequisites

| Component | Version / Pinned | Notes |
|-----------|-----------------|-------|
| MQTT Broker | — | Mosquitto 2.0.x, EMQX 5.x, HiveMQ 4.x, or NanoMQ 0.21+ |
| Protocol version | MQTT 5.0 | Backward-compatible with 3.1.1; 5.0 adds reason codes, shared subscriptions, flow control |
| Transport | TCP 1883 / TLS 8883 | WebSocket transport also common (443/8083) |
| Client library | Paho 2.x / MQTT.js 5.x / rumqtt 0.24+ | Language-specific |
| TLS | 1.2+ | Required for production; mTLS for device identity |
| OS | Linux/macOS/Windows/RTOS | Runs on everything from MCUs to cloud VMs |

Optional:
| Component | Purpose |
|-----------|---------|
| MQTT-SN gateway | Bridges UDP/ZigBee sensors to TCP broker |
| Sparkplug B | Industrial IoT namespace/payload standard over MQTT |
| MQTT Bridge | Broker-to-broker federation |

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          AI Agent Infrastructure                          │
│                                                                         │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐      │
│  │  Agent A   │  │  Agent B   │  │  Sensor N  │  │  Backend   │      │
│  │ (publisher)│  │(subscriber)│  │ (publisher)│  │(sub + pub) │      │
│  └─────┬──────┘  └─────┬──────┘  └─────┬──────┘  └─────┬──────┘      │
└────────┼──────────────┼──────────────┼──────────────┼───────────────────┘
         │ CONNECT      │ SUBSCRIBE    │ PUBLISH      │ PUBLISH/SUBSCRIBE
         │ PUBLISH      │              │              │
         ▼              ▼              ▼              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         TLS 1.3 / TCP                                    │
│         (optional: WebSocket upgrade for browser clients)                │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                          MQTT Broker                                      │
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────┐      │
│  │  Connection Manager                                           │      │
│  │  • Client authentication (username/password, mTLS, JWT)       │      │
│  │  • Session state (Clean Start = false → persistent)           │      │
│  │  • Keep-alive / Will message management                       │      │
│  │  • MQTT 5.0: Session Expiry Interval, Receive Maximum         │      │
│  └──────────────────────────────────────────────────────────────┘      │
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────┐      │
│  │  Topic Router                                                  │      │
│  │  • Hierarchical topic matching: agents/+/telemetry/#           │      │
│  │  • Shared subscriptions: $share/group/topic (load balancing)  │      │
│  │  • Retained messages (last known state per topic)             │      │
│  │  • Topic alias mapping (reduces wire overhead)                │      │
│  └──────────────────────────────────────────────────────────────┘      │
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────┐      │
│  │  QoS Engine                                                    │      │
│  │  • QoS 0: At most once (fire-and-forget)                     │      │
│  │  • QoS 1: At least once (PUBACK handshake)                   │      │
│  │  • QoS 2: Exactly once (4-step PUBREC/PUBREL/PUBCOMP)        │      │
│  │  • Message expiry interval (TTL per message)                  │      │
│  │  • Inflight window (Receive Maximum flow control)             │      │
│  └──────────────────────────────────────────────────────────────┘      │
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────┐      │
│  │  Persistence Layer                                             │      │
│  │  • Retained messages (1 per topic)                            │      │
│  │  • Queued QoS 1/2 messages for offline sessions               │      │
│  │  • Will Delay Interval (grace period before will fires)       │      │
│  └──────────────────────────────────────────────────────────────┘      │
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────┐      │
│  │  Bridge / Cluster                                              │      │
│  │  • Broker-to-broker bridging (topic replication)              │      │
│  │  • Cluster consensus (EMQX: Mria/Mnesia, HiveMQ: Raft)       │      │
│  │  • Geographic distribution via bridge chains                  │      │
│  └──────────────────────────────────────────────────────────────┘      │
└─────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼ Delivery to matched subscribers
┌─────────────────────────────────────────────────────────────────────────┐
│                     Downstream Consumers                                  │
│                                                                         │
│  ┌─────────────┐  ┌─────────────────┐  ┌─────────────────────────┐    │
│  │ Telemetry   │  │ Agent Command   │  │ Time-Series DB          │    │
│  │ Dashboard   │  │ Dispatcher      │  │ (InfluxDB/TimescaleDB)  │    │
│  └─────────────┘  └─────────────────┘  └─────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Wire Protocol

MQTT uses a compact binary framing designed for minimal overhead:

```
┌─────────────────────────────────────────────────┐
│  Fixed Header (2-5 bytes)                        │
│  ┌─────────┬─────────┬────────────────────────┐ │
│  │ Type(4) │ Flags(4)│ Remaining Length (1-4)  │ │
│  └─────────┴─────────┴────────────────────────┘ │
├─────────────────────────────────────────────────┤
│  Variable Header (packet-type specific)          │
│  • Packet Identifier (QoS 1/2)                  │
│  • Properties (MQTT 5.0: key-value pairs)       │
├─────────────────────────────────────────────────┤
│  Payload (packet-type specific)                  │
│  • PUBLISH: application message bytes           │
│  • SUBSCRIBE: topic filter + QoS list           │
│  • CONNECT: Client ID, Will, credentials        │
└─────────────────────────────────────────────────┘
```

Packet types:

| Type | Value | Direction | Purpose |
|------|-------|-----------|---------|
| CONNECT | 1 | C→S | Initiate session |
| CONNACK | 2 | S→C | Connection acknowledgment + session present flag |
| PUBLISH | 3 | Both | Deliver application message |
| PUBACK | 4 | Both | QoS 1 acknowledgment |
| PUBREC | 5 | Both | QoS 2 step 1 |
| PUBREL | 6 | Both | QoS 2 step 2 |
| PUBCOMP | 7 | Both | QoS 2 step 3 |
| SUBSCRIBE | 8 | C→S | Register topic filter |
| SUBACK | 9 | S→C | Subscription acknowledgment |
| UNSUBSCRIBE | 10 | C→S | Remove subscription |
| UNSUBACK | 11 | S→C | Unsubscribe acknowledgment |
| PINGREQ | 12 | C→S | Keep-alive probe |
| PINGRESP | 13 | S→C | Keep-alive response |
| DISCONNECT | 14 | Both | Graceful session termination (5.0: both directions) |
| AUTH | 15 | Both | Extended authentication exchange (5.0) |

---

## Instrumentation Walkthrough

### What Is Captured

| Telemetry Type | Example | Mechanism |
|----------------|---------|-----------|
| Connection events | Client connect/disconnect, auth failures | Broker event hooks ($SYS topics, webhooks) |
| Message flow | Publish/subscribe counts, bytes in/out | Broker metrics (Prometheus exporter) |
| QoS handshake | PUBACK latency, inflight depth | Client/broker instrumentation |
| Topic activity | Messages per topic, subscriber count | $SYS/broker/topics/# or management API |
| Will messages | Client ungraceful disconnect notifications | Broker Last Will and Testament delivery |
| Session state | Persistent session queue depth | Broker management API |

### Broker Observability Surfaces

**$SYS Topics (MQTT-native self-monitoring):**
```
$SYS/broker/clients/connected         → 1247
$SYS/broker/messages/received          → 8429301
$SYS/broker/messages/sent              → 12847562
$SYS/broker/load/messages/received/1   → 2341
$SYS/broker/subscriptions/count        → 5823
$SYS/broker/heap/current               → 47382528
$SYS/broker/uptime                     → "1429832 seconds"
```

**Prometheus Metrics (EMQX/Mosquitto exporter):**
```
# HELP mqtt_messages_received_total Total messages received
mqtt_messages_received_total{qos="0"} 5291034
mqtt_messages_received_total{qos="1"} 2847102
mqtt_messages_received_total{qos="2"} 291165

# HELP mqtt_connections_current Current active connections
mqtt_connections_current 1247

# HELP mqtt_message_delivery_latency_seconds Message delivery latency
mqtt_message_delivery_latency_seconds_bucket{le="0.001"} 4827301
mqtt_message_delivery_latency_seconds_bucket{le="0.01"} 7891204
```

### Client-Side Instrumentation

```python
# Paho MQTT Python client with telemetry hooks
import paho.mqtt.client as mqtt
import time, json

def on_publish(client, userdata, mid, reason_code, properties):
    latency = time.monotonic() - userdata['pending'][mid]
    del userdata['pending'][mid]
    # Emit to local telemetry
    print(f"PUBACK mid={mid} latency_ms={latency*1000:.2f}")

def on_message(client, userdata, msg):
    # Extract correlation data (MQTT 5.0 property)
    correlation = msg.properties.CorrelationData if hasattr(msg.properties, 'CorrelationData') else None
    print(f"RECV topic={msg.topic} qos={msg.qos} len={len(msg.payload)} correlation={correlation}")

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,
                     client_id="agent-telemetry-001",
                     protocol=mqtt.MQTTv5)
client.on_publish = on_publish
client.on_message = on_message
client.user_data_set({'pending': {}})
```

---

## Sample Trace Output

### MQTT 5.0 CONNECT Packet (decoded)

```json
{
  "packet_type": "CONNECT",
  "protocol_name": "MQTT",
  "protocol_version": 5,
  "connect_flags": {
    "clean_start": false,
    "will_flag": true,
    "will_qos": 1,
    "will_retain": false,
    "username_flag": true,
    "password_flag": true
  },
  "keep_alive": 60,
  "properties": {
    "session_expiry_interval": 3600,
    "receive_maximum": 20,
    "maximum_packet_size": 1048576,
    "topic_alias_maximum": 10,
    "authentication_method": "SCRAM-SHA-256"
  },
  "client_id": "agent-inference-us-east-1-0042",
  "will_properties": {
    "will_delay_interval": 30,
    "payload_format_indicator": 1,
    "content_type": "application/json",
    "response_topic": "agents/status/responses"
  },
  "will_topic": "agents/inference/0042/status",
  "will_payload": "{\"status\":\"offline\",\"last_seen\":\"2026-08-12T15:29:00Z\",\"reason\":\"ungraceful_disconnect\"}"
}
```

### Agent Telemetry PUBLISH

```json
{
  "packet_type": "PUBLISH",
  "topic": "agents/inference/0042/telemetry",
  "qos": 1,
  "retain": false,
  "packet_identifier": 4821,
  "properties": {
    "payload_format_indicator": 1,
    "content_type": "application/json",
    "message_expiry_interval": 300,
    "correlation_data": "trace-7f3a2b1c-9d4e",
    "user_property": [
      ["agent_type", "inference"],
      ["model", "llama-3.1-70b"],
      ["region", "us-east-1"]
    ]
  },
  "payload": {
    "timestamp": "2026-08-12T15:29:34.025Z",
    "tokens_processed": 2847,
    "inference_latency_ms": 142.7,
    "gpu_utilization": 0.87,
    "queue_depth": 3,
    "memory_used_gb": 38.2
  }
}
```

### Shared Subscription (Load-Balanced Consumers)

```
Topic filter: $share/telemetry-processors/agents/+/telemetry/#

Subscribers in group "telemetry-processors":
  - processor-001 (receives ~33% of messages)
  - processor-002 (receives ~33% of messages)
  - processor-003 (receives ~33% of messages)
```

---

## Topic Namespace Design for AI Agent Infrastructure

```
agents/
├── {agent-id}/
│   ├── telemetry          # Metrics: tokens, latency, GPU, memory
│   ├── status             # Online/offline/degraded (retained)
│   ├── commands           # Inbound: scale, reconfigure, shutdown
│   ├── responses          # Command acknowledgments
│   └── traces/            # Distributed trace spans
│       └── {trace-id}
├── orchestrator/
│   ├── assignments        # Task → agent routing decisions
│   ├── scaling            # Autoscaler decisions
│   └── health             # Cluster health aggregation
└── $SYS/                  # Broker self-monitoring
    └── broker/
        ├── clients/
        ├── messages/
        └── load/
```

---

## Cost Profile

| Dimension | Value | Notes |
|-----------|-------|-------|
| Wire overhead per message | 2-5 bytes fixed header | Minimal vs HTTP (hundreds of bytes of headers) |
| Topic alias (MQTT 5.0) | 2 bytes replaces full topic string | After initial mapping; saves bandwidth on repeated publishes |
| TLS handshake | ~2 KB + 1 RTT (session resumption) | One-time per connection; connections are long-lived |
| Broker memory per connection | ~5-20 KB | Varies by implementation; session state dominates |
| Broker memory per retained message | Message size + topic + metadata | One retained message per topic |
| QoS 0 CPU overhead | Negligible | No persistence, no acknowledgment |
| QoS 1 CPU overhead | 1 disk write + 1 ACK packet | Broker persists until PUBACK |
| QoS 2 CPU overhead | 2 disk writes + 3 extra packets | Exactly-once requires 4-step handshake |
| Throughput (single broker) | 100K-1M+ msg/s | Depends on QoS, message size, hardware |
| Storage (persistent sessions) | Proportional to offline queue depth | Configurable max queue per client |
| LLM token cost | None | Protocol-level; no LLM involvement |

### Comparison to Alternatives

| Protocol | Header Overhead | Connection Model | Delivery Guarantee |
|----------|----------------|------------------|--------------------|
| MQTT | 2-5 bytes | Long-lived TCP | QoS 0/1/2 |
| HTTP/REST | ~200-800 bytes | Per-request | Application-level retries |
| gRPC | ~9 bytes framing + HTTP/2 | Long-lived HTTP/2 | Application-level |
| AMQP | ~8 bytes | Long-lived TCP | Publisher confirms |
| WebSocket | 2-14 bytes | Long-lived TCP | None (application must add) |

---

## Validation Criteria

### Smoke Test

```bash
# 1. Start broker (Mosquitto)
mosquitto -c /etc/mosquitto/mosquitto.conf -v

# 2. Subscribe in terminal 1
mosquitto_sub -h localhost -t 'agents/+/telemetry' -v --mqtt-version 5

# 3. Publish in terminal 2
mosquitto_pub -h localhost -t 'agents/test-001/telemetry' \
  -m '{"tokens":100,"latency_ms":42.1}' \
  -q 1 --mqtt-version 5 \
  -D PUBLISH user-property agent_type inference \
  -D PUBLISH content-type application/json

# 4. Verify: subscriber receives message with properties
# Expected output:
# agents/test-001/telemetry {"tokens":100,"latency_ms":42.1}
```

### QoS Validation

```bash
# Verify QoS 2 exactly-once delivery
# Subscribe with QoS 2
mosquitto_sub -h localhost -t 'test/qos2' -q 2 -C 1 -v

# Publish with QoS 2
mosquitto_pub -h localhost -t 'test/qos2' -m "exactly-once" -q 2

# Verify: exactly one message received (no duplicates)
```

### Session Persistence Validation

```bash
# 1. Subscribe with persistent session (Clean Start = false)
mosquitto_sub -h localhost -t 'test/persist' -q 1 \
  -i "persistent-client" --mqtt-version 5 \
  -D CONNECT session-expiry-interval 3600
# Ctrl+C to disconnect

# 2. Publish while client is offline
mosquitto_pub -h localhost -t 'test/persist' -m "queued-message" -q 1

# 3. Reconnect — should receive queued message immediately
mosquitto_sub -h localhost -t 'test/persist' -q 1 \
  -i "persistent-client" --mqtt-version 5 \
  -D CONNECT session-expiry-interval 3600
# Expected: receives "queued-message" on reconnect
```

### Retained Message Validation

```bash
# Publish retained message (last known state)
mosquitto_pub -h localhost -t 'agents/test-001/status' \
  -m '{"status":"online"}' -r -q 1

# New subscriber immediately gets retained state
mosquitto_sub -h localhost -t 'agents/+/status' -C 1 -v
# Expected: immediately receives agents/test-001/status {"status":"online"}
```

---

## Limitations / Out of Scope

| Limitation | Impact | Mitigation |
|------------|--------|------------|
| No built-in message schema | Payload is opaque bytes; no validation at protocol level | Use Sparkplug B, JSON Schema validation at application layer, or broker plugins |
| No request/response primitive (native) | Must implement via correlation data + response topics | MQTT 5.0 adds Response Topic + Correlation Data properties |
| Single broker = SPOF | Broker failure loses all active sessions | Cluster deployment (EMQX, HiveMQ) or active-passive failover |
| No message replay / event sourcing | Cannot replay historical messages from broker | Persist to Kafka/Pulsar/DB; broker is router, not store |
| Topic explosion risk | Millions of unique topics degrades routing performance | Careful namespace design; use wildcards for monitoring |
| No built-in authorization model | Topic-level ACLs vary by broker implementation | Broker-specific ACL plugins; no standard ACL format |
| No end-to-end encryption | TLS terminates at broker; broker sees plaintext | Application-layer encryption for sensitive payloads |
| Ordering guarantee: per-client only | Messages from different publishers to same topic may interleave | Use sequence numbers in payload for multi-publisher ordering |
| Maximum payload: 256 MB | Spec limit; brokers typically cap lower (1-4 MB default) | Stream large data via object storage + MQTT notification |
| No native backpressure to publishers | Slow subscribers queue at broker; can cause OOM | Configure max queue depth, message expiry; use shared subscriptions |

---

## AAIF Evaluation

### Observability — Strong

MQTT brokers provide extensive self-monitoring capabilities:

**Strengths:**
- $SYS topic tree exposes broker internals via the protocol itself — you can monitor MQTT *with* MQTT
- Prometheus exporters available for all major brokers (Mosquitto, EMQX, HiveMQ)
- MQTT 5.0 user properties enable application-level metadata without payload changes
- Retained messages provide "last known state" queries without additional infrastructure
- Wireshark includes a full MQTT dissector for wire-level debugging
- Client libraries expose callback hooks for publish latency, connection state, and QoS handshakes

**Gaps:**
- No standardized distributed tracing propagation (must use user properties or correlation data manually)
- $SYS topics are not standardized across implementations — monitoring dashboards are broker-specific
- No built-in alerting; must export to external systems

### Security — Moderate

**Strengths:**
- TLS 1.2/1.3 for transport encryption with mTLS for client certificate authentication
- MQTT 5.0 AUTH packet enables challenge-response (SCRAM-SHA-256, OAuth token exchange)
- Username/password, client certificate, and JWT-based authentication all supported
- Will messages can notify when clients disconnect unexpectedly (availability monitoring)

**Gaps:**
- No end-to-end encryption — broker sees all message content in plaintext
- Topic-level ACLs are broker-specific (no standard format across implementations)
- No built-in audit logging standard; depends on broker implementation
- No message-level signing or integrity verification at protocol level
- Shared subscriptions expose messages to any group member without per-message authorization

### Identity Management — Moderate

**Strengths:**
- Client ID provides unique session identity (required, unique per broker)
- mTLS binds connections to X.509 certificate identities
- MQTT 5.0 Auth Method property supports pluggable authentication mechanisms
- Will messages announce identity departure to subscribers
- User properties can carry identity metadata (agent type, region, deployment ID)

**Gaps:**
- Client ID is self-asserted unless validated by authentication layer
- No built-in identity federation across broker clusters
- No standard principal-to-topic mapping (ACL rules are implementation-specific)
- Session takeover (same Client ID reconnects) has no standard notification mechanism
- No built-in human/AI identity distinction — all clients are equal at protocol level

### Reliability — Strong

**Strengths:**
- Three QoS levels cover fire-and-forget through exactly-once delivery
- Persistent sessions queue messages for offline clients (survives disconnection)
- Will messages guarantee disconnect notification (even on TCP timeout)
- MQTT 5.0 Session Expiry Interval provides deterministic session cleanup
- Keep-alive mechanism detects dead connections within 1.5× keep-alive interval
- Message Expiry Interval prevents stale message delivery
- Shared subscriptions provide consumer-group semantics for load balancing

**Gaps:**
- Ordering is per-publisher only; no global ordering guarantee
- No built-in deduplication beyond QoS 2 (which is per-flow, not per-content)
- Broker restart may lose in-flight QoS 0 messages (depends on persistence config)
- No native backpressure — slow consumers cause broker queue growth
- QoS 2 exactly-once is expensive (4-packet handshake per message) and rarely used at scale

### Accuracy — Moderate

**Strengths:**
- QoS 2 guarantees exactly-once delivery semantics at protocol level
- Payload Format Indicator (MQTT 5.0) distinguishes UTF-8 text from binary
- Content-Type property enables accurate deserialization
- Retained messages guarantee latest-value accuracy for state queries
- CONNACK Session Present flag tells client whether prior session state exists

**Gaps:**
- No payload validation at broker level — invalid JSON/corrupt data is delivered as-is
- No schema registry integration at protocol level
- Timestamps are application-layer only — protocol has no built-in message timestamp
- Topic alias mapping could be corrupted by buggy clients (broker-dependent validation)
- No checksum or integrity field in wire protocol (relies on TCP checksum)

---

## Summary

| Dimension | Rating | Key Gap |
|-----------|--------|---------|
| Observability | Strong | No standardized distributed tracing propagation; $SYS topics not uniform |
| Security | Moderate | No end-to-end encryption; broker sees plaintext; ACLs are non-standard |
| Identity | Moderate | Client ID is self-asserted; no identity federation standard |
| Reliability | Strong | No global ordering; no native backpressure to publishers |
| Accuracy | Moderate | No payload validation; no protocol-level timestamps or checksums |

---

## AI Agent Infrastructure Relevance

MQTT is particularly well-suited for AI agent infrastructure because:

1. **Fan-out efficiency**: A single telemetry publish reaches all monitoring subscribers without per-subscriber connections
2. **Presence detection**: Will messages + retained status topics create a lightweight agent registry
3. **Command dispatch**: Topic hierarchy maps naturally to agent addressing (`agents/{id}/commands`)
4. **Bandwidth efficiency**: 2-byte overhead for QoS 0 enables high-frequency metrics from edge inference nodes
5. **Session persistence**: Agents survive network partitions; queued messages deliver on reconnection
6. **Shared subscriptions**: Load-balance inference requests across agent pools without external load balancer
7. **Edge-to-cloud**: Same protocol works from Raspberry Pi inference nodes to cloud orchestrators
