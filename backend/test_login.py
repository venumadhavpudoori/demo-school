"""Test login directly."""
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.config import get_settings
from app.models.user import User
from app.services.auth_service import AuthService

settings = get_settings()
engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

db = SessionLocal()
auth_service = AuthService()

email = "admin@demo.com"
password = "admin123"

# Find user
user = db.execute(
    select(User).where(
        User.email == email,
        User.is_active == True,
    )
).scalar_one_or_none()

if user:
    print(f"Found user: {user.email}")
    print(f"User tenant_id: {user.tenant_id}")
    print(f"User is_active: {user.is_active}")
    print(f"Password hash: {user.password_hash}")
    
    # Verify password
    result = auth_service.verify_password(password, user.password_hash)
    print(f"Password verification: {result}")
else:
    print("User not found")

db.close()
