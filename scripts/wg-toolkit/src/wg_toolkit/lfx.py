"""Authenticated LFX MCP client: connection, tool lookup, and pagination."""

from __future__ import annotations

from contextlib import AsyncExitStack, asynccontextmanager
from dataclasses import dataclass, field
from datetime import timedelta
import json
import shutil
import sys
from typing import Any, AsyncGenerator, Iterable, Mapping

import httpx
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamable_http_client
from mcp.types import PaginatedRequestParams

from .common import JsonObject, require_secure_url


LFX_MCP_URL = "https://mcp.lfx.dev/mcp"
PROXY_CLIENT_ID = "tjrXD5ZJORf6rpngMSRqqPmf3W1bnHEV"
# Never forwarded to the mcp-remote helper process.
SECRET_ENV_VARS = frozenset({"OPENAI_API_KEY", "LFX_MCP_TOKEN"})


@dataclass(frozen=True)
class LfxConfig:
    """LFX MCP settings read from the environment; secrets are hidden from repr."""

    mcp_url: str = LFX_MCP_URL
    mcp_token: str | None = field(default=None, repr=False)
    proxy_env: Mapping[str, str] = field(default_factory=dict, repr=False)

    @classmethod
    def from_env(cls, env: Mapping[str, str], extra_secrets: Iterable[str] = ()) -> LfxConfig:
        """Read LFX settings; `extra_secrets` names more variables to withhold from mcp-remote."""
        secrets = SECRET_ENV_VARS | set(extra_secrets)
        return cls(
            mcp_url=env.get("LFX_MCP_URL") or LFX_MCP_URL,
            mcp_token=env.get("LFX_MCP_TOKEN") or None,
            proxy_env={key: value for key, value in env.items() if key not in secrets},
        )

    @property
    def default_auth(self) -> str:
        return "token" if self.mcp_token else "oauth"


class LfxClient:
    """LFX MCP session wrapper that locates tools by suffix and collects paginated results."""

    def __init__(self, session: ClientSession):
        self._session = session
        self._tools: list[Any] | None = None

    @staticmethod
    def oauth_parameters(config: LfxConfig) -> StdioServerParameters:
        if config.mcp_url.rstrip("/") != LFX_MCP_URL:
            raise ValueError("The registered OAuth proxy is for https://mcp.lfx.dev/mcp only; use --auth token for another endpoint.")
        command = shutil.which("npx")
        if not command:
            raise ValueError("OAuth requires Node.js/npx for LFX's supported mcp-remote bridge; alternatively use --auth token.")
        return StdioServerParameters(
            command=command,
            args=["--yes", "mcp-remote", LFX_MCP_URL, "3334",
                  "--static-oauth-client-info", json.dumps({"client_id": PROXY_CLIENT_ID})],
            env=dict(config.proxy_env),
        )

    @classmethod
    @asynccontextmanager
    async def connect(cls, config: LfxConfig, auth: str) -> AsyncGenerator[LfxClient]:
        """Open an initialized session via the mcp-remote OAuth bridge or a bearer token."""
        async with AsyncExitStack() as stack:
            if auth == "oauth":
                print("Connecting to LFX via mcp-remote; complete LFID login in your browser if prompted.", file=sys.stderr)
                read_stream, write_stream = await stack.enter_async_context(
                    stdio_client(cls.oauth_parameters(config)))
            else:
                if not config.mcp_token:
                    raise ValueError("--auth token requires LFX_MCP_TOKEN, an access token for the MCP endpoint.")
                require_secure_url(config.mcp_url, "LFX MCP")
                client = await stack.enter_async_context(httpx.AsyncClient(
                    headers={"Authorization": f"Bearer {config.mcp_token}"}, timeout=300,
                    follow_redirects=False,
                ))
                read_stream, write_stream, _ = await stack.enter_async_context(
                    streamable_http_client(config.mcp_url, http_client=client))
            session = await stack.enter_async_context(ClientSession(
                read_stream, write_stream, read_timeout_seconds=timedelta(seconds=300)))
            await session.initialize()
            yield cls(session)

    async def list_tools(self) -> list[Any]:
        if self._tools is None:
            tools, seen_cursors, cursor = [], set(), None
            while True:
                page = await self._session.list_tools(params=PaginatedRequestParams(cursor=cursor))
                tools.extend(page.tools)
                cursor = page.nextCursor
                if not cursor:
                    break
                if cursor in seen_cursors:
                    raise ValueError("LFX returned a repeated tool-list cursor.")
                seen_cursors.add(cursor)
            self._tools = tools
        return self._tools

    async def call(self, suffix: str, args: JsonObject) -> JsonObject:
        """Call the one tool whose name is `suffix` or ends with `_suffix`."""
        matches = [tool for tool in await self.list_tools()
                   if tool.name == suffix or tool.name.endswith(f"_{suffix}")]
        if len(matches) != 1:
            raise ValueError(f"Cannot uniquely locate LFX tool {suffix}.")
        result = await self._session.call_tool(matches[0].name, args, read_timeout_seconds=timedelta(seconds=120))
        return self._decode(result)

    @staticmethod
    def _decode(result: Any) -> JsonObject:
        if result.isError:
            raise ValueError("LFX MCP tool returned an error; check access permissions.")
        if result.structuredContent is not None:
            data = result.structuredContent
        else:
            text = "\n".join(item.text for item in result.content if item.type == "text")
            try:
                data = json.loads(text)
            except json.JSONDecodeError:
                raise ValueError("LFX MCP returned a non-JSON tool response.") from None
        if not isinstance(data, dict):
            raise ValueError("LFX MCP returned a non-object tool response.")
        return data

    async def collect_pages(self, name: str, args: JsonObject) -> list[JsonObject]:
        """Call a paginated search tool until exhausted and return all `resources`."""
        resources, seen_tokens, page_token = [], set(), None
        while True:
            page_args = {**args, "page_size": 100}
            if page_token:
                page_args["page_token"] = page_token
            page = await self.call(name, page_args)
            if not isinstance(page.get("resources"), list):
                raise ValueError("LFX response has no resources array.")
            resources.extend(page["resources"])
            page_token = page.get("next_page_token") or page.get("page_token")
            if not page_token:
                return resources
            if page_token in seen_tokens:
                raise ValueError("LFX returned a repeated pagination token.")
            seen_tokens.add(page_token)
