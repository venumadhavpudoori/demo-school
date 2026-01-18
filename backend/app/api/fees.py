"""Fee API endpoints for fee management.

This module provides REST API endpoints for fee operations
including creation, listing, payments, and reporting.
"""

from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.api.deps import ActiveUserDep
from app.models.fee import FeeStatus
from app.schemas.auth import ErrorResponse
from app.schemas.fee import (
    FeeCollectionReport,
    FeeCreate,
    FeeListResponse,
    FeeResponse,
    FeeUpdate,
    PaymentRecord,
    PaymentResponse,
    PendingFeeListResponse,
)
from app.services.fee_service import (
    FeeNotFoundError,
    FeeService,
    InvalidFeeDataError,
    InvalidPaymentError,
)

router = APIRouter(prefix="/api/fees", tags=["Fees"])


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


def get_fee_service(request: Request) -> FeeService:
    """Get FeeService instance with tenant context."""
    db = get_db(request)
    tenant_id = get_tenant_id(request)
    return FeeService(db, tenant_id)


@router.post(
    "",
    response_model=FeeResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        403: {"model": ErrorResponse, "description": "Permission denied"},
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
async def create_fee(
    request: Request,
    data: FeeCreate,
    current_user: ActiveUserDep,
) -> FeeResponse:
    """Create a new fee record.

    Only admins can create fee records.

    Args:
        request: The incoming request.
        data: Fee creation data.
        current_user: Current authenticated user.

    Returns:
        FeeResponse with created fee data.

    Raises:
        HTTPException: If permission denied or validation error.
    """
    # Check permission - only admins can create fees
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": {
                    "code": "PERMISSION_DENIED",
                    "message": "You don't have permission to create fees",
                }
            },
        )

    service = get_fee_service(request)

    try:
        fee = service.create_fee(
            student_id=data.student_id,
            fee_type=data.fee_type,
            amount=data.amount,
            due_date=data.due_date,
            academic_year=data.academic_year,
        )

        return FeeResponse(
            id=fee.id,
            student_id=fee.student_id,
            student_name=None,  # Will be populated if needed
            fee_type=fee.fee_type,
            amount=float(fee.amount),
            paid_amount=float(fee.paid_amount),
            remaining=float(fee.amount - fee.paid_amount),
            due_date=fee.due_date.isoformat(),
            payment_date=fee.payment_date.isoformat() if fee.payment_date else None,
            status=fee.status.value,
            academic_year=fee.academic_year,
        )

    except InvalidFeeDataError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error": {"code": e.code, "message": e.message}},
        )


@router.get(
    "",
    response_model=FeeListResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
    },
)
async def list_fees(
    request: Request,
    current_user: ActiveUserDep,
    student_id: int | None = Query(None, description="Filter by student ID"),
    fee_status: str | None = Query(None, alias="status", description="Filter by status"),
    fee_type: str | None = Query(None, description="Filter by fee type"),
    academic_year: str | None = Query(None, description="Filter by academic year"),
    due_date_start: date | None = Query(None, description="Filter by due date start"),
    due_date_end: date | None = Query(None, description="Filter by due date end"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
) -> FeeListResponse:
    """List fee records with filtering and pagination.

    Args:
        request: The incoming request.
        current_user: Current authenticated user.
        student_id: Optional student ID filter.
        fee_status: Optional status filter.
        fee_type: Optional fee type filter.
        academic_year: Optional academic year filter.
        due_date_start: Optional start date filter for due date.
        due_date_end: Optional end date filter for due date.
        page: Page number (1-indexed).
        page_size: Number of items per page.

    Returns:
        FeeListResponse with paginated fee list.
    """
    service = get_fee_service(request)

    # Convert status string to enum if provided
    status_enum = None
    if fee_status:
        try:
            status_enum = FeeStatus(fee_status)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": {
                        "code": "INVALID_STATUS",
                        "message": f"Invalid status value: {fee_status}",
                    }
                },
            )

    result = service.list_fees(
        student_id=student_id,
        status=status_enum,
        fee_type=fee_type,
        academic_year=academic_year,
        due_date_start=due_date_start,
        due_date_end=due_date_end,
        page=page,
        page_size=page_size,
    )

    return FeeListResponse(**result)


@router.get(
    "/pending",
    response_model=PendingFeeListResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
    },
)
async def get_pending_fees(
    request: Request,
    current_user: ActiveUserDep,
    student_id: int | None = Query(None, description="Filter by student ID"),
    academic_year: str | None = Query(None, description="Filter by academic year"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
) -> PendingFeeListResponse:
    """Get all pending, partial, and overdue fees.

    Args:
        request: The incoming request.
        current_user: Current authenticated user.
        student_id: Optional student ID filter.
        academic_year: Optional academic year filter.
        page: Page number (1-indexed).
        page_size: Number of items per page.

    Returns:
        PendingFeeListResponse with pending fees and total amount.
    """
    service = get_fee_service(request)

    result = service.get_pending_fees(
        student_id=student_id,
        academic_year=academic_year,
        page=page,
        page_size=page_size,
    )

    return PendingFeeListResponse(**result)


@router.get(
    "/report",
    response_model=FeeCollectionReport,
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        403: {"model": ErrorResponse, "description": "Permission denied"},
    },
)
async def get_fee_collection_report(
    request: Request,
    current_user: ActiveUserDep,
    academic_year: str | None = Query(None, description="Filter by academic year"),
    start_date: date | None = Query(None, description="Report start date"),
    end_date: date | None = Query(None, description="Report end date"),
) -> FeeCollectionReport:
    """Get fee collection report.

    Only admins can access fee collection reports.

    Args:
        request: The incoming request.
        current_user: Current authenticated user.
        academic_year: Optional academic year filter.
        start_date: Optional start date for the report period.
        end_date: Optional end date for the report period.

    Returns:
        FeeCollectionReport with comprehensive fee statistics.
    """
    # Check permission - only admins can view reports
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

    service = get_fee_service(request)

    result = service.get_fee_collection_report(
        academic_year=academic_year,
        start_date=start_date,
        end_date=end_date,
    )

    return FeeCollectionReport(**result)


@router.get(
    "/{fee_id}",
    response_model=FeeResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        404: {"model": ErrorResponse, "description": "Fee not found"},
    },
)
async def get_fee(
    request: Request,
    fee_id: int,
    current_user: ActiveUserDep,
) -> FeeResponse:
    """Get a fee record by ID.

    Args:
        request: The incoming request.
        fee_id: The fee record ID.
        current_user: Current authenticated user.

    Returns:
        FeeResponse with fee data.

    Raises:
        HTTPException: If fee not found.
    """
    service = get_fee_service(request)

    try:
        fee = service.get_fee(fee_id)

        student_name = None
        if fee.student and fee.student.user:
            first_name = fee.student.user.profile_data.get("first_name", "")
            last_name = fee.student.user.profile_data.get("last_name", "")
            student_name = f"{first_name} {last_name}".strip() or None

        return FeeResponse(
            id=fee.id,
            student_id=fee.student_id,
            student_name=student_name,
            fee_type=fee.fee_type,
            amount=float(fee.amount),
            paid_amount=float(fee.paid_amount),
            remaining=float(fee.amount - fee.paid_amount),
            due_date=fee.due_date.isoformat(),
            payment_date=fee.payment_date.isoformat() if fee.payment_date else None,
            status=fee.status.value,
            academic_year=fee.academic_year,
        )

    except FeeNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": e.code, "message": e.message}},
        )


@router.put(
    "/{fee_id}",
    response_model=FeeResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        403: {"model": ErrorResponse, "description": "Permission denied"},
        404: {"model": ErrorResponse, "description": "Fee not found"},
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
async def update_fee(
    request: Request,
    fee_id: int,
    data: FeeUpdate,
    current_user: ActiveUserDep,
) -> FeeResponse:
    """Update a fee record.

    Only admins can update fee records.

    Args:
        request: The incoming request.
        fee_id: The fee record ID.
        data: Fee update data.
        current_user: Current authenticated user.

    Returns:
        FeeResponse with updated fee data.

    Raises:
        HTTPException: If fee not found or permission denied.
    """
    # Check permission - only admins can update fees
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": {
                    "code": "PERMISSION_DENIED",
                    "message": "You don't have permission to update fees",
                }
            },
        )

    service = get_fee_service(request)

    try:
        # Convert status string to enum if provided
        status_enum = None
        if data.status:
            status_enum = FeeStatus(data.status)

        fee = service.update_fee(
            fee_id=fee_id,
            fee_type=data.fee_type,
            amount=data.amount,
            due_date=data.due_date,
            academic_year=data.academic_year,
            status=status_enum,
        )

        student_name = None
        if fee.student and fee.student.user:
            first_name = fee.student.user.profile_data.get("first_name", "")
            last_name = fee.student.user.profile_data.get("last_name", "")
            student_name = f"{first_name} {last_name}".strip() or None

        return FeeResponse(
            id=fee.id,
            student_id=fee.student_id,
            student_name=student_name,
            fee_type=fee.fee_type,
            amount=float(fee.amount),
            paid_amount=float(fee.paid_amount),
            remaining=float(fee.amount - fee.paid_amount),
            due_date=fee.due_date.isoformat(),
            payment_date=fee.payment_date.isoformat() if fee.payment_date else None,
            status=fee.status.value,
            academic_year=fee.academic_year,
        )

    except FeeNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": e.code, "message": e.message}},
        )
    except InvalidFeeDataError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error": {"code": e.code, "message": e.message}},
        )


@router.post(
    "/{fee_id}/payment",
    response_model=PaymentResponse,
    status_code=status.HTTP_200_OK,
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        403: {"model": ErrorResponse, "description": "Permission denied"},
        404: {"model": ErrorResponse, "description": "Fee not found"},
        422: {"model": ErrorResponse, "description": "Invalid payment"},
    },
)
async def record_payment(
    request: Request,
    fee_id: int,
    data: PaymentRecord,
    current_user: ActiveUserDep,
) -> PaymentResponse:
    """Record a payment for a fee.

    Updates the fee status based on the payment amount:
    - 'paid' if paid_amount >= amount
    - 'partial' if 0 < paid_amount < amount
    - 'pending' if paid_amount = 0

    Only admins can record payments.

    Args:
        request: The incoming request.
        fee_id: The fee record ID.
        data: Payment data.
        current_user: Current authenticated user.

    Returns:
        PaymentResponse with payment details and updated fee info.

    Raises:
        HTTPException: If fee not found, permission denied, or invalid payment.
    """
    # Check permission - only admins can record payments
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": {
                    "code": "PERMISSION_DENIED",
                    "message": "You don't have permission to record payments",
                }
            },
        )

    service = get_fee_service(request)

    try:
        result = service.record_payment(
            fee_id=fee_id,
            amount=data.amount,
            payment_method=data.payment_method,
            transaction_id=data.transaction_id,
            payment_date=data.payment_date,
        )

        return PaymentResponse(**result)

    except FeeNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": e.code, "message": e.message}},
        )
    except InvalidPaymentError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error": {"code": e.code, "message": e.message}},
        )


@router.delete(
    "/{fee_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        403: {"model": ErrorResponse, "description": "Permission denied"},
        404: {"model": ErrorResponse, "description": "Fee not found"},
    },
)
async def delete_fee(
    request: Request,
    fee_id: int,
    current_user: ActiveUserDep,
) -> None:
    """Delete a fee record.

    Only admins can delete fee records.

    Args:
        request: The incoming request.
        fee_id: The fee record ID.
        current_user: Current authenticated user.

    Raises:
        HTTPException: If fee not found or permission denied.
    """
    # Check permission - only admins can delete fees
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": {
                    "code": "PERMISSION_DENIED",
                    "message": "You don't have permission to delete fees",
                }
            },
        )

    service = get_fee_service(request)

    try:
        service.delete_fee(fee_id)
    except FeeNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": e.code, "message": e.message}},
        )
