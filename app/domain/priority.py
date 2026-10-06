from app.domain.enums import (
    InsuranceType,
    LeadPriority,
    RequirementType,
    ServiceType,
    TimelineType,
)
from app.domain.state import ConversationState


def _enum_value(value):
    """
    Return the underlying value of an enum.
    """

    if value is None:
        return None

    if hasattr(value, "value"):
        return value.value

    return value


def _has_contact_details(state: ConversationState) -> bool:
    """
    Check whether useful customer contact information exists.
    """

    if state.contact is None:
        return False

    return bool(
        state.contact.name
        or state.contact.mobile
        or state.contact.email
    )


def calculate_lead_priority(
    state: ConversationState,
) -> LeadPriority:
    """
    Calculate internal lead priority using deterministic rules.

    This value is for internal routing only.
    It should not be displayed to customers.
    """

    score = 0

    service = _enum_value(state.service)

    # ---------------------------------------------------------
    # Contact information
    # ---------------------------------------------------------

    if _has_contact_details(state):
        score += 2

    if state.contact and state.contact.mobile:
        score += 2

    # ---------------------------------------------------------
    # Real Estate
    # ---------------------------------------------------------

    if service == ServiceType.REAL_ESTATE.value:
        requirement = state.real_estate

        if requirement:
            requirement_type = _enum_value(
                requirement.requirement_type
            )

            timeline = _enum_value(
                requirement.timeline
            )

            if requirement_type in {
                RequirementType.BUY.value,
                RequirementType.SELL.value,
                RequirementType.RENT.value,
            }:
                score += 3

            if requirement_type == RequirementType.INVESTMENT.value:
                score += 3

            if timeline == TimelineType.IMMEDIATE.value:
                score += 4

            elif timeline == TimelineType.WITHIN_1_MONTH.value:
                score += 3

            elif timeline == TimelineType.ONE_TO_THREE_MONTHS.value:
                score += 2

            if requirement.location:
                score += 2

            if requirement.budget:
                score += 2

            if requirement.property_type:
                score += 1

            if requirement.bedrooms:
                score += 1

    # ---------------------------------------------------------
    # Insurance
    # ---------------------------------------------------------

    elif service == ServiceType.INSURANCE.value:
        requirement = state.insurance

        if requirement:
            insurance_type = _enum_value(
                requirement.insurance_type
            )

            timeline = _enum_value(
                requirement.timeline
            )

            if insurance_type:
                score += 2

            if timeline == TimelineType.IMMEDIATE.value:
                score += 4

            elif timeline == TimelineType.WITHIN_1_MONTH.value:
                score += 3

            elif timeline == TimelineType.ONE_TO_THREE_MONTHS.value:
                score += 2

            if insurance_type == InsuranceType.RENEWAL.value:
                score += 3

            if (
                insurance_type
                == InsuranceType.EXISTING_POLICY_ASSISTANCE.value
            ):
                score += 3

            if requirement.desired_cover:
                score += 2

            if requirement.existing_insurance:
                score += 1

    # ---------------------------------------------------------
    # IT Services
    # ---------------------------------------------------------

    elif service == ServiceType.IT_SERVICES.value:
        requirement = state.it_services

        if requirement:
            timeline = _enum_value(
                requirement.timeline
            )

            if requirement.technology_requirement:
                score += 3

            if timeline == TimelineType.IMMEDIATE.value:
                score += 4

            elif timeline == TimelineType.WITHIN_1_MONTH.value:
                score += 3

            elif timeline == TimelineType.ONE_TO_THREE_MONTHS.value:
                score += 2

            if requirement.objective:
                score += 2

            if requirement.current_process:
                score += 1

            if requirement.existing_system:
                score += 1

            if requirement.technical_requirements:
                score += 1

            if requirement.budget:
                score += 2

    # ---------------------------------------------------------
    # Convert score to priority
    # ---------------------------------------------------------

    if score >= 10:
        return LeadPriority.HOT

    if score >= 5:
        return LeadPriority.WARM

    return LeadPriority.COLD