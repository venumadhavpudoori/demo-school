"""Attendance API endpoints for attendance management.

This module provides REST API endpoints for attendance operations
including marking, listing, and reporting.
"""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.api.deps import ActiveUserDep
from app.models.attendance import AttendanceStatus
from app.schemas.attendance import (
    AttendanceListResponse,
    AttendanceReportResponse,
    AttendanceResponse,
    AttendanceUpdate,
    BulkAttendanceCreate,
    BulkAttendanceResponse,
)
from app.schemas.auth import ErrorResponse
from app.services.attendance_service import (
    AttendanceNotFoundError,
    AttendanceService,
    InvalidAttendanceDataError,
)

router = APIRouter(prefix="/api/attendance", tags=["Attendance"])


def get_db(request: Request) -> Session:
    """Get database session from request state."""
    if hasattr(request.state, "db"):
        return request.state.db
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Database session not available",
    )


def get_tenant_id(request: Request) -> int:
    """Get tenant ID from request state."""
    tenant_id = getattr(request.state, "tenant_id", None)
    if tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": "TENANT_REQUIRED",
                    "message": "Tenant context is required",
                }
            },
        )
    return tenant_id


def get_attendance_service(request: Request) -> AttendanceService:
    """Get AttendanceService instance with tenant context."""
    db = get_db(request)
    tenant_id = get_tenant_id(request)
    return AttendanceService(db, tenant_id)


@router.post(
    "/mark",
    response_model=BulkAttendanceResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        403: {"model": ErrorResponse, "description": "Permission denied"},
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
async def mark_bulk_attendance(
    request: Request,
    data: BulkAttendanceCreate,
    current_user: ActiveUserDep,
) -> BulkAttendanceResponse:
    """Mark attendance for multiple students in bulk.

    This endpoint allows teachers and admins to mark attendance for
    an entire class or section at once. If attendance already exists
    for a student on the given date, it will be updated.

    Args:
        request: The incoming request.
        data: Bulk attendance data.
        current_user: Current authenticated user.

    Returns:
        BulkAttendanceResponse with summary of marked attendance.

    Raises:
        HTTPException: If permission denied or validation error.
    """
    # Check permission - only admins and teachers can mark attendance
    if not (current_user.is_admin or current_user.is_teacher):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": {
                    "code": "PERMISSION_DENIED",
                    "message": "You don't have permission to mark attendance",
                }
            },
        )

    service = get_attendance_service(request)

    try:
        # Get teacher ID if current user is a teacher
        marked_by = None
        if current_user.is_teacher and hasattr(current_user, "teacher_id"):
            marked_by = current_user.teacher_id

        # Convert records to dict format
        records = [
            {
                "student_id": record.student_id,
                "status": record.status,
                "remarks": record.remarks,
            }
            for record in data.records
        ]

        result = service.bulk_mark_attendance(
            class_id=data.class_id,
            section_id=data.section_id,
            attendance_date=data.attendance_date,
            records=records,
            marked_by=marked_by,
        )

        return BulkAttendanceResponse(**result)

    except InvalidAttendanceDataError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error": {"code": e.code, "message": e.message}},
        )


@router.get(
    "",
    response_model=AttendanceListResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
    },
)
async def list_attendance(
    request: Request,
    current_user: ActiveUserDep,
    class_id: int | None = Query(None, description="Filter by class ID"),
    section_id: int | None = Query(None, description="Filter by section ID"),
    student_id: int | None = Query(None, description="Filter by student ID"),
    start_date: date | None = Query(None, description="Filter by start date"),
    end_date: date | None = Query(None, description="Filter by end date"),
    attendance_status: str | None = Query(
        None, alias="status", description="Filter by status"
    ),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
) -> AttendanceListResponse:
    """List attendance records with filtering and pagination.

    Args:
        request: The incoming request.
        current_user: Current authenticated user.
        class_id: Optional class ID filter.
        section_id: Optional section ID filter.
        student_id: Optional student ID filter.
        start_date: Optional start date filter.
        end_date: Optional end date filter.
        attendance_status: Optional status filter.
        page: Page number (1-indexed).
        page_size: Number of items per page.

    Returns:
        AttendanceListResponse with paginated attendance list.
    """
    service = get_attendance_service(request)

    # Convert status string to enum if provided
    status_enum = None
    if attendance_status:
        try:
            status_enum = AttendanceStatus(attendance_status)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": {
                        "code": "INVALID_STATUS",
                        "message": f"Invalid status value: {attendance_status}",
                    }
                },
            )

    result = service.list_attendance(
        class_id=class_id,
        section_id=section_id,
        student_id=student_id,
        start_date=start_date,
        end_date=end_date,
        status=status_enum,
        page=page,
        page_size=page_size,
    )

    return AttendanceListResponse(**result)


@router.get(
    "/report",
    response_model=AttendanceReportResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
    },
)
async def get_attendance_report(
    request: Request,
    current_user: ActiveUserDep,
    class_id: int | None = Query(None, description="Filter by class ID"),
    section_id: int | None = Query(None, description="Filter by section ID"),
    start_date: date | None = Query(None, description="Report start date"),
    end_date: date | None = Query(None, description="Report end date"),
) -> AttendanceReportResponse:
    """Get attendance report for a class or section.

    This endpoint generates a comprehensive attendance report including
    class-level summary and individual student summaries.

    Args:
        request: The incoming request.
        current_user: Current authenticated user.
        class_id: Optional class ID filter.
        section_id: Optional section ID filter.
        start_date: Optional start date for the report period.
        end_date: Optional end date for the report period.

    Returns:
        AttendanceReportResponse with comprehensive report data.
    """
    service = get_attendance_service(request)

    result = service.get_attendance_report(
        class_id=class_id,
        section_id=section_id,
        start_date=start_date,
        end_date=end_date,
    )

    return AttendanceReportResponse(**result)


@router.get(
    "/{attendance_id}",
    response_model=AttendanceResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        404: {"model": ErrorResponse, "description": "Attendance not found"},
    },
)
async def get_attendance(
    request: Request,
    attendance_id: int,
    current_user: ActiveUserDep,
) -> AttendanceResponse:
    """Get an attendance record by ID.

    Args:
        request: The incoming request.
        attendance_id: The attendance record ID.
        current_user: Current authenticated user.

    Returns:
        AttendanceResponse with attendance data.

    Raises:
        HTTPException: If attendance not found.
    """
    service = get_attendance_service(request)

    try:
        attendance = service.get_attendance(attendance_id)

        student_name = None
        if attendance.student and attendance.student.user:
            first_name = attendance.student.user.profile_data.get("first_name", "")
            last_name = attendance.student.user.profile_data.get("last_name", "")
            student_name = f"{first_name} {last_name}".strip() or None

        return AttendanceResponse(
            id=attendance.id,
            student_id=attendance.student_id,
            student_name=student_name,
            class_id=attendance.class_id,
            class_name=attendance.class_.name if attendance.class_ else None,
            date=attendance.date.isoformat(),
            status=attendance.status.value,
            remarks=attendance.remarks,
            marked_by=attendance.marked_by,
        )

    except AttendanceNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": e.code, "message": e.message}},
        )


@router.put(
    "/{attendance_id}",
    response_model=AttendanceResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        403: {"model": ErrorResponse, "description": "Permission denied"},
        404: {"model": ErrorResponse, "description": "Attendance not found"},
    },
)
async def update_attendance(
    request: Request,
    attendance_id: int,
    data: AttendanceUpdate,
    current_user: ActiveUserDep,
) -> AttendanceResponse:
    """Update an attendance record.

    Args:
        request: The incoming request.
        attendance_id: The attendance record ID.
        data: Attendance update data.
        current_user: Current authenticated user.

    Returns:
        AttendanceResponse with updated attendance data.

    Raises:
        HTTPException: If attendance not found or permission denied.
    """
    # Check permission - only admins and teachers can update attendance
    if not (current_user.is_admin or current_user.is_teacher):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": {
                    "code": "PERMISSION_DENIED",
                    "message": "You don't have permission to update attendance",
                }
            },
        )

    service = get_attendance_service(request)

    try:
        # Convert status string to enum if provided
        status_enum = None
        if data.status:
            status_enum = AttendanceStatus(data.status)

        attendance = service.update_attendance(
            attendance_id=attendance_id,
            status=status_enum,
            remarks=data.remarks,
        )

        student_name = None
        if attendance.student and attendance.student.user:
            first_name = attendance.student.user.profile_data.get("first_name", "")
            last_name = attendance.student.user.profile_data.get("last_name", "")
            student_name = f"{first_name} {last_name}".strip() or None

        return AttendanceResponse(
            id=attendance.id,
            student_id=attendance.student_id,
            student_name=student_name,
            class_id=attendance.class_id,
            class_name=attendance.class_.name if attendance.class_ else None,
            date=attendance.date.isoformat(),
            status=attendance.status.value,
            remarks=attendance.remarks,
            marked_by=attendance.marked_by,
        )

    except AttendanceNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": e.code, "message": e.message}},
        )


@router.delete(
    "/{attendance_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        403: {"model": ErrorResponse, "description": "Permission denied"},
        404: {"model": ErrorResponse, "description": "Attendance not found"},
    },
)
async def delete_attendance(
    request: Request,
    attendance_id: int,
    current_user: ActiveUserDep,
) -> None:
    """Delete an attendance record.

    Args:
        request: The incoming request.
        attendance_id: The attendance record ID.
        current_user: Current authenticated user.

    Raises:
        HTTPException: If attendance not found or permission denied.
    """
    # Check permission - only admins can delete attendance
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": {
                    "code": "PERMISSION_DENIED",
                    "message": "You don't have permission to delete attendance",
                }
            },
        )

    service = get_attendance_service(request)

    try:
        service.delete_attendance(attendance_id)
    except AttendanceNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": e.code, "message": e.message}},
        )
