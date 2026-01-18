"""Fee schemas for request/response validation.

This module provides Pydantic schemas for fee-related API operations
including creation, payments, and reporting.
"""

from datetime import date as date_type
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field


class FeeCreate(BaseModel):
    """Schema for creating a fee record."""

    student_id: int = Field(..., description="Student ID")
    fee_type: str = Field(..., min_length=1, max_length=100, description="Type of fee")
    amount: Decimal = Field(..., gt=0, description="Fee amount")
    due_date: date_type = Field(..., description="Due date for payment")
    academic_year: str = Field(
        ..., min_length=1, max_length=20, description="Academic year (e.g., 2024-2025)"
    )


class FeeUpdate(BaseModel):
    """Schema for updating a fee record."""

    fee_type: str | None = Field(
        None, min_length=1, max_length=100, description="Type of fee"
    )
    amount: Decimal | None = Field(None, gt=0, description="Fee amount")
    due_date: date_type | None = Field(None, description="Due date for payment")
    academic_year: str | None = Field(
        None, min_length=1, max_length=20, description="Academic year"
    )
    status: Literal["pending", "partial", "paid", "overdue", "waived"] | None = Field(
        None, description="Fee status"
    )


class PaymentRecord(BaseModel):
    """Schema for recording a payment."""

    amount: Decimal = Field(..., gt=0, description="Payment amount")
    payment_method: str | None = Field(
        None, max_length=50, description="Payment method (e.g., cash, card, bank transfer)"
    )
    transaction_id: str | None = Field(
        None, max_length=100, description="Transaction reference ID"
    )
    payment_date: date_type | None = Field(
        None, description="Date of payment (defaults to today)"
    )


class FeeResponse(BaseModel):
    """Schema for single fee record response."""

    id: int
    student_id: int
    student_name: str | None
    fee_type: str
    amount: float
    paid_amount: float
    remaining: float
    due_date: str
    payment_date: str | None
    status: str
    academic_year: str

    class Config:
        from_attributes = True


class FeeListItem(BaseModel):
    """Schema for fee in list responses."""

    id: int
    student_id: int
    student_name: str | None
    fee_type: str
    amount: float
    paid_amount: float
    remaining: float
    due_date: str
    payment_date: str | None
    status: str
    academic_year: str


class FeeListResponse(BaseModel):
    """Schema for paginated fee list response."""

    items: list[FeeListItem]
    total_count: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_previous: bool


class PendingFeeListResponse(BaseModel):
    """Schema for pending fees list response."""

    items: list[FeeListItem]
    total_pending_amount: float
    total_count: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_previous: bool


class PaymentResponse(BaseModel):
    """Schema for payment recording response."""

    fee_id: int
    student_id: int
    fee_type: str
    total_amount: float
    previous_paid: float
    payment_amount: float
    new_paid_amount: float
    remaining_balance: float
    previous_status: str
    new_status: str
    payment_date: str
    payment_method: str | None
    transaction_id: str | None


class FeeTypeSummary(BaseModel):
    """Schema for fee type summary in reports."""

    count: int
    total_amount: float
    collected: float
    pending: float


class FeeCollectionReport(BaseModel):
    """Schema for fee collection report response."""

    academic_year: str | None
    start_date: str | None
    end_date: str | None
    total_fees: int
    total_amount: float
    total_collected: float
    total_pending: float
    collection_percentage: float
    status_counts: dict[str, int]
    fee_type_summary: dict[str, FeeTypeSummary]


class StudentFeeSummary(BaseModel):
    """Schema for student fee summary."""

    total_fees: int
    total_amount: float
    total_paid: float
    total_pending: float
    pending_count: int
