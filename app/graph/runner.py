from app.domain.state import (
    ConversationState,
)

from app.graph.conversation import (
    conversation_graph,
)

from app.graph.session_store import (
    create_session,
    get_session,
    save_session,
)


def run_conversation(
    message: str | None = None,
    session_id: str | None = None,
    action: str | None = None,
    target: str | None = None,
) -> ConversationState:
    """
    Run either a natural-language message or a deterministic
    widget action through the LangGraph conversation engine.
    """

    if session_id:
        state = get_session(
            session_id
        )

        if state is None:
            state = ConversationState(
                session_id=session_id
            )

    else:
        state = create_session()


    # ---------------------------------------------------------
    # Remove transient response data from previous turn
    # ---------------------------------------------------------

    for key in (
        "response",
        "next_question",
        "main_menu",
        "action_options",
        "external_url",
        "lead_error",
    ):
        state.metadata.pop(
            key,
            None,
        )


    # ---------------------------------------------------------
    # Current request
    # ---------------------------------------------------------

    state.last_user_message = (
        message
    )

    state.pending_action = (
        action
    )

    state.action_target = (
        target
    )


    if message:
        state.history.append(
            {
                "role": "user",
                "content": message,
            }
        )


    if action:
        state.history.append(
            {
                "role": "action",
                "content": action,
                "target": target,
            }
        )


    result = conversation_graph.invoke(
        state
    )


    if isinstance(
        result,
        ConversationState,
    ):
        final_state = result

    else:
        final_state = (
            ConversationState.model_validate(
                result
            )
        )

    # ---------------------------------------------------------
    # Store the assistant reply in conversation history
    # ---------------------------------------------------------

    assistant_reply = (
        final_state.metadata.get(
            "response"
        )
        or final_state.metadata.get(
            "next_question"
        )
    )


    if (
        isinstance(
            assistant_reply,
            str,
        )
        and assistant_reply.strip()
    ):

        last_history_item = (
            final_state.history[-1]
            if final_state.history
            else None
        )


        already_stored = (
            isinstance(
                last_history_item,
                dict,
            )
            and last_history_item.get(
                "role"
            )
            == "assistant"
            and last_history_item.get(
                "content"
            )
            == assistant_reply.strip()
        )


        if not already_stored:

            final_state.history.append(
                {
                    "role": "assistant",
                    "content": (
                        assistant_reply.strip()
                    ),
                }
            )


    # Prevent unlimited session growth.
    final_state.history = (
        final_state.history[-200:]
    )

    save_session(
        final_state
    )

    return final_state