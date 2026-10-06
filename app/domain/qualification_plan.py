from typing import Any

from app.domain.flows.questions import ALL_QUESTIONS
from app.domain.state import ConversationState


# =========================================================
# Optional questions worth asking
# =========================================================

SMART_OPTIONAL_FIELDS = {
    # Real Estate
    "real_estate.property_size",
    "real_estate.bedrooms",
    "real_estate.financing",

    # Insurance
    "insurance.age",
    "insurance.desired_cover",
    "insurance.existing_insurance",
    "insurance.objective",

    # IT
    "it_services.current_process",
    "it_services.existing_system",
    "it_services.technical_requirements",
    "it_services.data_sources",
    "it_services.objective",
}


def _enum_value(
    value: Any,
) -> Any:
    if hasattr(value, "value"):
        return value.value

    return value


def get_nested_value(
    state: ConversationState,
    field: str,
) -> Any:
    """
    Read a nested value such as:

        real_estate.location
        contact.name
    """

    current: Any = state

    for part in field.split("."):
        if current is None:
            return None

        if not hasattr(
            current,
            part,
        ):
            return None

        current = getattr(
            current,
            part,
        )

    return current


def is_field_filled(
    value: Any,
) -> bool:
    if value is None:
        return False

    if isinstance(
        value,
        str,
    ):
        return bool(
            value.strip()
        )

    if isinstance(
        value,
        list,
    ):
        return len(value) > 0

    return True


def question_applies(
    question,
    state: ConversationState,
) -> bool:
    """
    Evaluate an existing question condition safely.
    """

    if question.condition is None:
        return True

    try:
        return bool(
            question.condition(
                state
            )
        )

    except Exception:
        return False


def _smart_optional_applies(
    field: str,
    state: ConversationState,
) -> bool:
    """
    Additional UX rules for optional questions.
    """

    # -----------------------------------------------------
    # Bedrooms only make sense for residential-type
    # properties.
    # -----------------------------------------------------

    if field == "real_estate.bedrooms":

        requirement = (
            state.real_estate
        )

        if requirement is None:
            return False

        property_type = (
            _enum_value(
                requirement.property_type
            )
        )

        return property_type in {
            "apartment",
            "flat",
            "house",
            "villa",
        }


    # -----------------------------------------------------
    # Financing is mainly relevant when buying/investing.
    # -----------------------------------------------------

    if field == "real_estate.financing":

        requirement = (
            state.real_estate
        )

        if requirement is None:
            return False

        requirement_type = (
            _enum_value(
                requirement.requirement_type
            )
        )

        return requirement_type in {
            "buy",
            "investment",
        }


    return True


def get_planned_questions(
    state: ConversationState,
):
    """
    Return all questions that are relevant to the current
    qualification journey.

    Required questions are included.

    Selected optional questions are included only when they
    are relevant.
    """

    planned = []

    seen_fields: set[str] = set()


    for question in ALL_QUESTIONS:

        field = question.field


        if field in seen_fields:
            continue


        if not question_applies(
            question,
            state,
        ):
            continue


        should_include = (
            question.required
            or (
                field
                in SMART_OPTIONAL_FIELDS
                and _smart_optional_applies(
                    field,
                    state,
                )
            )
        )


        if not should_include:
            continue


        planned.append(
            question
        )

        seen_fields.add(
            field
        )


    return planned


def get_missing_question_fields(
    state: ConversationState,
) -> list[str]:
    """
    Return all currently relevant fields that have not yet
    been filled.
    """

    missing: list[str] = []


    for question in get_planned_questions(
        state
    ):

        value = get_nested_value(
            state,
            question.field,
        )


        if not is_field_filled(
            value
        ):
            missing.append(
                question.field
            )


    return missing


def get_next_planned_question(
    state: ConversationState,
):
    """
    Return the next missing relevant question.
    """

    for question in get_planned_questions(
        state
    ):

        value = get_nested_value(
            state,
            question.field,
        )


        if is_field_filled(
            value
        ):
            state.mark_field_complete(
                question.field
            )

            continue


        return question


    return None