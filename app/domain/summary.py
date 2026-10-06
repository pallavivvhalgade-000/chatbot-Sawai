from typing import Any

from app.domain.flows.questions import ALL_QUESTIONS
from app.domain.state import ConversationState

from app.domain.qualification_plan import (
    get_planned_questions,
)


FIELD_LABELS = {
    "real_estate.requirement_type": "Requirement",
    "real_estate.property_type": "Property Type",
    "real_estate.purpose": "Purpose",
    "real_estate.location": "Location",
    "real_estate.budget": "Budget",
    "real_estate.property_size": "Property Size",
    "real_estate.bedrooms": "Bedrooms",
    "real_estate.timeline": "Timeline",
    "real_estate.financing": "Financing",

    "insurance.insurance_type": "Insurance Type",
    "insurance.age": "Age",
    "insurance.desired_cover": "Desired Cover",
    "insurance.existing_insurance": "Existing Insurance",
    "insurance.objective": "Objective",
    "insurance.timeline": "Timeline",

    "it_services.technology_requirement": "IT Service",
    "it_services.sub_service": "Sub-service",
    "it_services.current_process": "Current Process",
    "it_services.existing_system": "Existing System",
    "it_services.technical_requirements": "Technical Requirements",
    "it_services.data_sources": "Data Sources",
    "it_services.objective": "Objective",
    "it_services.budget": "Budget",
    "it_services.timeline": "Timeline",

    "contact.name": "Name",
    "contact.mobile": "Mobile",
    "contact.email": "Email",
    "contact.contact_preference": "Contact Preference",
}


def get_nested_value(
    state: ConversationState,
    field: str,
) -> Any:
    """
    Safely retrieve a nested ConversationState value.
    """

    current: Any = state

    for part in field.split("."):
        if current is None:
            return None

        if not hasattr(current, part):
            return None

        current = getattr(
            current,
            part,
        )

    return current


def _is_filled(value: Any) -> bool:
    if value is None:
        return False

    if isinstance(value, str):
        return bool(value.strip())

    if isinstance(value, list):
        return len(value) > 0

    return True


def _display_value(value: Any) -> str:
    """
    Convert internal values into customer-friendly text.
    """

    if hasattr(value, "value"):
        value = value.value

    if isinstance(value, bool):
        return "Yes" if value else "No"

    if isinstance(value, list):
        return ", ".join(
            _display_value(item)
            for item in value
        )

    if isinstance(value, str):
        return value.replace(
            "_",
            " ",
        ).strip()

    return str(value)


def get_field_label(
    field: str,
) -> str:
    """
    Return a readable label for a qualification field.
    """

    if field in FIELD_LABELS:
        return FIELD_LABELS[field]

    return (
        field.split(".")[-1]
        .replace("_", " ")
        .title()
    )


def _question_applies(
    question,
    state: ConversationState,
) -> bool:
    if question.condition is None:
        return True

    try:
        return bool(
            question.condition(state)
        )

    except Exception:
        return False


def get_question_for_field(
    state: ConversationState,
    field: str,
):
    """
    Find an applicable question for a state field.
    """

    for question in ALL_QUESTIONS:
        if question.field != field:
            continue

        if not _question_applies(
            question,
            state,
        ):
            continue

        return question

    return None


def build_customer_summary(
    state: ConversationState,
) -> list[dict[str, str]]:
    """
    Build a customer-safe summary.

    Internal fields such as priority and assigned team
    are intentionally excluded.
    """

    summary: list[dict[str, str]] = []

    if state.service:
        summary.append(
            {
                "label": "Service",
                "value": _display_value(
                    state.service
                ).title(),
            }
        )

    seen_fields: set[str] = set()

    for question in ALL_QUESTIONS:

        if question.field in seen_fields:
            continue

        if not _question_applies(
            question,
            state,
        ):
            continue

        value = get_nested_value(
            state,
            question.field,
        )

        if not _is_filled(value):
            continue

        seen_fields.add(
            question.field
        )

        summary.append(
            {
                "label": get_field_label(
                    question.field
                ),
                "value": _display_value(
                    value
                ),
            }
        )

    return summary


def get_editable_fields(
    state: ConversationState,
) -> list[dict[str, str]]:
    """
    Return fields the customer may edit.
    """

    editable: list[dict[str, str]] = []

    seen_fields: set[str] = set()

    for question in ALL_QUESTIONS:

        if question.field in seen_fields:
            continue

        if not _question_applies(
            question,
            state,
        ):
            continue

        value = get_nested_value(
            state,
            question.field,
        )

        # Show required fields and already-filled optional fields.
        if (
            not question.required
            and not _is_filled(value)
        ):
            continue

        seen_fields.add(
            question.field
        )

        editable.append(
            {
                "field": question.field,
                "label": get_field_label(
                    question.field
                ),
            }
        )

    return editable


def get_progress_label(
    state: ConversationState,
) -> str | None:
    """
    Return progress using the same dynamic question plan
    used by the qualification engine.
    """

    questions = (
        get_planned_questions(
            state
        )
    )


    fields: list[str] = []


    for question in questions:

        if (
            question.field
            not in fields
        ):
            fields.append(
                question.field
            )


    total = len(
        fields
    )


    if total == 0:
        return None


    if state.qualification_complete:
        return (
            f"Step {total} of {total}"
        )


    answered = 0


    for field in fields:

        value = get_nested_value(
            state,
            field,
        )


        if _is_filled(
            value
        ):
            answered += 1


    current = min(
        answered + 1,
        total,
    )


    return (
        f"Step {current} of {total}"
    )