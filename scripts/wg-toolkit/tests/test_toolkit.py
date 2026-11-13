import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import httpx

from wg_toolkit.common import error_message, require_secure_url, validate_date, write_private_json
from wg_toolkit.lfx import LFX_MCP_URL, PROXY_CLIENT_ID, LfxClient, LfxConfig
from wg_toolkit.llm import ModelConfig, StructuredModelClient
from wg_toolkit.transcripts import Cue, TranscriptDownloader


VTT = "WEBVTT\n\n1\n00:00:00.000 --> 00:00:02.000\nMatt: We will open an issue.\n"
CUES = [Cue("vtt-1", 0, 2, "Matt: We will open an issue.")]
MODEL_ENV = {"OPENAI_API_KEY": "test-key", "OPENAI_MODEL": "test-model"}
SCHEMA = {"type": "object", "additionalProperties": False, "properties": {"answer": {"type": "string"}}, "required": ["answer"]}


class CommonTests(unittest.TestCase):
    def test_grouped_errors_keep_messages_and_hide_credentials(self):
        error = ExceptionGroup("task group", [ExceptionGroup("nested", [ValueError("Download failed (HTTP 403).")])])
        self.assertEqual(error_message(error), "Download failed (HTTP 403).")
        error = ExceptionGroup("task group", [RuntimeError("https://secret.example/?token=secret")])
        self.assertNotIn("secret", error_message(error))
        self.assertIn("RuntimeError", error_message(error))
        self.assertNotIn("token", error_message(ValueError("see https://example.org/?token=secret")))

    def test_dates(self):
        for date in ["2026-02-29", "2026-13-01", "26-09-30", "2026-04-31", "2026-9-30"]:
            with self.subTest(date=date), self.assertRaisesRegex(ValueError, "valid date"):
                validate_date(date)
        self.assertEqual(validate_date("2028-02-29"), "2028-02-29")

    def test_secure_urls(self):
        require_secure_url(LFX_MCP_URL, "LFX")
        require_secure_url("http://127.0.0.1:8000/mcp", "LFX")
        for url in ["http://example.org/mcp", "https://user:password@example.org", "file:///tmp/transcript"]:
            with self.subTest(url=url), self.assertRaises(ValueError):
                require_secure_url(url, "LFX")

    def test_private_files_are_not_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "out.json"
            write_private_json(path, {"a": 1})
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            with self.assertRaises(FileExistsError):
                write_private_json(path, {})
            self.assertEqual(json.loads(path.read_text()), {"a": 1})


class LfxTests(unittest.TestCase):
    def test_documented_oauth_proxy_configuration(self):
        env = {**MODEL_ENV, "PATH": "/bin", "LFX_MCP_TOKEN": "secret", "OTHER_SECRET": "x"}
        with patch("wg_toolkit.lfx.shutil.which", return_value="/usr/bin/npx"):
            parameters = LfxClient.oauth_parameters(LfxConfig.from_env(env, extra_secrets={"OTHER_SECRET"}))
        self.assertEqual(parameters.args[0:4], ["--yes", "mcp-remote", LFX_MCP_URL, "3334"])
        self.assertEqual(json.loads(parameters.args[-1]), {"client_id": PROXY_CLIENT_ID})
        for name in ["OPENAI_API_KEY", "LFX_MCP_TOKEN", "OTHER_SECRET"]:
            self.assertNotIn(name, parameters.env)
        self.assertEqual(parameters.env["PATH"], "/bin")
        with self.assertRaisesRegex(ValueError, "only"):
            LfxClient.oauth_parameters(LfxConfig.from_env({"LFX_MCP_URL": "https://other.example/mcp"}))
        with patch("wg_toolkit.lfx.shutil.which", return_value=None), self.assertRaisesRegex(ValueError, "npx"):
            LfxClient.oauth_parameters(LfxConfig())

    def test_config_hides_secrets_and_selects_auth(self):
        config = LfxConfig.from_env({"LFX_MCP_TOKEN": "mcp-secret"})
        self.assertNotIn("mcp-secret", repr(config))
        self.assertEqual(config.default_auth, "token")
        self.assertEqual(LfxConfig.from_env({}).default_auth, "oauth")
        self.assertNotIn("test-key", repr(ModelConfig.from_env(MODEL_ENV)))


class TranscriptTests(unittest.TestCase):
    def test_transcript_file_selection(self):
        file = {"id": "vtt", "download_url": "https://example.org/transcript", "file_extension": "VTT", "file_type": "TRANSCRIPT", "status": "completed"}
        detail = {"transcript": {"Data": {"recording_files": [file, {**file, "file_extension": "JSON"}]}}}
        self.assertEqual(TranscriptDownloader.transcript_files(detail), [file])
        with self.assertRaisesRegex(ValueError, "No accessible VTT"):
            TranscriptDownloader.transcript_files({})

    def test_transcript_parsing(self):
        cue = Cue.parse(VTT)[0]
        self.assertEqual((cue.start_seconds, cue.end_seconds, cue.text), (0, 2, CUES[0].text))
        fractional = Cue.parse(VTT.replace("00:00:00.000", "00:00:01.125").replace("00:00:02.000", "00:00:02.750"))[0]
        self.assertEqual((fractional.start_seconds, fractional.end_seconds), (1.125, 2.75))
        self.assertEqual(len(Cue.parse("Matt: Discussion.\n\nPavan: Follow-up.")), 2)
        self.assertEqual(Cue.parse("\ufeff" + VTT)[0].text, CUES[0].text)
        for text in ["", "<!DOCTYPE html><html>Login</html>", "WEBVTT\n\ninvalid", VTT + "\n2\n00:bad --> 00:00:03.000\nBad cue\n"]:
            with self.subTest(text=text), self.assertRaises(ValueError):
                Cue.parse(text)

    def test_cue_validity(self):
        self.assertTrue(CUES[0].is_valid())
        self.assertTrue(Cue("s", None, None, "text").is_valid())
        for cue in [Cue("s", 0, -1, "t"), Cue("s", 2, 1, "t"), Cue("s", 0, None, "t"), Cue("s", 0, 1, " "), Cue("s", True, 1, "t")]:
            with self.subTest(cue=cue):
                self.assertFalse(cue.is_valid())

    def test_remote_transcript_requires_vtt_and_explains_local_fallback(self):
        request = httpx.Request("GET", "https://example.org/transcript?token=secret")
        for text, content_type in [
            ("<!DOCTYPE html><html>Login</html>", "text/html"),
            ("", "text/vtt"),
            ("Recording does not exist", "text/plain"),
            (VTT, "text/html"),
        ]:
            response = httpx.Response(200, text=text, headers={"content-type": content_type}, request=request)
            with self.subTest(content_type=content_type):
                with self.assertRaisesRegex(ValueError, "--transcript PATH") as raised:
                    Cue.parse_download(response, "vtt-1")
                self.assertNotIn("secret", str(raised.exception))
        response = httpx.Response(200, text=VTT, headers={"content-type": "text/vtt"}, request=request)
        self.assertEqual(Cue.parse_download(response, "vtt-1"), CUES)


class AsyncTests(unittest.IsolatedAsyncioTestCase):
    async def test_html_download_automatically_uses_zoom_player(self):
        file = {"id": "vtt-1", "download_url": "https://zoom.us/rec/webhook_download/example",
                "file_extension": "VTT", "file_type": "TRANSCRIPT", "status": "completed",
                "recording_start": "2026-09-30T16:57:05Z"}
        share_url = "https://zoom.us/rec/share/example"
        detail = {"transcript": {"Data": {"recording_files": [file], "sessions": [
            {"start_time": file["recording_start"], "share_url": share_url},
        ]}}}
        for response in [httpx.Response(200, text="<html>Error</html>"), httpx.Response(403)]:
            with patch.object(TranscriptDownloader, "from_zoom_player", return_value=CUES) as fallback:
                async with httpx.AsyncClient(transport=httpx.MockTransport(lambda request: response)) as client:
                    cues = await TranscriptDownloader(client).retrieve(detail)
                self.assertEqual(cues, CUES)
                fallback.assert_awaited_once_with(share_url, "vtt-1")

    async def test_valid_direct_download_does_not_launch_browser(self):
        file = {"id": "vtt-1", "download_url": "https://zoom.us/transcript",
                "file_extension": "VTT", "file_type": "TRANSCRIPT", "status": "completed"}
        detail = {"transcript": {"Data": {"recording_files": [file]}}}
        with patch.object(TranscriptDownloader, "from_zoom_player") as fallback:
            async with httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(200, text=VTT))) as client:
                self.assertEqual(await TranscriptDownloader(client).retrieve(detail), CUES)
            fallback.assert_not_called()

    async def test_download_failure_without_playback_url_is_explicit(self):
        file = {"id": "vtt-1", "download_url": "https://zoom.us/transcript",
                "file_extension": "VTT", "file_type": "TRANSCRIPT", "status": "completed"}
        detail = {"transcript": {"Data": {"recording_files": [file]}}}
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(403))) as client:
            with self.assertRaisesRegex(ValueError, r"HTTP 403"):
                await TranscriptDownloader(client).retrieve(detail)

    async def test_resource_pagination(self):
        args_seen = []

        async def call(name, args):
            args_seen.append(args)
            return {"resources": [2]} if args.get("page_token") else {"resources": [1], "next_page_token": "next"}

        lfx = LfxClient(session=None)
        lfx.call = call
        self.assertEqual(await lfx.collect_pages("search", {}), [1, 2])
        self.assertEqual(args_seen[1]["page_token"], "next")

        async def loop(name, args):
            return {"resources": [], "next_page_token": "loop"}

        lfx.call = loop
        with self.assertRaisesRegex(ValueError, "repeated"):
            await lfx.collect_pages("search", {})

    async def test_structured_completion_request_and_result(self):
        def handler(request):
            body = json.loads(request.content)
            self.assertEqual(request.headers["authorization"], "Bearer test-key")
            self.assertEqual(body["model"], "test-model")
            self.assertEqual(body["response_format"]["json_schema"], {"name": "answer", "strict": True, "schema": SCHEMA})
            self.assertEqual([m["role"] for m in body["messages"]], ["system", "user"])
            return httpx.Response(200, json={"choices": [{"finish_reason": "stop", "message": {"content": '{"answer":"ok"}'}}]})

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            result = await StructuredModelClient(ModelConfig.from_env(MODEL_ENV), client).complete("answer", SCHEMA, "system", "user")
        self.assertEqual(result, {"answer": "ok"})

    async def test_structured_completion_failures(self):
        responses = [
            httpx.Response(401),
            httpx.Response(200, json={"choices": [{"finish_reason": "length"}]}),
            httpx.Response(200, json={"choices": [{"finish_reason": "stop", "message": {"refusal": "No"}}]}),
            httpx.Response(200, json={"choices": [{"finish_reason": "stop", "message": {"content": "not json"}}]}),
            httpx.Response(200, text="<html>Gateway error</html>"),
            httpx.Response(200, json=[]),
        ]
        for response in responses:
            async with httpx.AsyncClient(transport=httpx.MockTransport(lambda request: response)) as client:
                with self.subTest(response=response), self.assertRaises(ValueError):
                    await StructuredModelClient(ModelConfig.from_env(MODEL_ENV), client).complete("answer", SCHEMA, "s", "u")

    async def test_model_client_rejects_missing_settings_and_insecure_endpoint(self):
        async with httpx.AsyncClient() as client:
            with self.assertRaisesRegex(ValueError, "OPENAI_MODEL"):
                StructuredModelClient(ModelConfig(api_key="k"), client)
            with self.assertRaisesRegex(ValueError, "HTTPS"):
                StructuredModelClient(ModelConfig("k", "m", "http://example.org/v1"), client)


if __name__ == "__main__":
    unittest.main()
