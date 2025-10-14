#!/usr/bin/env python3
"""
FontLab MCP Server
Provides Model Context Protocol access to FontLab's PythonQt API
"""

import asyncio
import sys
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    Resource,
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
)

from . import __version__
from .resources import register_resources, handle_read_resource
from .tools import register_tools, handle_call_tool
from .fontlab_bridge import FontLabBridge


class FontLabMCPServer:
    """Main MCP server for FontLab integration."""

    def __init__(self):
        """Initialize the FontLab MCP server."""
        self.server = Server("fontlab-mcp-server")
        self.bridge = FontLabBridge()
        self._setup_handlers()

    def _setup_handlers(self):
        """Set up MCP request handlers."""

        @self.server.list_resources()
        async def list_resources() -> list[Resource]:
            """List available FontLab resources."""
            return register_resources()

        @self.server.read_resource()
        async def read_resource(uri: str) -> str:
            """Read a FontLab resource."""
            return await handle_read_resource(uri, self.bridge)

        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            """List available FontLab tools."""
            return register_tools()

        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
            """Call a FontLab tool."""
            return await handle_call_tool(name, arguments, self.bridge)

    async def run(self):
        """Run the MCP server using stdio transport."""
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options(),
            )


def main():
    """Main entry point for the FontLab MCP server."""
    print(f"Starting FontLab MCP Server v{__version__}", file=sys.stderr)
    server = FontLabMCPServer()
    asyncio.run(server.run())


if __name__ == "__main__":
    main()
