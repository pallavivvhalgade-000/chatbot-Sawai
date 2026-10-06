import json
from datetime import datetime, timezone
from uuid import uuid4

from app.db.database import get_all_leads
from app.db.database import get_lead as database_get_lead
from app.db.database import insert_lead
from app.db.database import update_lead
from app.domain.models import Lead
from app.domain.state import ConversationState

from app.domain.assignment import assign_team
from app.domain.assignment import get_team_name
from app.domain.priority import calculate_lead_priority


def _enum_value(value):
    """
    Convert an enum to its underlying value.
    """

    if value is None:
        return None

    if hasattr(value, "value"):
        return value.value

    return value


def _model_dict(model):
    """
    Convert a Pydantic model to a dictionary.
    """

    if model is None:
        return None

    return model.model_dump(mode="json")


def create_lead_from_state(
    state: ConversationState,
) -> Lead:
    """
    Convert completed conversation state into a structured Lead.

    Priority and team assignment are calculated by
    deterministic backend rules.
    """

    lead_id = str(uuid4())

    priority = calculate_lead_priority(state)

    team = assign_team(state)

    lead = Lead(
        lead_id=lead_id,
        contact=state.contact,
        service=state.service,
        sub_service=_get_sub_service(state),
        real_estate=state.real_estate,
        insurance=state.insurance,
        it_services=state.it_services,
        priority=priority,
        status="new",
        assigned_to=team,
        source=state.metadata.get(
            "source",
            "website_chatbot",
        ),
        notes=state.metadata.get("notes"),
    )

    return lead


def _get_sub_service(state: ConversationState) -> str | None:
    """
    Determine the sub-service from the active requirement.
    """

    if state.service is None:
        return None

    if state.insurance is not None:
        return _enum_value(state.insurance.insurance_type)

    if state.it_services is not None:
        return _enum_value(state.it_services.technology_requirement)

    if state.real_estate is not None:
        return _enum_value(state.real_estate.requirement_type)

    return None


def lead_to_database_record(lead: Lead) -> dict:
    """
    Convert a Lead model into a flat SQLite record.
    """

    contact = lead.contact
    real_estate = lead.real_estate
    insurance = lead.insurance
    it_services = lead.it_services

    location = None
    budget = None
    timeline = None

    if real_estate:
        location = real_estate.location
        budget = real_estate.budget
        timeline = _enum_value(real_estate.timeline)

    elif insurance:
        timeline = _enum_value(insurance.timeline)

    elif it_services:
        budget = it_services.budget
        timeline = _enum_value(it_services.timeline)

    requirement = {
        "real_estate": _model_dict(real_estate),
        "insurance": _model_dict(insurance),
        "it_services": _model_dict(it_services),
    }

    return {
        "lead_id": lead.lead_id,
        "name": contact.name if contact else None,
        "mobile": contact.mobile if contact else None,
        "email": contact.email if contact else None,
        "service": _enum_value(lead.service),
        "sub_service": lead.sub_service,
        "requirement": json.dumps(
            requirement,
            ensure_ascii=False,
        ),
        "budget": str(budget) if budget is not None else None,
        "timeline": str(timeline) if timeline is not None else None,
        "location": location,
        "priority": _enum_value(lead.priority),
        "status": _enum_value(lead.status) or "new",
        "assigned_to": _enum_value(lead.assigned_to),
        "contact_preference": (
            _enum_value(contact.contact_preference)
            if contact
            else None
        ),
        "source": lead.source,
        "notes": lead.notes,
        "created_at": (
            lead.created_at.isoformat()
            if lead.created_at
            else datetime.now(timezone.utc).isoformat()
        ),
    }


def save_lead(lead: Lead) -> Lead:
    """
    Persist a Lead in SQLite.
    """

    record = lead_to_database_record(lead)

    insert_lead(record)

    return lead


def save_lead_from_state(
    state: ConversationState,
) -> Lead:
    """
    Create and persist a Lead from the conversation state.
    """

    lead = create_lead_from_state(state)

    save_lead(lead)

    state.lead = lead

    return lead

def save_or_update_lead_from_state(
    state: ConversationState,
) -> Lead:
    """
    Create a lead when none exists, otherwise update the
    existing lead while preserving its ID.
    """

    if state.lead is None:
        return save_lead_from_state(
            state
        )

    existing_lead = state.lead

    updated_lead = create_lead_from_state(
        state
    )

    # Preserve identity.
    updated_lead.lead_id = (
        existing_lead.lead_id
    )

    # Preserve original creation time.
    if existing_lead.created_at:
        updated_lead.created_at = (
            existing_lead.created_at
        )

    # Preserve current status.
    if existing_lead.status:
        updated_lead.status = (
            existing_lead.status
        )

    record = lead_to_database_record(
        updated_lead
    )

    updates = {
        key: value
        for key, value in record.items()
        if key not in {
            "lead_id",
            "created_at",
        }
    }

    updated = modify_lead(
        lead_id=updated_lead.lead_id,
        updates=updates,
    )

    # Recovery in case state contains a lead that is no
    # longer present in SQLite.
    if not updated:
        insert_lead(record)

    state.lead = updated_lead

    return updated_lead


def find_lead(lead_id: str) -> dict | None:
    """
    Find a stored lead.
    """

    return database_get_lead(lead_id)


def list_leads() -> list[dict]:
    """
    Return all stored leads.
    """

    return get_all_leads()


def modify_lead(
    lead_id: str,
    updates: dict,
) -> bool:
    """
    Update an existing stored lead.
    """

    return update_lead(
        lead_id=lead_id,
        updates=updates,
    )