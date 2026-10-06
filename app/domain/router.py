from app.domain.classification import ClassificationResult
from app.domain.enums import (
    ConversationMode,
    MainIntent,
    ServiceType,
)
from app.domain.state import ConversationState


def apply_classification(
    state: ConversationState,
    result: ClassificationResult,
) -> ConversationState:
    state.intent = result.intent
    state.service = result.service
    state.user_goal = result.user_goal


    if result.location:
        if result.service == ServiceType.REAL_ESTATE:
            if state.real_estate is None:
                from app.domain.models import RealEstateRequirement

                state.real_estate = RealEstateRequirement()

            state.real_estate.location = result.location

    if result.bedrooms:
        if result.service == ServiceType.REAL_ESTATE:
            if state.real_estate is None:
                from app.domain.models import RealEstateRequirement

                state.real_estate = RealEstateRequirement()

            state.real_estate.bedrooms = result.bedrooms

    if result.requirement_type:
        if state.real_estate is None:
            from app.domain.models import RealEstateRequirement

            state.real_estate = RealEstateRequirement()

        state.real_estate.requirement_type = (
            result.requirement_type
        )

    if result.property_type:
        if state.real_estate is None:
            from app.domain.models import RealEstateRequirement

            state.real_estate = RealEstateRequirement()

        state.real_estate.property_type = (
            result.property_type
        )

    if result.insurance_type:
        if state.insurance is None:
            from app.domain.models import InsuranceRequirement

            state.insurance = InsuranceRequirement()

        state.insurance.insurance_type = (
            result.insurance_type
        )

    if result.technology_requirement:
        if state.it_services is None:
            from app.domain.models import ITRequirement

            state.it_services = ITRequirement()

        state.it_services.technology_requirement = (
            result.technology_requirement
        )

    if result.intent == MainIntent.SERVICE_REQUEST:
        state.mode = ConversationMode.QUALIFICATION

    elif result.intent == MainIntent.TALK_TO_EXPERT:
        state.mode = ConversationMode.EXPERT_REQUEST

    elif result.intent == MainIntent.QUESTION:
        state.mode = ConversationMode.GENERAL_CHAT

    elif result.intent == MainIntent.UNSURE_HELP:
        state.mode = ConversationMode.MAIN_MENU

    else:
        state.mode = ConversationMode.GENERAL_CHAT

    return state