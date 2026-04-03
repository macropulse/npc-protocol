"""
NPCServer — the core class for building NPC Protocol servers.

Wraps an MCP server and automatically:
- Registers the NPC Card as an MCP resource at npc://card
- Registers the Skill File as an MCP resource at npc://skill (if provided)
- Registers a lightweight version check at npc://skill-version (if skill file provided)
- Registers the execute tool with the standard NPC Protocol schema
- Manages sessions via the provided SessionStore
- Routes execute calls to the registered instruction handler
- Injects skill_version into every execute() response (if skill file provided)
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Coroutine
from pathlib import Path
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    CallToolResult,
    ReadResourceResult,
    Resource,
    TextContent,
    TextResourceContents,
    Tool,
)

from .card import NPCCard
from .context import NPCContext
from .response import FailedResponse, NPCResponse
from .session import SessionStore

# Type for the instruction handler function
InstructionHandler = Callable[
    [str, str, NPCContext],
    Coroutine[Any, Any, NPCResponse],
]


def _parse_skill_frontmatter(content: str) -> dict[str, str]:
    """
    Parse YAML frontmatter from a Markdown skill file.
    Returns a dict of frontmatter key-value pairs.
    Only handles simple string values (no nested YAML).
    """
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
    if not match:
        return {}
    frontmatter = {}
    for line in match.group(1).splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            frontmatter[key.strip()] = value.strip()
    return frontmatter


class NPCServer:
    """
    An NPC Protocol server. Wraps an MCP server with protocol scaffolding.

    Usage:

        card = NPCCard(
            name="My NPC",
            domain="your domain description",
        )

        npc = NPCServer(card=card, skill_file="SKILL.md")

        @npc.instruction_handler
        async def handle(instruction: str, session_id: str, ctx: NPCContext) -> NPCResponse:
            # Your domain logic here
            return ctx.complete(result="Done")

        npc.run()  # starts the MCP server on stdio
    """

    def __init__(
        self,
        card: NPCCard,
        session_store: SessionStore | None = None,
        skill_file: str | Path | None = None,
    ) -> None:
        self.card = card
        self._session_store = session_store or SessionStore.in_memory()
        self._handler: InstructionHandler | None = None
        self._skill_content: str | None = None
        self._skill_version: str | None = None

        if skill_file is not None:
            path = Path(skill_file)
            if path.exists():
                self._skill_content = path.read_text(encoding="utf-8")
                meta = _parse_skill_frontmatter(self._skill_content)
                self._skill_version = meta.get("version")
                # Sync card fields
                if self._skill_version and not card.skill_version:
                    card.skill_version = self._skill_version
                if not card.skill_file_uri:
                    card.skill_file_uri = "npc://skill"

        self._mcp = Server(card.name)
        self._register_mcp_handlers()

    def instruction_handler(self, fn: InstructionHandler) -> InstructionHandler:
        """Decorator to register the instruction handler for this NPC."""
        self._handler = fn
        return fn

    def _register_mcp_handlers(self) -> None:
        mcp = self._mcp

        @mcp.list_resources()
        async def list_resources() -> list[Resource]:
            resources = [
                Resource(
                    uri="npc://card",
                    name="NPC Card",
                    description=f"Identity and capability declaration for {self.card.name}",
                    mimeType="application/json",
                )
            ]
            if self._skill_content is not None:
                resources.append(Resource(
                    uri="npc://skill",
                    name="Skill File",
                    description=f"Operational guide for using {self.card.name}",
                    mimeType="text/markdown",
                ))
                resources.append(Resource(
                    uri="npc://skill-version",
                    name="Skill File Version",
                    description="Current version of the Skill File (lightweight drift check)",
                    mimeType="application/json",
                ))
            return resources

        @mcp.read_resource()
        async def read_resource(uri: str) -> ReadResourceResult:
            if uri == "npc://card":
                return ReadResourceResult(
                    contents=[
                        TextResourceContents(
                            uri="npc://card",
                            mimeType="application/json",
                            text=json.dumps(self.card.to_json(), indent=2),
                        )
                    ]
                )
            if uri == "npc://skill":
                if self._skill_content is None:
                    raise ValueError("This NPC does not publish a Skill File")
                return ReadResourceResult(
                    contents=[
                        TextResourceContents(
                            uri="npc://skill",
                            mimeType="text/markdown",
                            text=self._skill_content,
                        )
                    ]
                )
            if uri == "npc://skill-version":
                if self._skill_version is None:
                    raise ValueError("This NPC does not publish a Skill File")
                return ReadResourceResult(
                    contents=[
                        TextResourceContents(
                            uri="npc://skill-version",
                            mimeType="application/json",
                            text=json.dumps({"version": self._skill_version}),
                        )
                    ]
                )
            raise ValueError(f"Unknown resource: {uri}")

        @mcp.list_tools()
        async def list_tools() -> list[Tool]:
            return [
                Tool(
                    name="execute",
                    description=(
                        f"Send a natural language instruction to {self.card.name}. "
                        f"Domain: {self.card.domain}"
                    ),
                    inputSchema={
                        "type": "object",
                        "required": ["instruction"],
                        "properties": {
                            "instruction": {
                                "type": "string",
                                "description": "A natural language instruction or reply",
                            },
                            "session_id": {
                                "type": "string",
                                "description": "Resume an existing session. Omit to start a new session.",
                            },
                            "confirm": {
                                "type": "boolean",
                                "description": "Confirmation reply to a needs_confirmation gate",
                            },
                            "choice": {
                                "type": "string",
                                "description": "Selection reply to a needs_input response with options",
                            },
                        },
                    },
                )
            ]

        @mcp.call_tool()
        async def call_tool(name: str, arguments: dict[str, Any]) -> CallToolResult:
            if name != "execute":
                raise ValueError(f"Unknown tool: {name}")
            return await self._handle_execute(arguments)

    async def _handle_execute(self, arguments: dict[str, Any]) -> CallToolResult:
        if self._handler is None:
            raise RuntimeError("No instruction handler registered. Use @npc.instruction_handler.")

        instruction = arguments.get("instruction", "")
        session_id = arguments.get("session_id")

        # Resolve or create session
        if session_id and await self._session_store.exists(session_id):
            session_data = (await self._session_store.get(session_id)) or {}
        else:
            session_id = await self._session_store.create(
                data={
                    "confirm": arguments.get("confirm"),
                    "choice": arguments.get("choice"),
                }
            )
            session_data = {}

        ctx = NPCContext(
            session_id=session_id,
            session_store=self._session_store,
            session_data=session_data,
        )

        try:
            response: NPCResponse = await self._handler(instruction, session_id, ctx)
        except Exception as e:
            response = FailedResponse(
                session_id=session_id,
                error=str(e),
                recovery_hint="An unexpected error occurred. Please try again or contact support.",
            )

        # Inject skill_version into every response (passive drift detection)
        response_dict = response.to_dict()
        if self._skill_version is not None:
            response_dict["skill_version"] = self._skill_version

        return CallToolResult(
            content=[
                TextContent(
                    type="text",
                    text=json.dumps(response_dict, indent=2),
                )
            ]
        )

    def run(self) -> None:
        """Start the NPC server using stdio transport (default MCP transport)."""
        import asyncio

        async def _run() -> None:
            async with stdio_server() as (read_stream, write_stream):
                await self._mcp.run(
                    read_stream,
                    write_stream,
                    self._mcp.create_initialization_options(),
                )

        asyncio.run(_run())
