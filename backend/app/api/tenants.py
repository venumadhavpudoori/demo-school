"""Tenant management API endpoints for super admin."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import CurrentUserDep
from app.models.tenant import SubscriptionPlan, Tenant, TenantStatus
from app.models.user import User, UserRole
from app.models.student import Student
from app.models.teacher import Teacher


router = APIRouter(prefix="/api/admin/tenants", tags=["Admin - Tenants"])


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
class TenantListItem(BaseModel):
    """Tenant list item response."""
    id: int
    name: str
    slug: str
    domain: Optional[str]
    subscription_plan: str
    status: str
    created_at: datetime
    updated_at: Optional[datetime]
    user_count: int = 0
    student_count: int = 0
    teacher_count: int = 0


class TenantListResponse(BaseModel):
    """Paginated tenant list response."""
    items: list[TenantListItem]
    total_count: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_previous: bool


class TenantDetailResponse(BaseModel):
    """Detailed tenant response with usage statistics."""
    id: int
    name: str
    slug: str
    domain: Optional[str]
    subscription_plan: str
    status: str
    settings: dict
    created_at: datetime
    updated_at: Optional[datetime]
    user_count: int = 0
    student_count: int = 0
    teacher_count: int = 0
    admin_count: int = 0
    active_user_count: int = 0


class TenantUpdateRequest(BaseModel):
    """Request model for updating tenant."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    domain: Optional[str] = Field(None, max_length=255)
    subscription_plan: Optional[str] = None
    status: Optional[str] = None
    settings: Optional[dict] = None


class TenantSettingsUpdate(BaseModel):
    """Request model for updating tenant settings."""
    settings: dict


@router.get(
    "",
    response_model=TenantListResponse,
)
async def list_tenants(
    request: Request,
    current_user: CurrentUserDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    subscription_plan: Optional[str] = Query(None),
) -> TenantListResponse:
    """List all tenants with pagination and filtering.
    
    Super admin only endpoint.
    """
    require_super_admin(current_user)
    db = get_db(request)
    
    # Base query
    query = select(Tenant)
    count_query = select(func.count(Tenant.id))
    
    # Apply filters
    if search:
        search_filter = f"%{search}%"
        query = query.where(
            (Tenant.name.ilike(search_filter)) |
            (Tenant.slug.ilike(search_filter)) |
            (Tenant.domain.ilike(search_filter))
        )
        count_query = count_query.where(
            (Tenant.name.ilike(search_filter)) |
            (Tenant.slug.ilike(search_filter)) |
            (Tenant.domain.ilike(search_filter))
        )
    
    if status_filter:
        try:
            tenant_status = TenantStatus(status_filter)
            query = query.where(Tenant.status == tenant_status)
            count_query = count_query.where(Tenant.status == tenant_status)
        except ValueError:
            pass  # Invalid status, ignore filter
    
    if subscription_plan:
        try:
            plan = SubscriptionPlan(subscription_plan)
            query = query.where(Tenant.subscription_plan == plan)
            count_query = count_query.where(Tenant.subscription_plan == plan)
        except ValueError:
            pass  # Invalid plan, ignore filter
    
    # Get total count
    total_count = db.execute(count_query).scalar() or 0
    
    # Calculate pagination
    total_pages = (total_count + page_size - 1) // page_size if total_count > 0 else 1
    offset = (page - 1) * page_size
    
    # Apply pagination and ordering
    query = query.order_by(Tenant.created_at.desc()).offset(offset).limit(page_size)
    
    # Execute query
    tenants = db.execute(query).scalars().all()
    
    # Get counts for each tenant
    items = []
    for tenant in tenants:
        user_count = db.execute(
            select(func.count(User.id)).where(User.tenant_id == tenant.id)
        ).scalar() or 0
        
        student_count = db.execute(
            select(func.count(Student.id)).where(Student.tenant_id == tenant.id)
        ).scalar() or 0
        
        teacher_count = db.execute(
            select(func.count(Teacher.id)).where(Teacher.tenant_id == tenant.id)
        ).scalar() or 0
        
        items.append(TenantListItem(
            id=tenant.id,
            name=tenant.name,
            slug=tenant.slug,
            domain=tenant.domain,
            subscription_plan=tenant.subscription_plan.value,
            status=tenant.status.value,
            created_at=tenant.created_at,
            updated_at=tenant.updated_at,
            user_count=user_count,
            student_count=student_count,
            teacher_count=teacher_count,
        ))
    
    return TenantListResponse(
        items=items,
        total_count=total_count,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_previous=page > 1,
    )


@router.get(
    "/{tenant_id}",
    response_model=TenantDetailResponse,
)
async def get_tenant(
    request: Request,
    tenant_id: int,
    current_user: CurrentUserDep,
) -> TenantDetailResponse:
    """Get detailed tenant information with usage statistics.
    
    Super admin only endpoint.
    """
    require_super_admin(current_user)
    db = get_db(request)
    
    # Get tenant
    tenant = db.execute(
        select(Tenant).where(Tenant.id == tenant_id)
    ).scalar_one_or_none()
    
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "TENANT_NOT_FOUND",
                    "message": f"Tenant with ID {tenant_id} not found",
                }
            },
        )
    
    # Get counts
    user_count = db.execute(
        select(func.count(User.id)).where(User.tenant_id == tenant.id)
    ).scalar() or 0
    
    student_count = db.execute(
        select(func.count(Student.id)).where(Student.tenant_id == tenant.id)
    ).scalar() or 0
    
    teacher_count = db.execute(
        select(func.count(Teacher.id)).where(Teacher.tenant_id == tenant.id)
    ).scalar() or 0
    
    admin_count = db.execute(
        select(func.count(User.id)).where(
            User.tenant_id == tenant.id,
            User.role == UserRole.ADMIN
        )
    ).scalar() or 0
    
    active_user_count = db.execute(
        select(func.count(User.id)).where(
            User.tenant_id == tenant.id,
            User.is_active == True
        )
    ).scalar() or 0
    
    return TenantDetailResponse(
        id=tenant.id,
        name=tenant.name,
        slug=tenant.slug,
        domain=tenant.domain,
        subscription_plan=tenant.subscription_plan.value,
        status=tenant.status.value,
        settings=tenant.settings,
        created_at=tenant.created_at,
        updated_at=tenant.updated_at,
        user_count=user_count,
        student_count=student_count,
        teacher_count=teacher_count,
        admin_count=admin_count,
        active_user_count=active_user_count,
    )


@router.put(
    "/{tenant_id}",
    response_model=TenantDetailResponse,
)
async def update_tenant(
    request: Request,
    tenant_id: int,
    data: TenantUpdateRequest,
    current_user: CurrentUserDep,
) -> TenantDetailResponse:
    """Update tenant information.
    
    Super admin only endpoint.
    """
    require_super_admin(current_user)
    db = get_db(request)
    
    # Get tenant
    tenant = db.execute(
        select(Tenant).where(Tenant.id == tenant_id)
    ).scalar_one_or_none()
    
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "TENANT_NOT_FOUND",
                    "message": f"Tenant with ID {tenant_id} not found",
                }
            },
        )
    
    # Update fields
    if data.name is not None:
        tenant.name = data.name
    
    if data.domain is not None:
        # Check for domain uniqueness
        if data.domain:
            existing = db.execute(
                select(Tenant).where(
                    Tenant.domain == data.domain,
                    Tenant.id != tenant_id
                )
            ).scalar_one_or_none()
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={
                        "error": {
                            "code": "DOMAIN_EXISTS",
                            "message": f"Domain '{data.domain}' is already in use",
                        }
                    },
                )
        tenant.domain = data.domain if data.domain else None
    
    if data.subscription_plan is not None:
        try:
            tenant.subscription_plan = SubscriptionPlan(data.subscription_plan)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": {
                        "code": "INVALID_PLAN",
                        "message": f"Invalid subscription plan: {data.subscription_plan}",
                    }
                },
            )
    
    if data.status is not None:
        try:
            tenant.status = TenantStatus(data.status)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": {
                        "code": "INVALID_STATUS",
                        "message": f"Invalid status: {data.status}",
                    }
                },
            )
    
    if data.settings is not None:
        tenant.settings = data.settings
    
    db.commit()
    db.refresh(tenant)
    
    # Get counts for response
    user_count = db.execute(
        select(func.count(User.id)).where(User.tenant_id == tenant.id)
    ).scalar() or 0
    
    student_count = db.execute(
        select(func.count(Student.id)).where(Student.tenant_id == tenant.id)
    ).scalar() or 0
    
    teacher_count = db.execute(
        select(func.count(Teacher.id)).where(Teacher.tenant_id == tenant.id)
    ).scalar() or 0
    
    admin_count = db.execute(
        select(func.count(User.id)).where(
            User.tenant_id == tenant.id,
            User.role == UserRole.ADMIN
        )
    ).scalar() or 0
    
    active_user_count = db.execute(
        select(func.count(User.id)).where(
            User.tenant_id == tenant.id,
            User.is_active == True
        )
    ).scalar() or 0
    
    return TenantDetailResponse(
        id=tenant.id,
        name=tenant.name,
        slug=tenant.slug,
        domain=tenant.domain,
        subscription_plan=tenant.subscription_plan.value,
        status=tenant.status.value,
        settings=tenant.settings,
        created_at=tenant.created_at,
        updated_at=tenant.updated_at,
        user_count=user_count,
        student_count=student_count,
        teacher_count=teacher_count,
        admin_count=admin_count,
        active_user_count=active_user_count,
    )


@router.patch(
    "/{tenant_id}/settings",
    response_model=TenantDetailResponse,
)
async def update_tenant_settings(
    request: Request,
    tenant_id: int,
    data: TenantSettingsUpdate,
    current_user: CurrentUserDep,
) -> TenantDetailResponse:
    """Update tenant settings only.
    
    Super admin only endpoint.
    """
    require_super_admin(current_user)
    db = get_db(request)
    
    # Get tenant
    tenant = db.execute(
        select(Tenant).where(Tenant.id == tenant_id)
    ).scalar_one_or_none()
    
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "TENANT_NOT_FOUND",
                    "message": f"Tenant with ID {tenant_id} not found",
                }
            },
        )
    
    # Merge settings
    current_settings = tenant.settings or {}
    current_settings.update(data.settings)
    tenant.settings = current_settings
    
    db.commit()
    db.refresh(tenant)
    
    # Get counts for response
    user_count = db.execute(
        select(func.count(User.id)).where(User.tenant_id == tenant.id)
    ).scalar() or 0
    
    student_count = db.execute(
        select(func.count(Student.id)).where(Student.tenant_id == tenant.id)
    ).scalar() or 0
    
    teacher_count = db.execute(
        select(func.count(Teacher.id)).where(Teacher.tenant_id == tenant.id)
    ).scalar() or 0
    
    admin_count = db.execute(
        select(func.count(User.id)).where(
            User.tenant_id == tenant.id,
            User.role == UserRole.ADMIN
        )
    ).scalar() or 0
    
    active_user_count = db.execute(
        select(func.count(User.id)).where(
            User.tenant_id == tenant.id,
            User.is_active == True
        )
    ).scalar() or 0
    
    return TenantDetailResponse(
        id=tenant.id,
        name=tenant.name,
        slug=tenant.slug,
        domain=tenant.domain,
        subscription_plan=tenant.subscription_plan.value,
        status=tenant.status.value,
        settings=tenant.settings,
        created_at=tenant.created_at,
        updated_at=tenant.updated_at,
        user_count=user_count,
        student_count=student_count,
        teacher_count=teacher_count,
        admin_count=admin_count,
        active_user_count=active_user_count,
    )
