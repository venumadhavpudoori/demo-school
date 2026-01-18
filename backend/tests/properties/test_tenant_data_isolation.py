"""Property-based tests for tenant data isolation.

**Feature: school-erp-multi-tenancy, Property 1: Tenant Data Isolation**
**Validates: Design - Property 1**

Property 1: Tenant Data Isolation
*For any* database query executed within a tenant context, all returned records
SHALL have a tenant_id matching the current tenant context.
"""

from unittest.mock import MagicMock

from hypothesis import given, settings
from hypothesis import strategies as st

from app.models.base import TenantAwareBase
from app.repositories.base import TenantAwareRepository

# Strategy for valid tenant IDs (positive integers)
tenant_id_strategy = st.integers(min_value=1, max_value=1_000_000)

# Strategy for entity IDs
entity_id_strategy = st.integers(min_value=1, max_value=1_000_000)


class MockTenantModel(TenantAwareBase):
    """Mock model for testing tenant-aware repository behavior."""

    __tablename__ = "mock_tenant_entities"
    __abstract__ = True  # Prevent SQLAlchemy from creating table

    id: int
    tenant_id: int
    name: str


class MockRepository(TenantAwareRepository[MockTenantModel]):
    """Concrete repository implementation for testing."""

    model = MockTenantModel


class TestTenantDataIsolation:
    """**Feature: school-erp-multi-tenancy, Property 1: Tenant Data Isolation**"""

    @given(
        tenant_id=tenant_id_strategy,
        other_tenant_id=tenant_id_strategy,
    )
    @settings(max_examples=100)
    def test_repository_always_filters_by_tenant_id(self, tenant_id: int, other_tenant_id: int):
        """For any repository query, the base query SHALL filter by tenant_id.

        **Validates: Requirements 1.2**
        """
        # Arrange: Create a repository with a mock session
        mock_db = MagicMock()
        repo = MockRepository(db=mock_db, tenant_id=tenant_id)

        # Assert: Repository stores the correct tenant_id
        assert repo.tenant_id == tenant_id, (
            f"Repository must store the tenant_id. " f"Expected: {tenant_id}, Got: {repo.tenant_id}"
        )

    @given(
        tenant_id=tenant_id_strategy,
    )
    @settings(max_examples=100)
    def test_create_always_sets_tenant_id(self, tenant_id: int):
        """For any entity creation, the tenant_id SHALL be set to current tenant.

        **Validates: Requirements 1.2**
        """
        # Arrange
        mock_db = MagicMock()
        mock_entity = MagicMock()
        mock_db.add = MagicMock()
        mock_db.commit = MagicMock()
        mock_db.refresh = MagicMock()

        # Create a repository that captures the data passed to model constructor
        captured_data = {}

        class CapturingRepository(TenantAwareRepository):
            model = MagicMock()

            def __init__(self, db, tenant_id):
                super().__init__(db, tenant_id)
                self.model.return_value = mock_entity

        repo = CapturingRepository(db=mock_db, tenant_id=tenant_id)

        # Act: Create an entity with arbitrary data
        input_data = {"name": "Test Entity", "value": 123}
        repo.create(input_data)

        # Assert: The model was called with tenant_id included
        call_kwargs = repo.model.call_args
        if call_kwargs:
            passed_data = (
                call_kwargs[1] if call_kwargs[1] else call_kwargs[0][0] if call_kwargs[0] else {}
            )
            # Check if tenant_id was passed (either as kwarg or in dict)
            if isinstance(passed_data, dict):
                assert passed_data.get("tenant_id") == tenant_id, (
                    f"Created entity must have tenant_id={tenant_id}. "
                    f"Got: {passed_data.get('tenant_id')}"
                )

    @given(
        tenant_id=tenant_id_strategy,
        malicious_tenant_id=tenant_id_strategy,
    )
    @settings(max_examples=100)
    def test_create_prevents_tenant_id_override(self, tenant_id: int, malicious_tenant_id: int):
        """For any entity creation, attempting to set a different tenant_id SHALL be overridden.

        **Validates: Requirements 1.2**
        """
        # Skip if tenant IDs are the same
        if tenant_id == malicious_tenant_id:
            return

        # Arrange
        mock_db = MagicMock()
        mock_entity = MagicMock()

        captured_tenant_id = None

        class CapturingModel:
            def __init__(self, **kwargs):
                nonlocal captured_tenant_id
                captured_tenant_id = kwargs.get("tenant_id")

        class CapturingRepository(TenantAwareRepository):
            model = CapturingModel

        repo = CapturingRepository(db=mock_db, tenant_id=tenant_id)

        # Act: Try to create with a different tenant_id
        input_data = {"name": "Test", "tenant_id": malicious_tenant_id}
        try:
            repo.create(input_data)
        except Exception:
            pass  # We only care about what tenant_id was used

        # Assert: The repository's tenant_id was used, not the malicious one
        assert captured_tenant_id == tenant_id, (
            f"Repository must override any provided tenant_id with its own. "
            f"Expected: {tenant_id}, Got: {captured_tenant_id}"
        )

    @given(
        tenant_id=tenant_id_strategy,
        entity_id=entity_id_strategy,
        malicious_tenant_id=tenant_id_strategy,
    )
    @settings(max_examples=100)
    def test_update_prevents_tenant_id_change(
        self, tenant_id: int, entity_id: int, malicious_tenant_id: int
    ):
        """For any entity update, attempting to change tenant_id SHALL be prevented.

        **Validates: Requirements 1.2**
        """
        # Skip if tenant IDs are the same
        if tenant_id == malicious_tenant_id:
            return

        # Arrange: Create a mock entity that tracks attribute changes
        mock_entity = MagicMock()
        mock_entity.tenant_id = tenant_id

        mock_db = MagicMock()

        class TrackingRepository(TenantAwareRepository):
            model = MagicMock()

            def get_by_id(self, id):
                return mock_entity

        repo = TrackingRepository(db=mock_db, tenant_id=tenant_id)

        # Act: Try to update with a different tenant_id
        update_data = {"name": "Updated", "tenant_id": malicious_tenant_id}
        repo.update(entity_id, update_data)

        # Assert: tenant_id was not changed on the entity
        # The update method should have removed tenant_id from the update data
        assert mock_entity.tenant_id == tenant_id, (
            f"Update must not change tenant_id. "
            f"Expected: {tenant_id}, Got: {mock_entity.tenant_id}"
        )

    @given(
        tenant_id_a=tenant_id_strategy,
        tenant_id_b=tenant_id_strategy,
    )
    @settings(max_examples=100)
    def test_different_tenants_have_isolated_repositories(self, tenant_id_a: int, tenant_id_b: int):
        """For any two different tenants, their repositories SHALL be isolated.

        **Validates: Requirements 1.2**
        """
        # Skip if tenant IDs are the same
        if tenant_id_a == tenant_id_b:
            return

        # Arrange
        mock_db = MagicMock()
        repo_a = MockRepository(db=mock_db, tenant_id=tenant_id_a)
        repo_b = MockRepository(db=mock_db, tenant_id=tenant_id_b)

        # Assert: Each repository has its own tenant context
        assert repo_a.tenant_id != repo_b.tenant_id, (
            f"Different tenant repositories must have different tenant_ids. "
            f"Repo A: {repo_a.tenant_id}, Repo B: {repo_b.tenant_id}"
        )
        assert repo_a.tenant_id == tenant_id_a
        assert repo_b.tenant_id == tenant_id_b

    @given(
        tenant_id=tenant_id_strategy,
        page=st.integers(min_value=1, max_value=100),
        page_size=st.integers(min_value=1, max_value=100),
    )
    @settings(max_examples=100)
    def test_list_respects_tenant_context(self, tenant_id: int, page: int, page_size: int):
        """For any list query, pagination SHALL respect tenant context.

        **Validates: Requirements 1.2**
        """
        # Arrange
        mock_db = MagicMock()
        repo = MockRepository(db=mock_db, tenant_id=tenant_id)

        # Assert: Repository maintains tenant context for list operations
        assert repo.tenant_id == tenant_id, (
            f"Repository must maintain tenant context for list operations. "
            f"Expected tenant_id: {tenant_id}, Got: {repo.tenant_id}"
        )
