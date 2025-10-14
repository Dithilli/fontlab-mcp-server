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
    RequestSizeError,
    validate_request_size,
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
        Tool(
            name="add_component",
            description="Add a component reference to a glyph",
            inputSchema={
                "type": "object",
                "properties": {
                    "glyph_name": {
                        "type": "string",
                        "description": "Target glyph name",
                    },
                    "base_glyph": {
                        "type": "string",
                        "description": "Base glyph to reference",
                    },
                    "x_offset": {
                        "type": "number",
                        "description": "Horizontal offset (default 0)",
                        "default": 0,
                    },
                    "y_offset": {
                        "type": "number",
                        "description": "Vertical offset (default 0)",
                        "default": 0,
                    },
                },
                "required": ["glyph_name", "base_glyph"],
            },
        ),
        Tool(
            name="decompose_glyph",
            description="Decompose all components in a glyph to outlines",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Glyph name",
                    },
                },
                "required": ["name"],
            },
        ),
        Tool(
            name="reverse_contours",
            description="Reverse the direction of all contours in a glyph",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Glyph name",
                    },
                },
                "required": ["name"],
            },
        ),
        Tool(
            name="remove_overlaps",
            description="Remove overlapping paths in a glyph",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Glyph name",
                    },
                },
                "required": ["name"],
            },
        ),
        Tool(
            name="set_feature_code",
            description="Set OpenType feature code for the font",
            inputSchema={
                "type": "object",
                "properties": {
                    "features": {
                        "type": "string",
                        "description": "OpenType feature code in Adobe FEA syntax",
                    },
                },
                "required": ["features"],
            },
        ),
        Tool(
            name="create_glyph_class",
            description="Create or update a glyph class",
            inputSchema={
                "type": "object",
                "properties": {
                    "class_name": {
                        "type": "string",
                        "description": "Class name (without @ prefix)",
                    },
                    "glyphs": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of glyph names in the class",
                    },
                },
                "required": ["class_name", "glyphs"],
            },
        ),
        Tool(
            name="add_anchor",
            description="Add an anchor point to a glyph",
            inputSchema={
                "type": "object",
                "properties": {
                    "glyph_name": {
                        "type": "string",
                        "description": "Glyph name",
                    },
                    "anchor_name": {
                        "type": "string",
                        "description": "Anchor name (e.g., 'top', 'bottom', '_top')",
                    },
                    "x": {
                        "type": "number",
                        "description": "X coordinate",
                    },
                    "y": {
                        "type": "number",
                        "description": "Y coordinate",
                    },
                },
                "required": ["glyph_name", "anchor_name", "x", "y"],
            },
        ),
        Tool(
            name="remove_anchor",
            description="Remove an anchor from a glyph",
            inputSchema={
                "type": "object",
                "properties": {
                    "glyph_name": {
                        "type": "string",
                        "description": "Glyph name",
                    },
                    "anchor_name": {
                        "type": "string",
                        "description": "Anchor name to remove",
                    },
                },
                "required": ["glyph_name", "anchor_name"],
            },
        ),
        Tool(
            name="move_anchor",
            description="Move an existing anchor to a new position",
            inputSchema={
                "type": "object",
                "properties": {
                    "glyph_name": {
                        "type": "string",
                        "description": "Glyph name",
                    },
                    "anchor_name": {
                        "type": "string",
                        "description": "Anchor name",
                    },
                    "x": {
                        "type": "number",
                        "description": "New X coordinate",
                    },
                    "y": {
                        "type": "number",
                        "description": "New Y coordinate",
                    },
                },
                "required": ["glyph_name", "anchor_name", "x", "y"],
            },
        ),
        Tool(
            name="add_layer",
            description="Add a new layer to a glyph",
            inputSchema={
                "type": "object",
                "properties": {
                    "glyph_name": {
                        "type": "string",
                        "description": "Glyph name",
                    },
                    "layer_name": {
                        "type": "string",
                        "description": "Name for the new layer",
                    },
                },
                "required": ["glyph_name", "layer_name"],
            },
        ),
        Tool(
            name="remove_layer",
            description="Remove a layer from a glyph by index",
            inputSchema={
                "type": "object",
                "properties": {
                    "glyph_name": {
                        "type": "string",
                        "description": "Glyph name",
                    },
                    "layer_index": {
                        "type": "integer",
                        "description": "Layer index (0-based)",
                    },
                },
                "required": ["glyph_name", "layer_index"],
            },
        ),
        Tool(
            name="add_guide",
            description="Add a global guide to the font",
            inputSchema={
                "type": "object",
                "properties": {
                    "position": {
                        "type": "number",
                        "description": "Guide position (y-coordinate for horizontal, x for vertical)",
                    },
                    "angle": {
                        "type": "number",
                        "description": "Guide angle in degrees (0=horizontal, 90=vertical)",
                        "default": 0,
                    },
                    "name": {
                        "type": "string",
                        "description": "Guide name (optional)",
                        "default": "",
                    },
                },
                "required": ["position"],
            },
        ),
        Tool(
            name="add_zone",
            description="Add an alignment zone (hint zone) to the font",
            inputSchema={
                "type": "object",
                "properties": {
                    "zone_type": {
                        "type": "string",
                        "description": "Zone type",
                        "enum": ["blue", "other_blue"],
                    },
                    "bottom": {
                        "type": "number",
                        "description": "Bottom edge of the zone",
                    },
                    "top": {
                        "type": "number",
                        "description": "Top edge of the zone",
                    },
                },
                "required": ["zone_type", "bottom", "top"],
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
    # SECURITY: Validate request size before processing
    try:
        validate_request_size(arguments, max_size_bytes=1_000_000)  # 1MB limit
    except RequestSizeError as e:
        logger.error(f"Request size exceeded for tool {name}: {e}")
        error_result = {"success": False, "error": "Request too large"}
        return [TextContent(type="text", text=json.dumps(error_result, indent=2))]

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

    elif name == "add_component":
        result = await _add_component(arguments, bridge)

    elif name == "decompose_glyph":
        result = await _decompose_glyph(arguments, bridge)

    elif name == "reverse_contours":
        result = await _reverse_contours(arguments, bridge)

    elif name == "remove_overlaps":
        result = await _remove_overlaps(arguments, bridge)

    elif name == "set_feature_code":
        result = await _set_feature_code(arguments, bridge)

    elif name == "create_glyph_class":
        result = await _create_glyph_class(arguments, bridge)

    elif name == "add_anchor":
        result = await _add_anchor(arguments, bridge)

    elif name == "remove_anchor":
        result = await _remove_anchor(arguments, bridge)

    elif name == "move_anchor":
        result = await _move_anchor(arguments, bridge)

    elif name == "add_layer":
        result = await _add_layer(arguments, bridge)

    elif name == "remove_layer":
        result = await _remove_layer(arguments, bridge)

    elif name == "add_guide":
        result = await _add_guide(arguments, bridge)

    elif name == "add_zone":
        result = await _add_zone(arguments, bridge)

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


async def _rename_glyph(args: dict[str, Any], bridge: FontLabBridge) -> dict[str, Any]:
    """Rename a glyph."""
    try:
        old_name = validate_glyph_name(args["old_name"])
        new_name = validate_glyph_name(args["new_name"])

        old_name_safe = sanitize_for_python(old_name)
        new_name_safe = sanitize_for_python(new_name)

        script = f"""
import json
import sys

try:
    from fontlab import flWorkspace

    font = flWorkspace.instance().currentFont()

    if font is None:
        result = {{"success": False, "error": "No font is currently open"}}
    else:
        glyph = font.findGlyph({old_name_safe})
        if glyph is None:
            result = {{"success": False, "error": f"Glyph not found: {old_name_safe}"}}
        else:
            # Check if new name already exists
            existing = font.findGlyph({new_name_safe})
            if existing is not None:
                result = {{"success": False, "error": f"Glyph already exists with name: {new_name_safe}"}}
            else:
                glyph.name = {new_name_safe}
                glyph.update()
                font.update()

                result = {{
                    "success": True,
                    "message": "Glyph renamed successfully",
                    "data": {{
                        "old_name": {old_name_safe},
                        "new_name": glyph.name
                    }}
                }}
except Exception as e:
    result = {{"success": False, "error": str(e)}}

with open(sys.argv[-1], 'w') as f:
    json.dump(result, f)
"""
        logger.info(f"Renaming glyph {old_name} to {new_name}")
        return await bridge.execute_script(script)
    except ValidationError as e:
        logger.error(f"Validation error in rename_glyph: {e}")
        return {"success": False, "error": f"Validation error: {e}"}


async def _duplicate_glyph(args: dict[str, Any], bridge: FontLabBridge) -> dict[str, Any]:
    """Duplicate a glyph."""
    try:
        name = validate_glyph_name(args["name"])
        new_name = validate_glyph_name(args["new_name"])

        name_safe = sanitize_for_python(name)
        new_name_safe = sanitize_for_python(new_name)

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
            result = {{"success": False, "error": f"Glyph not found: {name_safe}"}}
        else:
            # Check if new name already exists
            existing = font.findGlyph({new_name_safe})
            if existing is not None:
                result = {{"success": False, "error": f"Glyph already exists with name: {new_name_safe}"}}
            else:
                # Clone the glyph
                new_glyph = glyph.clone()
                new_glyph.name = {new_name_safe}
                font.addGlyph(new_glyph)
                font.update()

                result = {{
                    "success": True,
                    "message": "Glyph duplicated successfully",
                    "data": {{
                        "source": {name_safe},
                        "duplicate": new_glyph.name,
                        "width": new_glyph.width
                    }}
                }}
except Exception as e:
    result = {{"success": False, "error": str(e)}}

with open(sys.argv[-1], 'w') as f:
    json.dump(result, f)
"""
        logger.info(f"Duplicating glyph {name} as {new_name}")
        return await bridge.execute_script(script)
    except ValidationError as e:
        logger.error(f"Validation error in duplicate_glyph: {e}")
        return {"success": False, "error": f"Validation error: {e}"}


async def _set_glyph_sidebearings(args: dict[str, Any], bridge: FontLabBridge) -> dict[str, Any]:
    """Set glyph sidebearings."""
    try:
        name = validate_glyph_name(args["name"])
        lsb = args.get("lsb")
        rsb = args.get("rsb")

        if lsb is None and rsb is None:
            return {"success": False, "error": "At least one of lsb or rsb must be provided"}

        name_safe = sanitize_for_python(name)

        # Build the script conditionally based on what's provided
        lsb_line = ""
        rsb_line = ""
        if lsb is not None:
            lsb = validate_numeric_range(lsb, "lsb", min_val=-10000, max_val=10000)
            lsb_safe = sanitize_for_python(lsb)
            lsb_line = f"glyph.setLSB({lsb_safe})"

        if rsb is not None:
            rsb = validate_numeric_range(rsb, "rsb", min_val=-10000, max_val=10000)
            rsb_safe = sanitize_for_python(rsb)
            rsb_line = f"glyph.setRSB({rsb_safe})"

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
            result = {{"success": False, "error": f"Glyph not found: {name_safe}"}}
        else:
            {lsb_line}
            {rsb_line}
            glyph.update()

            result = {{
                "success": True,
                "message": "Sidebearings updated",
                "data": {{
                    "name": glyph.name,
                    "lsb": glyph.getLSB(),
                    "rsb": glyph.getRSB(),
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
        logger.error(f"Validation error in set_glyph_sidebearings: {e}")
        return {"success": False, "error": f"Validation error: {e}"}


async def _set_glyph_note(args: dict[str, Any], bridge: FontLabBridge) -> dict[str, Any]:
    """Set glyph note."""
    try:
        name = validate_glyph_name(args["name"])
        note = validate_string_length(args["note"], "note", max_length=10000)

        name_safe = sanitize_for_python(name)
        note_safe = sanitize_for_python(note)

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
            result = {{"success": False, "error": f"Glyph not found: {name_safe}"}}
        else:
            glyph.note = {note_safe}
            glyph.update()

            result = {{
                "success": True,
                "message": "Glyph note updated",
                "data": {{
                    "name": glyph.name,
                    "note": glyph.note
                }}
            }}
except Exception as e:
    result = {{"success": False, "error": str(e)}}

with open(sys.argv[-1], 'w') as f:
    json.dump(result, f)
"""
        return await bridge.execute_script(script)
    except ValidationError as e:
        logger.error(f"Validation error in set_glyph_note: {e}")
        return {"success": False, "error": f"Validation error: {e}"}


async def _set_glyph_tags(args: dict[str, Any], bridge: FontLabBridge) -> dict[str, Any]:
    """Set glyph tags."""
    try:
        name = validate_glyph_name(args["name"])
        tags = args["tags"]

        if not isinstance(tags, list):
            return {"success": False, "error": "Tags must be a list of strings"}

        # Validate each tag
        validated_tags = []
        for tag in tags:
            if not isinstance(tag, str):
                return {"success": False, "error": f"Invalid tag (must be string): {tag}"}
            validated_tags.append(validate_string_length(tag, "tag", max_length=255))

        name_safe = sanitize_for_python(name)
        tags_safe = sanitize_for_python(validated_tags)

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
            result = {{"success": False, "error": f"Glyph not found: {name_safe}"}}
        else:
            glyph.tags = {tags_safe}
            glyph.update()

            result = {{
                "success": True,
                "message": "Glyph tags updated",
                "data": {{
                    "name": glyph.name,
                    "tags": list(glyph.tags) if glyph.tags else []
                }}
            }}
except Exception as e:
    result = {{"success": False, "error": str(e)}}

with open(sys.argv[-1], 'w') as f:
    json.dump(result, f)
"""
        return await bridge.execute_script(script)
    except ValidationError as e:
        logger.error(f"Validation error in set_glyph_tags: {e}")
        return {"success": False, "error": f"Validation error: {e}"}


async def _set_glyph_mark(args: dict[str, Any], bridge: FontLabBridge) -> dict[str, Any]:
    """Set glyph mark color."""
    try:
        name = validate_glyph_name(args["name"])
        mark = validate_numeric_range(args["mark"], "mark", min_val=0, max_val=255)

        name_safe = sanitize_for_python(name)
        mark_safe = sanitize_for_python(int(mark))

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
            result = {{"success": False, "error": f"Glyph not found: {name_safe}"}}
        else:
            glyph.mark = {mark_safe}
            glyph.update()

            result = {{
                "success": True,
                "message": "Glyph mark updated",
                "data": {{
                    "name": glyph.name,
                    "mark": glyph.mark
                }}
            }}
except Exception as e:
    result = {{"success": False, "error": str(e)}}

with open(sys.argv[-1], 'w') as f:
    json.dump(result, f)
"""
        return await bridge.execute_script(script)
    except ValidationError as e:
        logger.error(f"Validation error in set_glyph_mark: {e}")
        return {"success": False, "error": f"Validation error: {e}"}


async def _set_kerning_pair(args: dict[str, Any], bridge: FontLabBridge) -> dict[str, Any]:
    """Set kerning between two glyphs."""
    try:
        left = validate_glyph_name(args["left"])
        right = validate_glyph_name(args["right"])
        value = validate_numeric_range(args["value"], "value", min_val=-10000, max_val=10000)

        left_safe = sanitize_for_python(left)
        right_safe = sanitize_for_python(right)
        value_safe = sanitize_for_python(value)

        script = f"""
import json
import sys

try:
    from fontlab import flWorkspace

    font = flWorkspace.instance().currentFont()

    if font is None:
        result = {{"success": False, "error": "No font is currently open"}}
    else:
        # Access fontgate for kerning
        fg_font = font.fgFont if hasattr(font, 'fgFont') else None

        if fg_font is None or not hasattr(fg_font, 'kerning'):
            result = {{"success": False, "error": "Font does not support kerning"}}
        else:
            # Set kerning value
            fg_font.kerning[{left_safe}, {right_safe}] = {value_safe}
            font.update()

            result = {{
                "success": True,
                "message": "Kerning pair updated",
                "data": {{
                    "left": {left_safe},
                    "right": {right_safe},
                    "value": {value_safe}
                }}
            }}
except Exception as e:
    result = {{"success": False, "error": str(e)}}

with open(sys.argv[-1], 'w') as f:
    json.dump(result, f)
"""
        logger.info(f"Setting kerning: {left}/{right} = {value}")
        return await bridge.execute_script(script)
    except ValidationError as e:
        logger.error(f"Validation error in set_kerning_pair: {e}")
        return {"success": False, "error": f"Validation error: {e}"}


async def _remove_kerning_pair(args: dict[str, Any], bridge: FontLabBridge) -> dict[str, Any]:
    """Remove kerning between two glyphs."""
    try:
        left = validate_glyph_name(args["left"])
        right = validate_glyph_name(args["right"])

        left_safe = sanitize_for_python(left)
        right_safe = sanitize_for_python(right)

        script = f"""
import json
import sys

try:
    from fontlab import flWorkspace

    font = flWorkspace.instance().currentFont()

    if font is None:
        result = {{"success": False, "error": "No font is currently open"}}
    else:
        # Access fontgate for kerning
        fg_font = font.fgFont if hasattr(font, 'fgFont') else None

        if fg_font is None or not hasattr(fg_font, 'kerning'):
            result = {{"success": False, "error": "Font does not support kerning"}}
        else:
            # Remove kerning
            if ({left_safe}, {right_safe}) in fg_font.kerning:
                del fg_font.kerning[{left_safe}, {right_safe}]
                font.update()
                result = {{
                    "success": True,
                    "message": "Kerning pair removed",
                    "data": {{
                        "left": {left_safe},
                        "right": {right_safe}
                    }}
                }}
            else:
                result = {{
                    "success": False,
                    "error": f"No kerning found for pair: {left_safe}/{right_safe}"
                }}
except Exception as e:
    result = {{"success": False, "error": str(e)}}

with open(sys.argv[-1], 'w') as f:
    json.dump(result, f)
"""
        logger.info(f"Removing kerning: {left}/{right}")
        return await bridge.execute_script(script)
    except ValidationError as e:
        logger.error(f"Validation error in remove_kerning_pair: {e}")
        return {"success": False, "error": f"Validation error: {e}"}


async def _add_component(args: dict[str, Any], bridge: FontLabBridge) -> dict[str, Any]:
    """Add a component reference to a glyph."""
    try:
        glyph_name = validate_glyph_name(args["glyph_name"])
        base_glyph = validate_glyph_name(args["base_glyph"])
        x_offset = validate_numeric_range(args.get("x_offset", 0), "x_offset", min_val=-10000, max_val=10000)
        y_offset = validate_numeric_range(args.get("y_offset", 0), "y_offset", min_val=-10000, max_val=10000)

        glyph_name_safe = sanitize_for_python(glyph_name)
        base_glyph_safe = sanitize_for_python(base_glyph)
        x_offset_safe = sanitize_for_python(x_offset)
        y_offset_safe = sanitize_for_python(y_offset)

        script = f"""
import json
import sys

try:
    from fontlab import flWorkspace, flShape

    font = flWorkspace.instance().currentFont()

    if font is None:
        result = {{"success": False, "error": "No font is currently open"}}
    else:
        glyph = font.findGlyph({glyph_name_safe})
        if glyph is None:
            result = {{"success": False, "error": f"Glyph not found: {glyph_name_safe}"}}
        else:
            base = font.findGlyph({base_glyph_safe})
            if base is None:
                result = {{"success": False, "error": f"Base glyph not found: {base_glyph_safe}"}}
            else:
                layer = glyph.layers[0] if glyph.layers else None
                if layer is None:
                    result = {{"success": False, "error": "Glyph has no layers"}}
                else:
                    # Create component
                    component = flShape()
                    component.shapeType = 1  # Component type
                    component.name = {base_glyph_safe}
                    component.transform.translate({x_offset_safe}, {y_offset_safe})

                    layer.addShape(component)
                    glyph.update()

                    result = {{
                        "success": True,
                        "message": "Component added successfully",
                        "data": {{
                            "glyph": {glyph_name_safe},
                            "base_glyph": {base_glyph_safe},
                            "offset": [{x_offset_safe}, {y_offset_safe}]
                        }}
                    }}
except Exception as e:
    result = {{"success": False, "error": str(e)}}

with open(sys.argv[-1], 'w') as f:
    json.dump(result, f)
"""
        return await bridge.execute_script(script)
    except ValidationError as e:
        logger.error(f"Validation error in add_component: {e}")
        return {"success": False, "error": f"Validation error: {e}"}


async def _decompose_glyph(args: dict[str, Any], bridge: FontLabBridge) -> dict[str, Any]:
    """Decompose all components in a glyph."""
    try:
        name = validate_glyph_name(args["name"])
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
            result = {{"success": False, "error": f"Glyph not found: {name_safe}"}}
        else:
            layer = glyph.layers[0] if glyph.layers else None
            if layer is None:
                result = {{"success": False, "error": "Glyph has no layers"}}
            else:
                # Decompose components
                layer.decompose()
                glyph.update()

                result = {{
                    "success": True,
                    "message": "Glyph decomposed successfully",
                    "data": {{"name": {name_safe}}}
                }}
except Exception as e:
    result = {{"success": False, "error": str(e)}}

with open(sys.argv[-1], 'w') as f:
    json.dump(result, f)
"""
        return await bridge.execute_script(script)
    except ValidationError as e:
        logger.error(f"Validation error in decompose_glyph: {e}")
        return {"success": False, "error": f"Validation error: {e}"}


async def _reverse_contours(args: dict[str, Any], bridge: FontLabBridge) -> dict[str, Any]:
    """Reverse the direction of all contours."""
    try:
        name = validate_glyph_name(args["name"])
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
            result = {{"success": False, "error": f"Glyph not found: {name_safe}"}}
        else:
            layer = glyph.layers[0] if glyph.layers else None
            if layer is None:
                result = {{"success": False, "error": "Glyph has no layers"}}
            else:
                # Reverse all contours
                for shape in layer.shapes:
                    if hasattr(shape, 'isContour') and shape.isContour:
                        shape.reverse()

                glyph.update()

                result = {{
                    "success": True,
                    "message": "Contours reversed successfully",
                    "data": {{"name": {name_safe}}}
                }}
except Exception as e:
    result = {{"success": False, "error": str(e)}}

with open(sys.argv[-1], 'w') as f:
    json.dump(result, f)
"""
        return await bridge.execute_script(script)
    except ValidationError as e:
        logger.error(f"Validation error in reverse_contours: {e}")
        return {"success": False, "error": f"Validation error: {e}"}


async def _remove_overlaps(args: dict[str, Any], bridge: FontLabBridge) -> dict[str, Any]:
    """Remove overlapping paths in a glyph."""
    try:
        name = validate_glyph_name(args["name"])
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
            result = {{"success": False, "error": f"Glyph not found: {name_safe}"}}
        else:
            layer = glyph.layers[0] if glyph.layers else None
            if layer is None:
                result = {{"success": False, "error": "Glyph has no layers"}}
            else:
                # Remove overlaps
                layer.removeOverlap()
                glyph.update()

                result = {{
                    "success": True,
                    "message": "Overlaps removed successfully",
                    "data": {{"name": {name_safe}}}
                }}
except Exception as e:
    result = {{"success": False, "error": str(e)}}

with open(sys.argv[-1], 'w') as f:
    json.dump(result, f)
"""
        return await bridge.execute_script(script)
    except ValidationError as e:
        logger.error(f"Validation error in remove_overlaps: {e}")
        return {"success": False, "error": f"Validation error: {e}"}


async def _set_feature_code(args: dict[str, Any], bridge: FontLabBridge) -> dict[str, Any]:
    """Set OpenType feature code."""
    try:
        features = validate_string_length(args["features"], "features", max_length=100000)
        features_safe = sanitize_for_python(features)

        script = f"""
import json
import sys

try:
    from fontlab import flWorkspace

    font = flWorkspace.instance().currentFont()

    if font is None:
        result = {{"success": False, "error": "No font is currently open"}}
    else:
        # Access fontgate for features
        fg_font = font.fgFont if hasattr(font, 'fgFont') else None

        if fg_font is None or not hasattr(fg_font, 'features'):
            result = {{"success": False, "error": "Font does not support features"}}
        else:
            # Set feature code
            fg_font.features.text = {features_safe}
            font.update()

            result = {{
                "success": True,
                "message": "Feature code updated successfully",
                "data": {{
                    "feature_length": len({features_safe})
                }}
            }}
except Exception as e:
    result = {{"success": False, "error": str(e)}}

with open(sys.argv[-1], 'w') as f:
    json.dump(result, f)
"""
        return await bridge.execute_script(script)
    except ValidationError as e:
        logger.error(f"Validation error in set_feature_code: {e}")
        return {"success": False, "error": f"Validation error: {e}"}


async def _create_glyph_class(args: dict[str, Any], bridge: FontLabBridge) -> dict[str, Any]:
    """Create or update a glyph class."""
    try:
        class_name = validate_string_length(args["class_name"], "class_name", max_length=255)
        glyphs = args["glyphs"]

        if not isinstance(glyphs, list):
            return {"success": False, "error": "Glyphs must be a list of strings"}

        # Validate each glyph name
        validated_glyphs = []
        for glyph in glyphs:
            if not isinstance(glyph, str):
                return {"success": False, "error": f"Invalid glyph name (must be string): {glyph}"}
            validated_glyphs.append(validate_glyph_name(glyph))

        class_name_safe = sanitize_for_python(class_name)
        glyphs_safe = sanitize_for_python(validated_glyphs)

        script = f"""
import json
import sys

try:
    from fontlab import flWorkspace

    font = flWorkspace.instance().currentFont()

    if font is None:
        result = {{"success": False, "error": "No font is currently open"}}
    else:
        # Access fontgate for glyph classes
        fg_font = font.fgFont if hasattr(font, 'fgFont') else None

        if fg_font is None or not hasattr(fg_font, 'groups'):
            result = {{"success": False, "error": "Font does not support glyph classes"}}
        else:
            # Create/update glyph class
            fg_font.groups[{class_name_safe}] = {glyphs_safe}
            font.update()

            result = {{
                "success": True,
                "message": "Glyph class created/updated successfully",
                "data": {{
                    "class_name": {class_name_safe},
                    "glyphs": {glyphs_safe},
                    "count": len({glyphs_safe})
                }}
            }}
except Exception as e:
    result = {{"success": False, "error": str(e)}}

with open(sys.argv[-1], 'w') as f:
    json.dump(result, f)
"""
        return await bridge.execute_script(script)
    except ValidationError as e:
        logger.error(f"Validation error in create_glyph_class: {e}")
        return {"success": False, "error": f"Validation error: {e}"}


async def _add_anchor(args: dict[str, Any], bridge: FontLabBridge) -> dict[str, Any]:
    """Add an anchor to a glyph."""
    try:
        glyph_name = validate_glyph_name(args["glyph_name"])
        anchor_name = validate_string_length(args["anchor_name"], "anchor_name", max_length=255)
        x = validate_numeric_range(args["x"], "x", min_val=-10000, max_val=10000)
        y = validate_numeric_range(args["y"], "y", min_val=-10000, max_val=10000)

        glyph_name_safe = sanitize_for_python(glyph_name)
        anchor_name_safe = sanitize_for_python(anchor_name)
        x_safe = sanitize_for_python(x)
        y_safe = sanitize_for_python(y)

        script = f"""
import json
import sys

try:
    from fontlab import flWorkspace

    font = flWorkspace.instance().currentFont()

    if font is None:
        result = {{"success": False, "error": "No font is currently open"}}
    else:
        glyph = font.findGlyph({glyph_name_safe})
        if glyph is None:
            result = {{"success": False, "error": f"Glyph not found: {glyph_name_safe}"}}
        else:
            # Check if anchor already exists
            existing_anchor = None
            if hasattr(glyph, 'anchors') and glyph.anchors:
                for anchor in glyph.anchors:
                    if hasattr(anchor, 'name') and anchor.name == {anchor_name_safe}:
                        existing_anchor = anchor
                        break

            if existing_anchor:
                result = {{"success": False, "error": f"Anchor already exists: {anchor_name_safe}"}}
            else:
                # Add anchor
                from fontlab import flAnchor
                anchor = flAnchor()
                anchor.name = {anchor_name_safe}
                anchor.x = {x_safe}
                anchor.y = {y_safe}

                if not hasattr(glyph, 'anchors'):
                    glyph.anchors = []
                glyph.anchors.append(anchor)
                glyph.update()

                result = {{
                    "success": True,
                    "message": "Anchor added successfully",
                    "data": {{
                        "glyph": {glyph_name_safe},
                        "anchor": {anchor_name_safe},
                        "position": [{x_safe}, {y_safe}]
                    }}
                }}
except Exception as e:
    result = {{"success": False, "error": str(e)}}

with open(sys.argv[-1], 'w') as f:
    json.dump(result, f)
"""
        return await bridge.execute_script(script)
    except ValidationError as e:
        logger.error(f"Validation error in add_anchor: {e}")
        return {"success": False, "error": f"Validation error: {e}"}


async def _remove_anchor(args: dict[str, Any], bridge: FontLabBridge) -> dict[str, Any]:
    """Remove an anchor from a glyph."""
    try:
        glyph_name = validate_glyph_name(args["glyph_name"])
        anchor_name = validate_string_length(args["anchor_name"], "anchor_name", max_length=255)

        glyph_name_safe = sanitize_for_python(glyph_name)
        anchor_name_safe = sanitize_for_python(anchor_name)

        script = f"""
import json
import sys

try:
    from fontlab import flWorkspace

    font = flWorkspace.instance().currentFont()

    if font is None:
        result = {{"success": False, "error": "No font is currently open"}}
    else:
        glyph = font.findGlyph({glyph_name_safe})
        if glyph is None:
            result = {{"success": False, "error": f"Glyph not found: {glyph_name_safe}"}}
        else:
            # Find and remove anchor
            found = False
            if hasattr(glyph, 'anchors') and glyph.anchors:
                for i, anchor in enumerate(glyph.anchors):
                    if hasattr(anchor, 'name') and anchor.name == {anchor_name_safe}:
                        glyph.anchors.pop(i)
                        found = True
                        break

            if found:
                glyph.update()
                result = {{
                    "success": True,
                    "message": "Anchor removed successfully",
                    "data": {{
                        "glyph": {glyph_name_safe},
                        "anchor": {anchor_name_safe}
                    }}
                }}
            else:
                result = {{"success": False, "error": f"Anchor not found: {anchor_name_safe}"}}
except Exception as e:
    result = {{"success": False, "error": str(e)}}

with open(sys.argv[-1], 'w') as f:
    json.dump(result, f)
"""
        return await bridge.execute_script(script)
    except ValidationError as e:
        logger.error(f"Validation error in remove_anchor: {e}")
        return {"success": False, "error": f"Validation error: {e}"}


async def _move_anchor(args: dict[str, Any], bridge: FontLabBridge) -> dict[str, Any]:
    """Move an existing anchor to a new position."""
    try:
        glyph_name = validate_glyph_name(args["glyph_name"])
        anchor_name = validate_string_length(args["anchor_name"], "anchor_name", max_length=255)
        x = validate_numeric_range(args["x"], "x", min_val=-10000, max_val=10000)
        y = validate_numeric_range(args["y"], "y", min_val=-10000, max_val=10000)

        glyph_name_safe = sanitize_for_python(glyph_name)
        anchor_name_safe = sanitize_for_python(anchor_name)
        x_safe = sanitize_for_python(x)
        y_safe = sanitize_for_python(y)

        script = f"""
import json
import sys

try:
    from fontlab import flWorkspace

    font = flWorkspace.instance().currentFont()

    if font is None:
        result = {{"success": False, "error": "No font is currently open"}}
    else:
        glyph = font.findGlyph({glyph_name_safe})
        if glyph is None:
            result = {{"success": False, "error": f"Glyph not found: {glyph_name_safe}"}}
        else:
            # Find and move anchor
            found = False
            if hasattr(glyph, 'anchors') and glyph.anchors:
                for anchor in glyph.anchors:
                    if hasattr(anchor, 'name') and anchor.name == {anchor_name_safe}:
                        old_x = anchor.x if hasattr(anchor, 'x') else 0
                        old_y = anchor.y if hasattr(anchor, 'y') else 0
                        anchor.x = {x_safe}
                        anchor.y = {y_safe}
                        found = True
                        break

            if found:
                glyph.update()
                result = {{
                    "success": True,
                    "message": "Anchor moved successfully",
                    "data": {{
                        "glyph": {glyph_name_safe},
                        "anchor": {anchor_name_safe},
                        "old_position": [old_x, old_y],
                        "new_position": [{x_safe}, {y_safe}]
                    }}
                }}
            else:
                result = {{"success": False, "error": f"Anchor not found: {anchor_name_safe}"}}
except Exception as e:
    result = {{"success": False, "error": str(e)}}

with open(sys.argv[-1], 'w') as f:
    json.dump(result, f)
"""
        return await bridge.execute_script(script)
    except ValidationError as e:
        logger.error(f"Validation error in move_anchor: {e}")
        return {"success": False, "error": f"Validation error: {e}"}


async def _add_layer(args: dict[str, Any], bridge: FontLabBridge) -> dict[str, Any]:
    """Add a new layer to a glyph."""
    try:
        glyph_name = validate_glyph_name(args["glyph_name"])
        layer_name = validate_string_length(args["layer_name"], "layer_name", max_length=255)

        glyph_name_safe = sanitize_for_python(glyph_name)
        layer_name_safe = sanitize_for_python(layer_name)

        script = f"""
import json
import sys

try:
    from fontlab import flWorkspace, flLayer

    font = flWorkspace.instance().currentFont()

    if font is None:
        result = {{"success": False, "error": "No font is currently open"}}
    else:
        glyph = font.findGlyph({glyph_name_safe})
        if glyph is None:
            result = {{"success": False, "error": f"Glyph not found: {glyph_name_safe}"}}
        else:
            # Create new layer
            new_layer = flLayer()
            new_layer.name = {layer_name_safe}

            # Add layer to glyph
            glyph.addLayer(new_layer)
            glyph.update()

            result = {{
                "success": True,
                "message": "Layer added successfully",
                "data": {{
                    "glyph": {glyph_name_safe},
                    "layer_name": {layer_name_safe},
                    "layer_count": len(glyph.layers)
                }}
            }}
except Exception as e:
    result = {{"success": False, "error": str(e)}}

with open(sys.argv[-1], 'w') as f:
    json.dump(result, f)
"""
        return await bridge.execute_script(script)
    except ValidationError as e:
        logger.error(f"Validation error in add_layer: {e}")
        return {"success": False, "error": f"Validation error: {e}"}


async def _remove_layer(args: dict[str, Any], bridge: FontLabBridge) -> dict[str, Any]:
    """Remove a layer from a glyph."""
    try:
        glyph_name = validate_glyph_name(args["glyph_name"])
        layer_index = validate_numeric_range(args["layer_index"], "layer_index", min_val=0, max_val=100)

        glyph_name_safe = sanitize_for_python(glyph_name)
        layer_index_safe = sanitize_for_python(int(layer_index))

        script = f"""
import json
import sys

try:
    from fontlab import flWorkspace

    font = flWorkspace.instance().currentFont()

    if font is None:
        result = {{"success": False, "error": "No font is currently open"}}
    else:
        glyph = font.findGlyph({glyph_name_safe})
        if glyph is None:
            result = {{"success": False, "error": f"Glyph not found: {glyph_name_safe}"}}
        else:
            if not hasattr(glyph, 'layers') or not glyph.layers:
                result = {{"success": False, "error": "Glyph has no layers"}}
            elif {layer_index_safe} >= len(glyph.layers):
                result = {{"success": False, "error": f"Layer index out of range: {layer_index_safe} (max: {{len(glyph.layers)-1}})"}}
            elif {layer_index_safe} == 0 and len(glyph.layers) == 1:
                result = {{"success": False, "error": "Cannot remove the only layer"}}
            else:
                # Remove layer
                removed_layer_name = glyph.layers[{layer_index_safe}].name if hasattr(glyph.layers[{layer_index_safe}], 'name') else f"Layer {layer_index_safe}"
                glyph.removeLayer({layer_index_safe})
                glyph.update()

                result = {{
                    "success": True,
                    "message": "Layer removed successfully",
                    "data": {{
                        "glyph": {glyph_name_safe},
                        "removed_layer": removed_layer_name,
                        "layer_count": len(glyph.layers)
                    }}
                }}
except Exception as e:
    result = {{"success": False, "error": str(e)}}

with open(sys.argv[-1], 'w') as f:
    json.dump(result, f)
"""
        return await bridge.execute_script(script)
    except ValidationError as e:
        logger.error(f"Validation error in remove_layer: {e}")
        return {"success": False, "error": f"Validation error: {e}"}


async def _add_guide(args: dict[str, Any], bridge: FontLabBridge) -> dict[str, Any]:
    """Add a global guide to the font."""
    try:
        position = validate_numeric_range(args["position"], "position", min_val=-10000, max_val=10000)
        angle = validate_numeric_range(args.get("angle", 0), "angle", min_val=-360, max_val=360)
        name = validate_string_length(args.get("name", ""), "name", max_length=255)

        position_safe = sanitize_for_python(position)
        angle_safe = sanitize_for_python(angle)
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
        # Access fontgate for guides
        fg_font = font.fgFont if hasattr(font, 'fgFont') else None

        if fg_font is None:
            result = {{"success": False, "error": "Font does not support guides"}}
        else:
            # Add guide using fontgate
            from fontgate import fgGuide
            guide = fgGuide()
            guide.position = {position_safe}
            guide.angle = {angle_safe}
            if {name_safe}:
                guide.name = {name_safe}

            if not hasattr(fg_font, 'guides'):
                fg_font.guides = []
            fg_font.guides.append(guide)
            font.update()

            result = {{
                "success": True,
                "message": "Guide added successfully",
                "data": {{
                    "position": {position_safe},
                    "angle": {angle_safe},
                    "name": {name_safe}
                }}
            }}
except Exception as e:
    result = {{"success": False, "error": str(e)}}

with open(sys.argv[-1], 'w') as f:
    json.dump(result, f)
"""
        return await bridge.execute_script(script)
    except ValidationError as e:
        logger.error(f"Validation error in add_guide: {e}")
        return {"success": False, "error": f"Validation error: {e}"}


async def _add_zone(args: dict[str, Any], bridge: FontLabBridge) -> dict[str, Any]:
    """Add an alignment zone to the font."""
    try:
        zone_type = args["zone_type"]
        if zone_type not in ["blue", "other_blue"]:
            return {"success": False, "error": f"Invalid zone type: {zone_type}"}

        bottom = validate_numeric_range(args["bottom"], "bottom", min_val=-10000, max_val=10000)
        top = validate_numeric_range(args["top"], "top", min_val=-10000, max_val=10000)

        if bottom >= top:
            return {"success": False, "error": "Bottom must be less than top"}

        zone_type_safe = sanitize_for_python(zone_type)
        bottom_safe = sanitize_for_python(bottom)
        top_safe = sanitize_for_python(top)

        script = f"""
import json
import sys

try:
    from fontlab import flWorkspace

    font = flWorkspace.instance().currentFont()

    if font is None:
        result = {{"success": False, "error": "No font is currently open"}}
    else:
        if not hasattr(font, 'info'):
            result = {{"success": False, "error": "Font does not have info"}}
        else:
            # Add zone to appropriate list
            if {zone_type_safe} == "blue":
                if not hasattr(font.info, 'postscriptBlueValues') or font.info.postscriptBlueValues is None:
                    font.info.postscriptBlueValues = []
                font.info.postscriptBlueValues.extend([{bottom_safe}, {top_safe}])
            else:  # other_blue
                if not hasattr(font.info, 'postscriptOtherBlues') or font.info.postscriptOtherBlues is None:
                    font.info.postscriptOtherBlues = []
                font.info.postscriptOtherBlues.extend([{bottom_safe}, {top_safe}])

            font.update()

            result = {{
                "success": True,
                "message": "Alignment zone added successfully",
                "data": {{
                    "type": {zone_type_safe},
                    "bottom": {bottom_safe},
                    "top": {top_safe}
                }}
            }}
except Exception as e:
    result = {{"success": False, "error": str(e)}}

with open(sys.argv[-1], 'w') as f:
    json.dump(result, f)
"""
        return await bridge.execute_script(script)
    except ValidationError as e:
        logger.error(f"Validation error in add_zone: {e}")
        return {"success": False, "error": f"Validation error: {e}"}
