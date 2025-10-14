"""
FontLab Resources
Handles read-only resource operations for MCP
"""

import json
from typing import Any
from mcp.types import Resource, TextContent

from .fontlab_bridge import FontLabBridge


def register_resources() -> list[Resource]:
    """
    Register all available FontLab resources.

    Returns:
        List of available resources
    """
    return [
        Resource(
            uri="fontlab://font/current",
            name="Current Font",
            description="Get information about the currently open font",
            mimeType="application/json",
        ),
        Resource(
            uri="fontlab://font/current/glyphs",
            name="Font Glyphs",
            description="List all glyphs in the current font",
            mimeType="application/json",
        ),
        Resource(
            uri="fontlab://font/info",
            name="Font Info",
            description="Get detailed font metadata and information",
            mimeType="application/json",
        ),
        Resource(
            uri="fontlab://glyph/{name}",
            name="Glyph Details",
            description="Get detailed information about a specific glyph (use glyph name)",
            mimeType="application/json",
        ),
    ]


async def handle_read_resource(uri: str, bridge: FontLabBridge) -> str:
    """
    Handle reading a FontLab resource.

    Args:
        uri: Resource URI to read
        bridge: FontLab bridge instance

    Returns:
        JSON string with resource data

    Raises:
        ValueError: If URI is invalid or resource not found
    """
    # Parse the URI
    if uri == "fontlab://font/current":
        result = await bridge.get_current_font()
        return json.dumps(result, indent=2)

    elif uri == "fontlab://font/current/glyphs":
        result = await bridge.list_glyphs()
        return json.dumps(result, indent=2)

    elif uri == "fontlab://font/info":
        # Get comprehensive font info
        result = await bridge.get_current_font()
        return json.dumps(result, indent=2)

    elif uri.startswith("fontlab://glyph/"):
        # Extract glyph name from URI
        glyph_name = uri.replace("fontlab://glyph/", "")
        if not glyph_name:
            raise ValueError("Glyph name is required")

        result = await bridge.get_glyph(glyph_name)
        return json.dumps(result, indent=2)

    else:
        raise ValueError(f"Unknown resource URI: {uri}")
