# WG Meeting Minutes Generator

Retrieve the full Observability & Traceability WG meeting for a UTC date from
LFX, combine its AI summary with the complete transcript, and emit detailed
draft minutes as JSON. Focus-group sessions are excluded. Other WGs can use
the same CLI by passing their own LFX identifiers (see
[Other Working Groups](#other-working-groups)).

LFX MCP access, transcript retrieval, and the structured-output model client
live in the reusable [`wg-toolkit`](../wg-toolkit/) package; this directory
holds only the minutes-specific selection rules, schema, and prompt.

## Setup

Requires [uv](https://docs.astral.sh/uv/) and Python 3.11 or newer (tested
with Python 3.14; uv downloads a matching Python if needed). Dependencies are
declared in `pyproject.toml` and pinned in `uv.lock`. From the repository root:

```sh
uv sync --project scripts/meeting-minutes
uv run --project scripts/meeting-minutes playwright install chromium
```

`uv run` also syncs the environment automatically, so `uv sync` is optional.
HTTPS connections use the operating system's certificate store (via
`truststore`), so TLS-inspecting corporate proxies work without extra setup.

Configure these environment variables in your terminal or a private environment
file. Do not commit credentials. Environment files are not loaded automatically;
export variables yourself or pass `uv run --env-file .env`:

| Variable | Purpose |
| --- | --- |
| `LFX_MCP_URL` | Optional endpoint; defaults to `https://mcp.lfx.dev/mcp` |
| `LFX_MCP_TOKEN` | Optional MCP bearer token; selects direct token mode when set |
| `OPENAI_API_KEY` | Credential for the chosen model provider |
| `OPENAI_MODEL` | Model with JSON Schema structured-output support and enough context for the complete transcript |
| `OPENAI_BASE_URL` | Optional OpenAI-compatible API base URL; defaults to `https://api.openai.com/v1` |

### LFX Authentication

By default, the Python CLI launches the `mcp-remote` OAuth bridge recommended in
the [LFX MCP documentation](https://github.com/linuxfoundation/lfx-mcp#additional-clients-via-mcp-remote).
This helper requires Node.js 20+ and `npx` on your PATH; retrieval and minutes
generation are implemented in Python. `npx --yes` downloads the helper on first
use. The script uses the documented proxy-only client ID and required callback
port `3334`. This ID is public client metadata, not a secret, and is never used
for a direct Python OAuth client.

On first use, the helper opens a browser for Linux Foundation account (LFID)
sign-in. Complete login directly in your browser. Your account must be enabled
for MCP access and have permission to read the WG's artifacts. The helper
manages cached OAuth credentials and token refresh in its own credential store
(normally under `~/.mcp-auth`); this is separate from VS Code's authenticated
session. Keep port `3334` available and avoid concurrent first-time logins.
OAuth bridge mode is restricted to the documented hosted endpoint.

Use `--auth oauth` to explicitly select browser authentication. For a valid
pre-issued access token for the MCP endpoint, set `LFX_MCP_TOKEN` and use
`--auth token`; this path uses Python's Streamable HTTP client directly and
does not need Node.js. Token acquisition and refresh are external in this mode.
Only HTTPS endpoints, or HTTP localhost endpoints for testing, are accepted.

Do not substitute an LFX API token from `lfx auth token` for a hosted MCP access
token. The upstream docs reserve that API token for running the LFX server
locally in stdio mode. The script does not reuse editor credentials, launch a
local LFX server, or implement a new, unregistered OAuth client.

The complete summary and transcript are sent to the configured model provider.
Choose an approved provider for the meeting's access classification. An
OpenAI-compatible provider must implement Chat Completions with
`response_format.type=json_schema`; compatibility with basic chat alone is not
sufficient. Generation may incur model-provider charges.

## Run

```sh
uv run --project scripts/meeting-minutes scripts/meeting-minutes/generate.py \
  2026-09-30 --auth oauth \
  --output meeting-minutes/2026-09-30.json
```

Without `--output`, JSON is written to stdout. Diagnostics go to stderr and
failures return a nonzero exit code. Output files are created with private
permissions and existing files are never overwritten.

The date is matched against LFX's UTC `start_time`. Some existing Markdown
minutes use a different date; supply the LFX UTC date, not the filename's date.
No match or multiple full-WG matches is an error.

LFX MCP returns stored Zoom links, not transcript bytes or a download proxy.
An HTTP 200 response from such a link can still be an HTML login/error page.
The CLI first tries the direct VTT download. If that fails, it automatically
opens the recording's Zoom share/play page in a fresh headless Chromium browser
and captures the VTT transcript response loaded by the player. No manual
download or `--transcript` argument is needed for publicly playable recordings.
Transcript files are matched to their recording sessions by start time.
If Playwright's bundled browser is missing, the CLI tries an installed Google
Chrome with a fresh session instead; it does not use your normal Chrome profile.

The browser route uses Zoom's current player behavior, not a documented Zoom
API, and may need updates if Zoom changes it. It does not reuse your browser
cookies or send LFX/model credentials to Zoom. Recordings that require a login,
passcode, or unavailable transcript still fail explicitly. In those cases,
download the transcript using the authorized LFX/Zoom browser workflow or
request the VTT from the meeting organizer, then supply `--transcript`:

```sh
uv run --project scripts/meeting-minutes scripts/meeting-minutes/generate.py \
  2026-09-30 \
  --transcript /path/to/transcript.vtt \
  --save-sources /path/to/2026-09-30.sources.json \
  --output meeting-minutes/2026-09-30.json
```

`--transcript` accepts WebVTT or plain text. WebVTT preserves timestamps and
speaker text; plain-text paragraphs receive null timestamps. All accessible,
completed audio-transcript VTT files are included when downloading from LFX.
The script does not send the MCP bearer token to Zoom.

To reuse sources without making any LFX requests:

```sh
uv run --project scripts/meeting-minutes scripts/meeting-minutes/generate.py \
  2026-09-30 \
  --sources /path/to/2026-09-30.sources.json \
  --output /path/to/regenerated-minutes.json
```

Source bundles contain meeting metadata, selected summary content, and parsed
transcript cues, not MCP credentials or signed download URLs. Treat source
bundles and output JSON as meeting data; do not publish restricted content.
`--save-sources` writes before generation so sources survive a model failure.
Source bundles from the earlier JavaScript CLI remain usable. Source hashes
are calculated from this implementation's compact JSON serialization; they are
not guaranteed to match hashes produced by a different implementation.

## Other Working Groups

The defaults select the Observability & Traceability WG. To generate minutes
for another WG, pass its LFX project UID, committee UID, and the exact title of
its full-WG meeting (meetings with any other title, such as focus groups, are
excluded):

```sh
uv run --project scripts/meeting-minutes scripts/meeting-minutes/generate.py \
  2026-09-30 \
  --project-uid <project-uid> --committee-uid <committee-uid> \
  --meeting-title "<Exact Meeting Title>" \
  --output /path/to/2026-09-30.json
```

Pass the same flags with `--sources`; saved bundles are checked against the
selected WG's project UID and meeting title.

## JSON Output

The output contains:

- `schema_version`, `status: "draft"`, meeting metadata, generation time, and model.
- `provenance`: summary ID, whether it was edited/approved, and a source SHA-256.
- `minutes.quick_recap`: an overview of the meeting.
- `minutes.discussion`: detailed topics, reasoning, speakers, and evidence.
- `minutes.decisions`: explicit decisions and rationale, not proposals.
- `minutes.action_items`: tasks, owners, due dates, and evidence.
- `minutes.open_questions`: unresolved questions and evidence.
- `minutes.references`: URLs mentioned in the meeting and evidence.
- `minutes.source_discrepancies`: summary/transcript conflicts and evidence.
- `transcript_evidence`: all source cues with indexes, source IDs, timestamps in
  seconds relative to each recording segment, and exact transcript text.

Each substantive item has an `evidence` array of indexes into
`transcript_evidence`. Unknown owners are `[]`; unknown due dates are `null`.
Speaker names are not a verified attendance roster.

The newest accessible nonempty summary is selected; its nonempty
`edited_content` supersedes generated `content`. Both summary and transcript
are required. Inputs are never silently truncated; inputs above 500,000
characters are rejected, and the selected model can have a smaller context
limit. Missing sources, invalid VTT, refused/truncated model output, invalid
JSON, or out-of-range evidence indexes fail without emitting partial minutes.

Schema and index validation do not prove factual accuracy. Human review must
confirm that cited text supports each claim, ownership, and decision before
publication, following the repository's working methods.

## Tests

```sh
uv run --project scripts/meeting-minutes python -m unittest discover \
  -s scripts/meeting-minutes -p 'test_*.py' -v
```

Tests use source fixtures, a real local stdio MCP server, and mocked transcript
downloads and model responses. They cover meeting and summary selection,
working-group overrides, source retrieval, schema/evidence checks, and
saved-bundle CLI output. OAuth helper settings, transcript parsing, the browser
fallback, and model-client failures are tested in
[`wg-toolkit`](../wg-toolkit/README.md#tests). They do not contact LFX or a model
provider and require no credentials, Chromium, or Node.js. Live LFID login and model
generation still require your credentials and browser authorization.