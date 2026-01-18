"""Seed script to create default tenant and admin user."""

import bcrypt
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import get_settings
from app.models.base import Base
from app.models.tenant import Tenant, TenantStatus, SubscriptionPlan
from app.models.user import User, UserRole

# Import all models to register them
from app.models import (
    Tenant, User, Student, Teacher, Class, Section, Subject,
    Attendance, Exam, Grade, Fee, Timetable, Announcement,
    LeaveRequest, AuditLog
)
from app.models.teacher import TeacherStatus

settings = get_settings()

# Database setup
engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def seed_database():
    """Create default tenant and admin user."""
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    
    try:
        # Check if default tenant exists
        existing_tenant = db.query(Tenant).filter(Tenant.slug == "demo").first()
        
        if existing_tenant:
            print("Default tenant 'demo' already exists.")
            tenant = existing_tenant
        else:
            # Create default tenant
            tenant = Tenant(
                name="Demo School",
                slug="demo",
                subscription_plan=SubscriptionPlan.PREMIUM,
                status=TenantStatus.ACTIVE,
                settings={},
            )
            db.add(tenant)
            db.flush()
            print("Created default tenant 'demo'.")
        
        # Create super admin user (platform-wide admin, no tenant)
        existing_super_admin = db.query(User).filter(
            User.email == "superadmin@eschool.com"
        ).first()
        
        if not existing_super_admin:
            super_admin_user = User(
                tenant_id=tenant.id,  # Super admin still needs a tenant for now
                email="superadmin@eschool.com",
                password_hash=hash_password("superadmin123"),
                role=UserRole.SUPER_ADMIN,
                profile_data={"name": "Super Admin"},
                is_active=True,
            )
            db.add(super_admin_user)
            print("Created super admin user.")
        else:
            print("Super admin user already exists.")
        
        # Create admin user
        existing_admin = db.query(User).filter(
            User.email == "admin@demo.com",
            User.tenant_id == tenant.id
        ).first()
        
        if not existing_admin:
            admin_user = User(
                tenant_id=tenant.id,
                email="admin@demo.com",
                password_hash=hash_password("admin123"),
                role=UserRole.ADMIN,
                profile_data={"name": "Admin User"},
                is_active=True,
            )
            db.add(admin_user)
            print("Created admin user.")
        else:
            print("Admin user already exists.")
        
        # Create a teacher user and teacher record
        existing_teacher = db.query(User).filter(
            User.email == "teacher@demo.com",
            User.tenant_id == tenant.id
        ).first()
        
        if not existing_teacher:
            teacher_user = User(
                tenant_id=tenant.id,
                email="teacher@demo.com",
                password_hash=hash_password("teacher123"),
                role=UserRole.TEACHER,
                profile_data={"first_name": "Demo", "last_name": "Teacher"},
                is_active=True,
            )
            db.add(teacher_user)
            db.flush()  # Get the user ID
            
            # Create corresponding Teacher record
            from datetime import date
            teacher_record = Teacher(
                tenant_id=tenant.id,
                user_id=teacher_user.id,
                employee_id="TCH001",
                subjects=["Mathematics", "Physics"],
                qualifications="M.Sc. Mathematics, B.Ed.",
                joining_date=date(2023, 1, 15),
                status=TeacherStatus.ACTIVE,
            )
            db.add(teacher_record)
            print("Created teacher user and teacher record.")
        else:
            # Check if teacher record exists
            existing_teacher_record = db.query(Teacher).filter(
                Teacher.user_id == existing_teacher.id
            ).first()
            if not existing_teacher_record:
                from datetime import date
                teacher_record = Teacher(
                    tenant_id=tenant.id,
                    user_id=existing_teacher.id,
                    employee_id="TCH001",
                    subjects=["Mathematics", "Physics"],
                    qualifications="M.Sc. Mathematics, B.Ed.",
                    joining_date=date(2023, 1, 15),
                    status=TeacherStatus.ACTIVE,
                )
                db.add(teacher_record)
                print("Created teacher record for existing teacher user.")
            else:
                print("Teacher user and record already exist.")
        
        # Create a second teacher for more options
        existing_teacher2 = db.query(User).filter(
            User.email == "teacher2@demo.com",
            User.tenant_id == tenant.id
        ).first()
        
        if not existing_teacher2:
            teacher_user2 = User(
                tenant_id=tenant.id,
                email="teacher2@demo.com",
                password_hash=hash_password("teacher123"),
                role=UserRole.TEACHER,
                profile_data={"first_name": "Jane", "last_name": "Smith"},
                is_active=True,
            )
            db.add(teacher_user2)
            db.flush()
            
            from datetime import date
            teacher_record2 = Teacher(
                tenant_id=tenant.id,
                user_id=teacher_user2.id,
                employee_id="TCH002",
                subjects=["English", "History"],
                qualifications="M.A. English Literature",
                joining_date=date(2023, 6, 1),
                status=TeacherStatus.ACTIVE,
            )
            db.add(teacher_record2)
            print("Created second teacher user and record.")
        else:
            print("Second teacher user already exists.")
        
        # Create a student user
        existing_student = db.query(User).filter(
            User.email == "student@demo.com",
            User.tenant_id == tenant.id
        ).first()
        
        if not existing_student:
            student_user = User(
                tenant_id=tenant.id,
                email="student@demo.com",
                password_hash=hash_password("student123"),
                role=UserRole.STUDENT,
                profile_data={"name": "Demo Student"},
                is_active=True,
            )
            db.add(student_user)
            print("Created student user.")
        else:
            print("Student user already exists.")
        
        # Create classes if they don't exist
        existing_classes = db.query(Class).filter(Class.tenant_id == tenant.id).all()
        
        if not existing_classes:
            # Get teacher records for assigning to subjects
            teacher1 = db.query(Teacher).filter(
                Teacher.tenant_id == tenant.id,
                Teacher.employee_id == "TCH001"
            ).first()
            teacher2 = db.query(Teacher).filter(
                Teacher.tenant_id == tenant.id,
                Teacher.employee_id == "TCH002"
            ).first()
            
            # Create classes
            classes_data = [
                {"name": "Class 1-A", "grade_level": 1, "academic_year": "2025-2026"},
                {"name": "Class 2-A", "grade_level": 2, "academic_year": "2025-2026"},
                {"name": "Class 3-A", "grade_level": 3, "academic_year": "2025-2026"},
                {"name": "Class 4-A", "grade_level": 4, "academic_year": "2025-2026"},
                {"name": "Class 5-A", "grade_level": 5, "academic_year": "2025-2026"},
            ]
            
            created_classes = []
            for cls_data in classes_data:
                new_class = Class(
                    tenant_id=tenant.id,
                    name=cls_data["name"],
                    grade_level=cls_data["grade_level"],
                    academic_year=cls_data["academic_year"],
                    class_teacher_id=teacher1.id if teacher1 else None,
                )
                db.add(new_class)
                created_classes.append(new_class)
            
            db.flush()  # Get class IDs
            
            # Create subjects for each class
            subjects_data = [
                {"name": "Mathematics", "code": "MATH", "credits": 4},
                {"name": "English", "code": "ENG", "credits": 4},
                {"name": "Science", "code": "SCI", "credits": 3},
                {"name": "Social Studies", "code": "SOC", "credits": 3},
                {"name": "Hindi", "code": "HIN", "credits": 3},
                {"name": "Computer Science", "code": "CS", "credits": 2},
            ]
            
            for cls in created_classes:
                for i, subj_data in enumerate(subjects_data):
                    # Alternate teachers for subjects
                    assigned_teacher = teacher1 if i % 2 == 0 else teacher2
                    subject = Subject(
                        tenant_id=tenant.id,
                        class_id=cls.id,
                        name=subj_data["name"],
                        code=f"{subj_data['code']}{cls.grade_level}",
                        credits=subj_data["credits"],
                        teacher_id=assigned_teacher.id if assigned_teacher else None,
                    )
                    db.add(subject)
            
            print(f"Created {len(created_classes)} classes with subjects.")
        else:
            print(f"Classes already exist ({len(existing_classes)} found).")
            
            # Check if subjects exist for existing classes
            existing_subjects = db.query(Subject).filter(Subject.tenant_id == tenant.id).all()
            if not existing_subjects:
                # Get teacher records
                teacher1 = db.query(Teacher).filter(
                    Teacher.tenant_id == tenant.id,
                    Teacher.employee_id == "TCH001"
                ).first()
                teacher2 = db.query(Teacher).filter(
                    Teacher.tenant_id == tenant.id,
                    Teacher.employee_id == "TCH002"
                ).first()
                
                subjects_data = [
                    {"name": "Mathematics", "code": "MATH", "credits": 4},
                    {"name": "English", "code": "ENG", "credits": 4},
                    {"name": "Science", "code": "SCI", "credits": 3},
                    {"name": "Social Studies", "code": "SOC", "credits": 3},
                    {"name": "Hindi", "code": "HIN", "credits": 3},
                    {"name": "Computer Science", "code": "CS", "credits": 2},
                ]
                
                for cls in existing_classes:
                    for i, subj_data in enumerate(subjects_data):
                        assigned_teacher = teacher1 if i % 2 == 0 else teacher2
                        subject = Subject(
                            tenant_id=tenant.id,
                            class_id=cls.id,
                            name=subj_data["name"],
                            code=f"{subj_data['code']}{cls.grade_level}",
                            credits=subj_data["credits"],
                            teacher_id=assigned_teacher.id if assigned_teacher else None,
                        )
                        db.add(subject)
                
                print(f"Created subjects for {len(existing_classes)} existing classes.")
            else:
                print(f"Subjects already exist ({len(existing_subjects)} found).")
        
        db.commit()
        
        print("\nDatabase seeded successfully!")
        print("\n=== Login Credentials ===")
        print("Super Admin: superadmin@eschool.com / superadmin123")
        print("Admin:       admin@demo.com / admin123")
        print("Teacher 1:   teacher@demo.com / teacher123")
        print("Teacher 2:   teacher2@demo.com / teacher123")
        print("Student:     student@demo.com / student123")
        
    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
