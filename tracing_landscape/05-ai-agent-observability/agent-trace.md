# AAIF Reference Architecture: Agent Trace

| Field | Value |
|-------|-------|
| **Subject** | [Agent Trace](https://github.com/cursor/agent-trace) |
| **Spec Version** | 0.1.0 (RFC) |
| **Date** | 2026-06-25 |

---

## Objective

Demonstrates how AI coding agents emit line-level code attribution traces using the Agent Trace open specification, enabling vendor-neutral tracking of which AI models produced which lines of code within a version-controlled repository.

---

## Scope / Zoom Level

**Inside a single invocation (primitive layer).**

One agent session performing file edits → trace records appended to `.agent-trace/traces.jsonl`. This covers the write path only: hook event fires, trace record is created and persisted. Querying/aggregation is out of scope.

---

## Prerequisites

| Component | Version / Pinned | Notes |
|-----------|-----------------|-------|
| Agent Trace spec | 0.1.0 | RFC status |
| Bun runtime | latest | Required for reference hook |
| Cursor | ≥ 2.4.0 | Provides `afterFileEdit`, `afterTabFileEdit`, `afterShellExecution`, `sessionStart/End` hooks |
| Claude Code | any | Provides `PostToolUse`, `SessionStart/End` hooks |
| VCS | git (or jj, hg, svn) | For revision binding |
| Storage | Local filesystem | `.agent-trace/traces.jsonl` (JSONL append) |

No external collector backend required — Agent Trace is a local-first data format. Downstream consumers (dashboards, CI gates) are implementation-defined.

---

## Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────────┐
│                        AI Coding Agent (Cursor / Claude Code)         │
│                                                                      │
│  ┌────────────┐    ┌────────────┐    ┌────────────┐                 │
│  │ File Edit  │    │ Tab Edit   │    │   Shell    │                 │
│  │   Action   │    │   Action   │    │  Execution │                 │
│  └─────┬──────┘    └─────┬──────┘    └─────┬──────┘                 │
│        │                  │                  │                        │
│        ▼                  ▼                  ▼                        │
│  ┌─────────────────────────────────────────────────┐                 │
│  │              Hook Event (stdin JSON)             │                 │
│  │  {hook_event_name, model, file_path, edits...}  │                 │
│  └─────────────────────────┬───────────────────────┘                 │
└────────────────────────────┼─────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────┐
│              trace-hook.ts (dispatcher)           │
│                                                  │
│  1. Parse stdin JSON                             │
│  2. Route by hook_event_name                     │
│  3. Compute range positions from edits           │
│  4. Resolve model_id (models.dev convention)     │
└────────────────────────┬─────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────┐
│              trace-store.ts (storage)             │
│                                                  │
│  1. getWorkspaceRoot()                           │
│  2. getVcsInfo() → {type: "git", revision: SHA} │
│  3. getToolInfo() → {name: "cursor", version}   │
│  4. createTrace() → TraceRecord                  │
│  5. appendTrace() → write JSONL line             │
└────────────────────────┬─────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────┐
│         .agent-trace/traces.jsonl                 │
│                                                  │
│  {"version":"0.1.0","id":"...","timestamp":...}  │
│  {"version":"0.1.0","id":"...","timestamp":...}  │
│  ...                                             │
└──────────────────────────────────────────────────┘
```

### Telemetry Emission Points

| Point | Trigger | Data Captured |
|-------|---------|---------------|
| File edit | `afterFileEdit` / `PostToolUse(Write/Edit)` | File path, line ranges, model_id, conversation_id |
| Tab completion | `afterTabFileEdit` | File path, line ranges, model_id |
| Shell execution | `afterShellExecution` / `PostToolUse(Bash)` | Command, duration, model_id |
| Session boundary | `sessionStart` / `sessionEnd` | Session ID, composer mode, duration |

---

## Instrumentation Walkthrough

### What is instrumented

The agent's **write operations** — every action that modifies the codebase or executes commands on behalf of the user.

### How

1. **Hook registration**: The agent platform (Cursor/Claude Code) invokes `trace-hook.ts` via stdin pipe after each qualifying action
2. **Event dispatch**: `trace-hook.ts` matches `hook_event_name` to a handler
3. **Range computation**: For file edits, `computeRangePositions()` determines the 1-indexed line range by:
   - Using explicit `range` from the edit if provided
   - Falling back to `indexOf(new_string)` in file content to find position
   - Final fallback: `{start_line: 1, end_line: lineCount}`
4. **Model normalization**: `normalizeModelId()` prefixes bare model names with provider (e.g., `claude-sonnet-4-20250514` → `anthropic/claude-sonnet-4-20250514`)
5. **VCS binding**: `getVcsInfo()` runs `git rev-parse HEAD` to pin the trace to a commit
6. **Persistence**: `appendTrace()` writes one JSON line to `.agent-trace/traces.jsonl`

### Telemetry produced

Each hook invocation produces exactly **one Trace Record** (one JSONL line). The record contains:
- Spec version, UUID, timestamp
- VCS revision at time of trace
- Tool identity (agent name + version)
- One or more file entries with conversation-grouped line ranges
- Contributor type and model_id
- Optional metadata (conversation_id, generation_id, command, duration)

---

## Sample Trace Output

### File edit trace (Cursor, afterFileEdit)

```json
{
  "version": "0.1.0",
  "id": "a3f7c291-4e82-4b1a-9d05-6f8e2c4a7b30",
  "timestamp": "2026-06-25T18:15:32.441Z",
  "vcs": {
    "type": "git",
    "revision": "e4a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9"
  },
  "tool": {
    "name": "cursor",
    "version": "2.4.1"
  },
  "files": [
    {
      "path": "src/handlers/auth.ts",
      "conversations": [
        {
          "url": "file:///tmp/cursor-transcripts/conv-12345.json",
          "contributor": {
            "type": "ai",
            "model_id": "anthropic/claude-sonnet-4-20250514"
          },
          "ranges": [
            { "start_line": 15, "end_line": 42 },
            { "start_line": 88, "end_line": 103 }
          ]
        }
      ]
    }
  ],
  "metadata": {
    "conversation_id": "conv-12345",
    "generation_id": "gen-67890"
  }
}
```

### Shell execution trace (Claude Code, PostToolUse)

```json
{
  "version": "0.1.0",
  "id": "b8d2e4f6-1a3c-5e7d-9f0b-2c4d6e8a0b1c",
  "timestamp": "2026-06-25T18:16:01.102Z",
  "vcs": {
    "type": "git",
    "revision": "e4a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9"
  },
  "tool": {
    "name": "claude-code"
  },
  "files": [
    {
      "path": ".shell-history",
      "conversations": [
        {
          "contributor": {
            "type": "ai",
            "model_id": "anthropic/claude-sonnet-4-20250514"
          },
          "ranges": [
            { "start_line": 1, "end_line": 1 }
          ]
        }
      ]
    }
  ],
  "metadata": {
    "session_id": "sess-abc123",
    "tool_name": "Bash",
    "tool_use_id": "tu-xyz789",
    "command": "npm test"
  }
}
```

### Span relationships

Agent Trace does not use distributed tracing spans. Instead, attribution relationships are expressed as:

- **Temporal**: `timestamp` + `vcs.revision` pins the trace to a point in history
- **Conversational**: `conversation.url` links ranges to the originating conversation
- **Hierarchical**: `related[]` links to parent sessions, prompts, or other artifacts
- **Positional**: `ranges[].start_line / end_line` ties attribution to specific code locations

---

## Cost Profile

### Token cost

**Zero additional LLM tokens.** Agent Trace is a post-hoc recording layer — it captures metadata about what the agent already did. No additional model invocations are required.

### Performance overhead

| Operation | Cost | Notes |
|-----------|------|-------|
| Hook invocation | ~5–15ms | Bun process spawn + stdin parse |
| `git rev-parse HEAD` | ~2–5ms | Subprocess call per trace |
| Range computation | <1ms | String indexOf + line counting |
| JSONL append | <1ms | Single filesystem write |
| **Total per edit** | **~10–20ms** | Negligible vs. LLM response time |

### Storage cost

| Metric | Estimate |
|--------|----------|
| Bytes per trace record | ~400–800 bytes |
| Typical session (50 edits) | ~20–40 KB |
| Heavy daily use (500 edits/day) | ~200–400 KB/day |

Storage is bounded by development activity, not model inference. JSONL is compressible (~5:1 with gzip).

---

## Validation Criteria

1. **Trace file exists**: After any agent file edit, `.agent-trace/traces.jsonl` contains a new line
2. **Schema compliance**: Each line validates against the [JSON Schema](https://agent-trace.dev/schemas/v1/trace-record.json) — required fields: `version`, `id`, `timestamp`, `files`
3. **VCS binding**: `vcs.revision` matches `git rev-parse HEAD` at time of edit
4. **Range accuracy**: For a known edit, `start_line`/`end_line` correctly bracket the modified code
5. **Model attribution**: `contributor.model_id` follows `provider/model-name` format per models.dev
6. **Idempotence**: Re-running the same hook event appends a new record (no deduplication — append-only)
7. **Line ownership query**: For any attributed line, the chain `git blame → revision → trace lookup → range match` resolves to the correct contributor

### Quick smoke test

```bash
# After an agent edit in Cursor:
tail -1 .agent-trace/traces.jsonl | python3 -m json.tool
# Verify: version, id, timestamp, files[0].path, files[0].conversations[0].contributor.type
```

---

## Limitations / Out of Scope

| Item | Status |
|------|--------|
| Query/aggregation layer | Not specified — left to implementations |
| Trace compaction / GC | No mechanism defined; JSONL grows unbounded |
| Authentication for trace data | None — local file permissions only |
| Multi-repo traces | Not addressed; traces are per-repository |
| Code ownership / copyright | Explicitly a non-goal of the spec |
| Training data provenance | Non-goal |
| Quality assessment of AI output | Non-goal |
| Rebase/merge conflict resolution | Unspecified; left to future spec revisions |
| Performance at scale (>100K traces) | No indexing; JSONL scan is O(n) |
| Real-time streaming / push | Not supported; append-only file |
| Cross-agent handoff within one conversation | Supported via per-range contributor override, but no formal protocol |
| Hashing algorithm constraint | `murmur3` used in examples but not mandated |
