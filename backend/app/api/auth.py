"""Authentication API endpoints for tenant registration, login, and token management."""

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import (
    ActiveUserDep,
    CurrentUserDep,
    get_auth_service,
)
from app.middleware.csrf import generate_csrf_token
from app.models.tenant import SubscriptionPlan, Tenant, TenantStatus
from app.models.user import User, UserRole
from app.schemas.auth import (
    CSRFTokenResponse,
    ErrorResponse,
    LoginRequest,
    LoginResponse,
    RefreshTokenRequest,
    RefreshTokenResponse,
    TenantRegisterRequest,
    TenantRegisterResponse,
    UserProfileResponse,
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


def get_db(request: Request) -> Session:
    """Get database session from request state.
    
    This is a placeholder that should be replaced with proper dependency injection.
    """
    if hasattr(request.state, "db"):
        return request.state.db
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Database session not available",
    )


@router.post(
    "/register",
    response_model=TenantRegisterResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        409: {"model": ErrorResponse, "description": "Tenant slug already exists"},
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
async def register_tenant(
    request: Request,
    data: TenantRegisterRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> TenantRegisterResponse:
    """Register a new tenant with an admin user.
    
    This endpoint creates a new tenant (school/organization) and its initial
    admin user. The admin user will have full access to manage the tenant.
    
    Args:
        request: The incoming request.
        data: Tenant registration data.
        auth_service: Authentication service instance.
        
    Returns:
        TenantRegisterResponse with tenant info and auth tokens.
        
    Raises:
        HTTPException: If tenant slug already exists.
    """
    db = get_db(request)
    
    try:
        # Check if slug already exists
        existing_tenant = db.execute(
            select(Tenant).where(Tenant.slug == data.slug)
        ).scalar_one_or_none()
        
        if existing_tenant:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "error": {
                        "code": "TENANT_EXISTS",
                        "message": f"Tenant with slug '{data.slug}' already exists",
                    }
                },
            )
        
        # Check if email already exists (globally)
        existing_user = db.execute(
            select(User).where(User.email == data.admin_email)
        ).scalar_one_or_none()
        
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "error": {
                        "code": "EMAIL_EXISTS",
                        "message": "A user with this email already exists",
                    }
                },
            )
        
        # Create tenant
        tenant = Tenant(
            name=data.name,
            slug=data.slug,
            subscription_plan=SubscriptionPlan.FREE,
            status=TenantStatus.TRIAL,
            settings={},
        )
        db.add(tenant)
        db.flush()  # Get tenant ID without committing
        
        # Create admin user
        password_hash = auth_service.hash_password(data.admin_password)
        admin_user = User(
            tenant_id=tenant.id,
            email=data.admin_email,
            password_hash=password_hash,
            role=UserRole.ADMIN,
            profile_data={},
            is_active=True,
        )
        db.add(admin_user)
        db.commit()
        db.refresh(tenant)
        db.refresh(admin_user)
        
        # Generate tokens
        access_token = auth_service.create_access_token(
            user_id=admin_user.id,
            tenant_id=tenant.id,
            role=admin_user.role.value,
        )
        refresh_token = auth_service.create_refresh_token(
            user_id=admin_user.id,
            tenant_id=tenant.id,
            role=admin_user.role.value,
        )
        
        return TenantRegisterResponse(
            id=tenant.id,
            name=tenant.name,
            slug=tenant.slug,
            status=tenant.status.value,
            subscription_plan=tenant.subscription_plan.value,
            admin_user_id=admin_user.id,
            access_token=access_token,
            refresh_token=refresh_token,
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": {
                    "code": "REGISTRATION_ERROR",
                    "message": f"Failed to register tenant: {str(e)}",
                }
            },
        )



@router.post(
    "/login",
    response_model=LoginResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Invalid credentials"},
        404: {"model": ErrorResponse, "description": "Tenant not found"},
    },
)
async def login(
    request: Request,
    data: LoginRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> LoginResponse:
    """Authenticate user and return access tokens.
    
    This endpoint validates user credentials within the tenant context
    and returns JWT tokens for authenticated access.
    
    Args:
        request: The incoming request (must have tenant context).
        data: Login credentials.
        auth_service: Authentication service instance.
        
    Returns:
        LoginResponse with access and refresh tokens.
        
    Raises:
        HTTPException: If credentials are invalid or tenant not found.
    """
    db = get_db(request)
    
    # Get tenant from request state (set by middleware)
    tenant_id = getattr(request.state, "tenant_id", None)
    
    # If no tenant context, try to find user by email and get their tenant
    if tenant_id is None:
        user = db.execute(
            select(User).where(
                User.email == data.email,
                User.is_active == True,
            )
        ).scalar_one_or_none()
    else:
        # Find user within tenant context
        user = db.execute(
            select(User).where(
                User.email == data.email,
                User.tenant_id == tenant_id,
                User.is_active == True,
            )
        ).scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "code": "AUTH_ERROR",
                    "message": "Invalid email or password",
                }
            },
        )
    
    # Verify password
    if not auth_service.verify_password(data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "code": "AUTH_ERROR",
                    "message": "Invalid email or password",
                }
            },
        )
    
    # Generate tokens
    access_token = auth_service.create_access_token(
        user_id=user.id,
        tenant_id=user.tenant_id,
        role=user.role.value,
    )
    refresh_token = auth_service.create_refresh_token(
        user_id=user.id,
        tenant_id=user.tenant_id,
        role=user.role.value,
    )
    
    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user_id=user.id,
        tenant_id=user.tenant_id,
        role=user.role.value,
    )


@router.post(
    "/refresh",
    response_model=RefreshTokenResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Invalid or expired refresh token"},
    },
)
async def refresh_token(
    request: Request,
    data: RefreshTokenRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> RefreshTokenResponse:
    """Refresh access token using a valid refresh token.
    
    This endpoint validates the refresh token and issues new access
    and refresh tokens.
    
    Args:
        request: The incoming request.
        data: Refresh token data.
        auth_service: Authentication service instance.
        
    Returns:
        RefreshTokenResponse with new tokens.
        
    Raises:
        HTTPException: If refresh token is invalid or expired.
    """
    db = get_db(request)
    
    # Verify refresh token
    payload = auth_service.verify_refresh_token(data.refresh_token)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "code": "INVALID_TOKEN",
                    "message": "Invalid or expired refresh token",
                }
            },
        )
    
    # Verify user still exists and is active
    user = db.execute(
        select(User).where(
            User.id == payload.user_id,
            User.tenant_id == payload.tenant_id,
            User.is_active == True,
        )
    ).scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "code": "USER_NOT_FOUND",
                    "message": "User not found or inactive",
                }
            },
        )
    
    # Generate new tokens
    new_access_token = auth_service.create_access_token(
        user_id=user.id,
        tenant_id=user.tenant_id,
        role=user.role.value,
    )
    new_refresh_token = auth_service.create_refresh_token(
        user_id=user.id,
        tenant_id=user.tenant_id,
        role=user.role.value,
    )
    
    return RefreshTokenResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
    )


@router.get(
    "/me",
    response_model=UserProfileResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        404: {"model": ErrorResponse, "description": "User not found"},
    },
)
async def get_current_user_profile(
    request: Request,
    current_user: CurrentUserDep,
) -> UserProfileResponse:
    """Get the current authenticated user's profile.
    
    This endpoint returns the profile information of the currently
    authenticated user based on their JWT token.
    
    Args:
        request: The incoming request.
        current_user: Current authenticated user from token.
        
    Returns:
        UserProfileResponse with user profile data.
        
    Raises:
        HTTPException: If user not found.
    """
    db = get_db(request)
    
    # Fetch full user from database
    user = db.execute(
        select(User).where(
            User.id == current_user.user_id,
            User.tenant_id == current_user.tenant_id,
        )
    ).scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "USER_NOT_FOUND",
                    "message": "User not found",
                }
            },
        )
    
    return UserProfileResponse(
        id=user.id,
        email=user.email,
        role=user.role.value,
        tenant_id=user.tenant_id,
        is_active=user.is_active,
        profile_data=user.profile_data,
        created_at=user.created_at,
    )


@router.get(
    "/csrf-token",
    response_model=CSRFTokenResponse,
)
async def get_csrf_token(response: Response) -> CSRFTokenResponse:
    """Get a CSRF token for form submissions.
    
    This endpoint generates a new CSRF token and sets it as a cookie.
    The token should be included in the X-CSRF-Token header or csrf_token
    form field for state-changing requests.
    
    Args:
        response: The response object to set the cookie on.
        
    Returns:
        CSRFTokenResponse with the CSRF token.
    """
    token = generate_csrf_token()
    
    # Set the token as a cookie
    response.set_cookie(
        key="csrf_token",
        value=token,
        max_age=3600,  # 1 hour
        httponly=False,  # Allow JavaScript access for header submission
        samesite="lax",
    )
    
    return CSRFTokenResponse(csrf_token=token)
