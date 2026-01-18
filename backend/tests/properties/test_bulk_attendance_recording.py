"""Property-based tests for bulk attendance recording.

**Feature: school-erp-multi-tenancy, Property 9: Bulk Attendance Recording**
**Validates: Design - Property 9**

Property 9: Bulk Attendance Recording
*For any* bulk attendance marking operation with N student records, exactly N attendance
records SHALL be created with correct student_id, status, date, and marked_by fields.
"""

from datetime import date, timedelta
from unittest.mock import MagicMock, patch

from hypothesis import given, settings, assume
from hypothesis import strategies as st

from app.models.attendance import AttendanceStatus


# Strategy for valid tenant IDs
tenant_id_strategy = st.integers(min_value=1, max_value=1_000_000)

# Strategy for valid class IDs
class_id_strategy = st.integers(min_value=1, max_value=1_000_000)

# Strategy for valid section IDs (optional)
section_id_strategy = st.one_of(st.none(), st.integers(min_value=1, max_value=1_000_000))

# Strategy for valid student IDs
student_id_strategy = st.integers(min_value=1, max_value=1_000_000)

# Strategy for valid teacher IDs (marked_by)
teacher_id_strategy = st.one_of(st.none(), st.integers(min_value=1, max_value=1_000_000))

# Strategy for attendance status
attendance_status_strategy = st.sampled_from([
    AttendanceStatus.PRESENT,
    AttendanceStatus.ABSENT,
    AttendanceStatus.LATE,
    AttendanceStatus.HALF_DAY,
    AttendanceStatus.EXCUSED,
])

# Strategy for attendance date (within reasonable range)
attendance_date_strategy = st.dates(
    min_value=date(2020, 1, 1),
    max_value=date(2030, 12, 31),
)

# Strategy for optional remarks
remarks_strategy = st.one_of(
    st.none(),
    st.text(
        alphabet=st.characters(whitelist_categories=("L", "N", "Zs", "P")),
        min_size=0,
        max_size=100,
    ),
)

# Strategy for a single attendance record
attendance_record_strategy = st.fixed_dictionaries({
    "student_id": student_id_strategy,
    "status": attendance_status_strategy,
    "remarks": remarks_strategy,
})


def unique_student_records(records: list[dict]) -> list[dict]:
    """Filter records to have unique student_ids."""
    seen = set()
    unique = []
    for record in records:
        if record["student_id"] not in seen:
            seen.add(record["student_id"])
            unique.append(record)
    return unique


# Strategy for list of attendance records with unique student IDs
attendance_records_strategy = st.lists(
    attendance_record_strategy,
    min_size=1,
    max_size=50,
).map(unique_student_records).filter(lambda x: len(x) >= 1)


class TestBulkAttendanceRecording:
    """**Feature: school-erp-multi-tenancy, Property 9: Bulk Attendance Recording**"""

    @given(
        tenant_id=tenant_id_strategy,
        class_id=class_id_strategy,
        section_id=section_id_strategy,
        attendance_date=attendance_date_strategy,
        records=attendance_records_strategy,
        marked_by=teacher_id_strategy,
    )
    @settings(max_examples=100, deadline=None)
    def test_bulk_attendance_creates_exact_number_of_records(
        self,
        tenant_id: int,
        class_id: int,
        section_id: int | None,
        attendance_date: date,
        records: list[dict],
        marked_by: int | None,
    ):
        """For any bulk attendance operation with N records, exactly N attendance records SHALL be created.

        **Validates: Design - Property 9**
        """
        # Arrange: Create mock database and repository
        created_records = []
        
        class MockAttendance:
            _id_counter = 0
            
            def __init__(self, **kwargs):
                MockAttendance._id_counter += 1
                self.id = MockAttendance._id_counter
                self.tenant_id = kwargs.get("tenant_id")
                self.student_id = kwargs.get("student_id")
                self.class_id = kwargs.get("class_id")
                self.date = kwargs.get("date")
                self.status = kwargs.get("status")
                self.marked_by = kwargs.get("marked_by")
                self.remarks = kwargs.get("remarks")
                created_records.append(self)

        mock_db = MagicMock()
        mock_db.add = MagicMock()
        mock_db.commit = MagicMock()
        mock_db.refresh = MagicMock()

        # Mock the repository's get_by_student_and_date to return None (no existing records)
        with patch("app.repositories.attendance.AttendanceRepository.get_by_student_and_date", return_value=None):
            with patch("app.models.attendance.Attendance", MockAttendance):
                from app.repositories.attendance import AttendanceRepository
                
                # Create repository with mocked session
                repo = AttendanceRepository(db=mock_db, tenant_id=tenant_id)
                
                # Act: Perform bulk upsert
                result = repo.bulk_upsert(
                    class_id=class_id,
                    attendance_date=attendance_date,
                    records=records,
                    marked_by=marked_by,
                )

        # Assert: Exactly N records were created
        n = len(records)
        assert len(result) == n, (
            f"Bulk attendance must create exactly {n} records. "
            f"Got: {len(result)}"
        )

    @given(
        tenant_id=tenant_id_strategy,
        class_id=class_id_strategy,
        attendance_date=attendance_date_strategy,
        records=attendance_records_strategy,
        marked_by=teacher_id_strategy,
    )
    @settings(max_examples=100)
    def test_bulk_attendance_records_have_correct_student_ids(
        self,
        tenant_id: int,
        class_id: int,
        attendance_date: date,
        records: list[dict],
        marked_by: int | None,
    ):
        """For any bulk attendance operation, all records SHALL have correct student_id.

        **Validates: Design - Property 9**
        """
        # Arrange
        created_records = []
        
        class MockAttendance:
            _id_counter = 0
            
            def __init__(self, **kwargs):
                MockAttendance._id_counter += 1
                self.id = MockAttendance._id_counter
                self.tenant_id = kwargs.get("tenant_id")
                self.student_id = kwargs.get("student_id")
                self.class_id = kwargs.get("class_id")
                self.date = kwargs.get("date")
                self.status = kwargs.get("status")
                self.marked_by = kwargs.get("marked_by")
                self.remarks = kwargs.get("remarks")
                created_records.append(self)

        mock_db = MagicMock()
        mock_db.add = MagicMock()
        mock_db.commit = MagicMock()
        mock_db.refresh = MagicMock()

        with patch("app.repositories.attendance.AttendanceRepository.get_by_student_and_date", return_value=None):
            with patch("app.models.attendance.Attendance", MockAttendance):
                from app.repositories.attendance import AttendanceRepository
                
                repo = AttendanceRepository(db=mock_db, tenant_id=tenant_id)
                
                # Act
                result = repo.bulk_upsert(
                    class_id=class_id,
                    attendance_date=attendance_date,
                    records=records,
                    marked_by=marked_by,
                )

        # Assert: Each record has the correct student_id
        expected_student_ids = {r["student_id"] for r in records}
        actual_student_ids = {r.student_id for r in result}
        
        assert actual_student_ids == expected_student_ids, (
            f"All student_ids must match input records. "
            f"Expected: {expected_student_ids}, Got: {actual_student_ids}"
        )

    @given(
        tenant_id=tenant_id_strategy,
        class_id=class_id_strategy,
        attendance_date=attendance_date_strategy,
        records=attendance_records_strategy,
        marked_by=teacher_id_strategy,
    )
    @settings(max_examples=100)
    def test_bulk_attendance_records_have_correct_status(
        self,
        tenant_id: int,
        class_id: int,
        attendance_date: date,
        records: list[dict],
        marked_by: int | None,
    ):
        """For any bulk attendance operation, all records SHALL have correct status.

        **Validates: Design - Property 9**
        """
        # Arrange
        created_records = []
        
        class MockAttendance:
            _id_counter = 0
            
            def __init__(self, **kwargs):
                MockAttendance._id_counter += 1
                self.id = MockAttendance._id_counter
                self.tenant_id = kwargs.get("tenant_id")
                self.student_id = kwargs.get("student_id")
                self.class_id = kwargs.get("class_id")
                self.date = kwargs.get("date")
                self.status = kwargs.get("status")
                self.marked_by = kwargs.get("marked_by")
                self.remarks = kwargs.get("remarks")
                created_records.append(self)

        mock_db = MagicMock()
        mock_db.add = MagicMock()
        mock_db.commit = MagicMock()
        mock_db.refresh = MagicMock()

        with patch("app.repositories.attendance.AttendanceRepository.get_by_student_and_date", return_value=None):
            with patch("app.models.attendance.Attendance", MockAttendance):
                from app.repositories.attendance import AttendanceRepository
                
                repo = AttendanceRepository(db=mock_db, tenant_id=tenant_id)
                
                # Act
                result = repo.bulk_upsert(
                    class_id=class_id,
                    attendance_date=attendance_date,
                    records=records,
                    marked_by=marked_by,
                )

        # Assert: Each record has the correct status matching input
        input_status_map = {r["student_id"]: r["status"] for r in records}
        
        for attendance_record in result:
            expected_status = input_status_map[attendance_record.student_id]
            assert attendance_record.status == expected_status, (
                f"Record for student {attendance_record.student_id} must have status={expected_status}. "
                f"Got: {attendance_record.status}"
            )

    @given(
        tenant_id=tenant_id_strategy,
        class_id=class_id_strategy,
        attendance_date=attendance_date_strategy,
        records=attendance_records_strategy,
        marked_by=teacher_id_strategy,
    )
    @settings(max_examples=100)
    def test_bulk_attendance_records_have_correct_date(
        self,
        tenant_id: int,
        class_id: int,
        attendance_date: date,
        records: list[dict],
        marked_by: int | None,
    ):
        """For any bulk attendance operation, all records SHALL have correct date.

        **Validates: Design - Property 9**
        """
        # Arrange
        created_records = []
        
        class MockAttendance:
            _id_counter = 0
            
            def __init__(self, **kwargs):
                MockAttendance._id_counter += 1
                self.id = MockAttendance._id_counter
                self.tenant_id = kwargs.get("tenant_id")
                self.student_id = kwargs.get("student_id")
                self.class_id = kwargs.get("class_id")
                self.date = kwargs.get("date")
                self.status = kwargs.get("status")
                self.marked_by = kwargs.get("marked_by")
                self.remarks = kwargs.get("remarks")
                created_records.append(self)

        mock_db = MagicMock()
        mock_db.add = MagicMock()
        mock_db.commit = MagicMock()
        mock_db.refresh = MagicMock()

        with patch("app.repositories.attendance.AttendanceRepository.get_by_student_and_date", return_value=None):
            with patch("app.models.attendance.Attendance", MockAttendance):
                from app.repositories.attendance import AttendanceRepository
                
                repo = AttendanceRepository(db=mock_db, tenant_id=tenant_id)
                
                # Act
                result = repo.bulk_upsert(
                    class_id=class_id,
                    attendance_date=attendance_date,
                    records=records,
                    marked_by=marked_by,
                )

        # Assert: All records have the correct date
        for attendance_record in result:
            assert attendance_record.date == attendance_date, (
                f"All records must have date={attendance_date}. "
                f"Got: {attendance_record.date}"
            )

    @given(
        tenant_id=tenant_id_strategy,
        class_id=class_id_strategy,
        attendance_date=attendance_date_strategy,
        records=attendance_records_strategy,
        marked_by=st.integers(min_value=1, max_value=1_000_000),  # Non-None marked_by
    )
    @settings(max_examples=100)
    def test_bulk_attendance_records_have_correct_marked_by(
        self,
        tenant_id: int,
        class_id: int,
        attendance_date: date,
        records: list[dict],
        marked_by: int,
    ):
        """For any bulk attendance operation, all records SHALL have correct marked_by field.

        **Validates: Design - Property 9**
        """
        # Arrange
        created_records = []
        
        class MockAttendance:
            _id_counter = 0
            
            def __init__(self, **kwargs):
                MockAttendance._id_counter += 1
                self.id = MockAttendance._id_counter
                self.tenant_id = kwargs.get("tenant_id")
                self.student_id = kwargs.get("student_id")
                self.class_id = kwargs.get("class_id")
                self.date = kwargs.get("date")
                self.status = kwargs.get("status")
                self.marked_by = kwargs.get("marked_by")
                self.remarks = kwargs.get("remarks")
                created_records.append(self)

        mock_db = MagicMock()
        mock_db.add = MagicMock()
        mock_db.commit = MagicMock()
        mock_db.refresh = MagicMock()

        with patch("app.repositories.attendance.AttendanceRepository.get_by_student_and_date", return_value=None):
            with patch("app.models.attendance.Attendance", MockAttendance):
                from app.repositories.attendance import AttendanceRepository
                
                repo = AttendanceRepository(db=mock_db, tenant_id=tenant_id)
                
                # Act
                result = repo.bulk_upsert(
                    class_id=class_id,
                    attendance_date=attendance_date,
                    records=records,
                    marked_by=marked_by,
                )

        # Assert: All records have the correct marked_by
        for attendance_record in result:
            assert attendance_record.marked_by == marked_by, (
                f"All records must have marked_by={marked_by}. "
                f"Got: {attendance_record.marked_by}"
            )

    @given(
        tenant_id=tenant_id_strategy,
        class_id=class_id_strategy,
        attendance_date=attendance_date_strategy,
        records=attendance_records_strategy,
    )
    @settings(max_examples=100)
    def test_bulk_attendance_records_have_correct_tenant_id(
        self,
        tenant_id: int,
        class_id: int,
        attendance_date: date,
        records: list[dict],
    ):
        """For any bulk attendance operation, all records SHALL have correct tenant_id.

        **Validates: Design - Property 9**
        """
        # Arrange
        created_records = []
        
        class MockAttendance:
            _id_counter = 0
            
            def __init__(self, **kwargs):
                MockAttendance._id_counter += 1
                self.id = MockAttendance._id_counter
                self.tenant_id = kwargs.get("tenant_id")
                self.student_id = kwargs.get("student_id")
                self.class_id = kwargs.get("class_id")
                self.date = kwargs.get("date")
                self.status = kwargs.get("status")
                self.marked_by = kwargs.get("marked_by")
                self.remarks = kwargs.get("remarks")
                created_records.append(self)

        mock_db = MagicMock()
        mock_db.add = MagicMock()
        mock_db.commit = MagicMock()
        mock_db.refresh = MagicMock()

        with patch("app.repositories.attendance.AttendanceRepository.get_by_student_and_date", return_value=None):
            with patch("app.models.attendance.Attendance", MockAttendance):
                from app.repositories.attendance import AttendanceRepository
                
                repo = AttendanceRepository(db=mock_db, tenant_id=tenant_id)
                
                # Act
                result = repo.bulk_upsert(
                    class_id=class_id,
                    attendance_date=attendance_date,
                    records=records,
                    marked_by=None,
                )

        # Assert: All records have the correct tenant_id
        for attendance_record in result:
            assert attendance_record.tenant_id == tenant_id, (
                f"All records must have tenant_id={tenant_id}. "
                f"Got: {attendance_record.tenant_id}"
            )
