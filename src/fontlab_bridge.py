"""
FontLab Bridge
Handles communication between MCP server and FontLab's Python environment
"""

import asyncio
import json
import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


class FontLabBridge:
    """Bridge for executing Python scripts in FontLab's environment."""

    def __init__(self, fontlab_path: Optional[str] = None):
        """
        Initialize the FontLab bridge.

        Args:
            fontlab_path: Optional path to FontLab executable
        """
        self.fontlab_path = fontlab_path or self._find_fontlab()
        self.scripts_dir = Path(__file__).parent.parent / "scripts"

    def _find_fontlab(self) -> Optional[str]:
        """
        Find FontLab installation path.

        Returns:
            Path to FontLab executable or None if not found
        """
        # Common installation paths
        possible_paths = [
            "/Applications/FontLab 8.app/Contents/MacOS/FontLab",
            "/Applications/FontLab 7.app/Contents/MacOS/FontLab",
            "/usr/local/bin/fontlab",
        ]

        for path in possible_paths:
            if Path(path).exists():
                return path

        return None

    async def execute_script(
        self, script_content: str, timeout: int = 30
    ) -> dict[str, Any]:
        """
        Execute a Python script in FontLab's environment.

        Args:
            script_content: Python script to execute
            timeout: Execution timeout in seconds

        Returns:
            Dictionary with execution result

        Raises:
            RuntimeError: If FontLab is not found or script execution fails
        """
        if not self.fontlab_path:
            raise RuntimeError(
                "FontLab executable not found. Please specify fontlab_path "
                "or ensure FontLab is installed in a standard location."
            )

        # Create temporary script file
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False
        ) as tmp_script:
            tmp_script.write(script_content)
            tmp_script_path = tmp_script.name

        # Create temporary output file
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as tmp_output:
            tmp_output_path = tmp_output.name

        try:
            # Build command to execute script in FontLab
            # Note: This assumes FontLab can be run with -script flag
            # Adjust based on actual FontLab CLI interface
            cmd = [
                self.fontlab_path,
                "-script",
                tmp_script_path,
                "-output",
                tmp_output_path,
            ]

            # Execute the script
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), timeout=timeout
                )
            except asyncio.TimeoutError:
                logger.error(f"Script execution timeout after {timeout}s")
                process.kill()
                # Wait for process to actually terminate
                try:
                    await asyncio.wait_for(process.wait(), timeout=5)
                except asyncio.TimeoutError:
                    logger.error("Process did not terminate after kill signal")
                raise RuntimeError(f"Script execution timed out after {timeout}s")

            # Read the output
            output_path = Path(tmp_output_path)
            if output_path.exists():
                with open(output_path, "r") as f:
                    result = json.load(f)
            else:
                # Fallback if no output file was created
                result = {
                    "success": process.returncode == 0,
                    "stdout": stdout.decode("utf-8") if stdout else "",
                    "stderr": stderr.decode("utf-8") if stderr else "",
                }

            return result

        finally:
            # Clean up temporary files
            Path(tmp_script_path).unlink(missing_ok=True)
            Path(tmp_output_path).unlink(missing_ok=True)

    async def get_current_font(self) -> dict[str, Any]:
        """
        Get information about the currently open font in FontLab.

        Returns:
            Dictionary with font information
        """
        script = """
import json
import sys

try:
    from fontlab import flWorkspace, fl

    # Get current font
    font = flWorkspace.instance().currentFont()

    if font is None:
        result = {
            "success": False,
            "error": "No font is currently open"
        }
    else:
        result = {
            "success": True,
            "data": {
                "family_name": font.info.familyName or "",
                "style_name": font.info.styleName or "",
                "full_name": font.info.fullName or "",
                "version": font.info.versionMajor or 1,
                "glyph_count": len(font.glyphs),
                "units_per_em": font.info.unitsPerEm or 1000,
            }
        }
except Exception as e:
    result = {
        "success": False,
        "error": str(e)
    }

# Write result to output file
with open(sys.argv[-1], 'w') as f:
    json.dump(result, f)
"""
        return await self.execute_script(script)

    async def list_glyphs(self) -> dict[str, Any]:
        """
        List all glyphs in the current font.

        Returns:
            Dictionary with list of glyphs
        """
        script = """
import json
import sys

try:
    from fontlab import flWorkspace

    font = flWorkspace.instance().currentFont()

    if font is None:
        result = {
            "success": False,
            "error": "No font is currently open"
        }
    else:
        glyphs = []
        for glyph in font.glyphs:
            glyphs.append({
                "name": glyph.name,
                "unicode": glyph.unicode if glyph.unicode else None,
                "width": glyph.width,
                "has_contours": len(glyph.layers[0].shapes) > 0
            })

        result = {
            "success": True,
            "data": {
                "glyphs": glyphs,
                "count": len(glyphs)
            }
        }
except Exception as e:
    result = {
        "success": False,
        "error": str(e)
    }

with open(sys.argv[-1], 'w') as f:
    json.dump(result, f)
"""
        return await self.execute_script(script)

    async def get_glyph(self, glyph_name: str) -> dict[str, Any]:
        """
        Get detailed information about a specific glyph.

        Args:
            glyph_name: Name of the glyph

        Returns:
            Dictionary with glyph information
        """
        # Sanitize glyph name to prevent command injection
        glyph_name_safe = json.dumps(glyph_name)

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
            result = {{"success": False, "error": f"Glyph not found: {{{{glyph_name_safe}}}}"}}
        else:
            layer = glyph.layers[0]

            result = {{
                "success": True,
                "data": {{
                    "name": glyph.name,
                    "unicode": glyph.unicode if glyph.unicode else None,
                    "width": glyph.width,
                    "height": layer.advanceHeight if hasattr(layer, 'advanceHeight') else 0,
                    "bounds": {{
                        "x": layer.boundingBox.x() if layer.boundingBox else 0,
                        "y": layer.boundingBox.y() if layer.boundingBox else 0,
                        "width": layer.boundingBox.width() if layer.boundingBox else 0,
                        "height": layer.boundingBox.height() if layer.boundingBox else 0,
                    }},
                    "contour_count": len(layer.shapes),
                }}
            }}
except Exception as e:
    result = {{"success": False, "error": str(e)}}

with open(sys.argv[-1], 'w') as f:
    json.dump(result, f)
"""
        return await self.execute_script(script)

    async def find_glyph_by_unicode(self, codepoint: int) -> dict[str, Any]:
        """
        Find glyph by Unicode code point.

        Args:
            codepoint: Unicode code point (integer)

        Returns:
            Dictionary with glyph information or error
        """
        script = f"""
import json
import sys

try:
    from fontlab import flWorkspace

    font = flWorkspace.instance().currentFont()

    if font is None:
        result = {{"success": False, "error": "No font is currently open"}}
    else:
        glyph = None
        # Search for glyph with this unicode
        for g in font.glyphs:
            if g.unicode == {codepoint}:
                glyph = g
                break

        if glyph is None:
            result = {{
                "success": False,
                "error": f"No glyph found with Unicode U+{{hex({codepoint})[2:].upper().zfill(4)}}"
            }}
        else:
            layer = glyph.layers[0] if glyph.layers else None
            result = {{
                "success": True,
                "data": {{
                    "name": glyph.name,
                    "unicode": glyph.unicode,
                    "width": glyph.width,
                    "height": layer.advanceHeight if layer and hasattr(layer, 'advanceHeight') else 0,
                    "has_contours": len(layer.shapes) > 0 if layer else False,
                }}
            }}
except Exception as e:
    result = {{"success": False, "error": str(e)}}

with open(sys.argv[-1], 'w') as f:
    json.dump(result, f)
"""
        return await self.execute_script(script)

    async def search_glyphs(self, pattern: str) -> dict[str, Any]:
        """
        Search for glyphs by name pattern.

        Args:
            pattern: Search pattern (supports * and ? wildcards)

        Returns:
            Dictionary with list of matching glyphs
        """
        script = f"""
import json
import sys
import fnmatch

try:
    from fontlab import flWorkspace

    font = flWorkspace.instance().currentFont()

    if font is None:
        result = {{"success": False, "error": "No font is currently open"}}
    else:
        pattern = {json.dumps(pattern)}
        matches = []

        for glyph in font.glyphs:
            if fnmatch.fnmatch(glyph.name, pattern):
                matches.append({{
                    "name": glyph.name,
                    "unicode": glyph.unicode if glyph.unicode else None,
                    "width": glyph.width,
                }})

        result = {{
            "success": True,
            "data": {{
                "pattern": pattern,
                "matches": matches,
                "count": len(matches)
            }}
        }}
except Exception as e:
    result = {{"success": False, "error": str(e)}}

with open(sys.argv[-1], 'w') as f:
    json.dump(result, f)
"""
        return await self.execute_script(script)

    async def get_glyph_metadata(self, glyph_name: str) -> dict[str, Any]:
        """
        Get metadata for a specific glyph (tags, note, mark).

        Args:
            glyph_name: Name of the glyph

        Returns:
            Dictionary with glyph metadata
        """
        script = f"""
import json
import sys

try:
    from fontlab import flWorkspace

    font = flWorkspace.instance().currentFont()

    if font is None:
        result = {{"success": False, "error": "No font is currently open"}}
    else:
        glyph = font.findGlyph({json.dumps(glyph_name)})

        if glyph is None:
            result = {{"success": False, "error": f"Glyph not found: {{{json.dumps(glyph_name)}}}"}}

        else:
            result = {{
                "success": True,
                "data": {{
                    "name": glyph.name,
                    "note": glyph.note if hasattr(glyph, 'note') and glyph.note else "",
                    "tags": list(glyph.tags) if hasattr(glyph, 'tags') and glyph.tags else [],
                    "mark": glyph.mark if hasattr(glyph, 'mark') else 0,
                }}
            }}
except Exception as e:
    result = {{"success": False, "error": str(e)}}

with open(sys.argv[-1], 'w') as f:
    json.dump(result, f)
"""
        return await self.execute_script(script)

    async def get_kerning(self) -> dict[str, Any]:
        """
        Get all kerning pairs from the current font.

        Returns:
            Dictionary with kerning data
        """
        script = """
import json
import sys

try:
    from fontlab import flWorkspace

    font = flWorkspace.instance().currentFont()

    if font is None:
        result = {"success": False, "error": "No font is currently open"}
    else:
        # Access the fontgate font for kerning data
        fg_font = font.fgFont if hasattr(font, 'fgFont') else None

        if fg_font is None or not hasattr(fg_font, 'kerning'):
            result = {
                "success": True,
                "data": {
                    "pairs": [],
                    "count": 0
                }
            }
        else:
            kerning_obj = fg_font.kerning
            pairs = []

            # Iterate through kerning pairs
            if hasattr(kerning_obj, 'asDict'):
                kern_dict = kerning_obj.asDict()
                for left_key, right_dict in kern_dict.items():
                    for right_key, value in right_dict.items():
                        pairs.append({
                            "left": left_key,
                            "right": right_key,
                            "value": value
                        })

            result = {
                "success": True,
                "data": {
                    "pairs": pairs,
                    "count": len(pairs)
                }
            }
except Exception as e:
    result = {"success": False, "error": str(e)}

with open(sys.argv[-1], 'w') as f:
    json.dump(result, f)
"""
        return await self.execute_script(script)
