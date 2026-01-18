"""Platform analytics API endpoints for super admin."""

from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select, and_, extract
from sqlalchemy.orm import Session

from app.api.deps import CurrentUserDep
from app.models.tenant import SubscriptionPlan, Tenant, TenantStatus
from app.models.user import User, UserRole
from app.models.student import Student
from app.models.teacher import Teacher
from app.models.fee import Fee, FeeStatus


router = APIRouter(prefix="/api/admin/analytics", tags=["Admin - Analytics"])


def get_db(request: Request) -> Session:
    """Get database session from request state."""
    if hasattr(request.state, "db"):
        return request.state.db
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Database session not available",
    )


def require_super_admin(current_user: CurrentUserDep) -> CurrentUserDep:
    """Verify that the current user is a super admin."""
    if current_user.role != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": {
                    "code": "PERMISSION_DENIED",
                    "message": "Super admin access required",
                }
            },
        )
    return current_user


# Response models
class PlatformOverview(BaseModel):
    """Platform overview statistics."""
    total_tenants: int
    active_tenants: int
    total_users: int
    total_students: int
    total_teachers: int
    total_revenue: float
    pending_revenue: float


class SubscriptionBreakdown(BaseModel):
    """Subscription plan breakdown."""
    plan: str
    count: int
    percentage: float


class GrowthMetric(BaseModel):
    """Growth metric for a time period."""
    period: str
    value: int
    previous_value: int
    growth_percentage: float


class TenantGrowthData(BaseModel):
    """Tenant growth data point."""
    month: str
    count: int


class UserGrowthData(BaseModel):
    """User growth data point."""
    month: str
    count: int


class RevenueData(BaseModel):
    """Revenue data point."""
    month: str
    amount: float


class PlatformAnalyticsResponse(BaseModel):
    """Complete platform analytics response."""
    overview: PlatformOverview
    subscription_breakdown: list[SubscriptionBreakdown]
    tenant_growth: GrowthMetric
    user_growth: GrowthMetric
    revenue_growth: GrowthMetric
    tenant_growth_chart: list[TenantGrowthData]
    user_growth_chart: list[UserGrowthData]
    revenue_chart: list[RevenueData]


class TenantStatusBreakdown(BaseModel):
    """Tenant status breakdown."""
    status: str
    count: int
    percentage: float


class TopTenant(BaseModel):
    """Top tenant by user count."""
    id: int
    name: str
    slug: str
    user_count: int
    student_count: int
    subscription_plan: str


class DetailedAnalyticsResponse(BaseModel):
    """Detailed analytics response."""
    tenant_status_breakdown: list[TenantStatusBreakdown]
    top_tenants_by_users: list[TopTenant]
    average_users_per_tenant: float
    average_students_per_tenant: float
    average_teachers_per_tenant: float


@router.get(
    "",
    response_model=PlatformAnalyticsResponse,
)
async def get_platform_analytics(
    request: Request,
    current_user: CurrentUserDep,
    months: int = Query(6, ge=1, le=12, description="Number of months for chart data"),
) -> PlatformAnalyticsResponse:
    """Get platform-wide analytics.
    
    Super admin only endpoint.
    """
    require_super_admin(current_user)
    db = get_db(request)
    
    now = datetime.utcnow()
    current_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    previous_month_start = (current_month_start - timedelta(days=1)).replace(day=1)
    
    # Overview statistics
    total_tenants = db.execute(select(func.count(Tenant.id))).scalar() or 0
    active_tenants = db.execute(
        select(func.count(Tenant.id)).where(Tenant.status == TenantStatus.ACTIVE)
    ).scalar() or 0
    total_users = db.execute(select(func.count(User.id))).scalar() or 0
    total_students = db.execute(select(func.count(Student.id))).scalar() or 0
    total_teachers = db.execute(select(func.count(Teacher.id))).scalar() or 0
    
    # Revenue calculations (from paid fees)
    total_revenue = db.execute(
        select(func.coalesce(func.sum(Fee.paid_amount), 0.0))
        .where(Fee.status.in_([FeeStatus.PAID, FeeStatus.PARTIAL]))
    ).scalar() or 0.0
    
    pending_revenue = db.execute(
        select(func.coalesce(func.sum(Fee.amount - Fee.paid_amount), 0.0))
        .where(Fee.status.in_([FeeStatus.PENDING, FeeStatus.PARTIAL, FeeStatus.OVERDUE]))
    ).scalar() or 0.0
    
    overview = PlatformOverview(
        total_tenants=total_tenants,
        active_tenants=active_tenants,
        total_users=total_users,
        total_students=total_students,
        total_teachers=total_teachers,
        total_revenue=float(total_revenue),
        pending_revenue=float(pending_revenue),
    )
    
    # Subscription breakdown
    subscription_counts = db.execute(
        select(Tenant.subscription_plan, func.count(Tenant.id))
        .group_by(Tenant.subscription_plan)
    ).all()
    
    subscription_breakdown = []
    for plan, count in subscription_counts:
        percentage = (count / total_tenants * 100) if total_tenants > 0 else 0
        subscription_breakdown.append(SubscriptionBreakdown(
            plan=plan.value,
            count=count,
            percentage=round(percentage, 1),
        ))
    
    # Growth metrics - Tenants
    current_month_tenants = db.execute(
        select(func.count(Tenant.id))
        .where(Tenant.created_at >= current_month_start)
    ).scalar() or 0
    
    previous_month_tenants = db.execute(
        select(func.count(Tenant.id))
        .where(and_(
            Tenant.created_at >= previous_month_start,
            Tenant.created_at < current_month_start
        ))
    ).scalar() or 0
    
    tenant_growth_pct = (
        ((current_month_tenants - previous_month_tenants) / previous_month_tenants * 100)
        if previous_month_tenants > 0 else 0
    )
    
    tenant_growth = GrowthMetric(
        period="This Month",
        value=current_month_tenants,
        previous_value=previous_month_tenants,
        growth_percentage=round(tenant_growth_pct, 1),
    )
    
    # Growth metrics - Users
    current_month_users = db.execute(
        select(func.count(User.id))
        .where(User.created_at >= current_month_start)
    ).scalar() or 0
    
    previous_month_users = db.execute(
        select(func.count(User.id))
        .where(and_(
            User.created_at >= previous_month_start,
            User.created_at < current_month_start
        ))
    ).scalar() or 0
    
    user_growth_pct = (
        ((current_month_users - previous_month_users) / previous_month_users * 100)
        if previous_month_users > 0 else 0
    )
    
    user_growth = GrowthMetric(
        period="This Month",
        value=current_month_users,
        previous_value=previous_month_users,
        growth_percentage=round(user_growth_pct, 1),
    )
    
    # Growth metrics - Revenue
    current_month_revenue = db.execute(
        select(func.coalesce(func.sum(Fee.paid_amount), 0.0))
        .where(and_(
            Fee.payment_date >= current_month_start,
            Fee.status.in_([FeeStatus.PAID, FeeStatus.PARTIAL])
        ))
    ).scalar() or 0.0
    
    previous_month_revenue = db.execute(
        select(func.coalesce(func.sum(Fee.paid_amount), 0.0))
        .where(and_(
            Fee.payment_date >= previous_month_start,
            Fee.payment_date < current_month_start,
            Fee.status.in_([FeeStatus.PAID, FeeStatus.PARTIAL])
        ))
    ).scalar() or 0.0
    
    revenue_growth_pct = (
        ((float(current_month_revenue) - float(previous_month_revenue)) / float(previous_month_revenue) * 100)
        if previous_month_revenue > 0 else 0
    )
    
    revenue_growth = GrowthMetric(
        period="This Month",
        value=int(current_month_revenue),
        previous_value=int(previous_month_revenue),
        growth_percentage=round(revenue_growth_pct, 1),
    )
    
    # Chart data - Tenant growth by month
    tenant_growth_chart = []
    for i in range(months - 1, -1, -1):
        month_start = (now - timedelta(days=30 * i)).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if i > 0:
            month_end = (now - timedelta(days=30 * (i - 1))).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        else:
            month_end = now
        
        count = db.execute(
            select(func.count(Tenant.id))
            .where(Tenant.created_at < month_end)
        ).scalar() or 0
        
        tenant_growth_chart.append(TenantGrowthData(
            month=month_start.strftime("%b %Y"),
            count=count,
        ))
    
    # Chart data - User growth by month
    user_growth_chart = []
    for i in range(months - 1, -1, -1):
        month_start = (now - timedelta(days=30 * i)).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if i > 0:
            month_end = (now - timedelta(days=30 * (i - 1))).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        else:
            month_end = now
        
        count = db.execute(
            select(func.count(User.id))
            .where(User.created_at < month_end)
        ).scalar() or 0
        
        user_growth_chart.append(UserGrowthData(
            month=month_start.strftime("%b %Y"),
            count=count,
        ))
    
    # Chart data - Revenue by month
    revenue_chart = []
    for i in range(months - 1, -1, -1):
        month_start = (now - timedelta(days=30 * i)).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if i > 0:
            month_end = (now - timedelta(days=30 * (i - 1))).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        else:
            month_end = now
        
        amount = db.execute(
            select(func.coalesce(func.sum(Fee.paid_amount), 0.0))
            .where(and_(
                Fee.payment_date >= month_start,
                Fee.payment_date < month_end,
                Fee.status.in_([FeeStatus.PAID, FeeStatus.PARTIAL])
            ))
        ).scalar() or 0.0
        
        revenue_chart.append(RevenueData(
            month=month_start.strftime("%b %Y"),
            amount=float(amount),
        ))
    
    return PlatformAnalyticsResponse(
        overview=overview,
        subscription_breakdown=subscription_breakdown,
        tenant_growth=tenant_growth,
        user_growth=user_growth,
        revenue_growth=revenue_growth,
        tenant_growth_chart=tenant_growth_chart,
        user_growth_chart=user_growth_chart,
        revenue_chart=revenue_chart,
    )


@router.get(
    "/detailed",
    response_model=DetailedAnalyticsResponse,
)
async def get_detailed_analytics(
    request: Request,
    current_user: CurrentUserDep,
    limit: int = Query(10, ge=1, le=50, description="Number of top tenants to return"),
) -> DetailedAnalyticsResponse:
    """Get detailed platform analytics.
    
    Super admin only endpoint.
    """
    require_super_admin(current_user)
    db = get_db(request)
    
    # Tenant status breakdown
    total_tenants = db.execute(select(func.count(Tenant.id))).scalar() or 0
    
    status_counts = db.execute(
        select(Tenant.status, func.count(Tenant.id))
        .group_by(Tenant.status)
    ).all()
    
    tenant_status_breakdown = []
    for tenant_status, count in status_counts:
        percentage = (count / total_tenants * 100) if total_tenants > 0 else 0
        tenant_status_breakdown.append(TenantStatusBreakdown(
            status=tenant_status.value,
            count=count,
            percentage=round(percentage, 1),
        ))
    
    # Top tenants by user count
    tenants = db.execute(select(Tenant)).scalars().all()
    
    tenant_stats = []
    for tenant in tenants:
        user_count = db.execute(
            select(func.count(User.id)).where(User.tenant_id == tenant.id)
        ).scalar() or 0
        
        student_count = db.execute(
            select(func.count(Student.id)).where(Student.tenant_id == tenant.id)
        ).scalar() or 0
        
        tenant_stats.append({
            "tenant": tenant,
            "user_count": user_count,
            "student_count": student_count,
        })
    
    # Sort by user count and take top N
    tenant_stats.sort(key=lambda x: x["user_count"], reverse=True)
    top_tenants = tenant_stats[:limit]
    
    top_tenants_by_users = [
        TopTenant(
            id=ts["tenant"].id,
            name=ts["tenant"].name,
            slug=ts["tenant"].slug,
            user_count=ts["user_count"],
            student_count=ts["student_count"],
            subscription_plan=ts["tenant"].subscription_plan.value,
        )
        for ts in top_tenants
    ]
    
    # Average metrics
    total_users = db.execute(select(func.count(User.id))).scalar() or 0
    total_students = db.execute(select(func.count(Student.id))).scalar() or 0
    total_teachers = db.execute(select(func.count(Teacher.id))).scalar() or 0
    
    avg_users = total_users / total_tenants if total_tenants > 0 else 0
    avg_students = total_students / total_tenants if total_tenants > 0 else 0
    avg_teachers = total_teachers / total_tenants if total_tenants > 0 else 0
    
    return DetailedAnalyticsResponse(
        tenant_status_breakdown=tenant_status_breakdown,
        top_tenants_by_users=top_tenants_by_users,
        average_users_per_tenant=round(avg_users, 1),
        average_students_per_tenant=round(avg_students, 1),
        average_teachers_per_tenant=round(avg_teachers, 1),
    )
