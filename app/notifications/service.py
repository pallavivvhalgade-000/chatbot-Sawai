import smtplib
from email.message import EmailMessage
from typing import Any

import httpx
from pydantic import BaseModel

from app.core.config import settings
from app.domain.assignment import TEAM_NAMES
from app.domain.enums import TeamType
from app.domain.models import Lead


class NotificationResult(BaseModel):
    sent: bool
    channel: str
    detail: str | None = None


def _enum_value(value: Any) -> Any:
    """
    Convert enum-like values into serializable values.
    """

    if value is None:
        return None

    if hasattr(value, "value"):
        return value.value

    return value


def _team_display_name(value: Any) -> str | None:
    """
    Convert an internal team value into a readable team name.
    """

    if value is None:
        return None

    raw_value = _enum_value(value)

    try:
        team = TeamType(raw_value)
        return TEAM_NAMES.get(team, raw_value)

    except ValueError:
        return str(raw_value)


def _lead_payload(lead: Lead) -> dict[str, Any]:
    """
    Create the structured lead payload used by notification channels.
    """

    contact = lead.contact

    return {
        "lead_id": lead.lead_id,
        "name": contact.name if contact else None,
        "mobile": contact.mobile if contact else None,
        "email": contact.email if contact else None,
        "contact_preference": (
            _enum_value(contact.contact_preference)
            if contact
            else None
        ),
        "service": _enum_value(lead.service),
        "sub_service": lead.sub_service,
        "priority": _enum_value(lead.priority),
        "status": _enum_value(lead.status),
        "assigned_to": _enum_value(lead.assigned_to),
        "assigned_team_name": _team_display_name(
            lead.assigned_to
        ),
        "real_estate": (
            lead.real_estate.model_dump(mode="json")
            if lead.real_estate
            else None
        ),
        "insurance": (
            lead.insurance.model_dump(mode="json")
            if lead.insurance
            else None
        ),
        "it_services": (
            lead.it_services.model_dump(mode="json")
            if lead.it_services
            else None
        ),
        "source": lead.source,
        "notes": lead.notes,
        "created_at": (
            lead.created_at.isoformat()
            if lead.created_at
            else None
        ),
    }


def _build_email_body(
    payload: dict[str, Any],
) -> str:
    """
    Create a plain-text internal lead notification.
    """

    lines = [
        "New Sawai Associates chatbot lead",
        "",
        f"Lead ID: {payload.get('lead_id') or '-'}",
        f"Name: {payload.get('name') or '-'}",
        f"Mobile: {payload.get('mobile') or '-'}",
        f"Email: {payload.get('email') or '-'}",
        f"Service: {payload.get('service') or '-'}",
        f"Sub-service: {payload.get('sub_service') or '-'}",
        f"Priority: {payload.get('priority') or '-'}",
        f"Assigned team: {payload.get('assigned_team_name') or '-'}",
        f"Contact preference: {payload.get('contact_preference') or '-'}",
        "",
        "Requirement details:",
    ]

    if payload.get("real_estate"):
        lines.append(
            str(payload["real_estate"])
        )

    if payload.get("insurance"):
        lines.append(
            str(payload["insurance"])
        )

    if payload.get("it_services"):
        lines.append(
            str(payload["it_services"])
        )

    return "\n".join(lines)


def _send_webhook(
    lead: Lead,
) -> NotificationResult:
    """
    Send a structured lead payload to a configured webhook.
    """

    if not settings.notification_webhook_url:
        return NotificationResult(
            sent=False,
            channel="webhook",
            detail="Webhook URL is not configured.",
        )

    payload = _lead_payload(lead)

    try:
        response = httpx.post(
            settings.notification_webhook_url,
            json=payload,
            timeout=10.0,
        )

        response.raise_for_status()

        return NotificationResult(
            sent=True,
            channel="webhook",
            detail="Lead notification delivered.",
        )

    except Exception as exc:
        return NotificationResult(
            sent=False,
            channel="webhook",
            detail=str(exc),
        )


def _send_smtp(
    lead: Lead,
) -> NotificationResult:
    """
    Send a lead notification using SMTP.
    """

    required = {
        "SMTP_HOST": settings.smtp_host,
        "SMTP_USERNAME": settings.smtp_username,
        "SMTP_PASSWORD": settings.smtp_password,
        "SMTP_FROM_EMAIL": settings.smtp_from_email,
        "LEAD_NOTIFICATION_TO_EMAIL": (
            settings.lead_notification_to_email
        ),
    }

    missing = [
        name
        for name, value in required.items()
        if not value
    ]

    if missing:
        return NotificationResult(
            sent=False,
            channel="smtp",
            detail=(
                "Missing SMTP configuration: "
                + ", ".join(missing)
            ),
        )

    payload = _lead_payload(lead)

    message = EmailMessage()

    message["Subject"] = (
        f"New chatbot lead - "
        f"{payload.get('service') or 'General'}"
    )

    message["From"] = settings.smtp_from_email
    message["To"] = settings.lead_notification_to_email

    message.set_content(
        _build_email_body(payload)
    )

    try:
        with smtplib.SMTP(
            settings.smtp_host,
            settings.smtp_port,
            timeout=15,
        ) as smtp:

            if settings.smtp_use_tls:
                smtp.starttls()

            smtp.login(
                settings.smtp_username,
                settings.smtp_password,
            )

            smtp.send_message(message)

        return NotificationResult(
            sent=True,
            channel="smtp",
            detail="Lead notification email sent.",
        )

    except Exception as exc:
        return NotificationResult(
            sent=False,
            channel="smtp",
            detail=str(exc),
        )


def notify_lead(
    lead: Lead,
) -> NotificationResult:
    """
    Send the lead using the configured notification channel.

    Supported values:
        none
        webhook
        smtp
    """

    channel = (
        settings.notification_channel
        or "none"
    ).strip().lower()

    if channel == "none":
        return NotificationResult(
            sent=False,
            channel="none",
            detail="Lead notifications are disabled.",
        )

    if channel == "webhook":
        return _send_webhook(lead)

    if channel == "smtp":
        return _send_smtp(lead)

    return NotificationResult(
        sent=False,
        channel=channel,
        detail=(
            f"Unsupported notification channel: {channel}"
        ),
    )