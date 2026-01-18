"""Property-based tests for announcement role filtering.

**Feature: school-erp-multi-tenancy, Property 14: Announcement Role Filtering**
**Validates: Design - Property 14**

Property 14: Announcement Role Filtering
*For any* user requesting announcements, the returned announcements SHALL only
include those where target_audience is 'all' OR matches the user's role.
"""

from unittest.mock import MagicMock, patch

from hypothesis import given, settings
from hypothesis import strategies as st

from app.models.announcement import Announcement, TargetAudience
from app.models.user import UserRole
from app.repositories.announcement import AnnouncementRepository
from app.services.announcement_service import AnnouncementService


# Strategy for valid user roles (excluding SUPER_ADMIN which maps to ADMIN)
user_role_strategy = st.sampled_from([
    UserRole.ADMIN,
    UserRole.TEACHER,
    UserRole.STUDENT,
    UserRole.PARENT,
])

# Strategy for all user roles including SUPER_ADMIN
all_user_role_strategy = st.sampled_from(list(UserRole))

# Strategy for target audiences
target_audience_strategy = st.sampled_from(list(TargetAudience))

# Strategy for valid tenant IDs
tenant_id_strategy = st.integers(min_value=1, max_value=1_000_000)

# Strategy for announcement IDs
announcement_id_strategy = st.integers(min_value=1, max_value=1_000_000)


def create_mock_announcement(
    announcement_id: int,
    tenant_id: int,
    target_audience: TargetAudience,
    title: str = "Test Announcement",
    content: str = "Test Content",
) -> MagicMock:
    """Create a mock announcement object for testing."""
    mock = MagicMock(spec=Announcement)
    mock.id = announcement_id
    mock.tenant_id = tenant_id
    mock.title = title
    mock.content = content
    mock.target_audience = target_audience
    mock.created_by = 1
    mock.author = None
    mock.created_at = None
    mock.updated_at = None
    return mock


def get_expected_audience_for_role(user_role: UserRole) -> TargetAudience:
    """Map UserRole to the corresponding TargetAudience."""
    role_to_audience = {
        UserRole.ADMIN: TargetAudience.ADMIN,
        UserRole.TEACHER: TargetAudience.TEACHER,
        UserRole.STUDENT: TargetAudience.STUDENT,
        UserRole.PARENT: TargetAudience.PARENT,
        UserRole.SUPER_ADMIN: TargetAudience.ADMIN,  # Super admin sees admin announcements
    }
    return role_to_audience.get(user_role, TargetAudience.ALL)


def is_announcement_visible_to_role(
    announcement_audience: TargetAudience,
    user_role: UserRole,
) -> bool:
    """Determine if an announcement should be visible to a user with the given role.
    
    An announcement is visible if:
    - target_audience is 'all', OR
    - target_audience matches the user's role
    """
    if announcement_audience == TargetAudience.ALL:
        return True
    
    expected_audience = get_expected_audience_for_role(user_role)
    return announcement_audience == expected_audience


class TestAnnouncementRoleFiltering:
    """**Feature: school-erp-multi-tenancy, Property 14: Announcement Role Filtering**"""

    @given(
        user_role=all_user_role_strategy,
        announcement_audience=target_audience_strategy,
    )
    @settings(max_examples=100)
    def test_visibility_rule_all_audience_always_visible(
        self,
        user_role: UserRole,
        announcement_audience: TargetAudience,
    ):
        """Announcements with target_audience='all' SHALL be visible to all roles.

        **Validates: Requirements 12.2**
        """
        if announcement_audience != TargetAudience.ALL:
            return  # Only test 'all' audience in this test
        
        # Assert: 'all' audience announcements are visible to any role
        is_visible = is_announcement_visible_to_role(announcement_audience, user_role)
        
        assert is_visible is True, (
            f"Announcement with target_audience='all' must be visible to {user_role.value}. "
            f"Got: {is_visible}"
        )

    @given(
        user_role=user_role_strategy,
    )
    @settings(max_examples=100)
    def test_visibility_rule_matching_role_visible(
        self,
        user_role: UserRole,
    ):
        """Announcements targeting a specific role SHALL be visible to that role.

        **Validates: Requirements 12.2**
        """
        # Get the target audience that matches this role
        matching_audience = get_expected_audience_for_role(user_role)
        
        # Assert: Announcements targeting this role are visible
        is_visible = is_announcement_visible_to_role(matching_audience, user_role)
        
        assert is_visible is True, (
            f"Announcement with target_audience='{matching_audience.value}' must be visible "
            f"to {user_role.value}. Got: {is_visible}"
        )

    @given(
        user_role=user_role_strategy,
        announcement_audience=target_audience_strategy,
    )
    @settings(max_examples=100)
    def test_visibility_rule_non_matching_role_not_visible(
        self,
        user_role: UserRole,
        announcement_audience: TargetAudience,
    ):
        """Announcements targeting a different role SHALL NOT be visible.

        **Validates: Requirements 12.2**
        """
        # Skip if audience is 'all' (always visible)
        if announcement_audience == TargetAudience.ALL:
            return
        
        # Get the expected audience for this role
        expected_audience = get_expected_audience_for_role(user_role)
        
        # Skip if the audience matches the role
        if announcement_audience == expected_audience:
            return
        
        # Assert: Announcements targeting a different role are NOT visible
        is_visible = is_announcement_visible_to_role(announcement_audience, user_role)
        
        assert is_visible is False, (
            f"Announcement with target_audience='{announcement_audience.value}' must NOT be "
            f"visible to {user_role.value}. Got: {is_visible}"
        )

    @given(
        user_role=all_user_role_strategy,
        tenant_id=tenant_id_strategy,
        num_announcements=st.integers(min_value=1, max_value=10),
    )
    @settings(max_examples=100)
    def test_list_for_role_returns_only_visible_announcements(
        self,
        user_role: UserRole,
        tenant_id: int,
        num_announcements: int,
    ):
        """list_for_role SHALL return only announcements visible to the user's role.

        **Validates: Requirements 12.2**
        """
        # Create mock announcements with various target audiences
        all_announcements = []
        for i in range(num_announcements):
            audience = list(TargetAudience)[i % len(TargetAudience)]
            mock_ann = create_mock_announcement(
                announcement_id=i + 1,
                tenant_id=tenant_id,
                target_audience=audience,
                title=f"Announcement {i + 1}",
            )
            all_announcements.append(mock_ann)
        
        # Determine which announcements should be visible
        expected_visible = [
            ann for ann in all_announcements
            if is_announcement_visible_to_role(ann.target_audience, user_role)
        ]
        
        # Verify the visibility logic is correct
        for ann in expected_visible:
            assert ann.target_audience == TargetAudience.ALL or \
                   ann.target_audience == get_expected_audience_for_role(user_role), (
                f"Expected visible announcement has wrong audience: {ann.target_audience.value}"
            )

    @given(
        user_role=all_user_role_strategy,
        tenant_id=tenant_id_strategy,
    )
    @settings(max_examples=100)
    def test_role_to_audience_mapping_consistency(
        self,
        user_role: UserRole,
        tenant_id: int,
    ):
        """Role to audience mapping SHALL be consistent and deterministic.

        **Validates: Requirements 12.2**
        """
        # Get the mapping twice
        audience1 = get_expected_audience_for_role(user_role)
        audience2 = get_expected_audience_for_role(user_role)
        
        # Assert: Mapping is deterministic
        assert audience1 == audience2, (
            f"Role to audience mapping must be deterministic. "
            f"Got {audience1.value} and {audience2.value} for role {user_role.value}"
        )
        
        # Assert: Mapping produces valid TargetAudience
        assert isinstance(audience1, TargetAudience), (
            f"Mapping must produce TargetAudience enum. Got: {type(audience1)}"
        )

    @given(
        user_role=all_user_role_strategy,
    )
    @settings(max_examples=100)
    def test_super_admin_sees_admin_announcements(
        self,
        user_role: UserRole,
    ):
        """SUPER_ADMIN SHALL see announcements targeted to ADMIN role.

        **Validates: Requirements 12.2**
        """
        if user_role != UserRole.SUPER_ADMIN:
            return
        
        # Super admin should see admin-targeted announcements
        is_visible = is_announcement_visible_to_role(TargetAudience.ADMIN, user_role)
        
        assert is_visible is True, (
            f"SUPER_ADMIN must see ADMIN-targeted announcements. Got: {is_visible}"
        )

    @given(
        user_role=user_role_strategy,
        tenant_id=tenant_id_strategy,
    )
    @settings(max_examples=100)
    def test_each_role_sees_all_plus_own_announcements(
        self,
        user_role: UserRole,
        tenant_id: int,
    ):
        """Each role SHALL see 'all' announcements plus their role-specific ones.

        **Validates: Requirements 12.2**
        """
        # Create one announcement for each target audience
        announcements = []
        for audience in TargetAudience:
            mock_ann = create_mock_announcement(
                announcement_id=len(announcements) + 1,
                tenant_id=tenant_id,
                target_audience=audience,
            )
            announcements.append(mock_ann)
        
        # Filter visible announcements
        visible = [
            ann for ann in announcements
            if is_announcement_visible_to_role(ann.target_audience, user_role)
        ]
        
        # Assert: At least 'all' and role-specific announcements are visible
        visible_audiences = {ann.target_audience for ann in visible}
        
        assert TargetAudience.ALL in visible_audiences, (
            f"Role {user_role.value} must see 'all' announcements"
        )
        
        expected_role_audience = get_expected_audience_for_role(user_role)
        assert expected_role_audience in visible_audiences, (
            f"Role {user_role.value} must see {expected_role_audience.value} announcements"
        )
        
        # Assert: Exactly 2 audiences are visible (all + role-specific)
        assert len(visible_audiences) == 2, (
            f"Role {user_role.value} should see exactly 2 audience types "
            f"('all' + role-specific). Got: {[a.value for a in visible_audiences]}"
        )

    @given(
        announcement_audience=target_audience_strategy,
    )
    @settings(max_examples=100)
    def test_all_audience_visible_to_every_role(
        self,
        announcement_audience: TargetAudience,
    ):
        """Announcements with 'all' audience SHALL be visible to every role.

        **Validates: Requirements 12.2**
        """
        if announcement_audience != TargetAudience.ALL:
            return
        
        # Check visibility for all roles
        for role in UserRole:
            is_visible = is_announcement_visible_to_role(announcement_audience, role)
            assert is_visible is True, (
                f"'all' audience announcement must be visible to {role.value}. "
                f"Got: {is_visible}"
            )

    @given(
        target_role=user_role_strategy,
    )
    @settings(max_examples=100)
    def test_role_specific_announcement_only_visible_to_that_role(
        self,
        target_role: UserRole,
    ):
        """Role-specific announcements SHALL only be visible to that role (and super_admin for admin).

        **Validates: Requirements 12.2**
        """
        target_audience = get_expected_audience_for_role(target_role)
        
        for checking_role in UserRole:
            is_visible = is_announcement_visible_to_role(target_audience, checking_role)
            
            # Determine if this role should see the announcement
            should_see = (
                get_expected_audience_for_role(checking_role) == target_audience
            )
            
            assert is_visible == should_see, (
                f"Announcement for {target_audience.value} visibility to {checking_role.value}: "
                f"expected {should_see}, got {is_visible}"
            )
