"""Initial schema for School ERP multi-tenancy system.

Revision ID: initial_001
Revises: 
Create Date: 2024-12-26

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'initial_001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create tenants table (no tenant_id - this is the root table)
    op.create_table(
        'tenants',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('slug', sa.String(length=100), nullable=False),
        sa.Column('domain', sa.String(length=255), nullable=True),
        sa.Column('subscription_plan', sa.Enum('free', 'basic', 'standard', 'premium', 'enterprise', name='subscriptionplan'), nullable=False),
        sa.Column('status', sa.Enum('active', 'inactive', 'suspended', 'trial', name='tenantstatus'), nullable=False),
        sa.Column('settings', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('domain'),
        sa.UniqueConstraint('slug')
    )
    op.create_index(op.f('ix_tenants_slug'), 'tenants', ['slug'], unique=False)

    # Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('role', sa.Enum('super_admin', 'admin', 'teacher', 'student', 'parent', name='userrole'), nullable=False),
        sa.Column('profile_data', sa.JSON(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=False)
    op.create_index(op.f('ix_users_tenant_id'), 'users', ['tenant_id'], unique=False)


    # Create classes table (before teachers due to class_teacher relationship)
    op.create_table(
        'classes',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('grade_level', sa.Integer(), nullable=False),
        sa.Column('academic_year', sa.String(length=20), nullable=False),
        sa.Column('class_teacher_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_classes_tenant_id'), 'classes', ['tenant_id'], unique=False)

    # Create teachers table
    op.create_table(
        'teachers',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('employee_id', sa.String(length=50), nullable=False),
        sa.Column('subjects', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('classes_assigned', postgresql.ARRAY(sa.Integer()), nullable=True),
        sa.Column('qualifications', sa.Text(), nullable=True),
        sa.Column('joining_date', sa.Date(), nullable=False),
        sa.Column('status', sa.Enum('active', 'inactive', 'on_leave', 'resigned', name='teacherstatus'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_teachers_employee_id'), 'teachers', ['employee_id'], unique=False)
    op.create_index(op.f('ix_teachers_tenant_id'), 'teachers', ['tenant_id'], unique=False)

    # Add foreign key for class_teacher_id in classes table
    op.create_foreign_key('fk_classes_class_teacher_id', 'classes', 'teachers', ['class_teacher_id'], ['id'], ondelete='SET NULL')

    # Create sections table
    op.create_table(
        'sections',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('class_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=50), nullable=False),
        sa.Column('capacity', sa.Integer(), nullable=False),
        sa.Column('students_count', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['class_id'], ['classes.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_sections_tenant_id'), 'sections', ['tenant_id'], unique=False)

    # Create subjects table
    op.create_table(
        'subjects',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('code', sa.String(length=20), nullable=False),
        sa.Column('class_id', sa.Integer(), nullable=False),
        sa.Column('teacher_id', sa.Integer(), nullable=True),
        sa.Column('credits', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['class_id'], ['classes.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['teacher_id'], ['teachers.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_subjects_tenant_id'), 'subjects', ['tenant_id'], unique=False)

    # Create students table
    op.create_table(
        'students',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('admission_number', sa.String(length=50), nullable=False),
        sa.Column('class_id', sa.Integer(), nullable=True),
        sa.Column('section_id', sa.Integer(), nullable=True),
        sa.Column('roll_number', sa.Integer(), nullable=True),
        sa.Column('date_of_birth', sa.Date(), nullable=False),
        sa.Column('gender', sa.Enum('male', 'female', 'other', name='gender'), nullable=False),
        sa.Column('address', sa.Text(), nullable=True),
        sa.Column('parent_ids', postgresql.ARRAY(sa.Integer()), nullable=True),
        sa.Column('admission_date', sa.Date(), nullable=False),
        sa.Column('status', sa.Enum('active', 'inactive', 'graduated', 'transferred', 'deleted', name='studentstatus'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['class_id'], ['classes.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['section_id'], ['sections.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_students_admission_number'), 'students', ['admission_number'], unique=False)
    op.create_index(op.f('ix_students_tenant_id'), 'students', ['tenant_id'], unique=False)


    # Create attendances table
    op.create_table(
        'attendances',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('student_id', sa.Integer(), nullable=False),
        sa.Column('class_id', sa.Integer(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('status', sa.Enum('present', 'absent', 'late', 'half_day', 'excused', name='attendancestatus'), nullable=False),
        sa.Column('marked_by', sa.Integer(), nullable=True),
        sa.Column('remarks', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['class_id'], ['classes.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['marked_by'], ['teachers.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['student_id'], ['students.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_attendances_class_id'), 'attendances', ['class_id'], unique=False)
    op.create_index(op.f('ix_attendances_date'), 'attendances', ['date'], unique=False)
    op.create_index(op.f('ix_attendances_student_id'), 'attendances', ['student_id'], unique=False)
    op.create_index(op.f('ix_attendances_tenant_id'), 'attendances', ['tenant_id'], unique=False)

    # Create exams table
    op.create_table(
        'exams',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('exam_type', sa.Enum('unit_test', 'midterm', 'final', 'quarterly', 'half_yearly', 'annual', name='examtype'), nullable=False),
        sa.Column('class_id', sa.Integer(), nullable=False),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=False),
        sa.Column('academic_year', sa.String(length=20), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['class_id'], ['classes.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_exams_class_id'), 'exams', ['class_id'], unique=False)
    op.create_index(op.f('ix_exams_tenant_id'), 'exams', ['tenant_id'], unique=False)

    # Create grades table
    op.create_table(
        'grades',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('student_id', sa.Integer(), nullable=False),
        sa.Column('subject_id', sa.Integer(), nullable=False),
        sa.Column('exam_id', sa.Integer(), nullable=False),
        sa.Column('marks_obtained', sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column('max_marks', sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column('grade', sa.String(length=5), nullable=True),
        sa.Column('remarks', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['exam_id'], ['exams.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['student_id'], ['students.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['subject_id'], ['subjects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_grades_exam_id'), 'grades', ['exam_id'], unique=False)
    op.create_index(op.f('ix_grades_student_id'), 'grades', ['student_id'], unique=False)
    op.create_index(op.f('ix_grades_subject_id'), 'grades', ['subject_id'], unique=False)
    op.create_index(op.f('ix_grades_tenant_id'), 'grades', ['tenant_id'], unique=False)

    # Create fees table
    op.create_table(
        'fees',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('student_id', sa.Integer(), nullable=False),
        sa.Column('fee_type', sa.String(length=100), nullable=False),
        sa.Column('amount', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('due_date', sa.Date(), nullable=False),
        sa.Column('paid_amount', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('payment_date', sa.Date(), nullable=True),
        sa.Column('status', sa.Enum('pending', 'partial', 'paid', 'overdue', 'waived', name='feestatus'), nullable=False),
        sa.Column('academic_year', sa.String(length=20), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['student_id'], ['students.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_fees_due_date'), 'fees', ['due_date'], unique=False)
    op.create_index(op.f('ix_fees_student_id'), 'fees', ['student_id'], unique=False)
    op.create_index(op.f('ix_fees_tenant_id'), 'fees', ['tenant_id'], unique=False)


    # Create timetables table
    op.create_table(
        'timetables',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('class_id', sa.Integer(), nullable=False),
        sa.Column('section_id', sa.Integer(), nullable=True),
        sa.Column('day_of_week', sa.Integer(), nullable=False),
        sa.Column('period_number', sa.Integer(), nullable=False),
        sa.Column('subject_id', sa.Integer(), nullable=False),
        sa.Column('teacher_id', sa.Integer(), nullable=True),
        sa.Column('start_time', sa.Time(), nullable=False),
        sa.Column('end_time', sa.Time(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['class_id'], ['classes.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['section_id'], ['sections.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['subject_id'], ['subjects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['teacher_id'], ['teachers.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_timetables_class_id'), 'timetables', ['class_id'], unique=False)
    op.create_index(op.f('ix_timetables_section_id'), 'timetables', ['section_id'], unique=False)
    op.create_index(op.f('ix_timetables_tenant_id'), 'timetables', ['tenant_id'], unique=False)

    # Create announcements table
    op.create_table(
        'announcements',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('target_audience', sa.Enum('all', 'admin', 'teacher', 'student', 'parent', name='targetaudience'), nullable=False),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_announcements_tenant_id'), 'announcements', ['tenant_id'], unique=False)

    # Create leave_requests table
    op.create_table(
        'leave_requests',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('requester_id', sa.Integer(), nullable=False),
        sa.Column('requester_type', sa.Enum('teacher', 'student', name='requestertype'), nullable=False),
        sa.Column('from_date', sa.Date(), nullable=False),
        sa.Column('to_date', sa.Date(), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('status', sa.Enum('pending', 'approved', 'rejected', 'cancelled', name='leavestatus'), nullable=False),
        sa.Column('approved_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['approved_by'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['requester_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_leave_requests_tenant_id'), 'leave_requests', ['tenant_id'], unique=False)


def downgrade() -> None:
    # Drop tables in reverse order of creation
    op.drop_index(op.f('ix_leave_requests_tenant_id'), table_name='leave_requests')
    op.drop_table('leave_requests')
    
    op.drop_index(op.f('ix_announcements_tenant_id'), table_name='announcements')
    op.drop_table('announcements')
    
    op.drop_index(op.f('ix_timetables_tenant_id'), table_name='timetables')
    op.drop_index(op.f('ix_timetables_section_id'), table_name='timetables')
    op.drop_index(op.f('ix_timetables_class_id'), table_name='timetables')
    op.drop_table('timetables')
    
    op.drop_index(op.f('ix_fees_tenant_id'), table_name='fees')
    op.drop_index(op.f('ix_fees_student_id'), table_name='fees')
    op.drop_index(op.f('ix_fees_due_date'), table_name='fees')
    op.drop_table('fees')
    
    op.drop_index(op.f('ix_grades_tenant_id'), table_name='grades')
    op.drop_index(op.f('ix_grades_subject_id'), table_name='grades')
    op.drop_index(op.f('ix_grades_student_id'), table_name='grades')
    op.drop_index(op.f('ix_grades_exam_id'), table_name='grades')
    op.drop_table('grades')
    
    op.drop_index(op.f('ix_exams_tenant_id'), table_name='exams')
    op.drop_index(op.f('ix_exams_class_id'), table_name='exams')
    op.drop_table('exams')
    
    op.drop_index(op.f('ix_attendances_tenant_id'), table_name='attendances')
    op.drop_index(op.f('ix_attendances_student_id'), table_name='attendances')
    op.drop_index(op.f('ix_attendances_date'), table_name='attendances')
    op.drop_index(op.f('ix_attendances_class_id'), table_name='attendances')
    op.drop_table('attendances')
    
    op.drop_index(op.f('ix_students_tenant_id'), table_name='students')
    op.drop_index(op.f('ix_students_admission_number'), table_name='students')
    op.drop_table('students')
    
    op.drop_index(op.f('ix_subjects_tenant_id'), table_name='subjects')
    op.drop_table('subjects')
    
    op.drop_index(op.f('ix_sections_tenant_id'), table_name='sections')
    op.drop_table('sections')
    
    op.drop_constraint('fk_classes_class_teacher_id', 'classes', type_='foreignkey')
    
    op.drop_index(op.f('ix_teachers_tenant_id'), table_name='teachers')
    op.drop_index(op.f('ix_teachers_employee_id'), table_name='teachers')
    op.drop_table('teachers')
    
    op.drop_index(op.f('ix_classes_tenant_id'), table_name='classes')
    op.drop_table('classes')
    
    op.drop_index(op.f('ix_users_tenant_id'), table_name='users')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')
    
    op.drop_index(op.f('ix_tenants_slug'), table_name='tenants')
    op.drop_table('tenants')
    
    # Drop enum types
    op.execute('DROP TYPE IF EXISTS leavestatus')
    op.execute('DROP TYPE IF EXISTS requestertype')
    op.execute('DROP TYPE IF EXISTS targetaudience')
    op.execute('DROP TYPE IF EXISTS feestatus')
    op.execute('DROP TYPE IF EXISTS examtype')
    op.execute('DROP TYPE IF EXISTS attendancestatus')
    op.execute('DROP TYPE IF EXISTS studentstatus')
    op.execute('DROP TYPE IF EXISTS gender')
    op.execute('DROP TYPE IF EXISTS teacherstatus')
    op.execute('DROP TYPE IF EXISTS userrole')
    op.execute('DROP TYPE IF EXISTS tenantstatus')
    op.execute('DROP TYPE IF EXISTS subscriptionplan')
