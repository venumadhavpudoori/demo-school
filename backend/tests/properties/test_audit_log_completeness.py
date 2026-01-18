"""Property-based tests for audit log completeness.

**Feature: school-erp-multi-tenancy, Property 17: Audit Log Completeness**
**Validates: Design - Property 17**

Property 17: Audit Log Completeness
*For any* sensitive operation (create, update, delete on core entities), an audit log entry
SHALL be created containing user_id, action, entity_type, entity_id, and timestamp.
"""

from datetime import datetime
from typing import Any
from unittest.mock import MagicMock, patch

from hypothesis import given, settings, HealthCheck
from hypothesis import strategies as st

from app.models.audit_log import AuditAction, AuditLog
from app.services.audit_service import AuditService
from app.repositories.audit_log import AuditLogRepository


# Strategy for valid tenant IDs (positive integers)
tenant_id_strategy = st.integers(min_value=1, max_value=1_000_000)

# Strategy for valid user IDs (positive integers or None for system operations)
user_id_strategy = st.one_of(
    st.none(),
    st.integers(min_value=1, max_value=1_000_000),
)

# Strategy for valid entity IDs (positive integers)
entity_id_strategy = st.integers(min_value=1, max_value=1_000_000)

# Strategy for entity types (core entities in the system)
entity_type_strategy = st.sampled_from([
    "student",
    "teacher",
    "class",
    "section",
    "exam",
    "fee",
    "announcement",
    "leave_request",
    "attendance",
    "grade",
    "timetable",
    "user",
])

# Strategy for audit actions (sensitive operations)
sensitive_action_strategy = st.sampled_from([
    AuditAction.CREATE,
    AuditAction.UPDATE,
    AuditAction.DELETE,
    AuditAction.SOFT_DELETE,
])

# Strategy for all audit actions
all_action_strategy = st.sampled_from(list(AuditAction))

# Strategy for IP addresses
ip_address_strategy = st.one_of(
    st.none(),
    st.from_regex(r"^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$", fullmatch=True),
)

# Strategy for user agent strings
user_agent_strategy = st.one_of(
    st.none(),
    st.text(min_size=1, max_size=200).filter(lambda x: x.strip()),
)

# Strategy for arbitrary JSON-serializable values
json_value_strategy = st.recursive(
    st.one_of(
        st.none(),
        st.booleans(),
        st.integers(),
        st.floats(allow_nan=False, allow_infinity=False),
        st.text(max_size=50),
    ),
    lambda children: st.one_of(
        st.lists(children, max_size=5),
        st.dictionaries(st.text(min_size=1, max_size=20), children, max_size=5),
    ),
    max_leaves=10,
)

# Strategy for old/new values dictionaries
values_dict_strategy = st.one_of(
    st.none(),
    st.dictionaries(
        st.text(min_size=1, max_size=30).filter(lambda x: x.strip()),
        json_value_strategy,
        min_size=0,
        max_size=10,
    ),
)


class TestAuditLogCompleteness:
    """**Feature: school-erp-multi-tenancy, Property 17: Audit Log Completeness**"""

    @given(
        tenant_id=tenant_id_strategy,
        user_id=user_id_strategy,
        entity_type=entity_type_strategy,
        entity_id=entity_id_strategy,
        action=sensitive_action_strategy,
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_audit_log_contains_required_fields(
        self,
        tenant_id: int,
        user_id: int | None,
        entity_type: str,
        entity_id: int,
        action: AuditAction,
    ):
        """For any sensitive operation, audit log SHALL contain user_id, action, entity_type, entity_id, and timestamp.

        **Validates: Requirements 17.3**
        """
        # Arrange: Create a mock that captures the data passed to create_log
        captured_data: dict[str, Any] = {}

        def mock_create_log(**kwargs):
            captured_data.update(kwargs)
            # Return a mock AuditLog with timestamp
            mock_log = MagicMock()
            mock_log.created_at = datetime.now()
            for key, value in kwargs.items():
                setattr(mock_log, key, value)
            return mock_log

        mock_db = MagicMock()

        # Create the service and patch the repository's create_log method
        audit_service = AuditService(db=mock_db, tenant_id=tenant_id)
        audit_service.repository.create_log = mock_create_log

        # Act: Log a sensitive operation
        result = audit_service.log_action(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
        )

        # Assert: All required fields are present in the captured data
        assert "user_id" in captured_data, "Audit log must contain user_id"
        assert "action" in captured_data, "Audit log must contain action"
        assert "entity_type" in captured_data, "Audit log must contain entity_type"
        assert "entity_id" in captured_data, "Audit log must contain entity_id"

        # Assert: Field values are correct
        assert captured_data["user_id"] == user_id, (
            f"user_id must be {user_id}, got {captured_data['user_id']}"
        )
        assert captured_data["action"] == action, (
            f"action must be {action}, got {captured_data['action']}"
        )
        assert captured_data["entity_type"] == entity_type, (
            f"entity_type must be {entity_type}, got {captured_data['entity_type']}"
        )
        assert captured_data["entity_id"] == entity_id, (
            f"entity_id must be {entity_id}, got {captured_data['entity_id']}"
        )

        # Assert: Result has timestamp
        assert hasattr(result, "created_at"), "Audit log must have timestamp (created_at)"
        assert isinstance(result.created_at, datetime), "created_at must be a datetime instance"

    @given(
        tenant_id=tenant_id_strategy,
        user_id=st.integers(min_value=1, max_value=1_000_000),
        entity_type=entity_type_strategy,
        entity_id=entity_id_strategy,
        new_values=values_dict_strategy,
    )
    @settings(max_examples=100)
    def test_create_operation_logs_correctly(
        self,
        tenant_id: int,
        user_id: int,
        entity_type: str,
        entity_id: int,
        new_values: dict | None,
    ):
        """For any CREATE operation, audit log SHALL record the action as CREATE with new values.

        **Validates: Requirements 17.3**
        """
        # Arrange
        captured_data: dict[str, Any] = {}

        def mock_create_log(**kwargs):
            captured_data.update(kwargs)
            mock_log = MagicMock()
            mock_log.created_at = datetime.now()
            for key, value in kwargs.items():
                setattr(mock_log, key, value)
            return mock_log

        mock_db = MagicMock()
        audit_service = AuditService(db=mock_db, tenant_id=tenant_id)
        audit_service.repository.create_log = mock_create_log

        # Act: Log a create operation
        audit_service.log_create(
            user_id=user_id,
            entity_type=entity_type,
            entity_id=entity_id,
            new_values=new_values,
        )

        # Assert: Action is CREATE
        assert captured_data["action"] == AuditAction.CREATE, (
            f"Create operation must log action as CREATE, got {captured_data['action']}"
        )
        # Assert: Required fields are present
        assert captured_data["user_id"] == user_id
        assert captured_data["entity_type"] == entity_type
        assert captured_data["entity_id"] == entity_id

    @given(
        tenant_id=tenant_id_strategy,
        user_id=st.integers(min_value=1, max_value=1_000_000),
        entity_type=entity_type_strategy,
        entity_id=entity_id_strategy,
        old_values=values_dict_strategy,
        new_values=values_dict_strategy,
    )
    @settings(max_examples=100)
    def test_update_operation_logs_correctly(
        self,
        tenant_id: int,
        user_id: int,
        entity_type: str,
        entity_id: int,
        old_values: dict | None,
        new_values: dict | None,
    ):
        """For any UPDATE operation, audit log SHALL record the action as UPDATE with old and new values.

        **Validates: Requirements 17.3**
        """
        # Arrange
        captured_data: dict[str, Any] = {}

        def mock_create_log(**kwargs):
            captured_data.update(kwargs)
            mock_log = MagicMock()
            mock_log.created_at = datetime.now()
            for key, value in kwargs.items():
                setattr(mock_log, key, value)
            return mock_log

        mock_db = MagicMock()
        audit_service = AuditService(db=mock_db, tenant_id=tenant_id)
        audit_service.repository.create_log = mock_create_log

        # Act: Log an update operation
        audit_service.log_update(
            user_id=user_id,
            entity_type=entity_type,
            entity_id=entity_id,
            old_values=old_values,
            new_values=new_values,
        )

        # Assert: Action is UPDATE
        assert captured_data["action"] == AuditAction.UPDATE, (
            f"Update operation must log action as UPDATE, got {captured_data['action']}"
        )
        # Assert: Required fields are present
        assert captured_data["user_id"] == user_id
        assert captured_data["entity_type"] == entity_type
        assert captured_data["entity_id"] == entity_id

    @given(
        tenant_id=tenant_id_strategy,
        user_id=st.integers(min_value=1, max_value=1_000_000),
        entity_type=entity_type_strategy,
        entity_id=entity_id_strategy,
        old_values=values_dict_strategy,
    )
    @settings(max_examples=100)
    def test_delete_operation_logs_correctly(
        self,
        tenant_id: int,
        user_id: int,
        entity_type: str,
        entity_id: int,
        old_values: dict | None,
    ):
        """For any DELETE operation, audit log SHALL record the action as DELETE with old values.

        **Validates: Requirements 17.3**
        """
        # Arrange
        captured_data: dict[str, Any] = {}

        def mock_create_log(**kwargs):
            captured_data.update(kwargs)
            mock_log = MagicMock()
            mock_log.created_at = datetime.now()
            for key, value in kwargs.items():
                setattr(mock_log, key, value)
            return mock_log

        mock_db = MagicMock()
        audit_service = AuditService(db=mock_db, tenant_id=tenant_id)
        audit_service.repository.create_log = mock_create_log

        # Act: Log a delete operation
        audit_service.log_delete(
            user_id=user_id,
            entity_type=entity_type,
            entity_id=entity_id,
            old_values=old_values,
        )

        # Assert: Action is DELETE
        assert captured_data["action"] == AuditAction.DELETE, (
            f"Delete operation must log action as DELETE, got {captured_data['action']}"
        )
        # Assert: Required fields are present
        assert captured_data["user_id"] == user_id
        assert captured_data["entity_type"] == entity_type
        assert captured_data["entity_id"] == entity_id

    @given(
        tenant_id=tenant_id_strategy,
        user_id=st.integers(min_value=1, max_value=1_000_000),
        entity_type=entity_type_strategy,
        entity_id=entity_id_strategy,
    )
    @settings(max_examples=100)
    def test_soft_delete_operation_logs_correctly(
        self,
        tenant_id: int,
        user_id: int,
        entity_type: str,
        entity_id: int,
    ):
        """For any SOFT_DELETE operation, audit log SHALL record the action as SOFT_DELETE.

        **Validates: Requirements 17.3**
        """
        # Arrange
        captured_data: dict[str, Any] = {}

        def mock_create_log(**kwargs):
            captured_data.update(kwargs)
            mock_log = MagicMock()
            mock_log.created_at = datetime.now()
            for key, value in kwargs.items():
                setattr(mock_log, key, value)
            return mock_log

        mock_db = MagicMock()
        audit_service = AuditService(db=mock_db, tenant_id=tenant_id)
        audit_service.repository.create_log = mock_create_log

        # Act: Log a soft delete operation
        audit_service.log_soft_delete(
            user_id=user_id,
            entity_type=entity_type,
            entity_id=entity_id,
        )

        # Assert: Action is SOFT_DELETE
        assert captured_data["action"] == AuditAction.SOFT_DELETE, (
            f"Soft delete operation must log action as SOFT_DELETE, got {captured_data['action']}"
        )
        # Assert: Required fields are present
        assert captured_data["user_id"] == user_id
        assert captured_data["entity_type"] == entity_type
        assert captured_data["entity_id"] == entity_id

    @given(
        tenant_id=tenant_id_strategy,
        user_id=user_id_strategy,
        entity_type=entity_type_strategy,
        entity_id=entity_id_strategy,
        action=sensitive_action_strategy,
        ip_address=ip_address_strategy,
        user_agent=user_agent_strategy,
    )
    @settings(max_examples=100)
    def test_audit_log_captures_request_context(
        self,
        tenant_id: int,
        user_id: int | None,
        entity_type: str,
        entity_id: int,
        action: AuditAction,
        ip_address: str | None,
        user_agent: str | None,
    ):
        """For any sensitive operation with request context, audit log SHALL capture IP and user agent.

        **Validates: Requirements 17.3**
        """
        # Arrange
        captured_data: dict[str, Any] = {}

        def mock_create_log(**kwargs):
            captured_data.update(kwargs)
            mock_log = MagicMock()
            mock_log.created_at = datetime.now()
            for key, value in kwargs.items():
                setattr(mock_log, key, value)
            return mock_log

        mock_db = MagicMock()
        audit_service = AuditService(db=mock_db, tenant_id=tenant_id)
        audit_service.repository.create_log = mock_create_log

        # Act: Log with request context
        audit_service.log_action(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        # Assert: Request context is captured
        assert captured_data.get("ip_address") == ip_address, (
            f"IP address must be {ip_address}, got {captured_data.get('ip_address')}"
        )
        assert captured_data.get("user_agent") == user_agent, (
            f"User agent must be {user_agent}, got {captured_data.get('user_agent')}"
        )

    @given(
        tenant_id=tenant_id_strategy,
        user_id=st.integers(min_value=1, max_value=1_000_000),
    )
    @settings(max_examples=100)
    def test_login_operation_logs_correctly(
        self,
        tenant_id: int,
        user_id: int,
    ):
        """For any LOGIN operation, audit log SHALL record the action as LOGIN.

        **Validates: Requirements 17.3**
        """
        # Arrange
        captured_data: dict[str, Any] = {}

        def mock_create_log(**kwargs):
            captured_data.update(kwargs)
            mock_log = MagicMock()
            mock_log.created_at = datetime.now()
            for key, value in kwargs.items():
                setattr(mock_log, key, value)
            return mock_log

        mock_db = MagicMock()
        audit_service = AuditService(db=mock_db, tenant_id=tenant_id)
        audit_service.repository.create_log = mock_create_log

        # Act: Log a login operation
        audit_service.log_login(user_id=user_id)

        # Assert: Action is LOGIN
        assert captured_data["action"] == AuditAction.LOGIN, (
            f"Login operation must log action as LOGIN, got {captured_data['action']}"
        )
        assert captured_data["user_id"] == user_id
        assert captured_data["entity_type"] == "user"
        assert captured_data["entity_id"] == user_id

    @given(
        tenant_id=tenant_id_strategy,
        user_id=st.integers(min_value=1, max_value=1_000_000),
    )
    @settings(max_examples=100)
    def test_password_change_operation_logs_correctly(
        self,
        tenant_id: int,
        user_id: int,
    ):
        """For any PASSWORD_CHANGE operation, audit log SHALL record the action correctly.

        **Validates: Requirements 17.3**
        """
        # Arrange
        captured_data: dict[str, Any] = {}

        def mock_create_log(**kwargs):
            captured_data.update(kwargs)
            mock_log = MagicMock()
            mock_log.created_at = datetime.now()
            for key, value in kwargs.items():
                setattr(mock_log, key, value)
            return mock_log

        mock_db = MagicMock()
        audit_service = AuditService(db=mock_db, tenant_id=tenant_id)
        audit_service.repository.create_log = mock_create_log

        # Act: Log a password change operation
        audit_service.log_password_change(user_id=user_id)

        # Assert: Action is PASSWORD_CHANGE
        assert captured_data["action"] == AuditAction.PASSWORD_CHANGE, (
            f"Password change must log action as PASSWORD_CHANGE, got {captured_data['action']}"
        )
        assert captured_data["user_id"] == user_id
        assert captured_data["entity_type"] == "user"
        assert captured_data["entity_id"] == user_id

    @given(
        tenant_id=tenant_id_strategy,
        user_id=st.integers(min_value=1, max_value=1_000_000),
        target_user_id=st.integers(min_value=1, max_value=1_000_000),
        old_role=st.sampled_from(["admin", "teacher", "student", "parent"]),
        new_role=st.sampled_from(["admin", "teacher", "student", "parent"]),
    )
    @settings(max_examples=100)
    def test_permission_change_operation_logs_correctly(
        self,
        tenant_id: int,
        user_id: int,
        target_user_id: int,
        old_role: str,
        new_role: str,
    ):
        """For any PERMISSION_CHANGE operation, audit log SHALL record the role change.

        **Validates: Requirements 17.3**
        """
        # Arrange
        captured_data: dict[str, Any] = {}

        def mock_create_log(**kwargs):
            captured_data.update(kwargs)
            mock_log = MagicMock()
            mock_log.created_at = datetime.now()
            for key, value in kwargs.items():
                setattr(mock_log, key, value)
            return mock_log

        mock_db = MagicMock()
        audit_service = AuditService(db=mock_db, tenant_id=tenant_id)
        audit_service.repository.create_log = mock_create_log

        # Act: Log a permission change operation
        audit_service.log_permission_change(
            user_id=user_id,
            target_user_id=target_user_id,
            old_role=old_role,
            new_role=new_role,
        )

        # Assert: Action is PERMISSION_CHANGE
        assert captured_data["action"] == AuditAction.PERMISSION_CHANGE, (
            f"Permission change must log action as PERMISSION_CHANGE, got {captured_data['action']}"
        )
        assert captured_data["user_id"] == user_id
        assert captured_data["entity_type"] == "user"
        assert captured_data["entity_id"] == target_user_id
        assert captured_data["old_values"] == {"role": old_role}
        assert captured_data["new_values"] == {"role": new_role}

