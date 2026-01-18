"""Input sanitization utilities for XSS prevention.

This module provides functions to sanitize user input and prevent
Cross-Site Scripting (XSS) attacks by escaping or removing potentially
dangerous content.
"""

import html
import re
from typing import Any


# Patterns for detecting potentially dangerous content
SCRIPT_PATTERN = re.compile(r"<script[^>]*>.*?</script>", re.IGNORECASE | re.DOTALL)
EVENT_HANDLER_PATTERN = re.compile(r"\s*on\w+\s*=", re.IGNORECASE)
JAVASCRIPT_URL_PATTERN = re.compile(r"javascript\s*:", re.IGNORECASE)
DATA_URL_PATTERN = re.compile(r"data\s*:", re.IGNORECASE)
VBSCRIPT_URL_PATTERN = re.compile(r"vbscript\s*:", re.IGNORECASE)

# HTML tags that are considered dangerous
DANGEROUS_TAGS = frozenset([
    "script", "iframe", "object", "embed", "form", "input",
    "button", "textarea", "select", "style", "link", "meta",
    "base", "applet", "frame", "frameset", "layer", "ilayer",
])


def sanitize_string(value: str, escape_html: bool = True) -> str:
    """Sanitize a string value to prevent XSS attacks.

    Args:
        value: The string to sanitize.
        escape_html: Whether to escape HTML entities.

    Returns:
        The sanitized string.
    """
    if not value:
        return value

    # Remove null bytes
    sanitized = value.replace("\x00", "")

    # Remove script tags and their content
    sanitized = SCRIPT_PATTERN.sub("", sanitized)

    # Remove event handlers (onclick, onload, etc.)
    sanitized = EVENT_HANDLER_PATTERN.sub(" ", sanitized)

    # Remove javascript: URLs
    sanitized = JAVASCRIPT_URL_PATTERN.sub("", sanitized)

    # Remove vbscript: URLs
    sanitized = VBSCRIPT_URL_PATTERN.sub("", sanitized)

    # Escape HTML entities if requested
    if escape_html:
        sanitized = html.escape(sanitized, quote=True)

    return sanitized


def sanitize_html(value: str) -> str:
    """Sanitize HTML content while preserving safe tags.

    This is a more permissive sanitization that allows some HTML
    but removes dangerous elements.

    Args:
        value: The HTML string to sanitize.

    Returns:
        The sanitized HTML string.
    """
    if not value:
        return value

    # Remove null bytes
    sanitized = value.replace("\x00", "")

    # Remove script tags and their content
    sanitized = SCRIPT_PATTERN.sub("", sanitized)

    # Remove event handlers
    sanitized = EVENT_HANDLER_PATTERN.sub(" ", sanitized)

    # Remove javascript: URLs
    sanitized = JAVASCRIPT_URL_PATTERN.sub("", sanitized)

    # Remove vbscript: URLs
    sanitized = VBSCRIPT_URL_PATTERN.sub("", sanitized)

    # Remove dangerous tags (but keep content)
    for tag in DANGEROUS_TAGS:
        # Remove opening tags
        sanitized = re.sub(
            rf"<{tag}[^>]*>",
            "",
            sanitized,
            flags=re.IGNORECASE,
        )
        # Remove closing tags
        sanitized = re.sub(
            rf"</{tag}>",
            "",
            sanitized,
            flags=re.IGNORECASE,
        )

    return sanitized


def sanitize_dict(data: dict[str, Any], escape_html: bool = True) -> dict[str, Any]:
    """Recursively sanitize all string values in a dictionary.

    Args:
        data: The dictionary to sanitize.
        escape_html: Whether to escape HTML entities.

    Returns:
        A new dictionary with sanitized values.
    """
    sanitized = {}
    for key, value in data.items():
        sanitized[key] = sanitize_value(value, escape_html)
    return sanitized


def sanitize_list(data: list[Any], escape_html: bool = True) -> list[Any]:
    """Recursively sanitize all string values in a list.

    Args:
        data: The list to sanitize.
        escape_html: Whether to escape HTML entities.

    Returns:
        A new list with sanitized values.
    """
    return [sanitize_value(item, escape_html) for item in data]


def sanitize_value(value: Any, escape_html: bool = True) -> Any:
    """Sanitize a value of any type.

    Args:
        value: The value to sanitize.
        escape_html: Whether to escape HTML entities.

    Returns:
        The sanitized value.
    """
    if isinstance(value, str):
        return sanitize_string(value, escape_html)
    elif isinstance(value, dict):
        return sanitize_dict(value, escape_html)
    elif isinstance(value, list):
        return sanitize_list(value, escape_html)
    else:
        # Non-string primitives (int, float, bool, None) are safe
        return value


def is_safe_url(url: str) -> bool:
    """Check if a URL is safe (not a javascript: or data: URL).

    Args:
        url: The URL to check.

    Returns:
        True if the URL is safe, False otherwise.
    """
    if not url:
        return True

    url_lower = url.strip().lower()

    # Check for dangerous URL schemes
    if JAVASCRIPT_URL_PATTERN.match(url_lower):
        return False
    if VBSCRIPT_URL_PATTERN.match(url_lower):
        return False
    if DATA_URL_PATTERN.match(url_lower):
        return False

    return True


def strip_tags(value: str) -> str:
    """Remove all HTML tags from a string.

    Args:
        value: The string to strip tags from.

    Returns:
        The string with all HTML tags removed.
    """
    if not value:
        return value

    # Remove all HTML tags
    return re.sub(r"<[^>]+>", "", value)


def escape_for_json(value: str) -> str:
    """Escape a string for safe inclusion in JSON.

    Args:
        value: The string to escape.

    Returns:
        The escaped string.
    """
    if not value:
        return value

    # Escape special characters
    escaped = value.replace("\\", "\\\\")
    escaped = escaped.replace('"', '\\"')
    escaped = escaped.replace("\n", "\\n")
    escaped = escaped.replace("\r", "\\r")
    escaped = escaped.replace("\t", "\\t")

    return escaped
