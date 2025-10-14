# Security Fixes TODO

## Completed ✅

- [x] Fix command injection in `create_glyph`
- [x] Fix command injection in `modify_glyph_width`
- [x] Fix command injection in `transform_glyph`
- [x] Fix command injection in `update_font_info`
- [x] Fix command injection in `export_font`
- [x] Fix command injection in `delete_glyph`
- [x] Fix command injection in `fontlab_bridge.get_glyph()`
- [x] Fix command injection in `fontlab_bridge.get_glyph_metadata()`
- [x] Fix path traversal in `export_font`
- [x] Add input validation utilities (`src/utils/validation.py`)
- [x] Add logging throughout
- [x] Improve error handling with timeout cleanup

## New Tools (Added by Other Agent) - ALL FIXED ✅

The other agent added these tools and **properly applied all security fixes** in parallel:

### tools.py - New Tool Functions (All Secured)

1. **`_rename_glyph()`** ✅
   - [x] Validates `old_name` and `new_name` with `validate_glyph_name()`
   - [x] Sanitizes both with `sanitize_for_python()`
   - [x] Includes error handling and logging

2. **`_duplicate_glyph()`** ✅
   - [x] Validates both names
   - [x] Properly sanitized

3. **`_set_glyph_sidebearings()`** ✅
   - [x] Validates name and sidebearing values (-10000 to 10000)
   - [x] Properly sanitized

4. **`_set_glyph_note()`** ✅
   - [x] Validates name and note length (max 10000 chars)
   - [x] Properly sanitized

5. **`_set_glyph_tags()`** ✅
   - [x] Validates name and each tag (max 255 chars)
   - [x] Validates tag array is a list
   - [x] Properly sanitized

6. **`_set_glyph_mark()`** ✅
   - [x] Validates name and mark range (0-255)
   - [x] Properly sanitized

7. **`_set_kerning_pair()`** ✅
   - [x] Validates left/right glyph names
   - [x] Validates kerning value (-10000 to 10000)
   - [x] Properly sanitized with logging

8. **`_remove_kerning_pair()`** ✅
   - [x] Validates left/right glyph names
   - [x] Properly sanitized with logging

All new tools follow the established security pattern and are safe from command injection!

## Pattern to Follow

All new tool functions should follow this pattern:

```python
async def _example_tool(args: dict[str, Any], bridge: FontLabBridge) -> dict[str, Any]:
    """Tool description."""
    try:
        # 1. Validate ALL inputs
        name = validate_glyph_name(args["name"])
        value = validate_numeric_range(args["value"], "value", min_val=0, max_val=1000)

        # 2. Sanitize for safe script inclusion
        name_safe = sanitize_for_python(name)
        value_safe = sanitize_for_python(value)

        # 3. Use sanitized values in f-strings
        script = f"""
import json
import sys

try:
    from fontlab import flWorkspace

    font = flWorkspace.instance().currentFont()

    if font is None:
        result = {{"success": False, "error": "No font is currently open"}}
    else:
        glyph = font.findGlyph({name_safe})  # ✅ SAFE
        # NOT: glyph = font.findGlyph("{name}")  # ❌ VULNERABLE

        # ... rest of logic

except Exception as e:
    result = {{"success": False, "error": str(e)}}

with open(sys.argv[-1], 'w') as f:
    json.dump(result, f)
"""
        logger.info(f"Executing tool: example_tool for {name}")
        return await bridge.execute_script(script)

    except ValidationError as e:
        logger.error(f"Validation error in example_tool: {e}")
        return {"success": False, "error": f"Validation error: {e}"}
```

## Testing Checklist

For each fixed tool, test with:
- [ ] Normal input (e.g., `"A"`)
- [ ] Special characters (e.g., `"A'\"B"`)
- [ ] Injection attempt (e.g., `"A\"; import os; os.system('whoami'); \""`)
- [ ] Path traversal attempt (for paths: `"../../etc/passwd"`)
- [ ] Oversized input (10000+ chars for strings)
- [ ] Out-of-range numbers (negative where not allowed, > max)

## Priority

**HIGH PRIORITY** - These tools can modify font data:
1. `_rename_glyph()` - Can corrupt font if injection succeeds
2. `_duplicate_glyph()` - Can fill font with malicious glyphs
3. `_set_kerning_pair()` - Can corrupt kerning tables
4. `_remove_kerning_pair()` - Less critical but still needs fixing

**MEDIUM PRIORITY** - Metadata only:
5. `_set_glyph_note()` - Just metadata but could inject
6. `_set_glyph_tags()` - Just metadata
7. `_set_glyph_mark()` - Just visual marker
8. `_set_glyph_sidebearings()` - Affects layout but not critical

## Second Round Security Fixes (Code Review 2) - ALL COMPLETED ✅

### Critical Vulnerabilities Fixed

1. **Command injection via fontlab_path** ✅
   - Added `_validate_fontlab_path()` method in `fontlab_bridge.py:63-104`
   - Validates executable exists, is executable, and has proper name
   - Security logging for suspicious paths

2. **Path traversal in URI parsing** ✅
   - Rewrote URI parsing in `resources.py` to use `urllib.parse`
   - Added `_parse_uri_path()` helper function with validation
   - Checks for `..` and other path traversal patterns before and after URL decoding

3. **TOCTOU race condition** ✅
   - Created secure temporary directory with 700 permissions
   - Files created with 600 permissions (owner-only access)
   - Proper cleanup with `shutil.rmtree()` in finally block

4. **Rate limiting (DoS prevention)** ✅
   - Added class-level `asyncio.Semaphore(3)` in `fontlab_bridge.py:26`
   - Limits concurrent script executions to 3
   - Clamped timeout to max 10 seconds

5. **Request size validation** ✅
   - Added `validate_request_size()` in `validation.py:22-51`
   - Added to `handle_call_tool()` in `tools.py:450-456`
   - 1MB limit on all tool requests

6. **Error message sanitization** ✅
   - Added `sanitize_error_message()` in `validation.py:54-122`
   - Added `_sanitize_error_for_api()` in `fontlab_bridge.py:23-58`
   - Sanitizes all errors returned from scripts in `execute_script()`
   - Removes paths, line numbers, tracebacks while keeping useful info
   - Full errors logged internally for debugging

7. **Security logging** ✅
   - Added security_logger throughout `fontlab_bridge.py`
   - Logs validation failures, suspicious paths, timeouts, etc.

8. **Subprocess cleanup** ✅
   - Fixed zombie process issue in `fontlab_bridge.py:216-238`
   - Escalating kill sequence: `kill() → terminate() → SIGKILL`
   - Proper error handling for process cleanup

9. **Symlink detection in export paths** ✅
   - Enhanced `validate_export_path()` in `validation.py:87-153`
   - Checks all parent directories for symlinks
   - Prevents symlink attacks to sensitive locations

## Additional Security Improvements (Future)

- [ ] Implement transaction/rollback support
- [ ] Add resource usage limits (max glyphs)
- [ ] Add configuration for allowed export directories
- [ ] Implement health checks for FontLab process
- [ ] Add metrics/monitoring
- [ ] Write unit tests for validation functions
- [ ] Write integration tests for security scenarios
