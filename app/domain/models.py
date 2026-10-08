from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import (
    AIGenAIType,
    ContactPreference,
    FinancingRequirement,
    InsuranceType,
    ITServiceType,
    LeadPriority,
    LeadStatus,
    PropertyType,
    RequirementType,
    ServiceType,
    TeamType,
    TimelineType,
)


class ContactDetails(BaseModel):
    """Customer contact information."""

    name: str | None = None
    mobile: str | None = None
    email: str | None = None
    contact_preference: ContactPreference | None = None
    
    consent_to_contact: bool | None = None
    consent_at: str | None = None


class RealEstateRequirement(BaseModel):
    """Fields collected for real-estate qualification."""

    requirement_type: RequirementType | None = None
    property_type: PropertyType | None = None
    purpose: str | None = None
    location: str | None = None
    budget: str | None = None
    property_size: str | None = None
    bedrooms: int | None = None
    timeline: TimelineType | None = None
    financing_requirement: FinancingRequirement | None = None


class InsuranceRequirement(BaseModel):
    """Fields collected for insurance qualification."""

    insurance_type: InsuranceType | None = None

    # Common insurance qualification information.
    objective: str | None = None
    age: int | None = None
    desired_cover: str | None = None
    existing_insurance: str | None = None
    existing_policy_details: str | None = None
    vehicle_details: str | None = None
    property_details: str | None = None
    business_details: str | None = None
    renewal_date: str | None = None
    timeline: TimelineType | None = None


class ITRequirement(BaseModel):
    """Fields collected for IT-services qualification."""

    technology_requirement: ITServiceType | None = None
    ai_genai_type: AIGenAIType | None = None

    sub_service: str | None = None
    current_process: str | None = None
    existing_system: str | None = None
    technical_requirements: str | None = None
    data_sources: str | None = None
    objective: str | None = None
    budget: str | None = None
    timeline: TimelineType | None = None


class Lead(BaseModel):
    """
    Structured lead record.

    This is the domain model. Database persistence will be added later.
    """

    model_config = ConfigDict(use_enum_values=True)

    lead_id: str | None = None

    # Contact
    contact: ContactDetails = Field(default_factory=ContactDetails)

    # Classification
    service: ServiceType | None = None
    sub_service: str | None = None

    # Service-specific requirements
    real_estate: RealEstateRequirement | None = None
    insurance: InsuranceRequirement | None = None
    it_services: ITRequirement | None = None

    # Business workflow
    priority: LeadPriority | None = None
    status: LeadStatus = LeadStatus.NEW
    assigned_to: TeamType | None = None

    source: str = "website_chatbot"
    notes: str | None = None

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    def summary(self) -> dict[str, Any]:
        """Return a structured summary suitable for display or persistence."""

        return {
            "lead_id": self.lead_id,
            "name": self.contact.name,
            "mobile": self.contact.mobile,
            "email": self.contact.email,
            "service": self.service,
            "sub_service": self.sub_service,
            "real_estate": self.real_estate.model_dump()
            if self.real_estate
            else None,
            "insurance": self.insurance.model_dump()
            if self.insurance
            else None,
            "it_services": self.it_services.model_dump()
            if self.it_services
            else None,
            "priority": self.priority,
            "status": self.status,
            "assigned_to": self.assigned_to,
            "source": self.source,
            "created_at": self.created_at.isoformat(),
        }