from contextlib import redirect_stdout
import copy
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import httpx
from mcp import StdioServerParameters
from mcp.server.fastmcp import FastMCP

import generate
from wg_toolkit.common import error_message, write_private_json
from wg_toolkit.lfx import LfxClient, LfxConfig
from wg_toolkit.llm import ModelConfig
from wg_toolkit.transcripts import TranscriptDownloader


WG = generate.WorkingGroup()
MEETING = {
    "id": "meeting-1", "meeting_and_occurrence_id": "meeting-1",
    "title": generate.MEETING_TITLE, "project_uid": generate.PROJECT_UID,
    "start_time": "2026-09-30T17:00:00Z",
}
VTT = "WEBVTT\n\n1\n00:00:00.000 --> 00:00:02.000\nMatt: We will open an issue.\n"
TRANSCRIPT = [{"source": "vtt-1", "start_seconds": 0, "end_seconds": 2, "text": "Matt: We will open an issue."}]
SOURCES = {
    "meeting": MEETING,
    "ai_summary": {"id": "summary-1", "content": "An issue will be opened.", "edited": False, "approved": False},
    "transcript": TRANSCRIPT,
}
MINUTES = {
    "quick_recap": "The group discussed opening an issue.", "discussion": [], "decisions": [],
    "action_items": [{"task": "Open an issue", "owners": ["Matt"], "due_date": None, "evidence": [0]}],
    "open_questions": [], "references": [], "source_discrepancies": [],
}
MODEL_ENV = {"OPENAI_API_KEY": "test-key", "OPENAI_MODEL": "test-model"}
MODEL_CONFIG = ModelConfig.from_env(MODEL_ENV)
BUNDLE = generate.SourceBundle.from_dict(SOURCES, "2026-09-30", WG)
MOCK_MCP = StdioServerParameters(command=sys.executable, args=[str(Path(__file__).resolve()), "--mock-mcp"], env=dict(os.environ))


def model_response(request: httpx.Request) -> httpx.Response:
    return httpx.Response(200, json={"choices": [{"finish_reason": "stop", "message": {"content": json.dumps(MINUTES)}}]})


class SourceTests(unittest.TestCase):
    def test_full_wg_selection_and_ambiguity(self):
        resources = [{"Data": MEETING}, {"Data": {**MEETING, "id": "fg", "title": "WG Focus Group"}}]
        self.assertEqual(generate.Meeting.select(resources, "2026-09-30", WG).id, "meeting-1")
        with self.assertRaisesRegex(ValueError, "found 0"):
            generate.Meeting.select(resources, "2026-09-29", WG)
        with self.assertRaisesRegex(ValueError, "found 2"):
            generate.Meeting.select(resources + [{"Data": {**MEETING, "id": "other", "meeting_and_occurrence_id": "other"}}], "2026-09-30", WG)
        self.assertEqual(generate.Meeting.select(resources + [{"Data": MEETING}], "2026-09-30", WG).id, "meeting-1")

    def test_other_working_group_selection(self):
        other = generate.WorkingGroup("project-2", "committee-2", "Other WG")
        resources = [{"Data": MEETING}, {"Data": {**MEETING, "id": "m2", "meeting_and_occurrence_id": "m2", "title": "Other WG", "project_uid": "project-2"}}]
        meeting = generate.Meeting.select(resources, "2026-09-30", other)
        self.assertEqual((meeting.id, meeting.committee_uid), ("m2", "committee-2"))
        with self.assertRaisesRegex(ValueError, "Source bundle"):
            generate.SourceBundle.from_dict(SOURCES, "2026-09-30", other)

    def test_summary_precedence_and_missing_summary(self):
        summary = {"id": "s1", "meeting_and_occurrence_id": "meeting-1", "content": "Generated", "edited_content": "Edited", "updated_at": "2026-09-30"}
        self.assertEqual(generate.Summary.select([{"Data": summary}], "meeting-1").content, "Edited")
        self.assertEqual(generate.Summary.select([{"Data": {**summary, "edited_content": " "}}], "meeting-1").content, "Generated")
        with self.assertRaisesRegex(ValueError, "No accessible"):
            generate.Summary.select([{"Data": summary}], "other")

    def test_source_validation(self):
        self.assertEqual(BUNDLE.to_dict()["transcript"], TRANSCRIPT)
        for sources in [{**SOURCES, "transcript": []}, {**SOURCES, "ai_summary": {}}, {**SOURCES, "meeting": None},
                        {**SOURCES, "transcript": [{**TRANSCRIPT[0], "end_seconds": -1}]},
                        {**SOURCES, "transcript": [{"text": "no timestamps"}]}, []]:
            with self.subTest(sources=sources), self.assertRaisesRegex(ValueError, "Source bundle"):
                generate.SourceBundle.from_dict(sources, "2026-09-30", WG)
        with self.assertRaisesRegex(ValueError, "Source bundle"):
            generate.SourceBundle.from_dict(SOURCES, "2026-09-29", WG)

    def test_schema_and_evidence_validation(self):
        generate.MinutesGenerator.validate(MINUTES, len(TRANSCRIPT))
        with self.assertRaisesRegex(ValueError, "Invalid minutes"):
            generate.MinutesGenerator.validate({**MINUTES, "extra": "invalid"}, len(TRANSCRIPT))
        for evidence in [[1], [-1], [], [True], [0.0]]:
            minutes = copy.deepcopy(MINUTES)
            minutes["action_items"][0]["evidence"] = evidence
            with self.subTest(evidence=evidence), self.assertRaises(ValueError):
                generate.MinutesGenerator.validate(minutes, len(TRANSCRIPT))


class AsyncTests(unittest.IsolatedAsyncioTestCase):
    async def test_generation_sends_both_sources(self):
        def request_handler(request):
            body = json.loads(request.content)
            source_input = json.loads(body["messages"][1]["content"])
            self.assertEqual(source_input["ai_summary"], SOURCES["ai_summary"]["content"])
            self.assertEqual(source_input["transcript"][0]["text"], TRANSCRIPT[0]["text"])
            self.assertTrue(body["response_format"]["json_schema"]["strict"])
            return model_response(request)

        async with httpx.AsyncClient(transport=httpx.MockTransport(request_handler)) as client:
            result = await generate.MinutesGenerator(MODEL_CONFIG, client).generate(BUNDLE)
        self.assertEqual(result["status"], "draft")
        self.assertEqual(result["model"], "test-model")
        self.assertFalse(result["provenance"]["summary_approved"])
        self.assertEqual(len(result["provenance"]["sources_sha256"]), 64)
        self.assertEqual(result["minutes"], MINUTES)

    async def test_schema_invalid_model_output_fails(self):
        response = httpx.Response(200, json={"choices": [{"finish_reason": "stop", "message": {"content": "{}"}}]})
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda request: response)) as client:
            with self.assertRaisesRegex(ValueError, "Invalid minutes"):
                await generate.MinutesGenerator(MODEL_CONFIG, client).generate(BUNDLE)

    async def test_saved_bundle_cli_emits_only_json(self):
        with tempfile.TemporaryDirectory() as directory:
            source_path = Path(directory) / "sources.json"
            write_private_json(source_path, SOURCES)
            output = io.StringIO()
            real_client = httpx.AsyncClient
            with patch("generate.httpx.AsyncClient", side_effect=lambda **kwargs: real_client(transport=httpx.MockTransport(model_response))), redirect_stdout(output):
                await generate.main(["2026-09-30", "--sources", str(source_path)], MODEL_ENV)
            self.assertEqual(json.loads(output.getvalue())["minutes"], MINUTES)

    async def test_cli_working_group_flags(self):
        with patch.object(generate, "retrieve_sources", side_effect=ValueError("stop")) as retrieve, self.assertRaisesRegex(ValueError, "stop"):
            await generate.main(["2026-09-30", "--project-uid", "p", "--committee-uid", "c", "--meeting-title", "T"], MODEL_ENV)
        self.assertEqual(retrieve.call_args.args[2], generate.WorkingGroup("p", "c", "T"))

    async def test_missing_model_settings_fail_before_lfx_login(self):
        with patch.object(generate, "retrieve_sources") as retrieve, self.assertRaisesRegex(ValueError, "OPENAI_MODEL"):
            await generate.main(["2026-09-30"], {"OPENAI_API_KEY": "test-key"})
        retrieve.assert_not_called()

    async def test_real_stdio_mcp_reports_download_failure_inside_task_group(self):
        with patch.object(LfxClient, "oauth_parameters", return_value=MOCK_MCP):
            try:
                async with LfxClient.connect(LfxConfig(), "oauth") as lfx:
                    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(403))) as client:
                        await generate.fetch_sources(lfx, WG, "2026-09-30", None, TranscriptDownloader(client))
            except ExceptionGroup as error:
                message = error_message(error)
                self.assertIn("Transcript download failed (HTTP 403)", message)
                self.assertNotIn("https://", message)
            else:
                self.fail("Expected the download failure to propagate through the MCP task group")

    async def test_local_transcript_bypasses_unavailable_download(self):
        def reject_download(request):
            self.fail("Local transcript mode must not attempt a remote download")

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "transcript.vtt"
            path.write_text(VTT, encoding="utf-8")
            with patch.object(LfxClient, "oauth_parameters", return_value=MOCK_MCP):
                async with LfxClient.connect(LfxConfig(), "oauth") as lfx:
                    async with httpx.AsyncClient(transport=httpx.MockTransport(reject_download)) as client:
                        result = await generate.fetch_sources(lfx, WG, "2026-09-30", path, TranscriptDownloader(client))
            result.validate("2026-09-30", WG)
            self.assertEqual(result.ai_summary.content, SOURCES["ai_summary"]["content"])
            self.assertEqual(result.transcript[0].text, TRANSCRIPT[0]["text"])

    async def test_real_stdio_mcp_retrieves_summary_and_downloads_transcript(self):
        def download(request):
            self.assertNotIn("authorization", request.headers)
            self.assertEqual(str(request.url), "https://example.org/transcript.vtt")
            return httpx.Response(200, text=VTT)

        with patch.object(LfxClient, "oauth_parameters", return_value=MOCK_MCP):
            async with LfxClient.connect(LfxConfig(), "oauth") as lfx:
                async with httpx.AsyncClient(transport=httpx.MockTransport(download)) as client:
                    result = await generate.fetch_sources(lfx, WG, "2026-09-30", None, TranscriptDownloader(client))
        result.validate("2026-09-30", WG)
        self.assertEqual(result.meeting.id, MEETING["id"])
        self.assertEqual(result.ai_summary.content, SOURCES["ai_summary"]["content"])
        self.assertEqual(result.transcript[0].text, TRANSCRIPT[0]["text"])


def run_mock_mcp():
    server = FastMCP("mock-lfx")

    @server.tool()
    def search_past_meetings(project_uid: str, committee_uid: str, date_from: str, date_to: str, page_size: int) -> dict:
        assert project_uid == generate.PROJECT_UID
        assert committee_uid == generate.COMMITTEE_UID
        assert date_from == "2026-09-30T00:00:00Z"
        return {"resources": [{"Data": MEETING}]}

    @server.tool()
    def search_past_meeting_summaries(past_meeting_id: str, page_size: int) -> dict:
        assert past_meeting_id == MEETING["id"]
        return {"resources": [{"Data": {**SOURCES["ai_summary"], "meeting_and_occurrence_id": MEETING["id"]}}]}

    @server.tool()
    def get_past_meeting(uid: str) -> dict:
        assert uid == MEETING["id"]
        return {"transcript": {"Data": {"recording_files": [{
            "id": "vtt-1", "download_url": "https://example.org/transcript.vtt",
            "file_extension": "VTT", "file_type": "TRANSCRIPT", "status": "completed",
        }]}}}

    server.run(transport="stdio")


if __name__ == "__main__":
    if "--mock-mcp" in sys.argv:
        run_mock_mcp()
    else:
        unittest.main()
