# Utils package - Utility functions

from app.utils.permissions import (
    Permission,
    PermissionChecker,
    PermissionDependency,
    permission_checker,
    require_all_permissions,
    require_any_permission,
    require_permission,
)
from app.utils.sanitization import (
    escape_for_json,
    is_safe_url,
    sanitize_dict,
    sanitize_html,
    sanitize_list,
    sanitize_string,
    sanitize_value,
    strip_tags,
)

__all__ = [
    # Permissions
    "Permission",
    "PermissionChecker",
    "PermissionDependency",
    "permission_checker",
    "require_permission",
    "require_any_permission",
    "require_all_permissions",
    # Sanitization
    "sanitize_string",
    "sanitize_html",
    "sanitize_dict",
    "sanitize_list",
    "sanitize_value",
    "is_safe_url",
    "strip_tags",
    "escape_for_json",
]
