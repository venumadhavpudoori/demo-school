"""Background tasks for email and notification handling.

This module provides Celery tasks for sending bulk emails, announcements,
and fee reminders with proper tenant context isolation.
"""

import logging
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

from celery import shared_task
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.celery_app import celery_app
from app.config import get_settings

logger = logging.getLogger(__name__)


def get_db_session() -> Session:
    """Create a new database session for background tasks."""
    settings = get_settings()
    engine = create_engine(settings.database_url, pool_pre_ping=True)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()


class EmailSender:
    """Email sender utility class for background tasks."""

    def __init__(self, tenant_id: int):
        """Initialize email sender with tenant context.

        Args:
            tenant_id: The tenant ID for context and logging.
        """
        self.tenant_id = tenant_id
        self.settings = get_settings()

    def send_email(
        self,
        recipient: str,
        subject: str,
        body: str,
        html_body: str | None = None,
    ) -> bool:
        """Send a single email.

        Args:
            recipient: Email address of the recipient.
            subject: Email subject line.
            body: Plain text email body.
            html_body: Optional HTML email body.

        Returns:
            True if email was sent successfully, False otherwise.
        """
        try:
            # In production, this would use actual SMTP settings
            # For now, we log the email and simulate success
            logger.info(
                f"[Tenant {self.tenant_id}] Sending email to {recipient}: {subject}"
            )

            # Simulate email sending - in production, uncomment SMTP code below
            # msg = MIMEMultipart("alternative")
            # msg["Subject"] = subject
            # msg["From"] = self.settings.email_from
            # msg["To"] = recipient
            #
            # msg.attach(MIMEText(body, "plain"))
            # if html_body:
            #     msg.attach(MIMEText(html_body, "html"))
            #
            # with smtplib.SMTP(self.settings.smtp_host, self.settings.smtp_port) as server:
            #     server.starttls()
            #     server.login(self.settings.smtp_user, self.settings.smtp_password)
            #     server.sendmail(self.settings.email_from, recipient, msg.as_string())

            return True
        except Exception as e:
            logger.error(
                f"[Tenant {self.tenant_id}] Failed to send email to {recipient}: {e}"
            )
            return False


@celery_app.task(
    bind=True,
    name="app.tasks.notifications.send_bulk_email",
    max_retries=3,
    default_retry_delay=60,
)
def send_bulk_email(
    self,
    tenant_id: int,
    recipients: list[str],
    subject: str,
    body: str,
    html_body: str | None = None,
    template_id: str | None = None,
    template_data: dict[str, Any] | None = None,
    batch_size: int = 50,
) -> dict:
    """Send bulk email notifications with tenant context.

    This task sends emails to multiple recipients in batches, tracking progress
    and handling failures gracefully. It maintains tenant context throughout
    the operation for proper data isolation and logging.

    Args:
        tenant_id: The tenant ID for context and logging.
        recipients: List of email addresses to send to.
        subject: Email subject line.
        body: Plain text email body.
        html_body: Optional HTML email body.
        template_id: Optional email template ID for rendering.
        template_data: Optional data for template rendering.
        batch_size: Number of emails to send per batch (default 50).

    Returns:
        dict with status, counts, and any failed recipients.
    """
    total_recipients = len(recipients)
    sent_count = 0
    failed_count = 0
    failed_recipients: list[str] = []

    logger.info(
        f"[Tenant {tenant_id}] Starting bulk email task: {total_recipients} recipients"
    )

    # Update task state to show progress
    self.update_state(
        state="PROGRESS",
        meta={
            "progress": 0,
            "sent": 0,
            "failed": 0,
            "total": total_recipients,
        },
    )

    email_sender = EmailSender(tenant_id)

    # Process recipients in batches
    for i in range(0, total_recipients, batch_size):
        batch = recipients[i : i + batch_size]

        for recipient in batch:
            try:
                # Apply template if provided
                final_body = body
                final_html = html_body
                final_subject = subject

                if template_id and template_data:
                    # Simple template variable replacement
                    for key, value in template_data.items():
                        placeholder = f"{{{{{key}}}}}"
                        final_body = final_body.replace(placeholder, str(value))
                        final_subject = final_subject.replace(placeholder, str(value))
                        if final_html:
                            final_html = final_html.replace(placeholder, str(value))

                success = email_sender.send_email(
                    recipient=recipient,
                    subject=final_subject,
                    body=final_body,
                    html_body=final_html,
                )

                if success:
                    sent_count += 1
                else:
                    failed_count += 1
                    failed_recipients.append(recipient)

            except Exception as e:
                logger.error(
                    f"[Tenant {tenant_id}] Error sending to {recipient}: {e}"
                )
                failed_count += 1
                failed_recipients.append(recipient)

        # Update progress after each batch
        progress = int((i + len(batch)) / total_recipients * 100)
        self.update_state(
            state="PROGRESS",
            meta={
                "progress": progress,
                "sent": sent_count,
                "failed": failed_count,
                "total": total_recipients,
            },
        )

    logger.info(
        f"[Tenant {tenant_id}] Bulk email completed: {sent_count} sent, {failed_count} failed"
    )

    return {
        "status": "completed",
        "tenant_id": tenant_id,
        "total": total_recipients,
        "sent": sent_count,
        "failed": failed_count,
        "failed_recipients": failed_recipients[:100],  # Limit to first 100 failures
        "completed_at": datetime.utcnow().isoformat(),
    }


@celery_app.task(
    bind=True,
    name="app.tasks.notifications.send_announcement_notification",
    max_retries=3,
    default_retry_delay=60,
)
def send_announcement_notification(
    self,
    tenant_id: int,
    announcement_id: int,
    target_audience: str,
) -> dict:
    """Send notification for a new announcement.

    This task fetches the announcement details and sends notifications to
    all users matching the target audience within the tenant.

    Args:
        tenant_id: The tenant ID.
        announcement_id: The announcement ID to notify about.
        target_audience: Target audience (all, teachers, students, parents, admin).

    Returns:
        dict with notification status and recipient count.
    """
    logger.info(
        f"[Tenant {tenant_id}] Sending announcement notification: "
        f"announcement_id={announcement_id}, audience={target_audience}"
    )

    db = get_db_session()
    try:
        # Import models here to avoid circular imports
        from app.models.announcement import Announcement
        from app.models.user import User, UserRole

        # Fetch announcement
        announcement = db.execute(
            select(Announcement).where(
                Announcement.id == announcement_id,
                Announcement.tenant_id == tenant_id,
            )
        ).scalar_one_or_none()

        if not announcement:
            logger.warning(
                f"[Tenant {tenant_id}] Announcement {announcement_id} not found"
            )
            return {
                "status": "failed",
                "tenant_id": tenant_id,
                "announcement_id": announcement_id,
                "error": "Announcement not found",
            }

        # Determine target roles based on audience
        target_roles: list[UserRole] = []
        if target_audience == "all":
            target_roles = [
                UserRole.ADMIN,
                UserRole.TEACHER,
                UserRole.STUDENT,
                UserRole.PARENT,
            ]
        elif target_audience == "teachers":
            target_roles = [UserRole.TEACHER]
        elif target_audience == "students":
            target_roles = [UserRole.STUDENT]
        elif target_audience == "parents":
            target_roles = [UserRole.PARENT]
        elif target_audience == "admin":
            target_roles = [UserRole.ADMIN]

        # Fetch recipient emails
        users = db.execute(
            select(User).where(
                User.tenant_id == tenant_id,
                User.role.in_(target_roles),
                User.is_active == True,
            )
        ).scalars().all()

        recipients = [user.email for user in users]

        if not recipients:
            logger.info(
                f"[Tenant {tenant_id}] No recipients found for audience {target_audience}"
            )
            return {
                "status": "completed",
                "tenant_id": tenant_id,
                "announcement_id": announcement_id,
                "target_audience": target_audience,
                "recipients_notified": 0,
            }

        # Send bulk email
        subject = f"New Announcement: {announcement.title}"
        body = f"""
Hello,

A new announcement has been posted:

Title: {announcement.title}

{announcement.content}

---
This is an automated notification from the School ERP System.
        """.strip()

        result = send_bulk_email.delay(
            tenant_id=tenant_id,
            recipients=recipients,
            subject=subject,
            body=body,
        )

        return {
            "status": "completed",
            "tenant_id": tenant_id,
            "announcement_id": announcement_id,
            "target_audience": target_audience,
            "recipients_notified": len(recipients),
            "email_task_id": result.id,
            "completed_at": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(
            f"[Tenant {tenant_id}] Error sending announcement notification: {e}"
        )
        return {
            "status": "failed",
            "tenant_id": tenant_id,
            "announcement_id": announcement_id,
            "error": str(e),
        }
    finally:
        db.close()


@celery_app.task(
    bind=True,
    name="app.tasks.notifications.send_fee_reminder",
    max_retries=3,
    default_retry_delay=60,
)
def send_fee_reminder(
    self,
    tenant_id: int,
    student_ids: list[int] | None = None,
    days_before_due: int | None = None,
    include_overdue: bool = True,
) -> dict:
    """Send fee payment reminders to students/parents.

    This task fetches pending fees and sends reminder emails to students
    and their parents. It can target specific students or all students
    with pending fees.

    Args:
        tenant_id: The tenant ID.
        student_ids: Optional list of specific student IDs to remind.
        days_before_due: Optional filter for fees due within N days.
        include_overdue: Whether to include overdue fees (default True).

    Returns:
        dict with reminder status and statistics.
    """
    logger.info(
        f"[Tenant {tenant_id}] Starting fee reminder task: "
        f"student_ids={student_ids}, days_before_due={days_before_due}"
    )

    db = get_db_session()
    try:
        from datetime import date, timedelta

        from sqlalchemy import and_, or_

        from app.models.fee import Fee, FeeStatus
        from app.models.student import Student
        from app.models.user import User

        # Build fee query
        query = select(Fee).where(
            Fee.tenant_id == tenant_id,
            Fee.status.in_([FeeStatus.PENDING, FeeStatus.PARTIAL]),
        )

        if student_ids:
            query = query.where(Fee.student_id.in_(student_ids))

        if days_before_due is not None:
            due_date_threshold = date.today() + timedelta(days=days_before_due)
            if include_overdue:
                query = query.where(Fee.due_date <= due_date_threshold)
            else:
                query = query.where(
                    and_(
                        Fee.due_date <= due_date_threshold,
                        Fee.due_date >= date.today(),
                    )
                )
        elif not include_overdue:
            query = query.where(Fee.due_date >= date.today())

        fees = db.execute(query).scalars().all()

        if not fees:
            logger.info(f"[Tenant {tenant_id}] No pending fees found for reminders")
            return {
                "status": "completed",
                "tenant_id": tenant_id,
                "students_notified": 0,
                "fees_included": 0,
            }

        # Group fees by student
        student_fees: dict[int, list[Fee]] = {}
        for fee in fees:
            if fee.student_id not in student_fees:
                student_fees[fee.student_id] = []
            student_fees[fee.student_id].append(fee)

        # Fetch student and user information
        student_ids_to_notify = list(student_fees.keys())
        students = db.execute(
            select(Student)
            .where(
                Student.tenant_id == tenant_id,
                Student.id.in_(student_ids_to_notify),
            )
        ).scalars().all()

        student_map = {s.id: s for s in students}

        # Prepare and send reminders
        recipients_notified = 0
        total_fees = 0

        for student_id, fees_list in student_fees.items():
            student = student_map.get(student_id)
            if not student:
                continue

            # Get student's user email
            user = db.execute(
                select(User).where(User.id == student.user_id)
            ).scalar_one_or_none()

            if not user or not user.email:
                continue

            # Calculate total pending amount
            total_pending = sum(
                float(fee.amount) - float(fee.paid_amount) for fee in fees_list
            )

            # Build fee details
            fee_details = "\n".join(
                f"  - {fee.fee_type}: ${float(fee.amount) - float(fee.paid_amount):.2f} "
                f"(Due: {fee.due_date.isoformat()})"
                for fee in fees_list
            )

            # Prepare email
            subject = f"Fee Payment Reminder - ${total_pending:.2f} Pending"
            body = f"""
Dear Student/Parent,

This is a reminder that you have pending fee payments:

{fee_details}

Total Pending Amount: ${total_pending:.2f}

Please make the payment at your earliest convenience to avoid any late fees.

If you have already made the payment, please disregard this reminder.

---
This is an automated notification from the School ERP System.
            """.strip()

            # Send email
            email_sender = EmailSender(tenant_id)
            if email_sender.send_email(
                recipient=user.email,
                subject=subject,
                body=body,
            ):
                recipients_notified += 1
                total_fees += len(fees_list)

        logger.info(
            f"[Tenant {tenant_id}] Fee reminders sent: "
            f"{recipients_notified} students, {total_fees} fees"
        )

        return {
            "status": "completed",
            "tenant_id": tenant_id,
            "students_notified": recipients_notified,
            "fees_included": total_fees,
            "completed_at": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"[Tenant {tenant_id}] Error sending fee reminders: {e}")
        return {
            "status": "failed",
            "tenant_id": tenant_id,
            "error": str(e),
        }
    finally:
        db.close()


@celery_app.task(
    bind=True,
    name="app.tasks.notifications.send_attendance_alert",
    max_retries=3,
    default_retry_delay=60,
)
def send_attendance_alert(
    self,
    tenant_id: int,
    student_id: int,
    attendance_date: str,
    status: str,
) -> dict:
    """Send attendance alert to parents when a student is marked absent.

    Args:
        tenant_id: The tenant ID.
        student_id: The student ID.
        attendance_date: Date of attendance (ISO format).
        status: Attendance status (absent, late, etc.).

    Returns:
        dict with alert status.
    """
    logger.info(
        f"[Tenant {tenant_id}] Sending attendance alert for student {student_id}"
    )

    db = get_db_session()
    try:
        from app.models.student import Student
        from app.models.user import User

        # Fetch student
        student = db.execute(
            select(Student).where(
                Student.id == student_id,
                Student.tenant_id == tenant_id,
            )
        ).scalar_one_or_none()

        if not student:
            return {
                "status": "failed",
                "tenant_id": tenant_id,
                "student_id": student_id,
                "error": "Student not found",
            }

        # Get student's user for email
        user = db.execute(
            select(User).where(User.id == student.user_id)
        ).scalar_one_or_none()

        recipients = []
        if user and user.email:
            recipients.append(user.email)

        # Get parent emails if available
        if student.parent_ids:
            parents = db.execute(
                select(User).where(User.id.in_(student.parent_ids))
            ).scalars().all()
            recipients.extend(p.email for p in parents if p.email)

        if not recipients:
            return {
                "status": "completed",
                "tenant_id": tenant_id,
                "student_id": student_id,
                "recipients_notified": 0,
                "message": "No recipients found",
            }

        # Prepare email
        status_text = "absent" if status == "absent" else f"marked as {status}"
        subject = f"Attendance Alert: Student {status_text} on {attendance_date}"
        body = f"""
Dear Parent/Guardian,

This is to inform you that your ward (Admission No: {student.admission_number}) 
was {status_text} on {attendance_date}.

If you believe this is an error, please contact the school administration.

---
This is an automated notification from the School ERP System.
        """.strip()

        # Send emails
        email_sender = EmailSender(tenant_id)
        sent_count = 0
        for recipient in recipients:
            if email_sender.send_email(recipient=recipient, subject=subject, body=body):
                sent_count += 1

        return {
            "status": "completed",
            "tenant_id": tenant_id,
            "student_id": student_id,
            "recipients_notified": sent_count,
            "completed_at": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"[Tenant {tenant_id}] Error sending attendance alert: {e}")
        return {
            "status": "failed",
            "tenant_id": tenant_id,
            "student_id": student_id,
            "error": str(e),
        }
    finally:
        db.close()
