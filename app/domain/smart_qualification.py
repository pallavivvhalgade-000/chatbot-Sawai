from typing import Any

from app.domain.qualification import (
    apply_answer,
)
from app.domain.qualification_plan import (
    get_missing_question_fields,
    get_nested_value,
    is_field_filled,
)
from app.domain.state import (
    ConversationState,
)


def apply_prefill_updates(
    state: ConversationState,
    updates: dict[str, Any],
    exclude_fields: set[str] | None = None,
) -> ConversationState:
    """
    Apply additional fields extracted from a user's message.

    Existing values are never overwritten.

    Contact details are never silently filled by this
    multi-field helper.
    """

    if not updates:
        return state


    excluded = (
        exclude_fields
        or set()
    )


    allowed_fields = set(
        get_missing_question_fields(
            state
        )
    )


    applied: list[str] = []

    rejected: list[
        dict[str, str]
    ] = []


    for field, value in (
        updates.items()
    ):

        if field in excluded:
            continue


        if field.startswith(
            "contact."
        ):
            continue


        if field not in allowed_fields:
            continue


        current_value = (
            get_nested_value(
                state,
                field,
            )
        )


        # Never overwrite something already supplied.
        if is_field_filled(
            current_value
        ):
            continue


        state.metadata.pop(
            "answer_validation_error",
            None,
        )


        apply_answer(
            state=state,
            field=field,
            value=value,
        )


        new_value = (
            get_nested_value(
                state,
                field,
            )
        )


        if is_field_filled(
            new_value
        ):
            applied.append(
                field
            )

        else:
            error = (
                state.metadata.get(
                    "answer_validation_error",
                    {}
                )
            )

            rejected.append(
                {
                    "field": field,
                    "reason": str(
                        error.get(
                            "message",
                            "Validation failed.",
                        )
                    ),
                }
            )


        # Optional prefill failure should not force the
        # customer to repeat their current primary answer.
        state.metadata.pop(
            "answer_validation_error",
            None,
        )


    if applied:
        state.metadata[
            "smart_prefill_applied"
        ] = applied


    if rejected:
        state.metadata[
            "smart_prefill_rejected"
        ] = rejected


    return state