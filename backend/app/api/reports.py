"""Reports API endpoints for generating various reports.

This module provides REST API endpoints for report generation
including attendance summary, grade analysis, and fee collection reports.
"""

from datetime import date, datetime

from fastapi import APIRouter, HTTPException, Query, Request, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.api.deps import ActiveUserDep
from app.schemas.auth import ErrorResponse
from app.schemas.report import (
    AttendanceSummaryResponse,
    ComprehensiveReportResponse,
    ExportRequest,
    FeeCollectionResponse,
    GradeAnalysisResponse,
    PDFExportData,
)
from app.services.report_service import (
    InvalidReportParametersError,
    ReportService,
)

router = APIRouter(prefix="/api/reports", tags=["Reports"])


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


def get_report_service(request: Request) -> ReportService:
    """Get ReportService instance with tenant context."""
    db = get_db(request)
    tenant_id = get_tenant_id(request)
    return ReportService(db, tenant_id)


@router.get(
    "/attendance-summary",
    response_model=AttendanceSummaryResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        403: {"model": ErrorResponse, "description": "Permission denied"},
    },
)
async def get_attendance_summary(
    request: Request,
    current_user: ActiveUserDep,
    class_id: int | None = Query(None, description="Filter by class ID"),
    section_id: int | None = Query(None, description="Filter by section ID"),
    start_date: date | None = Query(None, description="Report start date"),
    end_date: date | None = Query(None, description="Report end date"),
    academic_year: str | None = Query(None, description="Academic year filter"),
) -> AttendanceSummaryResponse:
    """Get attendance summary report.

    Provides comprehensive attendance statistics including class-level
    and student-level summaries with attendance percentages and distribution.

    Only admins and teachers can access attendance reports.

    Args:
        request: The incoming request.
        current_user: Current authenticated user.
        class_id: Optional class ID filter.
        section_id: Optional section ID filter.
        start_date: Optional start date for the report period.
        end_date: Optional end date for the report period.
        academic_year: Optional academic year filter.

    Returns:
        AttendanceSummaryResponse with comprehensive attendance data.
    """
    # Check permission - only admins and teachers can view reports
    if not (current_user.is_admin or current_user.is_teacher):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": {
                    "code": "PERMISSION_DENIED",
                    "message": "You don't have permission to view attendance reports",
                }
            },
        )

    service = get_report_service(request)

    result = service.get_attendance_summary(
        class_id=class_id,
        section_id=section_id,
        start_date=start_date,
        end_date=end_date,
        academic_year=academic_year,
    )

    return AttendanceSummaryResponse(**result)


@router.get(
    "/grade-analysis",
    response_model=GradeAnalysisResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        403: {"model": ErrorResponse, "description": "Permission denied"},
    },
)
async def get_grade_analysis(
    request: Request,
    current_user: ActiveUserDep,
    class_id: int | None = Query(None, description="Filter by class ID"),
    exam_id: int | None = Query(None, description="Filter by exam ID"),
    subject_id: int | None = Query(None, description="Filter by subject ID"),
    academic_year: str | None = Query(None, description="Academic year filter"),
) -> GradeAnalysisResponse:
    """Get grade analysis report.

    Provides comprehensive grade statistics including class-level
    analytics, subject-wise breakdown, and student rankings.

    For detailed analytics with rankings, provide both class_id and exam_id.

    Only admins and teachers can access grade reports.

    Args:
        request: The incoming request.
        current_user: Current authenticated user.
        class_id: Optional class ID filter.
        exam_id: Optional exam ID filter.
        subject_id: Optional subject ID filter.
        academic_year: Optional academic year filter.

    Returns:
        GradeAnalysisResponse with comprehensive grade analysis data.
    """
    # Check permission - only admins and teachers can view reports
    if not (current_user.is_admin or current_user.is_teacher):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": {
                    "code": "PERMISSION_DENIED",
                    "message": "You don't have permission to view grade reports",
                }
            },
        )

    service = get_report_service(request)

    result = service.get_grade_analysis(
        class_id=class_id,
        exam_id=exam_id,
        subject_id=subject_id,
        academic_year=academic_year,
    )

    return GradeAnalysisResponse(**result)


@router.get(
    "/fee-collection",
    response_model=FeeCollectionResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        403: {"model": ErrorResponse, "description": "Permission denied"},
    },
)
async def get_fee_collection_report(
    request: Request,
    current_user: ActiveUserDep,
    academic_year: str | None = Query(None, description="Academic year filter"),
    start_date: date | None = Query(None, description="Report start date"),
    end_date: date | None = Query(None, description="Report end date"),
    fee_type: str | None = Query(None, description="Fee type filter"),
) -> FeeCollectionResponse:
    """Get fee collection report.

    Provides comprehensive fee collection statistics including
    total amounts, collection rates, breakdowns by fee type and status,
    and a list of defaulters.

    Only admins can access fee collection reports.

    Args:
        request: The incoming request.
        current_user: Current authenticated user.
        academic_year: Optional academic year filter.
        start_date: Optional start date for the report period.
        end_date: Optional end date for the report period.
        fee_type: Optional fee type filter.

    Returns:
        FeeCollectionResponse with comprehensive fee collection data.
    """
    # Check permission - only admins can view fee reports
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": {
                    "code": "PERMISSION_DENIED",
                    "message": "You don't have permission to view fee reports",
                }
            },
        )

    service = get_report_service(request)

    result = service.get_fee_collection_report(
        academic_year=academic_year,
        start_date=start_date,
        end_date=end_date,
        fee_type=fee_type,
    )

    return FeeCollectionResponse(**result)


@router.get(
    "/comprehensive",
    response_model=ComprehensiveReportResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        403: {"model": ErrorResponse, "description": "Permission denied"},
    },
)
async def get_comprehensive_report(
    request: Request,
    current_user: ActiveUserDep,
    class_id: int | None = Query(None, description="Filter by class ID"),
    academic_year: str | None = Query(None, description="Academic year filter"),
    start_date: date | None = Query(None, description="Report start date"),
    end_date: date | None = Query(None, description="Report end date"),
) -> ComprehensiveReportResponse:
    """Get comprehensive report combining attendance, grades, and fees.

    Provides a high-level overview of all key metrics in a single report.

    Only admins can access comprehensive reports.

    Args:
        request: The incoming request.
        current_user: Current authenticated user.
        class_id: Optional class ID filter.
        academic_year: Optional academic year filter.
        start_date: Optional start date for the report period.
        end_date: Optional end date for the report period.

    Returns:
        ComprehensiveReportResponse with combined report data.
    """
    # Check permission - only admins can view comprehensive reports
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": {
                    "code": "PERMISSION_DENIED",
                    "message": "You don't have permission to view comprehensive reports",
                }
            },
        )

    service = get_report_service(request)

    result = service.get_comprehensive_report(
        class_id=class_id,
        academic_year=academic_year,
        start_date=start_date,
        end_date=end_date,
    )

    return ComprehensiveReportResponse(**result)


@router.post(
    "/export",
    responses={
        200: {
            "description": "Export file",
            "content": {
                "text/csv": {},
                "application/json": {},
            },
        },
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        403: {"model": ErrorResponse, "description": "Permission denied"},
        422: {"model": ErrorResponse, "description": "Invalid parameters"},
    },
)
async def export_report(
    request: Request,
    data: ExportRequest,
    current_user: ActiveUserDep,
) -> Response:
    """Export a report in CSV or PDF format.

    Generates and returns the report in the requested format.
    For PDF format, returns structured JSON data suitable for PDF generation.

    Only admins can export reports.

    Args:
        request: The incoming request.
        data: Export request parameters.
        current_user: Current authenticated user.

    Returns:
        Response with CSV content or PDF data structure.
    """
    # Check permission - only admins can export reports
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": {
                    "code": "PERMISSION_DENIED",
                    "message": "You don't have permission to export reports",
                }
            },
        )

    service = get_report_service(request)

    # Parse dates if provided
    start_date = None
    end_date = None
    if data.start_date:
        try:
            start_date = datetime.strptime(data.start_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "error": {
                        "code": "INVALID_DATE_FORMAT",
                        "message": "start_date must be in YYYY-MM-DD format",
                    }
                },
            )
    if data.end_date:
        try:
            end_date = datetime.strptime(data.end_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "error": {
                        "code": "INVALID_DATE_FORMAT",
                        "message": "end_date must be in YYYY-MM-DD format",
                    }
                },
            )

    # Generate report data based on type
    if data.report_type == "attendance_summary":
        report_data = service.get_attendance_summary(
            class_id=data.class_id,
            section_id=data.section_id,
            start_date=start_date,
            end_date=end_date,
            academic_year=data.academic_year,
        )
    elif data.report_type == "grade_analysis":
        report_data = service.get_grade_analysis(
            class_id=data.class_id,
            exam_id=data.exam_id,
            subject_id=data.subject_id,
            academic_year=data.academic_year,
        )
    elif data.report_type == "fee_collection":
        report_data = service.get_fee_collection_report(
            academic_year=data.academic_year,
            start_date=start_date,
            end_date=end_date,
            fee_type=data.fee_type,
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": {
                    "code": "INVALID_REPORT_TYPE",
                    "message": f"Invalid report type: {data.report_type}",
                }
            },
        )

    # Export based on format
    if data.format == "csv":
        csv_content = service.export_to_csv(data.report_type, report_data)
        filename = f"{data.report_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
            },
        )
    elif data.format == "pdf":
        # Return structured data for PDF generation
        # The actual PDF generation would be handled by a frontend library
        # or a separate PDF generation service
        pdf_data = service.export_to_pdf_data(data.report_type, report_data)
        return Response(
            content=PDFExportData(**pdf_data).model_dump_json(),
            media_type="application/json",
            headers={
                "Content-Disposition": f'attachment; filename="{data.report_type}_report.json"',
            },
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": {
                    "code": "INVALID_FORMAT",
                    "message": f"Invalid export format: {data.format}",
                }
            },
        )
