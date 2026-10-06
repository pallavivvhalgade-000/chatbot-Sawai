from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from app.domain.enums import (
    ConversationMode,
    MainIntent,
    ServiceType,
)
from app.domain.models import (
    ContactDetails,
    InsuranceRequirement,
    ITRequirement,
    Lead,
    RealEstateRequirement,
)


class ConversationState(BaseModel):
    """
    Complete state of one chatbot conversation.

    This object is passed through LangGraph on every turn.
    """

    session_id: str = Field(
        default_factory=lambda: str(uuid4())
    )

    mode: ConversationMode = ConversationMode.MAIN_MENU

    last_user_message: str | None = None

    intent: MainIntent | None = None

    service: ServiceType | None = None

    user_goal: str | None = None

    # ---------------------------------------------------------
    # Service-specific requirements
    # ---------------------------------------------------------

    real_estate: RealEstateRequirement | None = None

    insurance: InsuranceRequirement | None = None

    it_services: ITRequirement | None = None

    # ---------------------------------------------------------
    # Navigation / editing
    # ---------------------------------------------------------

    question_history: list[str] = Field(
        default_factory=list
    )

    pending_action: str | None = None

    action_target: str | None = None

    editing_field: str | None = None

    # ---------------------------------------------------------
    # Contact / lead
    # ---------------------------------------------------------

    contact: ContactDetails = Field(
    default_factory=ContactDetails
    )

    lead: Lead | None = None

    # ---------------------------------------------------------
    # Qualification tracking
    # ---------------------------------------------------------

    current_field: str | None = None

    completed_fields: list[str] = Field(
        default_factory=list
    )

    qualification_complete: bool = False

    requirement_summary: dict[str, Any] = Field(
        default_factory=dict
    )

    # ---------------------------------------------------------
    # Conversation history
    # ---------------------------------------------------------

    history: list[dict[str, Any]] = Field(
        default_factory=list
    )

    previous_modes: list[ConversationMode] = Field(
        default_factory=list
    )

    # ---------------------------------------------------------
    # Internal metadata
    # ---------------------------------------------------------

    metadata: dict[str, Any] = Field(
        default_factory=dict
    )

    def active_requirement(self) -> Any:
        """
        Return the requirement object for the selected service.
        """

        if self.service == ServiceType.REAL_ESTATE:
            return self.real_estate

        if self.service == ServiceType.INSURANCE:
            return self.insurance

        if self.service == ServiceType.IT_SERVICES:
            return self.it_services

        return None

    def mark_field_complete(self, field: str) -> None:
        """
        Mark a qualification field as completed.
        """

        if field not in self.completed_fields:
            self.completed_fields.append(field)

    def go_to_mode(self, mode: ConversationMode) -> None:
        """
        Change conversation mode while preserving navigation history.
        """

        if self.mode != mode:
            self.previous_modes.append(self.mode)

        self.mode = mode

    def back(self) -> None:
        """
        Return to the previous conversation mode.
        """

        if self.previous_modes:
            self.mode = self.previous_modes.pop()