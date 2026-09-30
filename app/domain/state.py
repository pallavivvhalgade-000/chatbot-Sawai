from typing import Any

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

    LangGraph will eventually use this object as the state contract.
    """

    # Session
    session_id: str

    # Current conversation mode
    mode: ConversationMode = ConversationMode.MAIN_MENU

    # User's latest message
    last_user_message: str | None = None

    # Intent classification
    intent: MainIntent | None = None
    service: ServiceType | None = None

    # Natural-language understanding
    user_goal: str | None = None

    # Service-specific qualification state
    real_estate: RealEstateRequirement = Field(
        default_factory=RealEstateRequirement
    )

    insurance: InsuranceRequirement = Field(
        default_factory=InsuranceRequirement
    )

    it_services: ITRequirement = Field(
        default_factory=ITRequirement
    )

    # Contact information
    contact: ContactDetails = Field(
        default_factory=ContactDetails
    )

    # Lead state
    lead: Lead | None = None

    # Qualification progress
    current_field: str | None = None
    completed_fields: list[str] = Field(default_factory=list)

    # Navigation
    history: list[str] = Field(default_factory=list)
    previous_modes: list[ConversationMode] = Field(default_factory=list)

    # Requirement summary shown to customer
    requirement_summary: str | None = None

    # Whether the conversation can now create a lead
    qualification_complete: bool = False

    # General chatbot metadata
    metadata: dict[str, Any] = Field(default_factory=dict)

    def active_requirement(self) -> (
        RealEstateRequirement
        | InsuranceRequirement
        | ITRequirement
        | None
    ):
        """Return the requirement model for the selected service."""

        if self.service == ServiceType.REAL_ESTATE:
            return self.real_estate

        if self.service == ServiceType.INSURANCE:
            return self.insurance

        if self.service == ServiceType.IT_SERVICES:
            return self.it_services

        return None

    def mark_field_complete(self, field_name: str) -> None:
        """Mark a qualification field as completed."""

        if field_name not in self.completed_fields:
            self.completed_fields.append(field_name)

    def go_to_mode(self, mode: ConversationMode) -> None:
        """Move to another conversation mode while preserving navigation."""

        if self.mode != mode:
            self.previous_modes.append(self.mode)

        self.mode = mode

    def back(self) -> ConversationMode:
        """Return to the previous conversation mode."""

        if self.previous_modes:
            self.mode = self.previous_modes.pop()

        return self.mode