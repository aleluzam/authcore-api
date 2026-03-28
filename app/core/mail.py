import resend
import logging
from fastapi import HTTPException, status

from app.settings import settings
from app.schemas.mail_schemas import EmailRequest

logger = logging.getLogger(__name__)
resend.api_key = settings.resend_api_key

    
def send_mail(email_request: EmailRequest):
    try:
        r = resend.Emails.send({
            "from": settings.admin_mail,
            "to": [email_request.to],
            "subject": email_request.subject,
            "html": f"<strong>{email_request.message}</strong>"
        })
    
    except Exception as e:
        logger.error(f"Error sending email: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send email"
        )
        
        