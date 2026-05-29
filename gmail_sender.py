"""
Gmail sender module - send personalized emails via Gmail SMTP
"""
import smtplib
import ssl
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formatdate, make_msgid
from typing import Dict, List, Optional, Callable
import logging

logger = logging.getLogger(__name__)


class GmailSender:
    """Send emails via Gmail SMTP with App Password"""

    SMTP_SERVER = "smtp.gmail.com"
    SMTP_PORT = 587

    def __init__(
        self,
        gmail_address: str,
        app_password: str,
        sender_name: str = "",
        delay_seconds: float = 30.0
    ):
        """
        Initialize Gmail sender

        Args:
            gmail_address: Your Gmail address (e.g., you@gmail.com)
            app_password: 16-char App Password (NOT your login password)
            sender_name: Display name (e.g., "John from AI Workflow Pro")
            delay_seconds: Delay between sends (30s recommended to avoid spam flags)
        """
        self.gmail_address = gmail_address
        self.app_password = app_password
        self.sender_name = sender_name or gmail_address
        self.delay_seconds = delay_seconds

    def test_connection(self) -> tuple[bool, str]:
        """Test Gmail SMTP connection with credentials"""
        try:
            context = ssl.create_default_context()
            with smtplib.SMTP(self.SMTP_SERVER, self.SMTP_PORT) as server:
                server.starttls(context=context)
                server.login(self.gmail_address, self.app_password)
            return True, "✅ Gmail 連接成功"
        except smtplib.SMTPAuthenticationError:
            return False, "❌ 登入失敗：請檢查 Gmail 地址同 App Password"
        except Exception as e:
            return False, f"❌ 連接失敗：{str(e)}"

    def send_email(
        self,
        to_email: str,
        subject: str,
        body: str,
        to_name: str = "",
        unsubscribe_text: str = ""
    ) -> tuple[bool, str]:
        """
        Send a single email

        Returns:
            (success, message)
        """
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"{self.sender_name} <{self.gmail_address}>"
            msg["To"] = f"{to_name} <{to_email}>" if to_name else to_email
            msg["Date"] = formatdate(localtime=True)
            msg["Message-ID"] = make_msgid(domain="gmail.com")

            # Plain text body with unsubscribe footer (PDPO compliance)
            full_body = body
            if unsubscribe_text:
                full_body += f"\n\n---\n{unsubscribe_text}"

            msg.attach(MIMEText(full_body, "plain", "utf-8"))

            # Send via SMTP
            context = ssl.create_default_context()
            with smtplib.SMTP(self.SMTP_SERVER, self.SMTP_PORT) as server:
                server.starttls(context=context)
                server.login(self.gmail_address, self.app_password)
                server.send_message(msg)

            logger.info(f"✅ Sent to {to_email}")
            return True, "已發送"

        except Exception as e:
            logger.error(f"❌ Failed to send to {to_email}: {e}")
            return False, str(e)

    def send_batch(
        self,
        emails: List[Dict],
        unsubscribe_text: str = "",
        progress_callback: Optional[Callable] = None
    ) -> List[Dict]:
        """
        Send batch of emails with delays

        Args:
            emails: List of dicts with keys: to_email, to_name, subject, body
            unsubscribe_text: Footer for PDPO compliance
            progress_callback: function(index, total, email_dict, success, message)

        Returns:
            List of results with status
        """
        results = []
        total = len(emails)

        for idx, email in enumerate(emails):
            success, message = self.send_email(
                to_email=email["to_email"],
                subject=email["subject"],
                body=email["body"],
                to_name=email.get("to_name", ""),
                unsubscribe_text=unsubscribe_text
            )

            result = {
                **email,
                "sent": success,
                "status_message": message,
                "sent_at": time.strftime("%Y-%m-%d %H:%M:%S") if success else ""
            }
            results.append(result)

            if progress_callback:
                progress_callback(idx + 1, total, email, success, message)

            # Delay between sends (except last one)
            if idx < total - 1 and success:
                time.sleep(self.delay_seconds)

        return results
