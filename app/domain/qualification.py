import re
from enum import Enum
from types import UnionType
from typing import Any, Union, get_args, get_origin

from pydantic import TypeAdapter, ValidationError

from app.domain.state import ConversationState


# =========================================================
# Normalization helpers
# =========================================================


def _normalize_token(
    value: str,
) -> str:
    """
    Convert human text into a comparable token.

    Examples:

    "Within 1 Month" -> "within_1_month"
    "AI / GenAI"     -> "ai_genai"
    "Plot-Land"      -> "plot_land"
    """

    value = value.strip().lower()

    value = value.replace(
        "&",
        " and ",
    )

    value = value.replace(
        "+",
        " plus ",
    )

    value = re.sub(
        r"[^a-z0-9]+",
        "_",
        value,
    )

    return value.strip("_")


# Common human-language aliases that may not exactly match
# our enum values.

_ENUM_ALIASES = {
    # Timeline
    "asap": "immediate",
    "immediately": "immediate",
    "urgent": "immediate",

    "within_a_month": "within_1_month",
    "within_one_month": "within_1_month",
    "one_month": "within_1_month",
    "1_month": "within_1_month",

    "1_3_months": "one_to_three_months",
    "1_to_3_months": "one_to_three_months",
    "one_three_months": "one_to_three_months",

    "3_6_months": "three_to_six_months",
    "3_to_6_months": "three_to_six_months",

    "6_plus_months": "six_plus_months",
    "more_than_6_months": "six_plus_months",
    "more_than_six_months": "six_plus_months",

    "just_exploring": "exploring",
    "researching": "exploring",

    "unsure": "not_sure",
    "not_sure_yet": "not_sure",
    "dont_know": "not_sure",
    "do_not_know": "not_sure",

    # Common yes/no variants
    "y": "yes",
    "yeah": "yes",
    "yep": "yes",

    "n": "no",
    "nope": "no",

    # Real-estate/common formatting
    "plot_land": "plot_land",

    # IT terminology
    "ai_gen_ai": "ai_genai",
    "generative_ai": "ai_genai",
    "gen_ai": "ai_genai",

    "rag": "rag_knowledge_assistant",
    "knowledge_assistant":
        "rag_knowledge_assistant",
}


def _annotation_contains_type(
    annotation: Any,
    target_type: type,
) -> bool:
    """
    Determine whether a Pydantic field annotation contains
    a specific type, including Optional/Union fields.
    """

    if annotation is target_type:
        return True

    origin = get_origin(
        annotation
    )

    if origin in (
        Union,
        UnionType,
    ):
        return any(
            _annotation_contains_type(
                argument,
                target_type,
            )
            for argument in get_args(
                annotation
            )
        )

    return False


def _find_enum_type(
    annotation: Any,
) -> type[Enum] | None:
    """
    Find an Enum class inside a type annotation.

    Handles:

        TimelineType
        TimelineType | None
        Optional[TimelineType]
    """

    if (
        isinstance(annotation, type)
        and issubclass(
            annotation,
            Enum,
        )
    ):
        return annotation

    origin = get_origin(
        annotation
    )

    if origin in (
        Union,
        UnionType,
    ):
        for argument in get_args(
            annotation
        ):
            enum_type = (
                _find_enum_type(
                    argument
                )
            )

            if enum_type is not None:
                return enum_type

    return None


# =========================================================
# Enum coercion
# =========================================================


def _coerce_enum(
    enum_type: type[Enum],
    value: Any,
) -> Enum:
    """
    Convert human/LLM text into an actual Enum member.
    """

    if isinstance(
        value,
        enum_type,
    ):
        return value


    if isinstance(
        value,
        Enum,
    ):
        value = value.value


    normalized = _normalize_token(
        str(value)
    )


    normalized = _ENUM_ALIASES.get(
        normalized,
        normalized,
    )


    for member in enum_type:

        member_name = (
            _normalize_token(
                member.name
            )
        )

        member_value = (
            _normalize_token(
                str(member.value)
            )
        )


        if normalized in {
            member_name,
            member_value,
        }:
            return member


    allowed = [
        str(member.value)
        for member in enum_type
    ]


    raise ValueError(
        "Expected one of: "
        + ", ".join(allowed)
    )


# =========================================================
# Primitive coercion
# =========================================================


def _coerce_boolean(
    value: Any,
) -> bool:
    if isinstance(
        value,
        bool,
    ):
        return value


    normalized = _normalize_token(
        str(value)
    )


    true_values = {
        "true",
        "yes",
        "y",
        "1",
        "available",
        "have",
    }


    false_values = {
        "false",
        "no",
        "n",
        "0",
        "none",
        "not_available",
        "dont_have",
        "do_not_have",
    }


    if normalized in true_values:
        return True


    if normalized in false_values:
        return False


    raise ValueError(
        "Expected a yes/no value."
    )


_NUMBER_WORDS = {
    "zero": 0,
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
}


def _coerce_integer(
    value: Any,
) -> int:
    if (
        isinstance(value, int)
        and not isinstance(
            value,
            bool,
        )
    ):
        return value


    text = str(
        value
    ).strip().lower()


    if text in _NUMBER_WORDS:
        return _NUMBER_WORDS[
            text
        ]


    match = re.search(
        r"-?\d+",
        text,
    )


    if match:
        return int(
            match.group()
        )


    raise ValueError(
        "Expected a whole number."
    )


def _coerce_float(
    value: Any,
) -> float:
    if (
        isinstance(
            value,
            (int, float),
        )
        and not isinstance(
            value,
            bool,
        )
    ):
        return float(value)


    text = (
        str(value)
        .replace(",", "")
        .strip()
    )


    match = re.search(
        r"-?\d+(?:\.\d+)?",
        text,
    )


    if match:
        return float(
            match.group()
        )


    raise ValueError(
        "Expected a number."
    )


# =========================================================
# Contact normalization
# =========================================================


def _normalize_mobile(
    value: Any,
) -> str:
    """
    Normalize a mobile number without assuming a specific
    country code.

    Allows 10-15 digits and preserves a leading +.
    """

    text = str(
        value
    ).strip()


    has_plus = (
        text.startswith("+")
    )


    digits = re.sub(
        r"\D",
        "",
        text,
    )


    if not (
        10 <= len(digits) <= 15
    ):
        raise ValueError(
            "Please enter a valid mobile number "
            "with 10 to 15 digits."
        )


    if has_plus:
        return "+" + digits


    return digits


def _normalize_email(
    value: Any,
) -> str:
    """
    Lightweight email validation.

    We intentionally avoid adding another dependency just
    for this validation step.
    """

    email = (
        str(value)
        .strip()
        .lower()
    )


    pattern = (
        r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
    )


    if not re.match(
        pattern,
        email,
    ):
        raise ValueError(
            "Please enter a valid email address."
        )


    return email


# =========================================================
# Field coercion
# =========================================================


def _coerce_field_value(
    field: str,
    annotation: Any,
    value: Any,
) -> Any:
    """
    Convert a user/LLM value into the type required by
    the destination Pydantic model field.
    """

    if value is None:
        return None


    # -----------------------------------------------------
    # Contact fields
    # -----------------------------------------------------

    if field == "contact.name":
        name = str(
            value
        ).strip()

        if not name:
            raise ValueError(
                "Name cannot be empty."
            )

        return name


    if field == "contact.mobile":
        return _normalize_mobile(
            value
        )


    if field == "contact.email":
        return _normalize_email(
            value
        )


    # -----------------------------------------------------
    # Enum fields
    # -----------------------------------------------------

    enum_type = (
        _find_enum_type(
            annotation
        )
    )


    if enum_type is not None:
        return _coerce_enum(
            enum_type,
            value,
        )


    # -----------------------------------------------------
    # Boolean fields
    # -----------------------------------------------------

    if _annotation_contains_type(
        annotation,
        bool,
    ):
        value = _coerce_boolean(
            value
        )


    # -----------------------------------------------------
    # Integer fields
    #
    # Example:
    # "2 BHK" -> 2
    # -----------------------------------------------------

    elif _annotation_contains_type(
        annotation,
        int,
    ):
        value = _coerce_integer(
            value
        )


    # -----------------------------------------------------
    # Floating-point fields
    # -----------------------------------------------------

    elif _annotation_contains_type(
        annotation,
        float,
    ):
        value = _coerce_float(
            value
        )


    # -----------------------------------------------------
    # String fields
    #
    # If the LLM happens to return a number for a field
    # represented as text, preserve it safely as text.
    # -----------------------------------------------------

    elif _annotation_contains_type(
        annotation,
        str,
    ):
        value = str(
            value
        ).strip()


    # -----------------------------------------------------
    # Final Pydantic validation
    # -----------------------------------------------------

    adapter = TypeAdapter(
        annotation
    )


    return adapter.validate_python(
        value
    )


# =========================================================
# Nested state setter
# =========================================================


def set_nested_value(
    state: ConversationState,
    field: str,
    value: Any,
) -> bool:
    """
    Safely set a qualified field such as:

        real_estate.timeline
        insurance.insurance_type
        it_services.technology_requirement
        contact.name

    The destination field's Pydantic annotation determines
    how the value is validated/coerced.
    """

    parts = field.split(".")


    if len(parts) != 2:
        state.metadata[
            "answer_validation_error"
        ] = {
            "field": field,
            "message":
                "Invalid qualification field path.",
        }

        return False


    parent_name, field_name = (
        parts
    )


    parent = getattr(
        state,
        parent_name,
        None,
    )


    if parent is None:
        state.metadata[
            "answer_validation_error"
        ] = {
            "field": field,
            "message":
                "The qualification section is not initialized.",
        }

        return False


    model_fields = getattr(
        parent.__class__,
        "model_fields",
        {},
    )


    field_info = model_fields.get(
        field_name
    )


    if field_info is None:
        state.metadata[
            "answer_validation_error"
        ] = {
            "field": field,
            "message":
                "Unknown qualification field.",
        }

        return False


    try:
        validated_value = (
            _coerce_field_value(
                field=field,
                annotation=(
                    field_info.annotation
                ),
                value=value,
            )
        )


        setattr(
            parent,
            field_name,
            validated_value,
        )


        state.mark_field_complete(
            field
        )


        state.metadata.pop(
            "answer_validation_error",
            None,
        )


        return True


    except (
        ValueError,
        TypeError,
        ValidationError,
    ) as exc:

        state.metadata[
            "answer_validation_error"
        ] = {
            "field": field,
            "message": str(exc),
        }


        return False


# =========================================================
# Public answer application
# =========================================================


def apply_answer(
    state: ConversationState,
    field: str,
    value: Any,
) -> ConversationState:
    """
    Validate and apply an extracted answer.

    Invalid answers are not written to the model and the
    field is not marked complete.
    """

    success = set_nested_value(
        state,
        field,
        value,
    )


    if not success:
        error = state.metadata.get(
            "answer_validation_error",
            {},
        )


        state.metadata.setdefault(
            "unapplied_answers",
            [],
        ).append(
            {
                "field": field,
                "reason": error.get(
                    "message",
                    "Validation failed.",
                ),
            }
        )


    return state