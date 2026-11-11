import smtplib
import ssl
from datetime import timedelta
from email.message import EmailMessage
from uuid import UUID,uuid4
from sqlalchemy import select
from app.core.config import get_settings
from app.core.security import decrypt_json,now
from app.db.sessions import SyncSession
from app.modules.auth.models import EmailJob,SecretPayload,User


def deliver_email(job_id: UUID):
    settings=get_settings();token=uuid4()
    with SyncSession.begin() as db:
        job=db.scalar(select(EmailJob).where(EmailJob.id==job_id).with_for_update())
        if not job or job.status!='queued' or job.attempt_count>=3:return
        secret=db.get(SecretPayload,job.secret_payload_id) if job.secret_payload_id else None
        user=db.get(User,job.user_id)
        if not secret or secret.destroyed_at or secret.expires_at<=now() or not user or user.deleted_at:
            job.status='cancelled';return
        job.status='running';job.lease_token=token;job.lease_expires_at=now()+timedelta(seconds=60);job.attempt_count+=1;job.updated_at=now()
        data=decrypt_json(secret.encrypted_payload)
    message=EmailMessage();message['From']=settings.smtp_from;message['To']=data['email'];message['Subject']='Verify your WorkQuest email' if data['kind']=='verify' else 'Reset your WorkQuest password'
    route='verify-email' if data['kind']=='verify' else 'reset-password'
    message.set_content(f"Your WorkQuest link (single use):\n{settings.app_origin}/{route}?token={data['token']}\n\nIf you did not request this, ignore this email.")
    try:
        cls=smtplib.SMTP_SSL if settings.smtp_tls=='tls' else smtplib.SMTP
        with cls(settings.smtp_host,settings.smtp_port,timeout=20) as smtp:
            if settings.smtp_tls=='starttls':smtp.starttls(context=ssl.create_default_context())
            if settings.smtp_username:smtp.login(settings.smtp_username,settings.smtp_password.get_secret_value())
            smtp.send_message(message)
    except (OSError,smtplib.SMTPException):
        with SyncSession.begin() as db:
            job=db.get(EmailJob,job_id)
            if job and job.lease_token==token and job.status=='running':job.status='queued' if job.attempt_count<3 else 'failed';job.updated_at=now()
        return
    with SyncSession.begin() as db:
        job=db.get(EmailJob,job_id)
        if not job or job.lease_token!=token or job.status!='running':return
        job.status='completed';job.updated_at=now()
        secret=db.get(SecretPayload,job.secret_payload_id)
        if secret:secret.encrypted_payload='';secret.destroyed_at=now()
