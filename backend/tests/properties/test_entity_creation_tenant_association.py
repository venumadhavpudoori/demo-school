"""Property-based tests for entity creation tenant association.

**Feature: school-erp-multi-tenancy, Property 7: Entity Creation Tenant Association**
**Validates: Design - Property 7**

Property 7: Entity Creation Tenant Association
*For any* entity (student, teacher, class, section, exam, fee, announcement, leave request)
created within a tenant context, the created record SHALL have tenant_id set to the current tenant.
"""

from unittest.mock import MagicMock

from hypothesis import given, settings
from hypothesis import strategies as st

from app.models.base import TenantAwareBase
from app.repositories.base import TenantAwareRepository

# Strategy for valid tenant IDs (positive integers)
tenant_id_strategy = st.integers(min_value=1, max_value=1_000_000)

# Strategy for entity data fields
entity_name_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N", "Zs")),
    min_size=1,
    max_size=50,
).filter(lambda x: x.strip())

# Strategy for arbitrary entity data
entity_data_strategy = st.fixed_dictionaries({
    "name": entity_name_strategy,
}).map(lambda d: {k: v for k, v in d.items() if v})


class MockTenantEntity(TenantAwareBase):
    """Mock entity for testing tenant-aware creation."""

    __tablename__ = "mock_entities"
    __abstract__ = True

    id: int
    tenant_id: int
    name: str


class MockEntityRepository(TenantAwareRepository[MockTenantEntity]):
    """Concrete repository for testing entity creation."""

    model = MockTenantEntity


class TestEntityCreationTenantAssociation:
    """**Feature: school-erp-multi-tenancy, Property 7: Entity Creation Tenant Association**"""

    @given(
        tenant_id=tenant_id_strategy,
        entity_data=entity_data_strategy,
    )
    @settings(max_examples=100)
    def test_created_entity_has_correct_tenant_id(
        self, tenant_id: int, entity_data: dict
    ):
        """For any entity creation, the created record SHALL have tenant_id set to current tenant.

        **Validates: Requirements 5.1, 6.1, 7.1, 9.1, 10.1, 11.1, 12.1, 13.1**
        """
        # Arrange: Track what data is passed to the model constructor
        captured_tenant_id = None

        class CapturingModel:
            def __init__(self, **kwargs):
                nonlocal captured_tenant_id
                captured_tenant_id = kwargs.get("tenant_id")
                self.tenant_id = captured_tenant_id
                for key, value in kwargs.items():
                    setattr(self, key, value)

        class CapturingRepository(TenantAwareRepository):
            model = CapturingModel

        mock_db = MagicMock()
        repo = CapturingRepository(db=mock_db, tenant_id=tenant_id)

        # Act: Create an entity
        repo.create(entity_data)

        # Assert: The created entity has the correct tenant_id
        assert captured_tenant_id == tenant_id, (
            f"Created entity must have tenant_id={tenant_id}. "
            f"Got: {captured_tenant_id}"
        )

    @given(
        tenant_id=tenant_id_strategy,
        malicious_tenant_id=tenant_id_strategy,
        entity_data=entity_data_strategy,
    )
    @settings(max_examples=100)
    def test_entity_creation_overrides_provided_tenant_id(
        self, tenant_id: int, malicious_tenant_id: int, entity_data: dict
    ):
        """For any entity creation with a different tenant_id in data, the repository's tenant_id SHALL be used.

        **Validates: Requirements 5.1, 6.1, 7.1, 9.1, 10.1, 11.1, 12.1, 13.1**
        """
        # Skip if tenant IDs are the same (not a meaningful test case)
        if tenant_id == malicious_tenant_id:
            return

        # Arrange: Track what tenant_id is actually used
        captured_tenant_id = None

        class CapturingModel:
            def __init__(self, **kwargs):
                nonlocal captured_tenant_id
                captured_tenant_id = kwargs.get("tenant_id")
                self.tenant_id = captured_tenant_id
                for key, value in kwargs.items():
                    setattr(self, key, value)

        class CapturingRepository(TenantAwareRepository):
            model = CapturingModel

        mock_db = MagicMock()
        repo = CapturingRepository(db=mock_db, tenant_id=tenant_id)

        # Act: Try to create with a malicious tenant_id in the data
        malicious_data = {**entity_data, "tenant_id": malicious_tenant_id}
        repo.create(malicious_data)

        # Assert: The repository's tenant_id was used, not the malicious one
        assert captured_tenant_id == tenant_id, (
            f"Repository must override any provided tenant_id. "
            f"Expected: {tenant_id}, Got: {captured_tenant_id}"
        )

    @given(
        tenant_id=tenant_id_strategy,
    )
    @settings(max_examples=100)
    def test_entity_creation_with_empty_data_still_sets_tenant_id(
        self, tenant_id: int
    ):
        """For any entity creation even with minimal data, tenant_id SHALL be set.

        **Validates: Requirements 5.1, 6.1, 7.1, 9.1, 10.1, 11.1, 12.1, 13.1**
        """
        # Arrange
        captured_tenant_id = None

        class CapturingModel:
            def __init__(self, **kwargs):
                nonlocal captured_tenant_id
                captured_tenant_id = kwargs.get("tenant_id")
                self.tenant_id = captured_tenant_id
                for key, value in kwargs.items():
                    setattr(self, key, value)

        class CapturingRepository(TenantAwareRepository):
            model = CapturingModel

        mock_db = MagicMock()
        repo = CapturingRepository(db=mock_db, tenant_id=tenant_id)

        # Act: Create with empty data
        repo.create({})

        # Assert: tenant_id is still set
        assert captured_tenant_id == tenant_id, (
            f"Even with empty data, tenant_id must be set to {tenant_id}. "
            f"Got: {captured_tenant_id}"
        )

    @given(
        tenant_id=tenant_id_strategy,
        num_entities=st.integers(min_value=1, max_value=10),
    )
    @settings(max_examples=100)
    def test_multiple_entity_creations_all_have_same_tenant_id(
        self, tenant_id: int, num_entities: int
    ):
        """For any number of entities created in same tenant context, all SHALL have same tenant_id.

        **Validates: Requirements 5.1, 6.1, 7.1, 9.1, 10.1, 11.1, 12.1, 13.1**
        """
        # Arrange
        captured_tenant_ids = []

        class CapturingModel:
            def __init__(self, **kwargs):
                captured_tenant_ids.append(kwargs.get("tenant_id"))
                self.tenant_id = kwargs.get("tenant_id")
                for key, value in kwargs.items():
                    setattr(self, key, value)

        class CapturingRepository(TenantAwareRepository):
            model = CapturingModel

        mock_db = MagicMock()
        repo = CapturingRepository(db=mock_db, tenant_id=tenant_id)

        # Act: Create multiple entities
        for i in range(num_entities):
            repo.create({"name": f"Entity {i}"})

        # Assert: All created entities have the same tenant_id
        assert len(captured_tenant_ids) == num_entities, (
            f"Expected {num_entities} entities to be created. "
            f"Got: {len(captured_tenant_ids)}"
        )
        assert all(tid == tenant_id for tid in captured_tenant_ids), (
            f"All entities must have tenant_id={tenant_id}. "
            f"Got: {captured_tenant_ids}"
        )

    @given(
        tenant_id_a=tenant_id_strategy,
        tenant_id_b=tenant_id_strategy,
    )
    @settings(max_examples=100)
    def test_different_tenant_repositories_create_with_different_tenant_ids(
        self, tenant_id_a: int, tenant_id_b: int
    ):
        """For any two different tenant contexts, created entities SHALL have their respective tenant_ids.

        **Validates: Requirements 5.1, 6.1, 7.1, 9.1, 10.1, 11.1, 12.1, 13.1**
        """
        # Skip if tenant IDs are the same
        if tenant_id_a == tenant_id_b:
            return

        # Arrange
        captured_tenant_ids = {"a": None, "b": None}

        class CapturingModelA:
            def __init__(self, **kwargs):
                captured_tenant_ids["a"] = kwargs.get("tenant_id")
                self.tenant_id = kwargs.get("tenant_id")
                for key, value in kwargs.items():
                    setattr(self, key, value)

        class CapturingModelB:
            def __init__(self, **kwargs):
                captured_tenant_ids["b"] = kwargs.get("tenant_id")
                self.tenant_id = kwargs.get("tenant_id")
                for key, value in kwargs.items():
                    setattr(self, key, value)

        class CapturingRepositoryA(TenantAwareRepository):
            model = CapturingModelA

        class CapturingRepositoryB(TenantAwareRepository):
            model = CapturingModelB

        mock_db = MagicMock()
        repo_a = CapturingRepositoryA(db=mock_db, tenant_id=tenant_id_a)
        repo_b = CapturingRepositoryB(db=mock_db, tenant_id=tenant_id_b)

        # Act: Create entities in both tenant contexts
        repo_a.create({"name": "Entity A"})
        repo_b.create({"name": "Entity B"})

        # Assert: Each entity has its respective tenant_id
        assert captured_tenant_ids["a"] == tenant_id_a, (
            f"Entity A must have tenant_id={tenant_id_a}. "
            f"Got: {captured_tenant_ids['a']}"
        )
        assert captured_tenant_ids["b"] == tenant_id_b, (
            f"Entity B must have tenant_id={tenant_id_b}. "
            f"Got: {captured_tenant_ids['b']}"
        )
