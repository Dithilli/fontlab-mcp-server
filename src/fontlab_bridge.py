"""
FontLab Bridge
Handles communication between MCP server and FontLab's Python environment
"""

import asyncio
import json
import logging
import os
import re
import shutil
import signal
import stat
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)
security_logger = logging.getLogger('security')


def _sanitize_error_for_api(error_msg: str) -> str:
    """
    Sanitize error message for API responses while keeping it useful.

    Removes:
    - Full file paths (replaces with [PATH])
    - Line numbers and tracebacks
    - System-specific details

    Args:
        error_msg: Raw error message

    Returns:
        Sanitized error message
    """
    if not error_msg or not isinstance(error_msg, str):
        return "An error occurred"

    # Log the full error internally
    logger.debug(f"Original error: {error_msg}")

    # Replace absolute paths with [PATH]
    sanitized = re.sub(r'/[\w\-./]+', '[PATH]', error_msg)
    sanitized = re.sub(r'[A-Za-z]:\\[\w\-\\/.]+', '[PATH]', sanitized)

    # Remove line number references
    sanitized = re.sub(r'line \d+', 'line [REDACTED]', sanitized, flags=re.IGNORECASE)
    sanitized = re.sub(r':\d+:', ':[REDACTED]:', sanitized)

    # Remove traceback-specific patterns
    if 'Traceback' in sanitized or 'File "' in sanitized:
        # Keep only the last line (the actual error)
        lines = sanitized.split('\n')
        sanitized = lines[-1] if lines else sanitized

    return sanitized[:300]  # Truncate to reasonable length


class FontLabBridge:
    """Bridge for executing Python scripts in FontLab's environment."""

    # Class-level semaphore for rate limiting concurrent executions
    _execution_semaphore = asyncio.Semaphore(3)  # Max 3 concurrent
    _max_timeout = 10  # Maximum timeout in seconds

    def __init__(self, fontlab_path: Optional[str] = None):
        """
        Initialize the FontLab bridge.

        Args:
            fontlab_path: Optional path to FontLab executable

        Raises:
            RuntimeError: If FontLab path is invalid or insecure
        """
        found_path = fontlab_path or self._find_fontlab()
        self.fontlab_path = self._validate_fontlab_path(found_path)
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

    def _validate_fontlab_path(self, path: Optional[str]) -> str:
        """
        Validate that FontLab executable path is secure.

        Args:
            path: Path to validate

        Returns:
            Validated path

        Raises:
            RuntimeError: If path is invalid or insecure
        """
        if not path:
            security_logger.error("FontLab executable path not provided")
            raise RuntimeError(
                "FontLab executable not found. Please specify fontlab_path "
                "or ensure FontLab is installed in a standard location."
            )

        path_obj = Path(path).resolve()

        # Check if file exists
        if not path_obj.is_file():
            security_logger.error(f"FontLab path does not exist or is not a file: {path}")
            raise RuntimeError(f"FontLab executable not found: {path}")

        # Check if executable
        if not os.access(path_obj, os.X_OK):
            security_logger.error(f"FontLab path is not executable: {path}")
            raise RuntimeError(f"FontLab executable is not executable: {path}")

        # Verify it's actually FontLab (basic check)
        if not path_obj.name.lower().startswith('fontlab'):
            security_logger.warning(f"Suspicious executable name: {path_obj.name}")
            logger.warning(
                f"Warning: Executable name '{path_obj.name}' does not start with 'fontlab'. "
                f"Proceeding but this may not be a valid FontLab installation."
            )

        security_logger.info(f"FontLab path validated: {path_obj}")
        return str(path_obj)

    async def execute_script(
        self, script_content: str, timeout: int = 30
    ) -> dict[str, Any]:
        """
        Execute a Python script in FontLab's environment.

        Args:
            script_content: Python script to execute
            timeout: Execution timeout in seconds (clamped to max_timeout)

        Returns:
            Dictionary with execution result

        Raises:
            RuntimeError: If FontLab is not found or script execution fails
        """
        # Clamp timeout to maximum allowed
        timeout = min(timeout, self._max_timeout)

        # Rate limiting: use semaphore to limit concurrent executions
        async with self._execution_semaphore:
            return await self._execute_script_impl(script_content, timeout)

    async def _execute_script_impl(
        self, script_content: str, timeout: int
    ) -> dict[str, Any]:
        """
        Internal implementation of script execution.

        Args:
            script_content: Python script to execute
            timeout: Execution timeout in seconds

        Returns:
            Dictionary with execution result
        """
        # Create secure temporary directory with restricted permissions
        tmpdir = tempfile.mkdtemp(prefix='fontlab_secure_')
        try:
            # Set directory permissions to 700 (owner only)
            os.chmod(tmpdir, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)

            # Create script and output files in secure directory
            script_path = os.path.join(tmpdir, 'script.py')
            output_path = os.path.join(tmpdir, 'output.json')

            # Write script with restricted permissions
            with open(script_path, 'w') as f:
                f.write(script_content)
            os.chmod(script_path, stat.S_IRUSR | stat.S_IWUSR)  # 600

            # Build command to execute script in FontLab
            # Note: This assumes FontLab can be run with -script flag
            cmd = [
                self.fontlab_path,
                "-script",
                script_path,
                "-output",
                output_path,
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
                security_logger.warning(f"Script execution timeout - possible DoS attempt")

                # Try to kill gracefully first
                process.kill()

                # Wait for process to terminate
                try:
                    await asyncio.wait_for(process.wait(), timeout=5)
                except asyncio.TimeoutError:
                    # Force termination if kill didn't work
                    logger.error("Process did not terminate after kill signal, forcing")
                    try:
                        process.terminate()
                        await asyncio.sleep(0.5)
                        if process.returncode is None:
                            # Nuclear option: SIGKILL
                            os.kill(process.pid, signal.SIGKILL)
                            logger.error(f"Force killed process {process.pid}")
                    except (ProcessLookupError, OSError) as e:
                        logger.error(f"Error force-killing process: {e}")

                raise RuntimeError(f"Script execution timed out after {timeout}s")

            # Read the output
            if Path(output_path).exists():
                with open(output_path, "r") as f:
                    result = json.load(f)
            else:
                # Fallback if no output file was created
                result = {
                    "success": process.returncode == 0,
                    "stdout": stdout.decode("utf-8") if stdout else "",
                    "stderr": stderr.decode("utf-8") if stderr else "",
                }

            # SECURITY: Sanitize error messages in result before returning
            if not result.get("success", False) and "error" in result:
                original_error = result["error"]
                logger.error(f"Script execution error (unsanitized): {original_error}")
                result["error"] = _sanitize_error_for_api(original_error)

            return result

        finally:
            # Clean up secure temporary directory
            try:
                shutil.rmtree(tmpdir, ignore_errors=True)
            except Exception as e:
                logger.error(f"Error cleaning up temp directory {tmpdir}: {e}")

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

    async def get_glyph_contours(self, glyph_name: str) -> dict[str, Any]:
        """
        Get contour information for a specific glyph.

        Args:
            glyph_name: Name of the glyph

        Returns:
            Dictionary with contour data
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
            result = {{"success": False, "error": f"Glyph not found: {json.dumps(glyph_name)}"}}
        else:
            layer = glyph.layers[0] if glyph.layers else None

            if layer is None:
                result = {{
                    "success": True,
                    "data": {{
                        "name": glyph.name,
                        "contours": [],
                        "count": 0
                    }}
                }}
            else:
                contours = []
                for i, shape in enumerate(layer.shapes):
                    if hasattr(shape, 'isContour') and shape.isContour:
                        contour_info = {{
                            "index": i,
                            "closed": shape.closed if hasattr(shape, 'closed') else True,
                            "nodes_count": len(shape.nodes) if hasattr(shape, 'nodes') else 0,
                            "clockwise": shape.clockwise if hasattr(shape, 'clockwise') else None,
                        }}
                        contours.append(contour_info)

                result = {{
                    "success": True,
                    "data": {{
                        "name": glyph.name,
                        "contours": contours,
                        "count": len(contours)
                    }}
                }}
except Exception as e:
    result = {{"success": False, "error": str(e)}}

with open(sys.argv[-1], 'w') as f:
    json.dump(result, f)
"""
        return await self.execute_script(script)

    async def get_glyph_paths(self, glyph_name: str) -> dict[str, Any]:
        """
        Get detailed path data with nodes for a specific glyph.

        Args:
            glyph_name: Name of the glyph

        Returns:
            Dictionary with detailed path data including node coordinates
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
            result = {{"success": False, "error": f"Glyph not found: {json.dumps(glyph_name)}"}}
        else:
            layer = glyph.layers[0] if glyph.layers else None

            if layer is None:
                result = {{
                    "success": True,
                    "data": {{
                        "name": glyph.name,
                        "paths": []
                    }}
                }}
            else:
                paths = []
                for shape in layer.shapes:
                    if hasattr(shape, 'isContour') and shape.isContour:
                        nodes = []
                        if hasattr(shape, 'nodes'):
                            for node in shape.nodes:
                                node_data = {{
                                    "x": node.x if hasattr(node, 'x') else 0,
                                    "y": node.y if hasattr(node, 'y') else 0,
                                    "type": node.type.name if hasattr(node, 'type') else "unknown",
                                    "smooth": node.smooth if hasattr(node, 'smooth') else False,
                                }}
                                nodes.append(node_data)

                        path_data = {{
                            "nodes": nodes,
                            "closed": shape.closed if hasattr(shape, 'closed') else True,
                            "clockwise": shape.clockwise if hasattr(shape, 'clockwise') else None,
                        }}
                        paths.append(path_data)

                result = {{
                    "success": True,
                    "data": {{
                        "name": glyph.name,
                        "paths": paths,
                        "path_count": len(paths)
                    }}
                }}
except Exception as e:
    result = {{"success": False, "error": str(e)}}

with open(sys.argv[-1], 'w') as f:
    json.dump(result, f)
"""
        return await self.execute_script(script)

    async def get_glyph_components(self, glyph_name: str) -> dict[str, Any]:
        """
        Get component references in a glyph.

        Args:
            glyph_name: Name of the glyph

        Returns:
            Dictionary with component data
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
            result = {{"success": False, "error": f"Glyph not found: {json.dumps(glyph_name)}"}}
        else:
            layer = glyph.layers[0] if glyph.layers else None

            if layer is None:
                result = {{
                    "success": True,
                    "data": {{
                        "name": glyph.name,
                        "components": [],
                        "count": 0
                    }}
                }}
            else:
                components = []
                for shape in layer.shapes:
                    if hasattr(shape, 'isComponent') and shape.isComponent:
                        comp_data = {{
                            "base_glyph": shape.name if hasattr(shape, 'name') else "",
                            "transform": {{
                                "xx": shape.transform.m11() if hasattr(shape, 'transform') else 1.0,
                                "xy": shape.transform.m12() if hasattr(shape, 'transform') else 0.0,
                                "yx": shape.transform.m21() if hasattr(shape, 'transform') else 0.0,
                                "yy": shape.transform.m22() if hasattr(shape, 'transform') else 1.0,
                                "dx": shape.transform.dx() if hasattr(shape, 'transform') else 0.0,
                                "dy": shape.transform.dy() if hasattr(shape, 'transform') else 0.0,
                            }}
                        }}
                        components.append(comp_data)

                result = {{
                    "success": True,
                    "data": {{
                        "name": glyph.name,
                        "components": components,
                        "count": len(components)
                    }}
                }}
except Exception as e:
    result = {{"success": False, "error": str(e)}}

with open(sys.argv[-1], 'w') as f:
    json.dump(result, f)
"""
        return await self.execute_script(script)

    async def get_font_features(self) -> dict[str, Any]:
        """
        Get all OpenType feature code from the font.

        Returns:
            Dictionary with feature code
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
        # Access fontgate for features
        fg_font = font.fgFont if hasattr(font, 'fgFont') else None

        if fg_font is None or not hasattr(fg_font, 'features'):
            result = {
                "success": True,
                "data": {
                    "features": "",
                    "has_features": False
                }
            }
        else:
            features_obj = fg_font.features
            features_text = ""

            if hasattr(features_obj, 'asFea'):
                features_text = features_obj.asFea()
            elif hasattr(features_obj, '__str__'):
                features_text = str(features_obj)

            result = {
                "success": True,
                "data": {
                    "features": features_text,
                    "has_features": len(features_text) > 0
                }
            }
except Exception as e:
    result = {"success": False, "error": str(e)}

with open(sys.argv[-1], 'w') as f:
    json.dump(result, f)
"""
        return await self.execute_script(script)

    async def get_glyph_classes(self) -> dict[str, Any]:
        """
        Get all glyph classes defined in the font.

        Returns:
            Dictionary with glyph classes
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
        # Access fontgate for glyph classes
        fg_font = font.fgFont if hasattr(font, 'fgFont') else None

        if fg_font is None or not hasattr(fg_font, 'groups'):
            result = {
                "success": True,
                "data": {
                    "classes": {},
                    "count": 0
                }
            }
        else:
            groups = fg_font.groups
            classes_dict = {}

            if hasattr(groups, 'asDict'):
                classes_dict = groups.asDict()
            elif hasattr(groups, 'items'):
                classes_dict = dict(groups.items())

            result = {
                "success": True,
                "data": {
                    "classes": classes_dict,
                    "count": len(classes_dict)
                }
            }
except Exception as e:
    result = {"success": False, "error": str(e)}

with open(sys.argv[-1], 'w') as f:
    json.dump(result, f)
"""
        return await self.execute_script(script)
