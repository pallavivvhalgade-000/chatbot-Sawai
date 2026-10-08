from typing import Literal

from fastapi import (
    APIRouter,
    Response,
    status,
)

from pydantic import (
    BaseModel,
    Field,
)

from app.db.analytics import (
    record_analytics_event,
)


router = APIRouter(
    prefix="/analytics",
    tags=["analytics"],
)


AllowedEvent = Literal[
    "chatbot_open",
    "expert_request",
    "call_request",
    "whatsapp_request",
]


class AnalyticsEventRequest(
    BaseModel
):
    event_type: AllowedEvent

    session_id: str | None = Field(
        default=None,
        max_length=100,
    )

    service: str | None = Field(
        default=None,
        max_length=50,
    )


@router.post(
    "/event",
    status_code=status.HTTP_204_NO_CONTENT,
)
def analytics_event(
    payload: AnalyticsEventRequest,
) -> Response:

    record_analytics_event(
        event_type=payload.event_type,
        session_id=payload.session_id,
        service=payload.service,
    )

    return Response(
        status_code=(
            status.HTTP_204_NO_CONTENT
        )
    )