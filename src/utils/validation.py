"""
Validation and sanitization utilities for FontLab MCP Server
"""

import json
import re
import sys
from pathlib import Path
from typing import Any


class ValidationError(Exception):
    """Raised when validation fails."""
    pass


class RequestSizeError(ValidationError):
    """Raised when request size exceeds limits."""
    pass


def validate_request_size(data: Any, max_size_bytes: int = 1_000_000) -> None:
    """
    Validate that request data size is within acceptable limits.

    Args:
        data: Request data to validate (dict, list, str, etc.)
        max_size_bytes: Maximum allowed size in bytes (default: 1MB)

    Raises:
        RequestSizeError: If request exceeds size limit
    """
    # Serialize to JSON to get approximate size
    try:
        serialized = json.dumps(data)
        size_bytes = len(serialized.encode('utf-8'))

        if size_bytes > max_size_bytes:
            raise RequestSizeError(
                f"Request too large: {size_bytes} bytes "
                f"(max: {max_size_bytes} bytes)"
            )

    except (TypeError, ValueError) as e:
        # If we can't serialize, estimate size differently
        size_bytes = sys.getsizeof(data)
        if size_bytes > max_size_bytes:
            raise RequestSizeError(
                f"Request too large: ~{size_bytes} bytes "
                f"(max: {max_size_bytes} bytes)"
            )


def sanitize_error_message(error_msg: str) -> str:
    """
    Sanitize error messages to prevent information disclosure.

    Removes or redacts sensitive information like:
    - Absolute file paths
    - User names
    - System details
    - Internal implementation details

    Args:
        error_msg: Raw error message

    Returns:
        Sanitized error message safe for external display
    """
    if not error_msg or not isinstance(error_msg, str):
        return "An error occurred"

    # Convert to lowercase for pattern matching
    msg_lower = error_msg.lower()

    # Patterns that indicate sensitive information disclosure
    sensitive_patterns = [
        "/users/",
        "/home/",
        "c:\\users\\",
        "\\users\\",
        "/private/",
        "/tmp/",
        "/var/",
        "c:\\",
        "traceback",
        "stack trace",
        "line ",
        "file \"",
        ".py\"",
        "errno",
    ]

    # Check if message contains sensitive patterns
    contains_sensitive = any(pattern in msg_lower for pattern in sensitive_patterns)

    if contains_sensitive:
        # Replace with generic error message
        if "permission denied" in msg_lower or "access" in msg_lower:
            return "Permission denied"
        elif "file" in msg_lower or "path" in msg_lower:
            return "File operation failed"
        elif "not found" in msg_lower:
            return "Resource not found"
        elif "invalid" in msg_lower or "error" in msg_lower:
            return "Invalid operation"
        else:
            return "Operation failed"

    # Remove file paths using regex (anything that looks like a path)
    import re
    # Match Unix paths: /path/to/file
    sanitized = re.sub(r'/[\w\-./]+', '[PATH]', error_msg)
    # Match Windows paths: C:\path\to\file
    sanitized = re.sub(r'[A-Za-z]:\\[\w\-\\/.]+', '[PATH]', sanitized)

    # Truncate very long error messages
    max_length = 200
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length] + "..."

    return sanitized


def sanitize_for_python(value: Any) -> str:
    """
    Sanitize a value for safe inclusion in Python script.
    Uses json.dumps to ensure proper escaping.

    Args:
        value: Value to sanitize

    Returns:
        JSON-encoded string safe for Python scripts
    """
    return json.dumps(value)


def validate_glyph_name(name: str) -> str:
    """
    Validate glyph name for safety.

    Args:
        name: Glyph name to validate

    Returns:
        Validated glyph name

    Raises:
        ValidationError: If name is invalid
    """
    if not name or not isinstance(name, str):
        raise ValidationError("Glyph name must be a non-empty string")

    if len(name) > 255:
        raise ValidationError("Glyph name too long (max 255 characters)")

    # Check for dangerous characters (injection attempts)
    dangerous_chars = ['\n', '\r', '\x00']
    if any(char in name for char in dangerous_chars):
        raise ValidationError("Glyph name contains invalid control characters")

    return name


def validate_export_path(path: str, allowed_extensions: list[str] = None) -> str:
    """
    Validate export file path for safety.

    Args:
        path: File path to validate
        allowed_extensions: List of allowed extensions (default: font formats)

    Returns:
        Validated absolute path

    Raises:
        ValidationError: If path is invalid or unsafe
    """
    if not path or not isinstance(path, str):
        raise ValidationError("Export path must be a non-empty string")

    if allowed_extensions is None:
        allowed_extensions = ['.otf', '.ttf', '.woff', '.woff2', '.ufo']

    try:
        path_obj = Path(path).expanduser()

        # Check for path traversal attempts BEFORE resolving
        if '..' in Path(path).parts:
            raise ValidationError("Path traversal detected (..) in path")

        # Resolve to absolute path
        path_obj = path_obj.resolve()

    except (ValueError, RuntimeError) as e:
        raise ValidationError(f"Invalid path: {e}")

    # Check extension
    if path_obj.suffix.lower() not in allowed_extensions:
        raise ValidationError(
            f"Invalid file extension '{path_obj.suffix}'. "
            f"Allowed: {', '.join(allowed_extensions)}"
        )

    # Ensure parent directory exists
    if not path_obj.parent.exists():
        raise ValidationError(f"Parent directory does not exist: {path_obj.parent}")

    # Check if parent directory is writable
    if not path_obj.parent.is_dir():
        raise ValidationError(f"Parent path is not a directory: {path_obj.parent}")

    # SECURITY: Check if the path or any parent is a symlink
    # This prevents symlink attacks where attacker creates symlink to sensitive location
    check_path = path_obj.parent
    while check_path != check_path.parent:  # Stop at root
        if check_path.is_symlink():
            raise ValidationError(
                f"Path contains symbolic link: {check_path}. "
                f"Symlinks are not allowed in export paths for security reasons."
            )
        check_path = check_path.parent

    # Check if the target file itself would be a symlink (if it exists)
    if path_obj.exists() and path_obj.is_symlink():
        raise ValidationError(
            f"Target path is a symbolic link: {path_obj}. "
            f"Cannot export to symlinks for security reasons."
        )

    return str(path_obj)


def validate_numeric_range(
    value: float,
    name: str,
    min_val: float = None,
    max_val: float = None
) -> float:
    """
    Validate a numeric value is within acceptable range.

    Args:
        value: Value to validate
        name: Name of the parameter (for error messages)
        min_val: Minimum allowed value
        max_val: Maximum allowed value

    Returns:
        Validated value

    Raises:
        ValidationError: If value is out of range
    """
    if not isinstance(value, (int, float)):
        raise ValidationError(f"{name} must be a number")

    if min_val is not None and value < min_val:
        raise ValidationError(f"{name} must be >= {min_val}, got {value}")

    if max_val is not None and value > max_val:
        raise ValidationError(f"{name} must be <= {max_val}, got {value}")

    return value


def validate_string_length(value: str, name: str, max_length: int = 1000) -> str:
    """
    Validate string length.

    Args:
        value: String to validate
        name: Parameter name (for error messages)
        max_length: Maximum allowed length

    Returns:
        Validated string

    Raises:
        ValidationError: If string is too long
    """
    if not isinstance(value, str):
        raise ValidationError(f"{name} must be a string")

    if len(value) > max_length:
        raise ValidationError(
            f"{name} too long (max {max_length} characters, got {len(value)})"
        )

    return value


def validate_unicode_codepoint(value: int) -> int:
    """
    Validate Unicode code point.

    Args:
        value: Unicode code point to validate

    Returns:
        Validated code point

    Raises:
        ValidationError: If code point is invalid
    """
    if not isinstance(value, int):
        raise ValidationError("Unicode code point must be an integer")

    # Valid Unicode range
    if value < 0 or value > 0x10FFFF:
        raise ValidationError(
            f"Invalid Unicode code point: {value} "
            f"(must be 0-0x10FFFF)"
        )

    # Check for surrogate range (not valid for standalone code points)
    if 0xD800 <= value <= 0xDFFF:
        raise ValidationError(
            f"Unicode code point {value:#x} is in surrogate range (invalid)"
        )

    return value
