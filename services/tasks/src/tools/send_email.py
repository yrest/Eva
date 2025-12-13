"""Send email tool (EXTERNAL_API)."""

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, List, Optional

from . import SafetyLevel, tool_registry


async def send_email_handler(
    to: str,
    subject: str,
    body: str,
    cc: Optional[List[str]] = None,
    html: bool = False,
) -> Dict[str, Any]:
    """
    Send email via SMTP.

    Args:
        to: Recipient email
        subject: Email subject
        body: Email body
        cc: CC recipients
        html: Whether body is HTML

    Returns:
        Result with success status
    """
    try:
        # This is a placeholder - you'd configure SMTP settings
        # For now, just return a mock success
        return {
            "success": True,
            "message": f"Email sent to {to}",
            "subject": subject,
            "note": "SMTP not configured - this is a simulation",
        }

        # Real implementation would be:
        # msg = MIMEMultipart()
        # msg['From'] = settings.smtp_from
        # msg['To'] = to
        # msg['Subject'] = subject
        #
        # if cc:
        #     msg['Cc'] = ', '.join(cc)
        #
        # msg.attach(MIMEText(body, 'html' if html else 'plain'))
        #
        # with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
        #     server.starttls()
        #     server.login(settings.smtp_user, settings.smtp_password)
        #     server.send_message(msg)

    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to send email: {str(e)}",
        }


# Register tool
tool_registry.register(
    name="send_email",
    description="Send an email to a recipient",
    safety_level=SafetyLevel.EXTERNAL_API,
    parameters={
        "type": "object",
        "properties": {
            "to": {
                "type": "string",
                "description": "Recipient email address",
            },
            "subject": {
                "type": "string",
                "description": "Email subject",
            },
            "body": {
                "type": "string",
                "description": "Email body content",
            },
            "cc": {
                "type": "array",
                "items": {"type": "string"},
                "description": "CC recipients (optional)",
            },
            "html": {
                "type": "boolean",
                "description": "Whether body is HTML formatted",
                "default": False,
            },
        },
        "required": ["to", "subject", "body"],
    },
    handler=send_email_handler,
)
