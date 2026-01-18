"""Property-based tests for soft delete preservation.

**Feature: school-erp-multi-tenancy, Property 8: Soft Delete Preservation**
**Validates: Design - Property 8**

Property 8: Soft Delete Preservation
*For any* soft-deleted student record, the record SHALL remain in the database
with a deleted status, and historical data (attendance, grades, fees) SHALL remain accessible.
"""

from unittest.mock import MagicMock

from hypothesis import given, settings
from hypothesis import strategies as st

from app.models.student import StudentStatus
from app.repositories.base import TenantAwareRepository

# Strategy for valid tenant IDs (positive integers)
tenant_id_strategy = st.integers(min_value=1, max_value=1_000_000)

# Strategy for entity IDs
entity_id_strategy = st.integers(min_value=1, max_value=1_000_000)

# Strategy for number of historical records
historical_records_strategy = st.integers(min_value=0, max_value=20)


# Mock model class defined at module level to avoid scoping issues
class MockStudentModel:
    """Mock model for testing."""
    pass


class TestSoftDeletePreservation:
    """**Feature: school-erp-multi-tenancy, Property 8: Soft Delete Preservation**"""

    @given(
        tenant_id=tenant_id_strategy,
        student_id=entity_id_strategy,
    )
    @settings(max_examples=100)
    def test_soft_delete_sets_deleted_status(
        self, tenant_id: int, student_id: int
    ):
        """For any soft-deleted student, the status SHALL be set to 'deleted'.

        **Validates: Requirements 5.4**
        """
        # Arrange: Create a mock entity with status attribute
        mock_entity = MagicMock()
        mock_entity.id = student_id
        mock_entity.tenant_id = tenant_id
        mock_entity.status = StudentStatus.ACTIVE

        mock_db = MagicMock()

        class MockStudentRepository(TenantAwareRepository):
            model = MockStudentModel

            def get_by_id(self, id):
                return mock_entity

        repo = MockStudentRepository(db=mock_db, tenant_id=tenant_id)

        # Act: Perform soft delete
        result = repo.soft_delete(student_id)

        # Assert: The entity status was set to 'deleted' and entity remains
        assert result is True, "Soft delete should return True on success"
        assert mock_entity.status == "deleted", (
            f"Soft-deleted entity must have status='deleted'. "
            f"Got: {mock_entity.status}"
        )
        # Verify commit was called (entity persisted, not removed)
        mock_db.commit.assert_called_once()
        # Verify delete was NOT called (entity not removed from DB)
        mock_db.delete.assert_not_called()

    @given(
        tenant_id=tenant_id_strategy,
        student_id=entity_id_strategy,
    )
    @settings(max_examples=100)
    def test_soft_deleted_record_remains_in_database(
        self, tenant_id: int, student_id: int
    ):
        """For any soft-deleted student, the record SHALL remain in the database.

        **Validates: Requirements 5.4**
        """
        # Arrange: Create a mock entity
        mock_entity = MagicMock()
        mock_entity.id = student_id
        mock_entity.tenant_id = tenant_id
        mock_entity.status = StudentStatus.ACTIVE

        mock_db = MagicMock()

        class MockStudentRepository(TenantAwareRepository):
            model = MockStudentModel

            def get_by_id(self, id):
                return mock_entity

        repo = MockStudentRepository(db=mock_db, tenant_id=tenant_id)

        # Act: Perform soft delete
        repo.soft_delete(student_id)

        # Assert: Entity was NOT deleted from database
        mock_db.delete.assert_not_called()
        # Entity should still be retrievable (status changed, not removed)
        assert mock_entity.status == "deleted"

    @given(
        tenant_id=tenant_id_strategy,
        student_id=entity_id_strategy,
        num_attendance=historical_records_strategy,
        num_grades=historical_records_strategy,
        num_fees=historical_records_strategy,
    )
    @settings(max_examples=100)
    def test_historical_data_remains_accessible_after_soft_delete(
        self,
        tenant_id: int,
        student_id: int,
        num_attendance: int,
        num_grades: int,
        num_fees: int,
    ):
        """For any soft-deleted student, historical data SHALL remain accessible.

        **Validates: Requirements 5.4**
        """
        # Arrange: Create mock attendance, grades, and fees records
        attendance_records = [
            MagicMock(id=i, student_id=student_id, tenant_id=tenant_id)
            for i in range(num_attendance)
        ]
        grade_records = [
            MagicMock(id=i, student_id=student_id, tenant_id=tenant_id)
            for i in range(num_grades)
        ]
        fee_records = [
            MagicMock(id=i, student_id=student_id, tenant_id=tenant_id)
            for i in range(num_fees)
        ]

        # Create mock student with relationships
        mock_student = MagicMock()
        mock_student.id = student_id
        mock_student.tenant_id = tenant_id
        mock_student.status = StudentStatus.ACTIVE
        mock_student.attendances = attendance_records
        mock_student.grades = grade_records
        mock_student.fees = fee_records

        mock_db = MagicMock()

        class MockStudentRepository(TenantAwareRepository):
            model = MockStudentModel

            def get_by_id(self, id):
                return mock_student

        repo = MockStudentRepository(db=mock_db, tenant_id=tenant_id)

        # Act: Perform soft delete
        repo.soft_delete(student_id)

        # Assert: Historical data is still accessible
        assert mock_student.status == "deleted", "Student should be soft-deleted"
        assert len(mock_student.attendances) == num_attendance, (
            f"Attendance records should remain accessible. "
            f"Expected: {num_attendance}, Got: {len(mock_student.attendances)}"
        )
        assert len(mock_student.grades) == num_grades, (
            f"Grade records should remain accessible. "
            f"Expected: {num_grades}, Got: {len(mock_student.grades)}"
        )
        assert len(mock_student.fees) == num_fees, (
            f"Fee records should remain accessible. "
            f"Expected: {num_fees}, Got: {len(mock_student.fees)}"
        )

    @given(
        tenant_id=tenant_id_strategy,
        student_id=entity_id_strategy,
    )
    @settings(max_examples=100)
    def test_soft_delete_returns_false_for_nonexistent_entity(
        self, tenant_id: int, student_id: int
    ):
        """For any non-existent student ID, soft delete SHALL return False.

        **Validates: Requirements 5.4**
        """
        # Arrange
        mock_db = MagicMock()

        class MockStudentRepository(TenantAwareRepository):
            model = MockStudentModel

            def get_by_id(self, id):
                return None  # Entity not found

        repo = MockStudentRepository(db=mock_db, tenant_id=tenant_id)

        # Act
        result = repo.soft_delete(student_id)

        # Assert
        assert result is False, (
            "Soft delete should return False for non-existent entity"
        )
        mock_db.commit.assert_not_called()

    @given(
        tenant_id=tenant_id_strategy,
        student_id=entity_id_strategy,
        initial_status=st.sampled_from([
            StudentStatus.ACTIVE,
            StudentStatus.INACTIVE,
            StudentStatus.GRADUATED,
            StudentStatus.TRANSFERRED,
        ]),
    )
    @settings(max_examples=100)
    def test_soft_delete_works_from_any_non_deleted_status(
        self, tenant_id: int, student_id: int, initial_status: StudentStatus
    ):
        """For any student with non-deleted status, soft delete SHALL set status to 'deleted'.

        **Validates: Requirements 5.4**
        """
        # Arrange
        mock_entity = MagicMock()
        mock_entity.id = student_id
        mock_entity.tenant_id = tenant_id
        mock_entity.status = initial_status

        mock_db = MagicMock()

        class MockStudentRepository(TenantAwareRepository):
            model = MockStudentModel

            def get_by_id(self, id):
                return mock_entity

        repo = MockStudentRepository(db=mock_db, tenant_id=tenant_id)

        # Act
        result = repo.soft_delete(student_id)

        # Assert
        assert result is True, "Soft delete should succeed"
        assert mock_entity.status == "deleted", (
            f"Status should be 'deleted' regardless of initial status. "
            f"Initial: {initial_status}, Final: {mock_entity.status}"
        )

    @given(
        tenant_id=tenant_id_strategy,
        student_id=entity_id_strategy,
    )
    @settings(max_examples=100)
    def test_soft_delete_is_idempotent(
        self, tenant_id: int, student_id: int
    ):
        """For any already soft-deleted student, soft delete SHALL succeed without error.

        **Validates: Requirements 5.4**
        """
        # Arrange: Entity already has deleted status
        mock_entity = MagicMock()
        mock_entity.id = student_id
        mock_entity.tenant_id = tenant_id
        mock_entity.status = StudentStatus.DELETED

        mock_db = MagicMock()

        class MockStudentRepository(TenantAwareRepository):
            model = MockStudentModel

            def get_by_id(self, id):
                return mock_entity

        repo = MockStudentRepository(db=mock_db, tenant_id=tenant_id)

        # Act: Soft delete an already deleted entity
        result = repo.soft_delete(student_id)

        # Assert: Operation succeeds (idempotent)
        assert result is True, "Soft delete should be idempotent"
        assert mock_entity.status == "deleted", "Status should remain 'deleted'"

    @given(
        tenant_id=tenant_id_strategy,
        student_id=entity_id_strategy,
    )
    @settings(max_examples=100)
    def test_soft_delete_does_not_cascade_to_related_records(
        self, tenant_id: int, student_id: int
    ):
        """For any soft-deleted student, related records SHALL NOT be deleted.

        **Validates: Requirements 5.4**
        """
        # Arrange: Create mock related records with their own status
        attendance_record = MagicMock()
        attendance_record.id = 1
        attendance_record.student_id = student_id
        attendance_record.status = "present"

        grade_record = MagicMock()
        grade_record.id = 1
        grade_record.student_id = student_id

        fee_record = MagicMock()
        fee_record.id = 1
        fee_record.student_id = student_id
        fee_record.status = "pending"

        mock_student = MagicMock()
        mock_student.id = student_id
        mock_student.tenant_id = tenant_id
        mock_student.status = StudentStatus.ACTIVE
        mock_student.attendances = [attendance_record]
        mock_student.grades = [grade_record]
        mock_student.fees = [fee_record]

        mock_db = MagicMock()

        class MockStudentRepository(TenantAwareRepository):
            model = MockStudentModel

            def get_by_id(self, id):
                return mock_student

        repo = MockStudentRepository(db=mock_db, tenant_id=tenant_id)

        # Act
        repo.soft_delete(student_id)

        # Assert: Related records are unchanged
        assert mock_student.status == "deleted", "Student should be soft-deleted"
        assert attendance_record.status == "present", (
            "Attendance record status should be unchanged"
        )
        assert fee_record.status == "pending", (
            "Fee record status should be unchanged"
        )
        # Related records should still be accessible
        assert len(mock_student.attendances) == 1
        assert len(mock_student.grades) == 1
        assert len(mock_student.fees) == 1
