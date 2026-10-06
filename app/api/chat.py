import logging

from fastapi import (
    APIRouter,
    HTTPException,
    Request,
)
from starlette.concurrency import run_in_threadpool

from app.api.schemas import (
    ChatRequest,
    ChatResponse,
)
from app.core.config import settings
from app.core.rate_limit import limiter
from app.domain.state import ConversationState
from app.graph.runner import run_conversation

from app.api.schemas import (
    ChatActionOption,
    ChatRequest,
    ChatResponse,
    SummaryItem,
)

from app.domain.enums import (
    ConversationMode,
)

from app.domain.summary import (
    build_customer_summary,
    get_progress_label,
)


logger = logging.getLogger(__name__)


router = APIRouter(
    tags=["chat"]
)


def _enum_value(value):
    """
    Safely convert enum-like values into strings.
    """

    if value is None:
        return None

    if hasattr(value, "value"):
        return value.value

    return str(value)


def _build_customer_reply(
    state: ConversationState,
) -> str:
    """
    Select the customer-facing response from ConversationState.

    Internal metadata is never returned directly.
    """

    response = state.metadata.get("response")

    if isinstance(response, str) and response.strip():
        return response.strip()

    next_question = state.metadata.get(
        "next_question"
    )

    if (
        isinstance(next_question, str)
        and next_question.strip()
    ):
        return next_question.strip()

    customer_message = state.metadata.get(
        "customer_message"
    )

    if (
        isinstance(customer_message, str)
        and customer_message.strip()
    ):
        return customer_message.strip()

    if state.metadata.get("lead_error"):
        return (
            "I still need some contact information before "
            "I can save your request. Please provide the "
            "requested details."
        )

    if state.qualification_complete:
        return (
            "Thank you. I have the information needed "
            "for your requirement."
        )

    return (
        "I can help with Real Estate, Insurance, "
        "IT Services, or connect you with the "
        "appropriate team."
    )


def _build_chat_response(
    state: ConversationState,
) -> ChatResponse:

    menu = state.metadata.get(
        "main_menu",
        [],
    )

    if not isinstance(
        menu,
        list,
    ):
        menu = []


    summary = []

    if (
        state.qualification_complete
        and state.mode
        != ConversationMode.MAIN_MENU
    ):
        summary = [
            SummaryItem(
                **item
            )
            for item in (
                build_customer_summary(
                    state
                )
            )
        ]


    progress = None

    if (
        state.current_field
        or state.qualification_complete
    ) and (
        state.mode
        != ConversationMode.MAIN_MENU
    ):
        progress = (
            get_progress_label(
                state
            )
        )


    return ChatResponse(
        session_id=(
            state.session_id
        ),

        reply=(
            _build_customer_reply(
                state
            )
        ),

        mode=(
            _enum_value(
                state.mode
            )
        ),

        service=(
            _enum_value(
                state.service
            )
        ),

        next_field=(
            state.current_field
        ),

        progress=progress,

        qualification_complete=(
            state.qualification_complete
        ),

        lead_created=bool(
            state.metadata.get(
                "lead_created",
                False,
            )
        ),

        lead_id=(
            state.metadata.get(
                "lead_id"
            )
        ),

        handoff_recommended=bool(
            state.metadata.get(
                "handoff_recommended",
                False,
            )
        ),

        menu_options=[
            str(item)
            for item in menu
        ],

        summary=summary,

        actions=(
            _build_actions(
                state
            )
        ),
    )

def _build_actions(
    state: ConversationState,
) -> list[ChatActionOption]:

    # Node-supplied actions override defaults.
    if "action_options" in state.metadata:

        raw_actions = state.metadata.get(
            "action_options"
        )

        if not isinstance(
            raw_actions,
            list,
        ):
            return []

        actions = []

        for item in raw_actions:
            if not isinstance(
                item,
                dict,
            ):
                continue

            try:
                actions.append(
                    ChatActionOption(
                        **item
                    )
                )

            except Exception:
                continue

        return actions


    # Completed requirement.
    if (
        state.qualification_complete
        and state.mode
        != ConversationMode.MAIN_MENU
    ):
        actions = [
            ChatActionOption(
                label="Edit Details",
                action="edit_details",
            ),
            ChatActionOption(
                label="Request a Call",
                action="request_call",
            ),
        ]

        if settings.whatsapp_url:
            actions.append(
                ChatActionOption(
                    label="WhatsApp",
                    action="whatsapp",
                    url=(
                        settings.whatsapp_url
                    ),
                )
            )

        actions.append(
            ChatActionOption(
                label="Main Menu",
                action="main_menu",
            )
        )

        return actions


    # Qualification in progress.
    if state.current_field:
        return [
            ChatActionOption(
                label="Back",
                action="back",
            ),
            ChatActionOption(
                label="Main Menu",
                action="main_menu",
            ),
        ]


    return [
        ChatActionOption(
            label="Main Menu",
            action="main_menu",
        )
    ]

@router.post(
    "/chat",
    response_model=ChatResponse,
)
@limiter.limit(
    settings.chat_rate_limit
)
async def chat(
    request: Request,
    payload: ChatRequest,
):
    try:
        # A normal chat request has a message.
        # A Step 13 navigation request may only have an action.
        message = (
            payload.message.strip()
            if payload.message
            else None
        )

        state = await run_in_threadpool(
            run_conversation,
            message,
            payload.session_id,
            payload.action,
            payload.target,
        )

        return _build_chat_response(
            state
        )

    except HTTPException:
        raise

    except Exception:
        logger.exception(
            "Chat request failed."
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "The chat service is temporarily "
                "unable to process this request."
            ),
        )

    