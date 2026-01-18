"""RBAC Permission Checker for role-based access control.

This module implements role-based access control (RBAC) with a permission checker
and decorator for protecting FastAPI routes.

Permission Rules (from design document):
- super_admin: Full platform access across all tenants
- admin: Full tenant access (all operations within their tenant)
- teacher: Access to assigned classes, own data, and student data in assigned classes
- student: Read access to own data only
- parent: Read access to linked children's data only
"""

from collections.abc import Callable
from enum import Enum
from functools import wraps
from typing import Any

from fastapi import HTTPException, status

from app.models.user import UserRole


class Permission(str, Enum):
    """Available permissions in the system."""

    # Tenant management
    TENANT_CREATE = "tenant:create"
    TENANT_READ = "tenant:read"
    TENANT_UPDATE = "tenant:update"
    TENANT_DELETE = "tenant:delete"
    TENANT_MANAGE_ALL = "tenant:manage_all"  # Super admin only

    # User management
    USER_CREATE = "user:create"
    USER_READ = "user:read"
    USER_UPDATE = "user:update"
    USER_DELETE = "user:delete"
    USER_READ_OWN = "user:read_own"
    USER_UPDATE_OWN = "user:update_own"

    # Student management
    STUDENT_CREATE = "student:create"
    STUDENT_READ = "student:read"
    STUDENT_UPDATE = "student:update"
    STUDENT_DELETE = "student:delete"
    STUDENT_READ_OWN = "student:read_own"
    STUDENT_READ_CHILDREN = "student:read_children"  # Parent access

    # Teacher management
    TEACHER_CREATE = "teacher:create"
    TEACHER_READ = "teacher:read"
    TEACHER_UPDATE = "teacher:update"
    TEACHER_DELETE = "teacher:delete"
    TEACHER_READ_OWN = "teacher:read_own"
    TEACHER_UPDATE_OWN = "teacher:update_own"

    # Class management
    CLASS_CREATE = "class:create"
    CLASS_READ = "class:read"
    CLASS_UPDATE = "class:update"
    CLASS_DELETE = "class:delete"
    CLASS_READ_ASSIGNED = "class:read_assigned"  # Teacher access

    # Section management
    SECTION_CREATE = "section:create"
    SECTION_READ = "section:read"
    SECTION_UPDATE = "section:update"
    SECTION_DELETE = "section:delete"

    # Subject management
    SUBJECT_CREATE = "subject:create"
    SUBJECT_READ = "subject:read"
    SUBJECT_UPDATE = "subject:update"
    SUBJECT_DELETE = "subject:delete"

    # Attendance management
    ATTENDANCE_CREATE = "attendance:create"
    ATTENDANCE_READ = "attendance:read"
    ATTENDANCE_UPDATE = "attendance:update"
    ATTENDANCE_DELETE = "attendance:delete"
    ATTENDANCE_READ_OWN = "attendance:read_own"
    ATTENDANCE_READ_CHILDREN = "attendance:read_children"
    ATTENDANCE_MARK = "attendance:mark"  # Bulk marking

    # Grade management
    GRADE_CREATE = "grade:create"
    GRADE_READ = "grade:read"
    GRADE_UPDATE = "grade:update"
    GRADE_DELETE = "grade:delete"
    GRADE_READ_OWN = "grade:read_own"
    GRADE_READ_CHILDREN = "grade:read_children"

    # Exam management
    EXAM_CREATE = "exam:create"
    EXAM_READ = "exam:read"
    EXAM_UPDATE = "exam:update"
    EXAM_DELETE = "exam:delete"

    # Fee management
    FEE_CREATE = "fee:create"
    FEE_READ = "fee:read"
    FEE_UPDATE = "fee:update"
    FEE_DELETE = "fee:delete"
    FEE_READ_OWN = "fee:read_own"
    FEE_READ_CHILDREN = "fee:read_children"
    FEE_RECORD_PAYMENT = "fee:record_payment"

    # Timetable management
    TIMETABLE_CREATE = "timetable:create"
    TIMETABLE_READ = "timetable:read"
    TIMETABLE_UPDATE = "timetable:update"
    TIMETABLE_DELETE = "timetable:delete"

    # Announcement management
    ANNOUNCEMENT_CREATE = "announcement:create"
    ANNOUNCEMENT_READ = "announcement:read"
    ANNOUNCEMENT_UPDATE = "announcement:update"
    ANNOUNCEMENT_DELETE = "announcement:delete"

    # Leave request management
    LEAVE_CREATE = "leave:create"
    LEAVE_READ = "leave:read"
    LEAVE_UPDATE = "leave:update"
    LEAVE_APPROVE = "leave:approve"
    LEAVE_READ_OWN = "leave:read_own"

    # Report access
    REPORT_READ = "report:read"
    REPORT_EXPORT = "report:export"

    # Audit log access
    AUDIT_READ = "audit:read"


class PermissionChecker:
    """RBAC permission checker with role-permission mapping.

    This class defines which roles have access to which permissions
    and provides methods to check if a user has a specific permission.
    """

    # Role to permissions mapping
    # Each role has a set of permissions they are allowed to perform
    PERMISSIONS: dict[UserRole, set[Permission]] = {
        UserRole.SUPER_ADMIN: {
            # Super admin has all permissions including cross-tenant access
            Permission.TENANT_CREATE,
            Permission.TENANT_READ,
            Permission.TENANT_UPDATE,
            Permission.TENANT_DELETE,
            Permission.TENANT_MANAGE_ALL,
            Permission.USER_CREATE,
            Permission.USER_READ,
            Permission.USER_UPDATE,
            Permission.USER_DELETE,
            Permission.USER_READ_OWN,
            Permission.USER_UPDATE_OWN,
            Permission.STUDENT_CREATE,
            Permission.STUDENT_READ,
            Permission.STUDENT_UPDATE,
            Permission.STUDENT_DELETE,
            Permission.STUDENT_READ_OWN,
            Permission.TEACHER_CREATE,
            Permission.TEACHER_READ,
            Permission.TEACHER_UPDATE,
            Permission.TEACHER_DELETE,
            Permission.TEACHER_READ_OWN,
            Permission.TEACHER_UPDATE_OWN,
            Permission.CLASS_CREATE,
            Permission.CLASS_READ,
            Permission.CLASS_UPDATE,
            Permission.CLASS_DELETE,
            Permission.SECTION_CREATE,
            Permission.SECTION_READ,
            Permission.SECTION_UPDATE,
            Permission.SECTION_DELETE,
            Permission.SUBJECT_CREATE,
            Permission.SUBJECT_READ,
            Permission.SUBJECT_UPDATE,
            Permission.SUBJECT_DELETE,
            Permission.ATTENDANCE_CREATE,
            Permission.ATTENDANCE_READ,
            Permission.ATTENDANCE_UPDATE,
            Permission.ATTENDANCE_DELETE,
            Permission.ATTENDANCE_MARK,
            Permission.GRADE_CREATE,
            Permission.GRADE_READ,
            Permission.GRADE_UPDATE,
            Permission.GRADE_DELETE,
            Permission.EXAM_CREATE,
            Permission.EXAM_READ,
            Permission.EXAM_UPDATE,
            Permission.EXAM_DELETE,
            Permission.FEE_CREATE,
            Permission.FEE_READ,
            Permission.FEE_UPDATE,
            Permission.FEE_DELETE,
            Permission.FEE_RECORD_PAYMENT,
            Permission.TIMETABLE_CREATE,
            Permission.TIMETABLE_READ,
            Permission.TIMETABLE_UPDATE,
            Permission.TIMETABLE_DELETE,
            Permission.ANNOUNCEMENT_CREATE,
            Permission.ANNOUNCEMENT_READ,
            Permission.ANNOUNCEMENT_UPDATE,
            Permission.ANNOUNCEMENT_DELETE,
            Permission.LEAVE_CREATE,
            Permission.LEAVE_READ,
            Permission.LEAVE_UPDATE,
            Permission.LEAVE_APPROVE,
            Permission.REPORT_READ,
            Permission.REPORT_EXPORT,
            Permission.AUDIT_READ,
        },
        UserRole.ADMIN: {
            # Admin has full tenant access (all operations within their tenant)
            Permission.TENANT_READ,
            Permission.TENANT_UPDATE,
            Permission.USER_CREATE,
            Permission.USER_READ,
            Permission.USER_UPDATE,
            Permission.USER_DELETE,
            Permission.USER_READ_OWN,
            Permission.USER_UPDATE_OWN,
            Permission.STUDENT_CREATE,
            Permission.STUDENT_READ,
            Permission.STUDENT_UPDATE,
            Permission.STUDENT_DELETE,
            Permission.TEACHER_CREATE,
            Permission.TEACHER_READ,
            Permission.TEACHER_UPDATE,
            Permission.TEACHER_DELETE,
            Permission.CLASS_CREATE,
            Permission.CLASS_READ,
            Permission.CLASS_UPDATE,
            Permission.CLASS_DELETE,
            Permission.SECTION_CREATE,
            Permission.SECTION_READ,
            Permission.SECTION_UPDATE,
            Permission.SECTION_DELETE,
            Permission.SUBJECT_CREATE,
            Permission.SUBJECT_READ,
            Permission.SUBJECT_UPDATE,
            Permission.SUBJECT_DELETE,
            Permission.ATTENDANCE_CREATE,
            Permission.ATTENDANCE_READ,
            Permission.ATTENDANCE_UPDATE,
            Permission.ATTENDANCE_DELETE,
            Permission.ATTENDANCE_MARK,
            Permission.GRADE_CREATE,
            Permission.GRADE_READ,
            Permission.GRADE_UPDATE,
            Permission.GRADE_DELETE,
            Permission.EXAM_CREATE,
            Permission.EXAM_READ,
            Permission.EXAM_UPDATE,
            Permission.EXAM_DELETE,
            Permission.FEE_CREATE,
            Permission.FEE_READ,
            Permission.FEE_UPDATE,
            Permission.FEE_DELETE,
            Permission.FEE_RECORD_PAYMENT,
            Permission.TIMETABLE_CREATE,
            Permission.TIMETABLE_READ,
            Permission.TIMETABLE_UPDATE,
            Permission.TIMETABLE_DELETE,
            Permission.ANNOUNCEMENT_CREATE,
            Permission.ANNOUNCEMENT_READ,
            Permission.ANNOUNCEMENT_UPDATE,
            Permission.ANNOUNCEMENT_DELETE,
            Permission.LEAVE_CREATE,
            Permission.LEAVE_READ,
            Permission.LEAVE_UPDATE,
            Permission.LEAVE_APPROVE,
            Permission.LEAVE_READ_OWN,
            Permission.REPORT_READ,
            Permission.REPORT_EXPORT,
            Permission.AUDIT_READ,
        },
        UserRole.TEACHER: {
            # Teacher has access to assigned classes, own data, and student data
            Permission.USER_READ_OWN,
            Permission.USER_UPDATE_OWN,
            Permission.STUDENT_READ,  # Can read students in assigned classes
            Permission.TEACHER_READ_OWN,
            Permission.TEACHER_UPDATE_OWN,
            Permission.CLASS_READ,
            Permission.CLASS_READ_ASSIGNED,
            Permission.SECTION_READ,
            Permission.SUBJECT_READ,
            Permission.ATTENDANCE_CREATE,
            Permission.ATTENDANCE_READ,
            Permission.ATTENDANCE_UPDATE,
            Permission.ATTENDANCE_MARK,
            Permission.GRADE_CREATE,
            Permission.GRADE_READ,
            Permission.GRADE_UPDATE,
            Permission.EXAM_READ,
            Permission.TIMETABLE_READ,
            Permission.ANNOUNCEMENT_READ,
            Permission.LEAVE_CREATE,
            Permission.LEAVE_READ_OWN,
            Permission.REPORT_READ,
        },
        UserRole.STUDENT: {
            # Student has read access to own data only
            Permission.USER_READ_OWN,
            Permission.USER_UPDATE_OWN,
            Permission.STUDENT_READ_OWN,
            Permission.CLASS_READ,
            Permission.SECTION_READ,
            Permission.SUBJECT_READ,
            Permission.ATTENDANCE_READ_OWN,
            Permission.GRADE_READ_OWN,
            Permission.EXAM_READ,
            Permission.FEE_READ_OWN,
            Permission.TIMETABLE_READ,
            Permission.ANNOUNCEMENT_READ,
            Permission.LEAVE_CREATE,
            Permission.LEAVE_READ_OWN,
        },
        UserRole.PARENT: {
            # Parent has read access to linked children's data only
            Permission.USER_READ_OWN,
            Permission.USER_UPDATE_OWN,
            Permission.STUDENT_READ_CHILDREN,
            Permission.CLASS_READ,
            Permission.SECTION_READ,
            Permission.SUBJECT_READ,
            Permission.ATTENDANCE_READ_CHILDREN,
            Permission.GRADE_READ_CHILDREN,
            Permission.EXAM_READ,
            Permission.FEE_READ_CHILDREN,
            Permission.TIMETABLE_READ,
            Permission.ANNOUNCEMENT_READ,
        },
    }

    def has_permission(self, user_role: UserRole, permission: Permission | str) -> bool:
        """Check if a role has a specific permission.

        Args:
            user_role: The user's role.
            permission: The permission to check (can be Permission enum or string).

        Returns:
            True if the role has the permission, False otherwise.
        """
        # Convert string to Permission enum if needed
        if isinstance(permission, str):
            try:
                permission = Permission(permission)
            except ValueError:
                return False

        role_permissions = self.PERMISSIONS.get(user_role, set())
        return permission in role_permissions

    def get_permissions(self, user_role: UserRole) -> set[Permission]:
        """Get all permissions for a role.

        Args:
            user_role: The user's role.

        Returns:
            Set of permissions for the role.
        """
        return self.PERMISSIONS.get(user_role, set()).copy()

    def check_permission(self, user_role: UserRole, permission: Permission | str) -> None:
        """Check permission and raise HTTPException if denied.

        Args:
            user_role: The user's role.
            permission: The permission to check.

        Raises:
            HTTPException: 403 Forbidden if permission is denied.
        """
        if not self.has_permission(user_role, permission):
            permission_str = permission.value if isinstance(permission, Permission) else permission
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {permission_str}",
            )


# Global permission checker instance
permission_checker = PermissionChecker()



def require_permission(permission: Permission | str) -> Callable:
    """Decorator factory for protecting routes with permission checks.

    This decorator checks if the current user has the required permission
    before allowing access to the route. It must be used with FastAPI's
    dependency injection system.

    Usage:
        @router.get("/students")
        @require_permission(Permission.STUDENT_READ)
        async def list_students(current_user: CurrentUserDep):
            ...

    Args:
        permission: The permission required to access the route.

    Returns:
        Decorator function that wraps the route handler.
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Look for current_user in kwargs (injected by FastAPI dependency)
            current_user = kwargs.get("current_user")

            if current_user is None:
                # Try to find it in args by checking for CurrentUser type
                from app.api.deps import CurrentUser

                for arg in args:
                    if isinstance(arg, CurrentUser):
                        current_user = arg
                        break

            if current_user is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required",
                )

            # Check permission
            permission_checker.check_permission(current_user.role, permission)

            # Call the original function
            return await func(*args, **kwargs)

        return wrapper

    return decorator


def require_any_permission(*permissions: Permission | str) -> Callable:
    """Decorator factory for routes requiring any one of multiple permissions.

    This decorator checks if the current user has at least one of the
    required permissions before allowing access to the route.

    Usage:
        @router.get("/data")
        @require_any_permission(Permission.STUDENT_READ, Permission.STUDENT_READ_OWN)
        async def get_data(current_user: CurrentUserDep):
            ...

    Args:
        *permissions: The permissions, any of which grants access.

    Returns:
        Decorator function that wraps the route handler.
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Look for current_user in kwargs
            current_user = kwargs.get("current_user")

            if current_user is None:
                from app.api.deps import CurrentUser

                for arg in args:
                    if isinstance(arg, CurrentUser):
                        current_user = arg
                        break

            if current_user is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required",
                )

            # Check if user has any of the required permissions
            has_any = any(
                permission_checker.has_permission(current_user.role, perm)
                for perm in permissions
            )

            if not has_any:
                perm_strs = [
                    p.value if isinstance(p, Permission) else p for p in permissions
                ]
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission denied: requires one of {perm_strs}",
                )

            return await func(*args, **kwargs)

        return wrapper

    return decorator


def require_all_permissions(*permissions: Permission | str) -> Callable:
    """Decorator factory for routes requiring all specified permissions.

    This decorator checks if the current user has all of the required
    permissions before allowing access to the route.

    Usage:
        @router.delete("/students/{id}")
        @require_all_permissions(Permission.STUDENT_READ, Permission.STUDENT_DELETE)
        async def delete_student(current_user: CurrentUserDep):
            ...

    Args:
        *permissions: All permissions required for access.

    Returns:
        Decorator function that wraps the route handler.
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Look for current_user in kwargs
            current_user = kwargs.get("current_user")

            if current_user is None:
                from app.api.deps import CurrentUser

                for arg in args:
                    if isinstance(arg, CurrentUser):
                        current_user = arg
                        break

            if current_user is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required",
                )

            # Check if user has all required permissions
            missing = []
            for perm in permissions:
                if not permission_checker.has_permission(current_user.role, perm):
                    perm_str = perm.value if isinstance(perm, Permission) else perm
                    missing.append(perm_str)

            if missing:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission denied: missing {missing}",
                )

            return await func(*args, **kwargs)

        return wrapper

    return decorator


class PermissionDependency:
    """FastAPI dependency class for permission checking.

    This provides an alternative way to check permissions using FastAPI's
    dependency injection system directly.

    Usage:
        @router.get("/students")
        async def list_students(
            current_user: CurrentUserDep,
            _: None = Depends(PermissionDependency(Permission.STUDENT_READ))
        ):
            ...
    """

    def __init__(self, permission: Permission | str):
        """Initialize with required permission.

        Args:
            permission: The permission required for access.
        """
        self.permission = permission

    async def __call__(self, current_user: Any = None) -> None:
        """Check permission when dependency is resolved.

        Args:
            current_user: The current user (injected by FastAPI).

        Raises:
            HTTPException: If permission is denied.
        """
        if current_user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
            )

        permission_checker.check_permission(current_user.role, self.permission)


def require_super_admin() -> Callable:
    """Decorator for protecting routes that require super admin access.

    This decorator ensures that only users with the SUPER_ADMIN role
    can access the decorated route. It's used for platform-wide
    administrative operations.

    Usage:
        @router.get("/tenants")
        @require_super_admin()
        async def list_all_tenants(current_user: CurrentUserDep):
            ...

    Returns:
        Decorator function that wraps the route handler.
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Look for current_user in kwargs (injected by FastAPI dependency)
            current_user = kwargs.get("current_user")

            if current_user is None:
                # Try to find it in args by checking for CurrentUser type
                from app.api.deps import CurrentUser

                for arg in args:
                    if isinstance(arg, CurrentUser):
                        current_user = arg
                        break

            if current_user is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required",
                )

            # Check for super admin role
            if current_user.role != UserRole.SUPER_ADMIN:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Super admin access required",
                )

            # Call the original function
            return await func(*args, **kwargs)

        return wrapper

    return decorator


def is_super_admin(user_role: UserRole) -> bool:
    """Check if a role is super admin.

    Args:
        user_role: The user's role to check.

    Returns:
        True if the role is SUPER_ADMIN, False otherwise.
    """
    return user_role == UserRole.SUPER_ADMIN
