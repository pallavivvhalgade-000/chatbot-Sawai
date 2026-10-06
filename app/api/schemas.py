from typing import Literal

from pydantic import (
    BaseModel,
    Field,
    model_validator,
)

from app.core.config import settings


ChatAction = Literal[
    "back",
    "main_menu",
    "edit_details",
    "edit_field",
    "request_call",
    "whatsapp",
]


class ChatRequest(BaseModel):
    """
    A request may contain either natural language or
    a deterministic navigation action.
    """

    message: str | None = Field(
        default=None,
        min_length=1,
        max_length=(
            settings.max_chat_message_length
        ),
    )

    session_id: str | None = Field(
        default=None,
        max_length=128,
    )

    action: ChatAction | None = None

    target: str | None = Field(
        default=None,
        max_length=128,
    )


    @model_validator(
        mode="after"
    )
    def validate_request(self):

        has_message = bool(
            self.message
            and self.message.strip()
        )

        if (
            not has_message
            and self.action is None
        ):
            raise ValueError(
                "Either message or action is required."
            )

        if (
            self.action == "edit_field"
            and not self.target
        ):
            raise ValueError(
                "target is required for edit_field."
            )

        return self


class SummaryItem(BaseModel):
    label: str
    value: str


class ChatActionOption(BaseModel):
    label: str
    action: ChatAction
    target: str | None = None
    url: str | None = None


class ChatResponse(BaseModel):
    session_id: str

    reply: str

    mode: str | None = None

    service: str | None = None

    next_field: str | None = None

    progress: str | None = None

    qualification_complete: bool = False

    lead_created: bool = False

    lead_id: str | None = None

    handoff_recommended: bool = False

    menu_options: list[str] = Field(
        default_factory=list
    )

    summary: list[SummaryItem] = Field(
        default_factory=list
    )

    actions: list[
        ChatActionOption
    ] = Field(
        default_factory=list
    )


class HealthResponse(BaseModel):
    status: str
    environment: str