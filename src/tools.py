"""
FontLab Tools
Handles write operations and tool calls for MCP
"""

import json
import logging
from typing import Any
from mcp.types import Tool, TextContent

from .fontlab_bridge import FontLabBridge
from .utils.validation import (
    ValidationError,
    sanitize_for_python,
    validate_glyph_name,
    validate_export_path,
    validate_numeric_range,
    validate_string_length,
    validate_unicode_codepoint,
)

logger = logging.getLogger(__name__)


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
        Tool(
            name="rename_glyph",
            description="Rename an existing glyph",
            inputSchema={
                "type": "object",
                "properties": {
                    "old_name": {
                        "type": "string",
                        "description": "Current glyph name",
                    },
                    "new_name": {
                        "type": "string",
                        "description": "New glyph name",
                    },
                },
                "required": ["old_name", "new_name"],
            },
        ),
        Tool(
            name="duplicate_glyph",
            description="Duplicate a glyph with a new name",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Glyph name to duplicate",
                    },
                    "new_name": {
                        "type": "string",
                        "description": "Name for the duplicate glyph",
                    },
                },
                "required": ["name", "new_name"],
            },
        ),
        Tool(
            name="set_glyph_sidebearings",
            description="Set left and right sidebearings for a glyph",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Glyph name",
                    },
                    "lsb": {
                        "type": "number",
                        "description": "Left sidebearing (optional)",
                    },
                    "rsb": {
                        "type": "number",
                        "description": "Right sidebearing (optional)",
                    },
                },
                "required": ["name"],
            },
        ),
        Tool(
            name="set_glyph_note",
            description="Set note text for a glyph",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Glyph name",
                    },
                    "note": {
                        "type": "string",
                        "description": "Note text (empty string to clear)",
                    },
                },
                "required": ["name", "note"],
            },
        ),
        Tool(
            name="set_glyph_tags",
            description="Set tags for a glyph",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Glyph name",
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of tag strings (empty array to clear)",
                    },
                },
                "required": ["name", "tags"],
            },
        ),
        Tool(
            name="set_glyph_mark",
            description="Set color mark for a glyph",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Glyph name",
                    },
                    "mark": {
                        "type": "integer",
                        "description": "Mark color index (0 = none, 1-255 = color)",
                    },
                },
                "required": ["name", "mark"],
            },
        ),
        Tool(
            name="set_kerning_pair",
            description="Set kerning value between two glyphs",
            inputSchema={
                "type": "object",
                "properties": {
                    "left": {
                        "type": "string",
                        "description": "Left glyph name or class",
                    },
                    "right": {
                        "type": "string",
                        "description": "Right glyph name or class",
                    },
                    "value": {
                        "type": "number",
                        "description": "Kerning value (use 0 to remove)",
                    },
                },
                "required": ["left", "right", "value"],
            },
        ),
        Tool(
            name="remove_kerning_pair",
            description="Remove kerning between two glyphs",
            inputSchema={
                "type": "object",
                "properties": {
                    "left": {
                        "type": "string",
                        "description": "Left glyph name or class",
                    },
                    "right": {
                        "type": "string",
                        "description": "Right glyph name or class",
                    },
                },
                "required": ["left", "right"],
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

    elif name == "rename_glyph":
        result = await _rename_glyph(arguments, bridge)

    elif name == "duplicate_glyph":
        result = await _duplicate_glyph(arguments, bridge)

    elif name == "set_glyph_sidebearings":
        result = await _set_glyph_sidebearings(arguments, bridge)

    elif name == "set_glyph_note":
        result = await _set_glyph_note(arguments, bridge)

    elif name == "set_glyph_tags":
        result = await _set_glyph_tags(arguments, bridge)

    elif name == "set_glyph_mark":
        result = await _set_glyph_mark(arguments, bridge)

    elif name == "set_kerning_pair":
        result = await _set_kerning_pair(arguments, bridge)

    elif name == "remove_kerning_pair":
        result = await _remove_kerning_pair(arguments, bridge)

    else:
        raise ValueError(f"Unknown tool: {name}")

    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def _create_glyph(args: dict[str, Any], bridge: FontLabBridge) -> dict[str, Any]:
    """Create a new glyph."""
    try:
        # Validate inputs
        name = validate_glyph_name(args["name"])
        unicode_val = args.get("unicode")
        if unicode_val is not None:
            unicode_val = validate_unicode_codepoint(unicode_val)
        width = validate_numeric_range(
            args.get("width", 600),
            "width",
            min_val=0,
            max_val=10000
        )

        # Sanitize for safe inclusion in Python script
        name_safe = sanitize_for_python(name)
        width_safe = sanitize_for_python(width)
        unicode_line = f"glyph.unicode = {sanitize_for_python(unicode_val)}" if unicode_val else ""

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
        existing = font.findGlyph({name_safe})
        if existing is not None:
            result = {{"success": False, "error": f"Glyph already exists: {{{{name_safe}}}}"}}
        else:
            # Create new glyph
            glyph = flGlyph()
            glyph.name = {name_safe}
            glyph.width = {width_safe}

            {unicode_line}

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
    except ValidationError as e:
        logger.error(f"Validation error in create_glyph: {e}")
        return {"success": False, "error": f"Validation error: {e}"}


async def _modify_glyph_width(args: dict[str, Any], bridge: FontLabBridge) -> dict[str, Any]:
    """Modify glyph width."""
    try:
        # Validate inputs
        name = validate_glyph_name(args["name"])
        width = validate_numeric_range(
            args["width"],
            "width",
            min_val=0,
            max_val=10000
        )

        # Sanitize for safe inclusion in Python script
        name_safe = sanitize_for_python(name)
        width_safe = sanitize_for_python(width)

        script = f"""
import json
import sys

try:
    from fontlab import flWorkspace

    font = flWorkspace.instance().currentFont()

    if font is None:
        result = {{"success": False, "error": "No font is currently open"}}
    else:
        glyph = font.findGlyph({name_safe})
        if glyph is None:
            result = {{"success": False, "error": f"Glyph not found: {{{{name_safe}}}}"}}
        else:
            old_width = glyph.width
            glyph.width = {width_safe}
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
    except ValidationError as e:
        logger.error(f"Validation error in modify_glyph_width: {e}")
        return {"success": False, "error": f"Validation error: {e}"}


async def _transform_glyph(args: dict[str, Any], bridge: FontLabBridge) -> dict[str, Any]:
    """Apply transformation to glyph."""
    try:
        # Validate inputs
        name = validate_glyph_name(args["name"])
        scale_x = validate_numeric_range(
            args.get("scale_x", 1.0), "scale_x", min_val=0.001, max_val=100
        )
        scale_y = validate_numeric_range(
            args.get("scale_y", 1.0), "scale_y", min_val=0.001, max_val=100
        )
        rotate = validate_numeric_range(
            args.get("rotate", 0), "rotate", min_val=-360, max_val=360
        )
        translate_x = validate_numeric_range(
            args.get("translate_x", 0), "translate_x", min_val=-10000, max_val=10000
        )
        translate_y = validate_numeric_range(
            args.get("translate_y", 0), "translate_y", min_val=-10000, max_val=10000
        )

        # Sanitize for safe inclusion in Python script
        name_safe = sanitize_for_python(name)
        scale_x_safe = sanitize_for_python(scale_x)
        scale_y_safe = sanitize_for_python(scale_y)
        rotate_safe = sanitize_for_python(rotate)
        translate_x_safe = sanitize_for_python(translate_x)
        translate_y_safe = sanitize_for_python(translate_y)

        script = f"""
import json
import sys

try:
    from fontlab import flWorkspace, flTransform

    font = flWorkspace.instance().currentFont()

    if font is None:
        result = {{"success": False, "error": "No font is currently open"}}
    else:
        glyph = font.findGlyph({name_safe})
        if glyph is None:
            result = {{"success": False, "error": f"Glyph not found: {{{{name_safe}}}}"}}
        else:
            # Create transformation matrix
            transform = flTransform()

            # Apply transformations
            if {scale_x_safe} != 1.0 or {scale_y_safe} != 1.0:
                transform.scale({scale_x_safe}, {scale_y_safe})

            if {rotate_safe} != 0:
                transform.rotate({rotate_safe})

            if {translate_x_safe} != 0 or {translate_y_safe} != 0:
                transform.translate({translate_x_safe}, {translate_y_safe})

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
                        "scale_x": {scale_x_safe},
                        "scale_y": {scale_y_safe},
                        "rotate": {rotate_safe},
                        "translate_x": {translate_x_safe},
                        "translate_y": {translate_y_safe}
                    }}
                }}
            }}
except Exception as e:
    result = {{"success": False, "error": str(e)}}

with open(sys.argv[-1], 'w') as f:
    json.dump(result, f)
"""
        return await bridge.execute_script(script)
    except ValidationError as e:
        logger.error(f"Validation error in transform_glyph: {e}")
        return {"success": False, "error": f"Validation error: {e}"}


async def _update_font_info(args: dict[str, Any], bridge: FontLabBridge) -> dict[str, Any]:
    """Update font metadata."""
    try:
        updates = []

        # Validate and sanitize each field
        if "family_name" in args:
            family_name = validate_string_length(args["family_name"], "family_name", max_length=255)
            updates.append(f'font.info.familyName = {sanitize_for_python(family_name)}')
        if "style_name" in args:
            style_name = validate_string_length(args["style_name"], "style_name", max_length=255)
            updates.append(f'font.info.styleName = {sanitize_for_python(style_name)}')
        if "version" in args:
            version = validate_string_length(args["version"], "version", max_length=100)
            updates.append(f'font.info.version = {sanitize_for_python(version)}')
        if "copyright" in args:
            copyright_text = validate_string_length(args["copyright"], "copyright", max_length=2000)
            updates.append(f'font.info.copyright = {sanitize_for_python(copyright_text)}')

        if not updates:
            return {"success": False, "error": "No valid updates provided"}

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
    except ValidationError as e:
        logger.error(f"Validation error in update_font_info: {e}")
        return {"success": False, "error": f"Validation error: {e}"}


async def _export_font(args: dict[str, Any], bridge: FontLabBridge) -> dict[str, Any]:
    """Export font to file."""
    try:
        # Validate export path (prevents path traversal)
        format_type = args.get("format", "otf")
        allowed_extensions = [f".{format_type}"]
        path = validate_export_path(args["path"], allowed_extensions)

        # Sanitize for safe inclusion in Python script
        path_safe = sanitize_for_python(path)
        format_safe = sanitize_for_python(format_type)

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
        success = font.save({path_safe}, {format_safe})

        if success:
            result = {{
                "success": True,
                "message": "Font exported successfully",
                "data": {{
                    "path": {path_safe},
                    "format": {format_safe}
                }}
            }}
        else:
            result = {{"success": False, "error": "Export failed"}}
except Exception as e:
    result = {{"success": False, "error": str(e)}}

with open(sys.argv[-1], 'w') as f:
    json.dump(result, f)
"""
        logger.info(f"Exporting font to {path} as {format_type}")
        return await bridge.execute_script(script)
    except ValidationError as e:
        logger.error(f"Validation error in export_font: {e}")
        return {"success": False, "error": f"Validation error: {e}"}


async def _delete_glyph(args: dict[str, Any], bridge: FontLabBridge) -> dict[str, Any]:
    """Delete a glyph."""
    try:
        # Validate inputs
        name = validate_glyph_name(args["name"])

        # Sanitize for safe inclusion in Python script
        name_safe = sanitize_for_python(name)

        script = f"""
import json
import sys

try:
    from fontlab import flWorkspace

    font = flWorkspace.instance().currentFont()

    if font is None:
        result = {{"success": False, "error": "No font is currently open"}}
    else:
        glyph = font.findGlyph({name_safe})
        if glyph is None:
            result = {{"success": False, "error": f"Glyph not found: {{{{name_safe}}}}"}}
        else:
            font.removeGlyph(glyph)
            font.update()

            result = {{
                "success": True,
                "message": "Glyph deleted successfully",
                "data": {{"name": {name_safe}}}
            }}
except Exception as e:
    result = {{"success": False, "error": str(e)}}

with open(sys.argv[-1], 'w') as f:
    json.dump(result, f)
"""
        logger.info(f"Deleting glyph: {name}")
        return await bridge.execute_script(script)
    except ValidationError as e:
        logger.error(f"Validation error in delete_glyph: {e}")
        return {"success": False, "error": f"Validation error: {e}"}
