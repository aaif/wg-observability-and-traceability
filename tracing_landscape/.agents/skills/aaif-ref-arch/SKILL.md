---
name: aaif-ref-arch
description: "Produce AAIF reference architecture documents for AI/agent technologies. This skill should be used when analyzing open-source AI agent tools, frameworks, or specifications to produce a structured reference architecture assessment. Triggers include: 'aaif-ref-arch', 'reference architecture', 'aaif analysis', 'evaluate technology', 'architecture assessment', 'analyze this project'."
license: MIT
compatibility: Requires internet access (GitHub API / raw content fetching) and git CLI
runtimes:
  - kiro
metadata:
  version: "0.1.0"
  short_description: Generate structured AAIF reference architecture assessments for AI/agent technologies.
  authors:
    - "Matthew Khouzam"
  roles:
    - solution-architect
    - developer
---

# AAIF Reference Architecture Skill

Produce structured reference architecture documents and evaluation assessments for AI agent technologies, frameworks, and specifications.

## Process

### 1. Gather Source Material

Fetch and read the target project's documentation:

- Clone or fetch README, architecture docs, and schema definitions from the repository
- Identify the core components: data models, APIs, runtime behavior, integration points
- Read reference implementations if available

### 2. Produce Reference Architecture Document

Write a markdown file to the project root following this structure:

```markdown
# AAIF Reference Architecture: {Technology Name}

| Field | Value |
|-------|-------|
| **Subject** | [{Name}]({URL}) |
| **Version** | {version} |
| **Date** | {today} |

## Objective
What this reference architecture demonstrates — one sentence.

## Scope / Zoom Level
Where this sits: inside a single invocation (primitive layer), orchestration layer, or system layer.

## Prerequisites
Pinned versions of all required components: runtimes, extensions, LLM providers, collector backends.

## Architecture Diagram
ASCII diagram showing components, data flows, and telemetry emission points.

## Instrumentation Walkthrough
What was instrumented, how, and what telemetry it produces. Cover:
- What is captured
- The mechanism (hooks, middleware, SDK calls)
- Data format produced

## Sample Trace Output
Actual or realistic JSON/structured output showing attributes and relationships.

## Cost Profile
Token cost and performance overhead for this architecture variant:
- LLM token cost (if any)
- Compute/IO overhead per operation
- Storage growth rate

## Validation Criteria
Concrete checks to confirm it is working correctly. Include a quick smoke test.

## Limitations / Out of Scope
Table of what the technology does not cover.
```

### 3. Produce Evaluation Assessment

After the reference architecture, evaluate the technology across five dimensions:

| Dimension | What to assess |
|-----------|---------------|
| **Observability** | Can you observe the system's behavior? Does it observe itself? Metrics, logs, traces, alerting surfaces |
| **Security** | Access control, integrity, encryption, data leakage vectors, tamper resistance |
| **Identity Management** | Human identity, AI identity, verification, session linking, principal binding |
| **Reliability** | Delivery guarantees, failure modes, recovery, ordering, deduplication, backpressure |
| **Accuracy** | Correctness of captured data, fallback behaviors, validation, semantic precision |

For each dimension:
- Assign a grade: Strong / Moderate / Partial / Weak / Minimal / None
- State key strengths (if any)
- State key gaps
- Note what implementations would need to add

End with a summary table:

```markdown
| Dimension | Rating | Key Gap |
|-----------|--------|---------|
| Observability | ... | ... |
| Security | ... | ... |
| Identity | ... | ... |
| Reliability | ... | ... |
| Accuracy | ... | ... |
```

### 4. Commit

Commit the reference architecture file to the repo with message: `Add AAIF reference architecture for {technology-name}`.

## Writing Style

- Use technical language appropriate for solution architects
- Be direct and specific — name concrete mechanisms, not vague properties
- Grade honestly — most early-stage specs have significant gaps; that's expected
- Distinguish between what the *spec defines* vs what *implementations must add*
- Use ASCII diagrams, not image references
- Include realistic JSON samples with plausible field values
- Keep the document self-contained
