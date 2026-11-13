# WG Toolkit

Reusable Python building blocks for AAIF working group scripts that read LFX
meeting data. The [meeting minutes generator](../meeting-minutes/) is built on
it; other WGs can use it for minutes, reports, attendance summaries, or any
other workflow over LFX MCP data.

| Module | Provides |
| --- | --- |
| `wg_toolkit.lfx` | `LfxConfig`, `LfxClient`: LFID OAuth through the documented `mcp-remote` bridge or a bearer token, tool lookup by name suffix, `collect_pages` pagination |
| `wg_toolkit.transcripts` | `Cue` WebVTT/plain-text parsing, `TranscriptDownloader`: direct Zoom VTT download with a headless Playwright fallback via the recording player |
| `wg_toolkit.llm` | `ModelConfig`, `StructuredModelClient`: one strict JSON Schema completion from an OpenAI-compatible Chat Completions endpoint |
| `wg_toolkit.common` | Date and HTTPS URL validation, owner-only no-overwrite JSON output, credential-safe CLI error messages |

Authentication behavior, the security constraints, and the Zoom fallback's
limits are documented in the
[meeting minutes README](../meeting-minutes/README.md#lfx-authentication);
they apply unchanged to any script using this toolkit.

## Use From Another Script

Add a path dependency (or a git dependency once this moves to a shared repo)
to your script's `pyproject.toml`:

```toml
[project]
dependencies = ["wg-toolkit[browser]"]  # drop [browser] if you never need the Zoom fallback

[tool.uv.sources]
wg-toolkit = { path = "../wg-toolkit", editable = true }
```

Then, for example, list a committee's past meetings:

```python
import asyncio, os
from wg_toolkit.lfx import LfxClient, LfxConfig

async def main():
    config = LfxConfig.from_env(os.environ)
    async with LfxClient.connect(config, config.default_auth) as lfx:
        meetings = await lfx.collect_pages("search_past_meetings", {
            "project_uid": "<project-uid>", "committee_uid": "<committee-uid>",
            "date_from": "2026-09-01T00:00:00Z", "date_to": "2026-09-30T23:59:59Z",
        })
    for meeting in meetings:
        print(meeting["Data"]["start_time"], meeting["Data"]["title"])

asyncio.run(main())
```

`LfxConfig.from_env` withholds `LFX_MCP_TOKEN` and `OPENAI_API_KEY` from the
`mcp-remote` helper process; pass `extra_secrets={"MY_TOKEN"}` to withhold
other variables your script reads.

Structured model output:

```python
from wg_toolkit.llm import ModelConfig, StructuredModelClient

async with httpx.AsyncClient(timeout=300) as client:
    result = await StructuredModelClient(ModelConfig.from_env(os.environ), client).complete(
        "my_output", schema, system_prompt, user_content)
```

The model client checks transport, refusal, and truncation, and decodes the
JSON. Validate `result` against your schema yourself, since providers differ
in how strictly they enforce it.

## Tests

```sh
uv run --project scripts/wg-toolkit python -m unittest discover -s scripts/wg-toolkit/tests -v
```

Tests use mocked HTTP and model responses and need no credentials, Node.js,
or Chromium.
