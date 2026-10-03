import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

from dotenv import load_dotenv

from .grok_client import GrokClient

BACKEND_DIR = Path(__file__).resolve().parent
OUTREACH_DIR = BACKEND_DIR / "outreach"

load_dotenv(BACKEND_DIR / ".env")


def filter_valid_leads(leads: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [
        lead for lead in leads
        if lead.get("name") and not str(lead.get("name", "")).startswith("Sample ")
    ]


def save_lead_log(leads: List[Dict[str, Any]]) -> str:
    OUTREACH_DIR.mkdir(exist_ok=True)
    valid_leads = filter_valid_leads(leads)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_path = OUTREACH_DIR / f"lead_outreach_{timestamp}.json"
    file_path.write_text(json.dumps(valid_leads, indent=2), encoding="utf-8")
    return str(file_path)


def load_recent_leads(limit: int = 20) -> List[Dict[str, Any]]:
    if not OUTREACH_DIR.exists():
        return []

    files = sorted(OUTREACH_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    for file_path in files:
        try:
            data = json.loads(file_path.read_text(encoding="utf-8"))
            if isinstance(data, list):
                valid = filter_valid_leads(data)
                if valid:
                    return valid[:limit]
        except Exception:
            continue
    return []


def generate_outreach_message(lead: Dict[str, Any]) -> str:
    client = GrokClient()
    return client.generate_custom_message(
        business_name=lead.get("name", "Your business"),
        category=lead.get("category", "local business"),
        city=lead.get("city", "India"),
        website=lead.get("website"),
    )


def prepare_lead_for_outreach(lead: Dict[str, Any]) -> Dict[str, Any]:
    lead = dict(lead)
    has_website = bool(lead.get("website"))
    lead["has_website"] = has_website
    lead["message"] = generate_outreach_message(lead) if not has_website else "Website already exists; no outreach required"
    return lead


def send_lead_outreach(lead: Dict[str, Any]) -> bool:
    if lead.get("has_website"):
        return False

    message = lead.get("message") or generate_outreach_message(lead)
    email = lead.get("email")
    phone = lead.get("phone")

    if email:
        return send_email_message(email, message)
    if phone:
        return send_whatsapp_message(phone, message)

    print(f"[Draft Only] {lead.get('name')} -> {message}")
    return False


def send_whatsapp_message(phone_number: str, message: str) -> bool:
    from twilio.rest import Client

    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    from_number = os.getenv("TWILIO_WHATSAPP_FROM")

    if not all([account_sid, auth_token, from_number]):
        print(f"[WhatsApp Draft] To: {phone_number}\n{message}")
        return False

    client = Client(account_sid, auth_token)
    client.messages.create(
        from_=from_number,
        body=message,
        to=f"whatsapp:{phone_number}",
    )
    return True


def send_email_message(email: str, message: str) -> bool:
    import smtplib
    from email.message import EmailMessage

    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_username = os.getenv("SMTP_USERNAME")
    smtp_password = os.getenv("SMTP_PASSWORD")

    if not all([smtp_host, smtp_username, smtp_password]):
        print(f"[Email Draft] To: {email}\n{message}")
        return False

    email_message = EmailMessage()
    email_message["Subject"] = "Website Partnership Opportunity"
    email_message["From"] = smtp_username
    email_message["To"] = email
    email_message.set_content(message)

    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.starttls()
        server.login(smtp_username, smtp_password)
        server.send_message(email_message)

    return True
