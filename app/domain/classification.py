from typing import Any

from pydantic import BaseModel, Field

from app.domain.enums import (
    InsuranceType,
    ITServiceType,
    MainIntent,
    PropertyType,
    RequirementType,
    ServiceType,
)


class ClassificationResult(BaseModel):
    intent: MainIntent = MainIntent.GENERAL
    service: ServiceType | None = None

    requirement_type: RequirementType | None = None
    property_type: PropertyType | None = None

    insurance_type: InsuranceType | None = None

    technology_requirement: ITServiceType | None = None

    user_goal: str | None = None

    location: str | None = None
    bedrooms: int | None = None

    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
    )

    missing_information: list[str] = Field(
        default_factory=list
    )

    reasoning: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")