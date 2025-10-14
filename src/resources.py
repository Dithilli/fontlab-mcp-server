"""
FontLab Resources
Handles read-only resource operations for MCP
"""

import json
import logging
from typing import Any
from urllib.parse import urlparse, parse_qs, unquote
from mcp.types import Resource, TextContent

from .fontlab_bridge import FontLabBridge

logger = logging.getLogger(__name__)


class URIParseError(Exception):
    """Raised when URI parsing fails."""
    pass


def _parse_uri_path(uri: str, expected_prefix: str) -> str:
    """
    Safely parse URI path and extract the component after the prefix.

    Args:
        uri: Full URI to parse
        expected_prefix: Expected URI scheme and path prefix

    Returns:
        Extracted path component (unquoted)

    Raises:
        URIParseError: If URI is malformed or contains path traversal
    """
    try:
        parsed = urlparse(uri)

        # Verify scheme
        if parsed.scheme != "fontlab":
            raise URIParseError(f"Invalid URI scheme: {parsed.scheme}")

        # Get the path without leading slash
        path = parsed.path.lstrip('/')

        # Check for path traversal attempts
        if '..' in path or path.startswith('.'):
            raise URIParseError(f"Path traversal detected in URI: {uri}")

        # Extract the component after expected prefix
        prefix_without_scheme = expected_prefix.replace("fontlab://", "")
        if not path.startswith(prefix_without_scheme):
            raise URIParseError(f"URI does not match expected prefix: {expected_prefix}")

        component = path[len(prefix_without_scheme):]

        # URL decode the component
        decoded = unquote(component)

        # Additional check after decoding
        if '..' in decoded or '\x00' in decoded:
            raise URIParseError(f"Invalid characters in URI component: {component}")

        return decoded

    except URIParseError:
        raise
    except Exception as e:
        raise URIParseError(f"Failed to parse URI: {e}")


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
        Resource(
            uri="fontlab://glyphs/by-unicode/{codepoint}",
            name="Glyph by Unicode",
            description="Find glyph by Unicode code point (decimal or hex with 0x prefix)",
            mimeType="application/json",
        ),
        Resource(
            uri="fontlab://glyphs/search?pattern={pattern}",
            name="Search Glyphs",
            description="Search for glyphs by name pattern (supports wildcards: * and ?)",
            mimeType="application/json",
        ),
        Resource(
            uri="fontlab://glyph/{name}/metadata",
            name="Glyph Metadata",
            description="Get glyph metadata (tags, note, mark color)",
            mimeType="application/json",
        ),
        Resource(
            uri="fontlab://font/kerning",
            name="Font Kerning",
            description="Get all kerning pairs in the font",
            mimeType="application/json",
        ),
        Resource(
            uri="fontlab://glyph/{name}/contours",
            name="Glyph Contours",
            description="Get contour data for a specific glyph",
            mimeType="application/json",
        ),
        Resource(
            uri="fontlab://glyph/{name}/paths",
            name="Glyph Paths",
            description="Get detailed path data with nodes for a specific glyph",
            mimeType="application/json",
        ),
        Resource(
            uri="fontlab://glyph/{name}/components",
            name="Glyph Components",
            description="Get component references in a glyph",
            mimeType="application/json",
        ),
        Resource(
            uri="fontlab://font/features",
            name="OpenType Features",
            description="Get all OpenType feature code",
            mimeType="application/json",
        ),
        Resource(
            uri="fontlab://font/classes",
            name="Glyph Classes",
            description="Get all glyph classes defined in the font",
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
    try:
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

        elif uri == "fontlab://font/kerning":
            result = await bridge.get_kerning()
            return json.dumps(result, indent=2)

        elif uri == "fontlab://font/features":
            result = await bridge.get_font_features()
            return json.dumps(result, indent=2)

        elif uri == "fontlab://font/classes":
            result = await bridge.get_glyph_classes()
            return json.dumps(result, indent=2)

        elif uri.startswith("fontlab://glyph/") and "/metadata" in uri:
            # Extract glyph name from URI (before /metadata)
            full_path = _parse_uri_path(uri, "fontlab://glyph/")
            glyph_name = full_path.replace("/metadata", "")
            if not glyph_name:
                raise ValueError("Glyph name is required")

            result = await bridge.get_glyph_metadata(glyph_name)
            return json.dumps(result, indent=2)

        elif uri.startswith("fontlab://glyph/") and "/contours" in uri:
            # Extract glyph name from URI (before /contours)
            full_path = _parse_uri_path(uri, "fontlab://glyph/")
            glyph_name = full_path.replace("/contours", "")
            if not glyph_name:
                raise ValueError("Glyph name is required")

            result = await bridge.get_glyph_contours(glyph_name)
            return json.dumps(result, indent=2)

        elif uri.startswith("fontlab://glyph/") and "/paths" in uri:
            # Extract glyph name from URI (before /paths)
            full_path = _parse_uri_path(uri, "fontlab://glyph/")
            glyph_name = full_path.replace("/paths", "")
            if not glyph_name:
                raise ValueError("Glyph name is required")

            result = await bridge.get_glyph_paths(glyph_name)
            return json.dumps(result, indent=2)

        elif uri.startswith("fontlab://glyph/") and "/components" in uri:
            # Extract glyph name from URI (before /components)
            full_path = _parse_uri_path(uri, "fontlab://glyph/")
            glyph_name = full_path.replace("/components", "")
            if not glyph_name:
                raise ValueError("Glyph name is required")

            result = await bridge.get_glyph_components(glyph_name)
            return json.dumps(result, indent=2)

        elif uri.startswith("fontlab://glyph/"):
            # Extract glyph name from URI
            glyph_name = _parse_uri_path(uri, "fontlab://glyph/")
            if not glyph_name:
                raise ValueError("Glyph name is required")

            result = await bridge.get_glyph(glyph_name)
            return json.dumps(result, indent=2)

        elif uri.startswith("fontlab://glyphs/by-unicode/"):
            # Extract unicode code point
            codepoint_str = _parse_uri_path(uri, "fontlab://glyphs/by-unicode/")
            if not codepoint_str:
                raise ValueError("Unicode code point is required")

            # Parse hex (0x...) or decimal
            try:
                if codepoint_str.lower().startswith("0x"):
                    codepoint = int(codepoint_str, 16)
                else:
                    codepoint = int(codepoint_str)
            except ValueError:
                raise ValueError(f"Invalid unicode code point: {codepoint_str}")

            result = await bridge.find_glyph_by_unicode(codepoint)
            return json.dumps(result, indent=2)

        elif uri.startswith("fontlab://glyphs/search"):
            # Extract search pattern from query string using urlparse
            parsed = urlparse(uri)
            if not parsed.query:
                raise ValueError("Search pattern is required (use ?pattern=...)")

            params = parse_qs(parsed.query)
            if "pattern" not in params or not params["pattern"]:
                raise ValueError("Missing 'pattern' parameter")

            # parse_qs returns lists, get first value
            pattern = params["pattern"][0]

            # Decode and validate pattern
            pattern = unquote(pattern)
            if '..' in pattern or '\x00' in pattern:
                raise ValueError("Invalid characters in search pattern")

            result = await bridge.search_glyphs(pattern)
            return json.dumps(result, indent=2)

        else:
            raise ValueError(f"Unknown resource URI: {uri}")

    except URIParseError as e:
        logger.error(f"URI parsing error: {e}")
        raise ValueError(f"Invalid URI: {str(e)}")
    except Exception as e:
        logger.error(f"Error handling resource {uri}: {e}")
        raise
