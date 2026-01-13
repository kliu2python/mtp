"""
Notification Service for sending emails and Teams messages
"""
import logging
import aiohttp
import json
from typing import Optional

logger = logging.getLogger(__name__)


async def send_email_notification(to_email: str, subject: str, body: str):
    """
    Send email notification

    Args:
        to_email: Recipient email address
        subject: Email subject
        body: Email body

    Note:
        This is a stub implementation. In production, integrate with:
        - SMTP server (using aiosmtplib)
        - SendGrid API
        - AWS SES
        - etc.
    """
    logger.info(f"[EMAIL] To: {to_email}, Subject: {subject}")
    logger.info(f"[EMAIL] Body: {body}")

    # TODO: Implement actual email sending
    # Example with SMTP:
    # import aiosmtplib
    # from email.mime.text import MIMEText
    #
    # message = MIMEText(body)
    # message["From"] = "noreply@mtp.local"
    # message["To"] = to_email
    # message["Subject"] = subject
    #
    # await aiosmtplib.send(
    #     message,
    #     hostname="smtp.gmail.com",
    #     port=587,
    #     start_tls=True,
    #     username="your-email@gmail.com",
    #     password="your-password"
    # )

    return True


async def send_teams_notification(webhook_url: str, title: str, text: str, color: str = "0078D4"):
    """
    Send notification to Microsoft Teams via webhook

    Args:
        webhook_url: Teams webhook URL
        title: Message title
        text: Message text
        color: Card color (hex code)

    Returns:
        True if successful
    """
    try:
        # Prepare Teams message card
        message = {
            "@type": "MessageCard",
            "@context": "https://schema.org/extensions",
            "summary": title,
            "themeColor": color,
            "title": title,
            "sections": [
                {
                    "activityTitle": "Mobile Test Pilot",
                    "activitySubtitle": "Automated Test Notification",
                    "facts": [
                        {
                            "name": "Details",
                            "value": text
                        }
                    ],
                    "markdown": True
                }
            ]
        }

        # Send to Teams webhook
        async with aiohttp.ClientSession() as session:
            async with session.post(
                webhook_url,
                json=message,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    logger.info(f"Successfully sent Teams notification: {title}")
                    return True
                else:
                    error_text = await response.text()
                    logger.error(f"Failed to send Teams notification: {response.status} - {error_text}")
                    return False

    except Exception as e:
        logger.error(f"Error sending Teams notification: {e}")
        return False


async def send_slack_notification(webhook_url: str, title: str, text: str):
    """
    Send notification to Slack via webhook

    Args:
        webhook_url: Slack webhook URL
        title: Message title
        text: Message text

    Returns:
        True if successful
    """
    try:
        message = {
            "text": title,
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": title
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": text
                    }
                }
            ]
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                webhook_url,
                json=message,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    logger.info(f"Successfully sent Slack notification: {title}")
                    return True
                else:
                    error_text = await response.text()
                    logger.error(f"Failed to send Slack notification: {response.status} - {error_text}")
                    return False

    except Exception as e:
        logger.error(f"Error sending Slack notification: {e}")
        return False
