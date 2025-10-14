"""
FontLab Tools
Handles write operations and tool calls for MCP
"""

import json
from typing import Any
from mcp.types import Tool, TextContent

from .fontlab_bridge import FontLabBridge


def register_tools() -> list[Tool]:
    """
    Register all available FontLab tools.

    Returns:
        List of available tools
    """
    return [
        Tool(
            name="create_glyph",
            description="Create a new glyph in the current font",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Glyph name (e.g., 'A', 'B', 'space')",
                    },
                    "unicode": {
                        "type": "integer",
                        "description": "Unicode code point (optional)",
                    },
                    "width": {
                        "type": "number",
                        "description": "Glyph width (optional, defaults to 600)",
                        "default": 600,
                    },
                },
                "required": ["name"],
            },
        ),
        Tool(
            name="modify_glyph_width",
            description="Modify the width of an existing glyph",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Glyph name",
                    },
                    "width": {
                        "type": "number",
                        "description": "New width value",
                    },
                },
                "required": ["name", "width"],
            },
        ),
        Tool(
            name="transform_glyph",
            description="Apply transformation to a glyph (scale, rotate, translate)",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Glyph name",
                    },
                    "scale_x": {
                        "type": "number",
                        "description": "Horizontal scale factor (1.0 = no change)",
                        "default": 1.0,
                    },
                    "scale_y": {
                        "type": "number",
                        "description": "Vertical scale factor (1.0 = no change)",
                        "default": 1.0,
                    },
                    "rotate": {
                        "type": "number",
                        "description": "Rotation angle in degrees",
                        "default": 0,
                    },
                    "translate_x": {
                        "type": "number",
                        "description": "Horizontal translation",
                        "default": 0,
                    },
                    "translate_y": {
                        "type": "number",
                        "description": "Vertical translation",
                        "default": 0,
                    },
                },
                "required": ["name"],
            },
        ),
        Tool(
            name="update_font_info",
            description="Update font metadata",
            inputSchema={
                "type": "object",
                "properties": {
                    "family_name": {
                        "type": "string",
                        "description": "Font family name",
                    },
                    "style_name": {
                        "type": "string",
                        "description": "Font style name",
                    },
                    "version": {
                        "type": "string",
                        "description": "Font version",
                    },
                    "copyright": {
                        "type": "string",
                        "description": "Copyright notice",
                    },
                },
            },
        ),
        Tool(
            name="export_font",
            description="Export the current font to a file",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Output file path",
                    },
                    "format": {
                        "type": "string",
                        "description": "Export format",
                        "enum": ["otf", "ttf", "woff", "woff2", "ufo"],
                        "default": "otf",
                    },
                },
                "required": ["path"],
            },
        ),
        Tool(
            name="delete_glyph",
            description="Delete a glyph from the current font",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Glyph name to delete",
                    },
                },
                "required": ["name"],
            },
        ),
    ]


async def handle_call_tool(
    name: str, arguments: dict[str, Any], bridge: FontLabBridge
) -> list[TextContent]:
    """
    Handle calling a FontLab tool.

    Args:
        name: Tool name
        arguments: Tool arguments
        bridge: FontLab bridge instance

    Returns:
        List of text content with results

    Raises:
        ValueError: If tool name is unknown
    """
    if name == "create_glyph":
        result = await _create_glyph(arguments, bridge)

    elif name == "modify_glyph_width":
        result = await _modify_glyph_width(arguments, bridge)

    elif name == "transform_glyph":
        result = await _transform_glyph(arguments, bridge)

    elif name == "update_font_info":
        result = await _update_font_info(arguments, bridge)

    elif name == "export_font":
        result = await _export_font(arguments, bridge)

    elif name == "delete_glyph":
        result = await _delete_glyph(arguments, bridge)

    else:
        raise ValueError(f"Unknown tool: {name}")

    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def _create_glyph(args: dict[str, Any], bridge: FontLabBridge) -> dict[str, Any]:
    """Create a new glyph."""
    name = args["name"]
    unicode_val = args.get("unicode")
    width = args.get("width", 600)

    script = f"""
import json
import sys

try:
    from fontlab import flWorkspace, flGlyph

    font = flWorkspace.instance().currentFont()

    if font is None:
        result = {{"success": False, "error": "No font is currently open"}}
    else:
        # Check if glyph already exists
        existing = font.findGlyph("{name}")
        if existing is not None:
            result = {{"success": False, "error": "Glyph already exists: {name}"}}
        else:
            # Create new glyph
            glyph = flGlyph()
            glyph.name = "{name}"
            glyph.width = {width}

            {f'glyph.unicode = {unicode_val}' if unicode_val else ''}

            # Add glyph to font
            font.addGlyph(glyph)

            result = {{
                "success": True,
                "message": "Glyph created successfully",
                "data": {{
                    "name": glyph.name,
                    "unicode": glyph.unicode if glyph.unicode else None,
                    "width": glyph.width
                }}
            }}
except Exception as e:
    result = {{"success": False, "error": str(e)}}

with open(sys.argv[-1], 'w') as f:
    json.dump(result, f)
"""
    return await bridge.execute_script(script)


async def _modify_glyph_width(args: dict[str, Any], bridge: FontLabBridge) -> dict[str, Any]:
    """Modify glyph width."""
    name = args["name"]
    width = args["width"]

    script = f"""
import json
import sys

try:
    from fontlab import flWorkspace

    font = flWorkspace.instance().currentFont()

    if font is None:
        result = {{"success": False, "error": "No font is currently open"}}
    else:
        glyph = font.findGlyph("{name}")
        if glyph is None:
            result = {{"success": False, "error": "Glyph not found: {name}"}}
        else:
            old_width = glyph.width
            glyph.width = {width}
            glyph.update()

            result = {{
                "success": True,
                "message": "Glyph width updated",
                "data": {{
                    "name": glyph.name,
                    "old_width": old_width,
                    "new_width": glyph.width
                }}
            }}
except Exception as e:
    result = {{"success": False, "error": str(e)}}

with open(sys.argv[-1], 'w') as f:
    json.dump(result, f)
"""
    return await bridge.execute_script(script)


async def _transform_glyph(args: dict[str, Any], bridge: FontLabBridge) -> dict[str, Any]:
    """Apply transformation to glyph."""
    name = args["name"]
    scale_x = args.get("scale_x", 1.0)
    scale_y = args.get("scale_y", 1.0)
    rotate = args.get("rotate", 0)
    translate_x = args.get("translate_x", 0)
    translate_y = args.get("translate_y", 0)

    script = f"""
import json
import sys

try:
    from fontlab import flWorkspace, flTransform

    font = flWorkspace.instance().currentFont()

    if font is None:
        result = {{"success": False, "error": "No font is currently open"}}
    else:
        glyph = font.findGlyph("{name}")
        if glyph is None:
            result = {{"success": False, "error": "Glyph not found: {name}"}}
        else:
            # Create transformation matrix
            transform = flTransform()

            # Apply transformations
            if {scale_x} != 1.0 or {scale_y} != 1.0:
                transform.scale({scale_x}, {scale_y})

            if {rotate} != 0:
                transform.rotate({rotate})

            if {translate_x} != 0 or {translate_y} != 0:
                transform.translate({translate_x}, {translate_y})

            # Apply to glyph
            layer = glyph.layers[0]
            layer.applyTransform(transform)
            glyph.update()

            result = {{
                "success": True,
                "message": "Transformation applied",
                "data": {{
                    "name": glyph.name,
                    "transformations": {{
                        "scale_x": {scale_x},
                        "scale_y": {scale_y},
                        "rotate": {rotate},
                        "translate_x": {translate_x},
                        "translate_y": {translate_y}
                    }}
                }}
            }}
except Exception as e:
    result = {{"success": False, "error": str(e)}}

with open(sys.argv[-1], 'w') as f:
    json.dump(result, f)
"""
    return await bridge.execute_script(script)


async def _update_font_info(args: dict[str, Any], bridge: FontLabBridge) -> dict[str, Any]:
    """Update font metadata."""
    updates = []

    if "family_name" in args:
        updates.append(f'font.info.familyName = "{args["family_name"]}"')
    if "style_name" in args:
        updates.append(f'font.info.styleName = "{args["style_name"]}"')
    if "version" in args:
        updates.append(f'font.info.version = "{args["version"]}"')
    if "copyright" in args:
        updates.append(f'font.info.copyright = "{args["copyright"]}"')

    updates_str = "\n            ".join(updates)

    script = f"""
import json
import sys

try:
    from fontlab import flWorkspace

    font = flWorkspace.instance().currentFont()

    if font is None:
        result = {{"success": False, "error": "No font is currently open"}}
    else:
        # Apply updates
        {updates_str}

        font.update()

        result = {{
            "success": True,
            "message": "Font info updated",
            "data": {{
                "family_name": font.info.familyName or "",
                "style_name": font.info.styleName or "",
                "version": getattr(font.info, 'version', ''),
                "copyright": getattr(font.info, 'copyright', '')
            }}
        }}
except Exception as e:
    result = {{"success": False, "error": str(e)}}

with open(sys.argv[-1], 'w') as f:
    json.dump(result, f)
"""
    return await bridge.execute_script(script)


async def _export_font(args: dict[str, Any], bridge: FontLabBridge) -> dict[str, Any]:
    """Export font to file."""
    path = args["path"]
    format_type = args.get("format", "otf")

    script = f"""
import json
import sys

try:
    from fontlab import flWorkspace

    font = flWorkspace.instance().currentFont()

    if font is None:
        result = {{"success": False, "error": "No font is currently open"}}
    else:
        # Export font
        success = font.save("{path}", "{format_type}")

        if success:
            result = {{
                "success": True,
                "message": "Font exported successfully",
                "data": {{
                    "path": "{path}",
                    "format": "{format_type}"
                }}
            }}
        else:
            result = {{"success": False, "error": "Export failed"}}
except Exception as e:
    result = {{"success": False, "error": str(e)}}

with open(sys.argv[-1], 'w') as f:
    json.dump(result, f)
"""
    return await bridge.execute_script(script)


async def _delete_glyph(args: dict[str, Any], bridge: FontLabBridge) -> dict[str, Any]:
    """Delete a glyph."""
    name = args["name"]

    script = f"""
import json
import sys

try:
    from fontlab import flWorkspace

    font = flWorkspace.instance().currentFont()

    if font is None:
        result = {{"success": False, "error": "No font is currently open"}}
    else:
        glyph = font.findGlyph("{name}")
        if glyph is None:
            result = {{"success": False, "error": "Glyph not found: {name}"}}
        else:
            font.removeGlyph(glyph)
            font.update()

            result = {{
                "success": True,
                "message": "Glyph deleted successfully",
                "data": {{"name": "{name}"}}
            }}
except Exception as e:
    result = {{"success": False, "error": str(e)}}

with open(sys.argv[-1], 'w') as f:
    json.dump(result, f)
"""
    return await bridge.execute_script(script)
