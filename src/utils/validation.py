"""
Validation and sanitization utilities for FontLab MCP Server
"""

import json
import re
from pathlib import Path
from typing import Any


class ValidationError(Exception):
    """Raised when validation fails."""
    pass


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
        path_obj = Path(path).expanduser().resolve()
    except (ValueError, RuntimeError) as e:
        raise ValidationError(f"Invalid path: {e}")

    # Check extension
    if path_obj.suffix.lower() not in allowed_extensions:
        raise ValidationError(
            f"Invalid file extension '{path_obj.suffix}'. "
            f"Allowed: {', '.join(allowed_extensions)}"
        )

    # Ensure parent directory exists or can be created
    if not path_obj.parent.exists():
        raise ValidationError(f"Parent directory does not exist: {path_obj.parent}")

    # Check for suspicious patterns (path traversal attempts)
    path_str = str(path_obj)
    if '..' in Path(path).parts:
        raise ValidationError("Path traversal detected (..) in path")

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
