from dataclasses import dataclass
from typing import Callable

from app.domain.enums import (
    InsuranceType,
    ServiceType,
)
from app.domain.state import ConversationState


@dataclass(frozen=True)
class QuestionDefinition:
    """
    Defines one qualification question.

    `condition` determines whether the question applies.
    """

    field: str
    question: str
    required: bool = True
    condition: Callable[[ConversationState], bool] = lambda state: True


def service_is(
    service: ServiceType,
) -> Callable[[ConversationState], bool]:
    """Create a condition that checks the active service."""

    return lambda state: state.service == service


def insurance_is(
    insurance_type: InsuranceType,
) -> Callable[[ConversationState], bool]:
    """Create an insurance-specific condition."""

    return lambda state: (
        state.service == ServiceType.INSURANCE
        and state.insurance.insurance_type == insurance_type
    )


COMMON_CONTACT_QUESTIONS = [
    QuestionDefinition(
        field="contact.name",
        question="May I have your name?",
    ),
    QuestionDefinition(
        field="contact.mobile",
        question="What mobile number should our team use to contact you?",
    ),
    QuestionDefinition(
        field="contact.email",
        question="Would you like to provide your email address as well?",
        required=False,
    ),
]


REAL_ESTATE_QUESTIONS = [
    QuestionDefinition(
        field="real_estate.requirement_type",
        question="Are you looking to buy, sell, rent, invest, or evaluate a property?",
        condition=service_is(ServiceType.REAL_ESTATE),
    ),
    QuestionDefinition(
        field="real_estate.property_type",
        question="What type of property are you looking for?",
        condition=service_is(ServiceType.REAL_ESTATE),
    ),
    QuestionDefinition(
        field="real_estate.purpose",
        question="What is the main purpose of the property?",
        condition=service_is(ServiceType.REAL_ESTATE),
    ),
    QuestionDefinition(
        field="real_estate.location",
        question="Which location or area are you considering?",
        condition=service_is(ServiceType.REAL_ESTATE),
    ),
    QuestionDefinition(
        field="real_estate.budget",
        question="What is your approximate budget?",
        condition=service_is(ServiceType.REAL_ESTATE),
    ),
    QuestionDefinition(
        field="real_estate.property_size",
        question="What property size are you looking for?",
        required=False,
        condition=service_is(ServiceType.REAL_ESTATE),
    ),
    QuestionDefinition(
        field="real_estate.bedrooms",
        question="How many bedrooms do you need?",
        required=False,
        condition=service_is(ServiceType.REAL_ESTATE),
    ),
    QuestionDefinition(
        field="real_estate.timeline",
        question="When are you planning to make the move or complete the transaction?",
        condition=service_is(ServiceType.REAL_ESTATE),
    ),
    QuestionDefinition(
        field="real_estate.financing_requirement",
        question="Will you require financing assistance?",
        required=False,
        condition=service_is(ServiceType.REAL_ESTATE),
    ),
]


INSURANCE_COMMON_QUESTIONS = [
    QuestionDefinition(
        field="insurance.insurance_type",
        question="What type of insurance assistance do you need?",
        condition=service_is(ServiceType.INSURANCE),
    ),
    QuestionDefinition(
        field="insurance.objective",
        question="What would you like the insurance to help you achieve?",
        condition=service_is(ServiceType.INSURANCE),
    ),
    QuestionDefinition(
        field="insurance.timeline",
        question="When would you like to proceed?",
        required=False,
        condition=service_is(ServiceType.INSURANCE),
    ),
]


INSURANCE_LIFE_QUESTIONS = [
    QuestionDefinition(
        field="insurance.age",
        question="What is the age of the person to be insured?",
        condition=insurance_is(InsuranceType.LIFE),
    ),
    QuestionDefinition(
        field="insurance.desired_cover",
        question="What approximate life cover are you considering?",
        condition=insurance_is(InsuranceType.LIFE),
    ),
    QuestionDefinition(
        field="insurance.existing_insurance",
        question="Do you already have any life insurance?",
        required=False,
        condition=insurance_is(InsuranceType.LIFE),
    ),
]


INSURANCE_HEALTH_QUESTIONS = [
    QuestionDefinition(
        field="insurance.age",
        question="What is the age of the person or family members to be covered?",
        condition=insurance_is(InsuranceType.HEALTH),
    ),
    QuestionDefinition(
        field="insurance.desired_cover",
        question="What approximate health cover are you considering?",
        condition=insurance_is(InsuranceType.HEALTH),
    ),
    QuestionDefinition(
        field="insurance.existing_insurance",
        question="Do you already have health insurance?",
        required=False,
        condition=insurance_is(InsuranceType.HEALTH),
    ),
]


IT_QUESTIONS = [
    QuestionDefinition(
        field="it_services.technology_requirement",
        question="What technology solution do you need?",
        condition=service_is(ServiceType.IT_SERVICES),
    ),
    QuestionDefinition(
        field="it_services.sub_service",
        question="Could you describe the specific solution or feature you need?",
        condition=service_is(ServiceType.IT_SERVICES),
    ),
    QuestionDefinition(
        field="it_services.current_process",
        question="How are you handling this process today?",
        condition=service_is(ServiceType.IT_SERVICES),
    ),
    QuestionDefinition(
        field="it_services.existing_system",
        question="Do you already have an existing system or software?",
        required=False,
        condition=service_is(ServiceType.IT_SERVICES),
    ),
    QuestionDefinition(
        field="it_services.technical_requirements",
        question="Are there any important technical requirements or integrations?",
        required=False,
        condition=service_is(ServiceType.IT_SERVICES),
    ),
    QuestionDefinition(
        field="it_services.data_sources",
        question="What data sources or systems would the solution need to work with?",
        required=False,
        condition=service_is(ServiceType.IT_SERVICES),
    ),
    QuestionDefinition(
        field="it_services.objective",
        question="What outcome are you hoping to achieve?",
        condition=service_is(ServiceType.IT_SERVICES),
    ),
    QuestionDefinition(
        field="it_services.budget",
        question="What is your approximate budget?",
        required=False,
        condition=service_is(ServiceType.IT_SERVICES),
    ),
    QuestionDefinition(
        field="it_services.timeline",
        question="When would you like the solution to be ready?",
        condition=service_is(ServiceType.IT_SERVICES),
    ),
]


ALL_QUESTIONS = (
    REAL_ESTATE_QUESTIONS
    + INSURANCE_COMMON_QUESTIONS
    + INSURANCE_LIFE_QUESTIONS
    + INSURANCE_HEALTH_QUESTIONS
    + IT_QUESTIONS
    + COMMON_CONTACT_QUESTIONS
)

def _get_nested_value(state: ConversationState, path: str):
    """
    Read a nested Pydantic model field.

    Example:
        "real_estate.location"
    """

    value = state

    for part in path.split("."):
        value = getattr(value, part, None)

        if value is None:
            return None

    return value


def get_next_question(
    state: ConversationState,
) -> QuestionDefinition | None:
    """
    Find the first applicable unanswered qualification question.

    The ordering is deterministic, but the conditions make the flow dynamic.
    """

    for question in ALL_QUESTIONS:
        if not question.condition(state):
            continue

        if not question.required:
            # Optional questions are skipped for now.
            # They can be requested later if needed.
            continue

        value = _get_nested_value(state, question.field)

        if value is None or value == "":
            return question

    return None