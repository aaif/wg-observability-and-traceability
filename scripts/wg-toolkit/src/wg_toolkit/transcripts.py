"""Transcript cues and Zoom transcript retrieval for LFX past meetings."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import math
import re
import sys
from typing import Any
from urllib.parse import parse_qs, urlparse

import httpx
import webvtt
from webvtt.models import Timestamp

from .common import JsonObject, is_zoom_host, require_secure_url


@dataclass(frozen=True)
class Cue:
    """One transcript cue; timestamps are seconds within its recording segment."""

    source: str
    start_seconds: float | None
    end_seconds: float | None
    text: str

    @classmethod
    def from_dict(cls, data: Any) -> Cue:
        if not isinstance(data, dict) or "start_seconds" not in data or "end_seconds" not in data:
            raise ValueError("Transcript cue must contain start_seconds and end_seconds.")
        return cls(data.get("source"), data["start_seconds"], data["end_seconds"], data.get("text"))

    @classmethod
    def parse(cls, text: str, source: str = "transcript") -> list[Cue]:
        """Parse WebVTT, or plain text split into paragraphs with null timestamps."""
        text = text.lstrip("\ufeff")
        if not text.strip() or re.match(r"\s*(?:<!doctype html|<html)", text, re.I):
            raise ValueError("Transcript is empty or an HTML login/error page.")
        if not text.startswith("WEBVTT"):
            return [cls(source, None, None, paragraph.strip())
                    for paragraph in re.split(r"\r?\n\s*\r?\n", text) if paragraph.strip()]
        try:
            captions = list(webvtt.from_string(text))
        except (ValueError, webvtt.errors.MalformedFileError, webvtt.errors.MalformedCaptionError):
            raise ValueError("Transcript contains invalid or empty WebVTT cues.") from None
        timing_lines = sum("-->" in line for line in text.splitlines())
        if not captions or len(captions) != timing_lines:
            raise ValueError("Transcript contains invalid or empty WebVTT cues.")
        return [cls(source, cls._seconds(caption.start), cls._seconds(caption.end), caption.raw_text)
                for caption in captions]

    @classmethod
    def parse_download(cls, response: httpx.Response, source: str) -> list[Cue]:
        content_type = response.headers.get("content-type", "").split(";", 1)[0].strip().lower()
        text = response.text.lstrip("\ufeff")
        if content_type in {"text/html", "application/xhtml+xml"} or not text.startswith("WEBVTT"):
            raise ValueError(
                "The transcript download returned HTML, empty content, or non-VTT text instead of a transcript. "
                "LFX MCP access does not authorize Zoom downloads. Download the transcript through "
                "LFX/Zoom in your browser (or ask the meeting organizer for it), then rerun with --transcript PATH."
            )
        return cls.parse(text, source)

    @staticmethod
    def _seconds(value: str) -> float:
        timestamp = Timestamp.from_string(value)
        return (timestamp.hours * 3600 + timestamp.minutes * 60
                + timestamp.seconds + timestamp.milliseconds / 1000)

    def is_valid(self) -> bool:
        if not isinstance(self.text, str) or not self.text.strip() or not isinstance(self.source, str):
            return False
        for value in (self.start_seconds, self.end_seconds):
            if value is not None and (type(value) not in (int, float) or not math.isfinite(value) or value < 0):
                return False
        start, end = self.start_seconds, self.end_seconds
        return (start is None and end is None) or (start is not None and end is not None and end >= start)

    def to_dict(self) -> JsonObject:
        return asdict(self)


class TranscriptDownloader:
    """Download VTT transcripts directly, falling back to Zoom's recording player."""

    def __init__(self, client: httpx.AsyncClient):
        self._client = client

    @staticmethod
    def transcript_files(detail: JsonObject) -> list[JsonObject]:
        """Return completed VTT transcript files from a `get_past_meeting` response."""
        files = detail.get("transcript", {}).get("Data", {}).get("recording_files", [])
        transcripts = [file for file in files if file.get("download_url")
                       and file.get("status") == "completed"
                       and file.get("file_extension") == "VTT"
                       and (file.get("file_type") == "TRANSCRIPT"
                            or file.get("recording_type") == "audio_transcript")]
        if not transcripts:
            raise ValueError("No accessible VTT transcript. Supply --transcript PATH if needed.")
        return sorted(transcripts, key=lambda file: file.get("recording_start") or "")

    @staticmethod
    def playback_url(detail: JsonObject, file: JsonObject) -> str | None:
        sessions = detail.get("transcript", {}).get("Data", {}).get("sessions", [])
        matching = [session for session in sessions if file.get("recording_start")
                    and session.get("start_time") == file["recording_start"]]
        if not matching and len(sessions) == 1:
            matching = sessions
        url = (matching[0].get("share_url") if len(matching) == 1 else None) or file.get("play_url")
        if not url:
            return None
        require_secure_url(url, "Zoom playback", allow_localhost=False)
        if not is_zoom_host(urlparse(url).hostname):
            raise ValueError("Browser transcript fallback requires a Zoom recording URL.")
        return url

    @staticmethod
    def is_zoom_transcript_url(url: str) -> bool:
        parsed = urlparse(url)
        return (parsed.scheme == "https" and is_zoom_host(parsed.hostname)
                and parsed.path == "/rec/play/vtt"
                and parse_qs(parsed.query).get("type") == ["transcript"])

    async def retrieve(self, detail: JsonObject) -> list[Cue]:
        transcript = []
        for file in self.transcript_files(detail):
            require_secure_url(file["download_url"], "Transcript download", allow_localhost=False)
            try:
                response = await self._client.get(file["download_url"])
                response.raise_for_status()
                cues = Cue.parse_download(response, file["id"])
            except (httpx.HTTPError, ValueError) as error:
                playback_url = self.playback_url(detail, file)
                if playback_url:
                    cues = await self.from_zoom_player(playback_url, file["id"])
                elif isinstance(error, httpx.HTTPStatusError):
                    raise ValueError(f"Transcript download failed (HTTP {error.response.status_code}); use --transcript PATH if Zoom requires authorization.") from None
                elif isinstance(error, httpx.HTTPError):
                    raise ValueError("Transcript download failed; use --transcript PATH if Zoom requires authorization.") from None
                else:
                    raise
            transcript.extend(cues)
        return transcript

    async def from_zoom_player(self, url: str, source: str) -> list[Cue]:
        """Capture the VTT response that Zoom's player loads in a fresh headless browser."""
        try:
            from playwright.async_api import Error as BrowserError, async_playwright
        except ImportError:
            raise ValueError(
                "Zoom browser transcript retrieval needs Playwright; install wg-toolkit[browser] "
                "or use --transcript PATH."
            ) from None

        print("Direct transcript link unavailable; retrieving VTT from Zoom's recording player.", file=sys.stderr)
        try:
            async with async_playwright() as playwright:
                try:
                    browser = await playwright.chromium.launch(headless=True)
                except BrowserError as error:
                    if "Executable doesn't exist" not in str(error):
                        raise
                    browser = await playwright.chromium.launch(channel="chrome", headless=True)
                try:
                    page = await browser.new_page()
                    async with page.expect_response(
                        lambda response: self.is_zoom_transcript_url(response.url), timeout=60_000,
                    ) as pending:
                        try:
                            await page.goto(url, wait_until="domcontentloaded", timeout=60_000)
                        except BrowserError as error:
                            if "ERR_ABORTED" not in str(error):
                                raise
                    response = await pending.value
                    if not response.ok:
                        raise ValueError(f"Zoom player transcript request failed (HTTP {response.status}).")
                    captured = httpx.Response(response.status, headers=response.headers, content=await response.body())
                    return Cue.parse_download(captured, source)
                finally:
                    await browser.close()
        except BrowserError:
            raise ValueError(
                "Zoom browser transcript retrieval failed. Install Chromium with 'uv run playwright install chromium'. "
                "The recording must be publicly playable; if it requires login or a passcode, use --transcript PATH."
            ) from None
