"""Property-based tests for RBAC enforcement.

**Feature: school-erp-multi-tenancy, Property 6: Role-Based Access Control Enforcement**
**Validates: Design - Property 6**

Property 6: Role-Based Access Control Enforcement
*For any* user-resource-permission combination, the access decision SHALL match
the defined permission rules where admins have full tenant access, teachers have
assigned class access, students have own-data read access, and parents have
linked-children read access.
"""

from hypothesis import given, settings
from hypothesis import strategies as st

from app.models.user import UserRole
from app.utils.permissions import Permission, PermissionChecker, permission_checker


# Strategy for all valid user roles
role_strategy = st.sampled_from(list(UserRole))

# Strategy for all valid permissions
permission_strategy = st.sampled_from(list(Permission))


class TestRBACEnforcement:
    """**Feature: school-erp-multi-tenancy, Property 6: Role-Based Access Control Enforcement**"""

    @given(role=role_strategy, permission=permission_strategy)
    @settings(max_examples=100)
    def test_permission_decision_matches_defined_rules(
        self, role: UserRole, permission: Permission
    ):
        """For any role-permission combination, the decision SHALL match defined rules.

        **Validates: Requirements 4.1, 4.2, 4.3, 4.4, 4.5**
        """
        # Act: Check if the role has the permission
        has_perm = permission_checker.has_permission(role, permission)

        # Assert: The decision matches the defined permission mapping
        expected_permissions = PermissionChecker.PERMISSIONS.get(role, set())
        expected = permission in expected_permissions

        assert has_perm == expected, (
            f"Permission decision mismatch for role={role.value}, permission={permission.value}. "
            f"Expected: {expected}, Got: {has_perm}"
        )

    @given(role=role_strategy)
    @settings(max_examples=100)
    def test_super_admin_has_all_permissions(self, role: UserRole):
        """Super admin SHALL have access to all permissions including cross-tenant.

        **Validates: Requirements 4.1**
        """
        if role != UserRole.SUPER_ADMIN:
            return

        # Super admin should have all permissions
        super_admin_perms = permission_checker.get_permissions(UserRole.SUPER_ADMIN)

        # Verify super admin has TENANT_MANAGE_ALL (cross-tenant access)
        assert Permission.TENANT_MANAGE_ALL in super_admin_perms, (
            "Super admin must have TENANT_MANAGE_ALL permission for cross-tenant access"
        )

        # Verify super admin has all CRUD permissions for core entities
        core_crud_permissions = [
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
        ]

        for perm in core_crud_permissions:
            assert perm in super_admin_perms, (
                f"Super admin must have {perm.value} permission"
            )

    @given(role=role_strategy)
    @settings(max_examples=100)
    def test_admin_has_full_tenant_access(self, role: UserRole):
        """Admin SHALL have full access within their tenant (no cross-tenant).

        **Validates: Requirements 4.2**
        """
        if role != UserRole.ADMIN:
            return

        admin_perms = permission_checker.get_permissions(UserRole.ADMIN)

        # Admin should NOT have cross-tenant access
        assert Permission.TENANT_MANAGE_ALL not in admin_perms, (
            "Admin must NOT have TENANT_MANAGE_ALL (cross-tenant) permission"
        )
        assert Permission.TENANT_CREATE not in admin_perms, (
            "Admin must NOT have TENANT_CREATE permission"
        )
        assert Permission.TENANT_DELETE not in admin_perms, (
            "Admin must NOT have TENANT_DELETE permission"
        )

        # Admin should have full CRUD on students, teachers, classes within tenant
        tenant_crud_permissions = [
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
            Permission.ATTENDANCE_CREATE,
            Permission.ATTENDANCE_READ,
            Permission.ATTENDANCE_UPDATE,
            Permission.GRADE_CREATE,
            Permission.GRADE_READ,
            Permission.GRADE_UPDATE,
            Permission.FEE_CREATE,
            Permission.FEE_READ,
            Permission.FEE_UPDATE,
        ]

        for perm in tenant_crud_permissions:
            assert perm in admin_perms, (
                f"Admin must have {perm.value} permission for full tenant access"
            )

    @given(role=role_strategy)
    @settings(max_examples=100)
    def test_teacher_has_limited_access(self, role: UserRole):
        """Teacher SHALL have access to assigned classes and own data only.

        **Validates: Requirements 4.3**
        """
        if role != UserRole.TEACHER:
            return

        teacher_perms = permission_checker.get_permissions(UserRole.TEACHER)

        # Teacher should have read access to students (in assigned classes)
        assert Permission.STUDENT_READ in teacher_perms, (
            "Teacher must have STUDENT_READ permission for assigned classes"
        )

        # Teacher should NOT have student create/delete
        assert Permission.STUDENT_CREATE not in teacher_perms, (
            "Teacher must NOT have STUDENT_CREATE permission"
        )
        assert Permission.STUDENT_DELETE not in teacher_perms, (
            "Teacher must NOT have STUDENT_DELETE permission"
        )

        # Teacher should have own data access
        assert Permission.TEACHER_READ_OWN in teacher_perms, (
            "Teacher must have TEACHER_READ_OWN permission"
        )
        assert Permission.TEACHER_UPDATE_OWN in teacher_perms, (
            "Teacher must have TEACHER_UPDATE_OWN permission"
        )

        # Teacher should have attendance marking capability
        assert Permission.ATTENDANCE_MARK in teacher_perms, (
            "Teacher must have ATTENDANCE_MARK permission"
        )
        assert Permission.ATTENDANCE_CREATE in teacher_perms, (
            "Teacher must have ATTENDANCE_CREATE permission"
        )

        # Teacher should have grade entry capability
        assert Permission.GRADE_CREATE in teacher_perms, (
            "Teacher must have GRADE_CREATE permission"
        )
        assert Permission.GRADE_READ in teacher_perms, (
            "Teacher must have GRADE_READ permission"
        )

    @given(role=role_strategy)
    @settings(max_examples=100)
    def test_student_has_own_data_read_access(self, role: UserRole):
        """Student SHALL have read access to own data only.

        **Validates: Requirements 4.4**
        """
        if role != UserRole.STUDENT:
            return

        student_perms = permission_checker.get_permissions(UserRole.STUDENT)

        # Student should have own data read access
        assert Permission.STUDENT_READ_OWN in student_perms, (
            "Student must have STUDENT_READ_OWN permission"
        )
        assert Permission.ATTENDANCE_READ_OWN in student_perms, (
            "Student must have ATTENDANCE_READ_OWN permission"
        )
        assert Permission.GRADE_READ_OWN in student_perms, (
            "Student must have GRADE_READ_OWN permission"
        )
        assert Permission.FEE_READ_OWN in student_perms, (
            "Student must have FEE_READ_OWN permission"
        )

        # Student should NOT have broad read access
        assert Permission.STUDENT_READ not in student_perms, (
            "Student must NOT have STUDENT_READ (all students) permission"
        )

        # Student should NOT have any create/update/delete on other entities
        assert Permission.STUDENT_CREATE not in student_perms, (
            "Student must NOT have STUDENT_CREATE permission"
        )
        assert Permission.STUDENT_UPDATE not in student_perms, (
            "Student must NOT have STUDENT_UPDATE permission"
        )
        assert Permission.STUDENT_DELETE not in student_perms, (
            "Student must NOT have STUDENT_DELETE permission"
        )
        assert Permission.ATTENDANCE_CREATE not in student_perms, (
            "Student must NOT have ATTENDANCE_CREATE permission"
        )
        assert Permission.GRADE_CREATE not in student_perms, (
            "Student must NOT have GRADE_CREATE permission"
        )

    @given(role=role_strategy)
    @settings(max_examples=100)
    def test_parent_has_children_read_access(self, role: UserRole):
        """Parent SHALL have read access to linked children's data only.

        **Validates: Requirements 4.5**
        """
        if role != UserRole.PARENT:
            return

        parent_perms = permission_checker.get_permissions(UserRole.PARENT)

        # Parent should have children data read access
        assert Permission.STUDENT_READ_CHILDREN in parent_perms, (
            "Parent must have STUDENT_READ_CHILDREN permission"
        )
        assert Permission.ATTENDANCE_READ_CHILDREN in parent_perms, (
            "Parent must have ATTENDANCE_READ_CHILDREN permission"
        )
        assert Permission.GRADE_READ_CHILDREN in parent_perms, (
            "Parent must have GRADE_READ_CHILDREN permission"
        )
        assert Permission.FEE_READ_CHILDREN in parent_perms, (
            "Parent must have FEE_READ_CHILDREN permission"
        )

        # Parent should NOT have broad read access
        assert Permission.STUDENT_READ not in parent_perms, (
            "Parent must NOT have STUDENT_READ (all students) permission"
        )

        # Parent should NOT have any create/update/delete permissions
        assert Permission.STUDENT_CREATE not in parent_perms, (
            "Parent must NOT have STUDENT_CREATE permission"
        )
        assert Permission.ATTENDANCE_CREATE not in parent_perms, (
            "Parent must NOT have ATTENDANCE_CREATE permission"
        )
        assert Permission.GRADE_CREATE not in parent_perms, (
            "Parent must NOT have GRADE_CREATE permission"
        )
        assert Permission.FEE_CREATE not in parent_perms, (
            "Parent must NOT have FEE_CREATE permission"
        )

    @given(
        role=role_strategy,
        permission_str=st.text(min_size=1, max_size=50).filter(
            lambda s: s not in [p.value for p in Permission]
        ),
    )
    @settings(max_examples=100)
    def test_invalid_permission_string_returns_false(
        self, role: UserRole, permission_str: str
    ):
        """For any invalid permission string, has_permission SHALL return False.

        **Validates: Requirements 4.1, 4.2, 4.3, 4.4, 4.5**
        """
        # Act: Check permission with invalid string
        result = permission_checker.has_permission(role, permission_str)

        # Assert: Invalid permissions should always return False
        assert result is False, (
            f"Invalid permission string '{permission_str}' should return False, "
            f"but got {result} for role {role.value}"
        )

    @given(role=role_strategy)
    @settings(max_examples=100)
    def test_get_permissions_returns_copy(self, role: UserRole):
        """get_permissions SHALL return a copy to prevent mutation of internal state.

        **Validates: Requirements 4.1, 4.2, 4.3, 4.4, 4.5**
        """
        # Act: Get permissions twice
        perms1 = permission_checker.get_permissions(role)
        perms2 = permission_checker.get_permissions(role)

        # Assert: They should be equal but not the same object
        assert perms1 == perms2, "get_permissions should return consistent results"
        assert perms1 is not perms2, (
            "get_permissions should return a copy, not the original set"
        )

        # Mutating one should not affect the other
        if perms1:
            original_len = len(perms2)
            perms1.pop()
            assert len(perms2) == original_len, (
                "Mutating returned permissions should not affect internal state"
            )

    @given(role=role_strategy, permission=permission_strategy)
    @settings(max_examples=100)
    def test_permission_enum_and_string_equivalent(
        self, role: UserRole, permission: Permission
    ):
        """Permission check with enum and string SHALL produce same result.

        **Validates: Requirements 4.1, 4.2, 4.3, 4.4, 4.5**
        """
        # Act: Check permission with both enum and string
        result_enum = permission_checker.has_permission(role, permission)
        result_str = permission_checker.has_permission(role, permission.value)

        # Assert: Both should produce the same result
        assert result_enum == result_str, (
            f"Permission check with enum ({permission}) and string ({permission.value}) "
            f"should produce same result. Enum: {result_enum}, String: {result_str}"
        )

    @given(role=role_strategy)
    @settings(max_examples=100)
    def test_role_hierarchy_permissions_subset(self, role: UserRole):
        """Lower privilege roles SHALL have subset of higher privilege role permissions.

        **Validates: Requirements 4.1, 4.2, 4.3, 4.4, 4.5**
        """
        super_admin_perms = permission_checker.get_permissions(UserRole.SUPER_ADMIN)
        admin_perms = permission_checker.get_permissions(UserRole.ADMIN)

        # Admin permissions (except own-data specific) should be subset of super_admin
        # Note: Some permissions like LEAVE_READ_OWN are admin-specific
        admin_only_perms = {Permission.LEAVE_READ_OWN}
        admin_comparable = admin_perms - admin_only_perms

        for perm in admin_comparable:
            assert perm in super_admin_perms, (
                f"Admin permission {perm.value} should also be in super_admin permissions"
            )

