from typing import Any


from app.db.leads import (
    save_or_update_lead_from_state,
)
from app.domain import state
from app.domain.classification import ClassificationResult
from app.domain.enums import (
    ConversationMode,
    MainIntent,
    ServiceType,
)
from app.domain.qualification_plan import (
    get_next_planned_question,
)
from app.domain.models import (
    InsuranceRequirement,
    ITRequirement,
    RealEstateRequirement,
)
from app.domain.qualification import apply_answer
from app.domain.state import ConversationState
from app.llm.answer_extractor import extract_answer
from app.rag.answering import answer_knowledge_question

from app.core.config import settings

from app.db.leads import (
    save_or_update_lead_from_state,
)

from app.domain.enums import (
    ContactPreference,
    ConversationMode,
    MainIntent,
    ServiceType,
)

from app.domain.summary import (
    get_editable_fields,
    get_field_label,
    get_question_for_field,
)

from app.domain.qualification_plan import (
    get_next_planned_question,
)

from app.domain.smart_qualification import (
    apply_prefill_updates,
)

from app.llm.qualification_extractor import (
    extract_qualification_updates,
)

from app.llm.classifier import (
    ClassificationResult,
    classify_message,
)


from app.db.lead_operations import (
    enqueue_lead_delivery,
    get_lead_events,
    record_lead_event,
)

from datetime import (
    datetime,
    timezone,
)

from app.db.lead_conversations import (
    link_lead_to_session,
)


def classify_node(
    state: ConversationState,
) -> ConversationState:
    """
    Classify the user's message, initialize the correct
    service state, then extract any additional qualification
    details already present in the same message.
    """

    result = classify_message(
        state.last_user_message
        or ""
    )


    # ---------------------------------------------------------
    # First apply normal classification
    # ---------------------------------------------------------

    apply_classification(
        state,
        result,
    )


    # ---------------------------------------------------------
    # Then perform smart multi-field extraction
    #
    # At this point:
    #
    # state.intent is current
    # state.service is current
    # service-specific requirement model exists
    # ---------------------------------------------------------

    if (
        state.intent
        == MainIntent.SERVICE_REQUEST
        and state.service
        not in {
            None,
            ServiceType.GENERAL,
        }
    ):
        extraction = (
            extract_qualification_updates(
                state=state,
                message=(
                    state.last_user_message
                    or ""
                ),
            )
        )


        state.metadata[
            "multi_field_extraction"
        ] = extraction.model_dump(
            mode="json"
        )


        apply_prefill_updates(
            state=state,
            updates=(
                extraction.updates
            ),
        )


    return state


def apply_classification(
    state: ConversationState,
    result: ClassificationResult,
) -> ConversationState:
    """
    Safely apply classifier output to ConversationState.

    The LLM extracts information.
    Python controls state transitions.
    """

    state.intent = result.intent

    previous_service = (
        state.service
    )

    new_service = (
        result.service
    )

    # If the classifier did not identify a new service,
    # preserve the existing conversation service.
    if new_service is None:
        effective_service = previous_service
    else:
        effective_service = new_service


    if (
        previous_service
        and effective_service
        and previous_service
        != ServiceType.GENERAL
        and effective_service
        != ServiceType.GENERAL
        and previous_service
        != effective_service
    ):

        
        # The previous lead stays in SQLite.
        # This state now begins a new service journey.

        state.lead = None

        state.qualification_complete = False

        state.completed_fields = []

        state.question_history = []

        state.current_field = None

        state.real_estate = None
        state.insurance = None
        state.it_services = None


    state.service = effective_service
    state.user_goal = result.user_goal

    # ---------------------------------------------------------
    # Real Estate
    # ---------------------------------------------------------

    if result.service == ServiceType.REAL_ESTATE:

        if state.real_estate is None:
            state.real_estate = RealEstateRequirement()

        if result.location:
            state.real_estate.location = (
                result.location
            )

        if result.bedrooms:
            state.real_estate.bedrooms = (
                result.bedrooms
            )

        if result.requirement_type:
            state.real_estate.requirement_type = (
                result.requirement_type
            )

        if result.property_type:
            state.real_estate.property_type = (
                result.property_type
            )

    # ---------------------------------------------------------
    # Insurance
    # ---------------------------------------------------------

    if result.service == ServiceType.INSURANCE:

        if state.insurance is None:
            state.insurance = InsuranceRequirement()

        if result.insurance_type:
            state.insurance.insurance_type = (
                result.insurance_type
            )

    # ---------------------------------------------------------
    # IT
    # ---------------------------------------------------------

    if result.service == ServiceType.IT_SERVICES:

        if state.it_services is None:
            state.it_services = ITRequirement()

        if result.technology_requirement:
            state.it_services.technology_requirement = (
                result.technology_requirement
            )

    # ---------------------------------------------------------
    # Conversation mode
    # ---------------------------------------------------------

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


def answer_node(
    state: ConversationState,
) -> ConversationState:
    """
    Apply the user's answer to the exact field that the
    conversation is currently asking for.

    Contact fields are handled deterministically.

    Other fields may use the LLM for extraction, but the LLM
    is NOT allowed to decide which state field gets modified.
    """

    field = state.current_field

    message = (
        state.last_user_message or ""
    ).strip()


    # ---------------------------------------------------------
    # Nothing to process
    # ---------------------------------------------------------

    if not field or not message:
        return state


    # Remove validation error from an earlier turn.
    state.metadata.pop(
        "answer_validation_error",
        None,
    )


    # ---------------------------------------------------------
    # Deterministic contact fields
    #
    # These do not need an LLM call.
    # ---------------------------------------------------------

    if field in {
        "contact.name",
        "contact.mobile",
        "contact.email",
    }:

        apply_answer(
            state=state,
            field=field,
            value=message,
        )


        validation_error = (
            state.metadata.get(
                "answer_validation_error"
            )
        )


        state.metadata[
            "last_extracted_answer"
        ] = {
            "field": field,
            "value": (
                None
                if validation_error
                else message
            ),
            "confidence": 1.0,
            "source":
                "deterministic",
        }


        if not validation_error:
            state.editing_field = None


        return state


    # ---------------------------------------------------------
    # Complex fields use the existing LLM extractor
    # ---------------------------------------------------------

    answer = extract_answer(
        state,
        message,
    )


    state.metadata[
        "last_extracted_answer"
    ] = answer.model_dump(
        mode="json"
    )


    if answer.value is None:
        state.metadata[
            "answer_validation_error"
        ] = {
            "field": field,
            "message":
                "No usable value was extracted.",
        }

        return state


    # ---------------------------------------------------------
    # SECURITY / STATE SAFETY
    #
    # IMPORTANT:
    #
    # Use `field`, which came from state.current_field.
    #
    # Do NOT use answer.field as the destination.
    #
    # The LLM may extract the value, but it cannot choose
    # which state field gets modified.
    # ---------------------------------------------------------

    apply_answer(
        state=state,
        field=field,
        value=answer.value,
    )


    if not state.metadata.get(
        "answer_validation_error"
    ):
        state.editing_field = None


    return state


def qualification_node(
    state: ConversationState,
) -> ConversationState:
    """
    Determine the next qualification question.

    Business/service questions are handled first.
    Contact details are then collected before the
    qualification can be marked complete.
    """

    # ---------------------------------------------------------
    # Retry the same field after validation failure
    # ---------------------------------------------------------

    validation_error = (
        state.metadata.pop(
            "answer_validation_error",
            None,
        )
    )


    if (
        validation_error
        and state.current_field
    ):
        state.qualification_complete = False

        state.mode = (
            ConversationMode.QUALIFICATION
        )


        question = get_question_for_field(
            state,
            state.current_field,
        )


        if question is not None:
            state.metadata[
                "next_question"
            ] = question.question

            state.metadata[
                "response"
            ] = (
                "I couldn't use that answer. "
                + question.question
            )

        else:
            state.metadata[
                "response"
            ] = (
                "I couldn't use that answer. "
                "Please try again."
            )


        return state

    # ---------------------------------------------------------
    # 1. Ask the next service-specific qualification question
    # ---------------------------------------------------------

    question = get_next_planned_question(state)

    # ---------------------------------------------------------
    # Privacy gate
    #
    # Do not collect Name / Mobile / Email until the user
    # explicitly agrees to be contacted.
    # ---------------------------------------------------------

    if (
        settings.require_contact_consent
        and question is not None
        and question.field.startswith(
            "contact."
        )
        and state.contact.consent_to_contact
        is not True
    ):

        state.qualification_complete = False

        state.current_field = None

        state.metadata.pop(
            "next_question",
            None,
        )

        state.metadata[
            "response"
        ] = (
            "Before I collect your contact details: "
            "your information will be used only to "
            "understand your requirement and connect "
            "you with the appropriate Sawai Associates "
            "team. Do you agree to be contacted "
            "regarding this enquiry?"
        )

        state.metadata[
            "action_options"
        ] = [
            {
                "label": "I Agree",
                "action":
                    "consent_contact",
            },
            {
                "label": "Main Menu",
                "action":
                    "main_menu",
            },
        ]

        return state

    if question is not None:
        state.qualification_complete = False
        state.mode = ConversationMode.QUALIFICATION

        state.current_field = (
            question.field
        )

        if (
            not state.question_history
            or state.question_history[-1]
            != question.field
        ):
            state.question_history.append(
                question.field
            )

        state.metadata["next_question"] = (
            question.question
        )

        # Remove any previous completion response.
        state.metadata.pop(
            "response",
            None,
        )

        return state


    # ---------------------------------------------------------
    # 2. Collect customer name
    # ---------------------------------------------------------

    if not state.contact.name:
        state.qualification_complete = False
        state.mode = ConversationMode.QUALIFICATION

        state.current_field = (
            "contact.name"
        )

        if (
            not state.question_history
            or state.question_history[-1]
            != "contact.name"
        ):
            state.question_history.append(
                "contact.name"
            )

        state.metadata["next_question"] = (
            "May I have your name?"
        )

        state.metadata["response"] = (
            "Before I save your request, "
            "may I have your name?"
        )

        return state


    # ---------------------------------------------------------
    # 3. Collect a contact number if no mobile/email exists
    # ---------------------------------------------------------

    if (
        not state.contact.mobile
        and not state.contact.email
    ):
        state.qualification_complete = False
        state.mode = ConversationMode.QUALIFICATION

        state.current_field = (
            "contact.mobile"
        )

        if (
            not state.question_history
            or state.question_history[-1]
            != "contact.mobile"
        ):
            state.question_history.append(
                "contact.mobile"
            )

        state.metadata["next_question"] = (
            "Please provide your mobile number."
        )

        state.metadata["response"] = (
            "Thank you. Please provide a mobile number "
            "so the team can contact you."
        )

        return state


    # ---------------------------------------------------------
    # 4. Everything required is now collected
    # ---------------------------------------------------------

    state.qualification_complete = True

    state.current_field = None
    state.editing_field = None

    state.requirement_summary = (
        build_requirement_summary(
            state
        )
    )

    state.metadata.pop(
        "next_question",
        None,
    )

    state.metadata.pop(
        "response",
        None,
    )

    return state


def rag_node(
    state: ConversationState,
) -> ConversationState:
    """
    Answer a knowledge question using service-aware,
    thresholded RAG retrieval.
    """

    question = (
        state.last_user_message or ""
    ).strip()


    result = answer_knowledge_question(
        question=question,
        service=state.service,
    )


    state.metadata["response"] = (
        result.answer
    )


    state.metadata["rag_grounded"] = (
        result.grounded
    )


    state.metadata[
        "handoff_recommended"
    ] = result.handoff_recommended


    state.metadata["rag_reason"] = (
        result.reason
    )


    state.metadata["rag_sources"] = (
        result.sources
    )


    state.metadata[
        "rag_best_relevance_score"
    ] = result.best_relevance_score


    state.metadata[
        "rag_retrieved_chunks"
    ] = result.retrieved_chunks


    state.metadata[
        "rag_rejected_chunks"
    ] = result.rejected_chunks


    return state


def expert_node(
    state: ConversationState,
) -> ConversationState:
    """
    Prepare a human handoff request.

    Contact details are not invented here.
    """

    state.mode = (
        ConversationMode.EXPERT_REQUEST
    )

    state.metadata["response"] = (
        "I can help arrange a follow-up with the "
        "appropriate Sawai Associates team. "
        "Please provide your contact details."
    )

    state.metadata[
        "handoff_recommended"
    ] = True

    return state


def main_menu_node(
    state: ConversationState,
) -> ConversationState:
    """
    Present the supported top-level options.
    """

    state.mode = ConversationMode.MAIN_MENU

    state.metadata["response"] = (
        "I can help you with Real Estate, Insurance, "
        "IT Services, or connecting with an expert."
    )

    state.metadata["main_menu"] = [
        "Real Estate",
        "Insurance",
        "IT Services",
        "Talk to an Expert",
        "Ask a Question",
        "I'm not sure — Help me choose",
    ]

    return state


def general_node(
    state: ConversationState,
) -> ConversationState:
    """
    Handle greetings or unsupported/general interactions
    without inventing business information.
    """

    state.mode = (
        ConversationMode.GENERAL_CHAT
    )

    state.metadata["response"] = (
        "I can help with questions about Real Estate, "
        "Insurance, IT Services, or help connect you "
        "with the appropriate team."
    )

    return state


def build_requirement_summary(
    state: ConversationState,
) -> dict[str, Any]:
    """
    Build a structured summary of collected information.
    """

    summary: dict[str, Any] = {
        "service": (
            state.service.value
            if state.service
            else None
        ),
        "goal": state.user_goal,
    }

    if state.real_estate is not None:
        summary["real_estate"] = (
            state.real_estate.model_dump(
                mode="json"
            )
        )

    if state.insurance is not None:
        summary["insurance"] = (
            state.insurance.model_dump(
                mode="json"
            )
        )

    if state.it_services is not None:
        summary["it_services"] = (
            state.it_services.model_dump(
                mode="json"
            )
        )

    if state.contact is not None:
        summary["contact"] = (
            state.contact.model_dump(
                mode="json"
            )
        )

    return summary


def finalize_lead_node(
    state: ConversationState,
) -> ConversationState:
    """
    Persist a completed lead, record operational audit events,
    queue the configured business delivery, and move the
    customer to the final summary.
    """

    # ---------------------------------------------------------
    # Qualification must be complete first
    # ---------------------------------------------------------

    if not state.qualification_complete:
        return state


    # ---------------------------------------------------------
    # Contact object safety check
    # ---------------------------------------------------------

    if state.contact is None:
        state.metadata["lead_error"] = (
            "Contact information is missing."
        )

        return state


    # ---------------------------------------------------------
    # Privacy / consent safety net
    # ---------------------------------------------------------

    if (
        settings.require_contact_consent
        and state.contact.consent_to_contact
        is not True
    ):
        state.qualification_complete = False

        state.mode = (
            ConversationMode.QUALIFICATION
        )

        state.current_field = None

        state.metadata.pop(
            "next_question",
            None,
        )

        state.metadata[
            "response"
        ] = (
            "Before I collect or submit your contact "
            "details, I need your permission to use "
            "them to understand your enquiry and "
            "connect you with the appropriate "
            "Sawai Associates team."
        )

        state.metadata[
            "action_options"
        ] = [
            {
                "label": "I Agree",
                "action": "consent_contact",
            },
            {
                "label": "Main Menu",
                "action": "main_menu",
            },
        ]

        return state


    # ---------------------------------------------------------
    # Required contact information — Name
    # ---------------------------------------------------------

    if not state.contact.name:
        state.qualification_complete = False

        state.mode = (
            ConversationMode.QUALIFICATION
        )

        state.current_field = (
            "contact.name"
        )

        state.editing_field = None

        if (
            not state.question_history
            or state.question_history[-1]
            != "contact.name"
        ):
            state.question_history.append(
                "contact.name"
            )

        state.metadata[
            "next_question"
        ] = "May I have your name?"

        state.metadata[
            "response"
        ] = (
            "Before I save your request, "
            "may I have your name?"
        )

        return state


    # ---------------------------------------------------------
    # Required contact information — Mobile or Email
    # ---------------------------------------------------------

    if (
        not state.contact.mobile
        and not state.contact.email
    ):
        state.qualification_complete = False

        state.mode = (
            ConversationMode.QUALIFICATION
        )

        state.current_field = (
            "contact.mobile"
        )

        state.editing_field = None

        if (
            not state.question_history
            or state.question_history[-1]
            != "contact.mobile"
        ):
            state.question_history.append(
                "contact.mobile"
            )

        state.metadata[
            "next_question"
        ] = (
            "Please provide your mobile number."
        )

        state.metadata[
            "response"
        ] = (
            "Thank you. Please provide a mobile number "
            "so the team can contact you."
        )

        return state


    # ---------------------------------------------------------
    # Create or update the lead
    # ---------------------------------------------------------

    lead = save_or_update_lead_from_state(
        state
    )

    state.lead = lead


    if not lead.lead_id:
        state.metadata[
            "lead_error"
        ] = (
            "Lead ID could not be created."
        )

        return state

    # ---------------------------------------------------------
    # Connect the lead to its original chatbot conversation
    # ---------------------------------------------------------

    link_lead_to_session(
        lead_id=lead.lead_id,
        session_id=state.session_id,
    )


    # ---------------------------------------------------------
    # Read existing audit events
    # ---------------------------------------------------------

    existing_events = get_lead_events(
        lead.lead_id
    )


    # ---------------------------------------------------------
    # Record lead creation only once
    # ---------------------------------------------------------

    lead_created_already_recorded = any(
        event.get("event_type")
        == "lead_created"
        for event in existing_events
    )


    if not lead_created_already_recorded:
        record_lead_event(
            lead_id=lead.lead_id,
            event_type="lead_created",
            new_value=(
                lead.status.value
                if hasattr(
                    lead.status,
                    "value",
                )
                else str(
                    lead.status
                )
            ),
            actor="chatbot",
            notes=(
                "Lead created from website chatbot."
            ),
        )


    # ---------------------------------------------------------
    # Record customer contact consent only once
    # ---------------------------------------------------------

    consent_already_recorded = any(
        event.get("event_type")
        == "contact_consent_granted"
        for event in existing_events
    )


    if (
        state.contact.consent_to_contact
        is True
        and not consent_already_recorded
    ):
        record_lead_event(
            lead_id=lead.lead_id,
            event_type=(
                "contact_consent_granted"
            ),
            new_value=(
                state.contact.consent_at
                or "granted"
            ),
            actor="customer",
            notes=(
                "Customer explicitly agreed to "
                "be contacted regarding the enquiry."
            ),
        )


    # ---------------------------------------------------------
    # Queue notification / integration delivery
    #
    # This does NOT send the notification immediately.
    # The Step 18 delivery worker processes the queued job.
    # ---------------------------------------------------------

    enqueue_lead_delivery(
        lead_id=lead.lead_id,
        channel=(
            settings.notification_channel
        ),
        event_type="lead_created",
    )


    # ---------------------------------------------------------
    # Clean qualification metadata
    # ---------------------------------------------------------

    state.current_field = None
    state.editing_field = None

    state.metadata.pop(
        "next_question",
        None,
    )

    state.metadata.pop(
        "action_options",
        None,
    )

    state.metadata.pop(
        "lead_error",
        None,
    )


    # ---------------------------------------------------------
    # Customer-facing completion state
    # ---------------------------------------------------------

    state.metadata[
        "lead_created"
    ] = True

    state.metadata[
        "lead_id"
    ] = lead.lead_id


    # ---------------------------------------------------------
    # Move to summary
    # ---------------------------------------------------------

    state.mode = (
        ConversationMode.SUMMARY
    )


    state.metadata[
        "response"
    ] = (
        "Thank you. Your requirement has been captured. "
        "Please review the details below."
    )


    return state

def navigation_node(
    state: ConversationState,
) -> ConversationState:
    """
    Handle deterministic UI navigation actions.

    These actions do not go through the intent classifier.
    """

    action = state.pending_action
    target = state.action_target

    # Consume action.
    state.pending_action = None
    state.action_target = None

    # ---------------------------------------------------------
    # Main Menu
    # ---------------------------------------------------------

    if action == "main_menu":
        state.current_field = None
        state.mode = (
            ConversationMode.MAIN_MENU
        )

        state.metadata["response"] = (
            "How can I help you?"
        )

        state.metadata["main_menu"] = [
            "Real Estate",
            "Insurance",
            "IT Services",
            "Talk to an Expert",
            "Ask a Question",
            "I'm not sure — Help me choose",
        ]

        # Prevent default summary actions while on menu.
        state.metadata[
            "action_options"
        ] = []

        return state

    # ---------------------------------------------------------
    # Back
    # ---------------------------------------------------------

    if action == "back":

        # If the visitor is editing one summary field,
        # Back returns to the summary without changing it.
        if state.editing_field:
            state.editing_field = None
            state.current_field = None
            state.qualification_complete = True

            state.mode = (
                ConversationMode.SUMMARY
            )

            state.metadata["response"] = (
                "No changes were made. "
                "Here are your current details."
            )

            return state

        if (
            state.current_field
            and state.question_history
            and state.question_history[-1]
            == state.current_field
        ):
            state.question_history.pop()

        if not state.question_history:
            state.metadata["response"] = (
                "You're already at the first step."
            )

            return state

        previous_field = (
            state.question_history[-1]
        )

        question = get_question_for_field(
            state,
            previous_field,
        )

        if question is None:
            state.metadata["response"] = (
                "I couldn't find the previous question."
            )

            return state

        state.current_field = (
            previous_field
        )

        state.qualification_complete = False

        state.mode = (
            ConversationMode.QUALIFICATION
        )

        state.metadata["response"] = (
            "Sure — let's go back. "
            + question.question
        )

        return state

    # ---------------------------------------------------------
    # Edit Details
    # ---------------------------------------------------------

    if action == "edit_details":

        fields = get_editable_fields(
            state
        )

        state.mode = (
            ConversationMode.SUMMARY
        )

        state.current_field = None

        state.metadata["response"] = (
            "Choose the detail you would like to update."
        )

        state.metadata[
            "action_options"
        ] = [
            {
                "label": item["label"],
                "action": "edit_field",
                "target": item["field"],
            }
            for item in fields
        ] + [
            {
                "label": "Main Menu",
                "action": "main_menu",
            }
        ]

        return state

    # ---------------------------------------------------------
    # Edit one field
    # ---------------------------------------------------------

    if action == "edit_field":

        if not target:
            state.metadata["response"] = (
                "I couldn't determine which detail "
                "you wanted to edit."
            )

            return state

        question = get_question_for_field(
            state,
            target,
        )

        if question is None:
            state.metadata["response"] = (
                "That detail cannot be edited here."
            )

            return state

        state.current_field = target
        state.editing_field = target

        state.qualification_complete = False

        state.mode = (
            ConversationMode.QUALIFICATION
        )

        state.metadata["response"] = (
            f"Let's update "
            f"{get_field_label(target)}. "
            f"{question.question}"
        )

        return state

    # ---------------------------------------------------------
    # Request a Call
    # ---------------------------------------------------------

    if action == "request_call":

        if (
            state.contact is None
            or not state.contact.mobile
        ):
            state.current_field = (
                "contact.mobile"
            )

            state.qualification_complete = False

            state.mode = (
                ConversationMode.QUALIFICATION
            )

            state.metadata["response"] = (
                "Please provide the mobile number "
                "you would like the team to use."
            )

            return state

        state.contact.contact_preference = (
            ContactPreference.CALL
        )

        if state.lead is not None:
            save_or_update_lead_from_state(
                state
            )

        state.metadata[
            "handoff_recommended"
        ] = True

        state.metadata["response"] = (
            "Your preference for a call has been "
            "saved with your request."
        )

        return state

    # ---------------------------------------------------------
    # WhatsApp
    # ---------------------------------------------------------

    if action == "whatsapp":

        if not settings.whatsapp_url:
            state.metadata["response"] = (
                "WhatsApp contact is not currently "
                "configured in this assistant."
            )

            return state

        if state.contact is not None:
            state.contact.contact_preference = (
                ContactPreference.WHATSAPP
            )

        if state.lead is not None:
            save_or_update_lead_from_state(
                state
            )

        state.metadata["response"] = (
            "Your WhatsApp preference has been "
            "saved with your request."
        )

        return state

    # ---------------------------------------------------------
    # Explicit consent before collecting contact information
    # ---------------------------------------------------------

    if action == "consent_contact":

        state.contact.consent_to_contact = True

        state.contact.consent_at = (
            datetime.now(
                timezone.utc
            ).isoformat()
        )

        state.mode = (
            ConversationMode.QUALIFICATION
        )

        state.current_field = None

        state.metadata.pop(
            "action_options",
            None,
        )


        question = (
            get_next_planned_question(
                state
            )
        )


        if question is not None:

            state.current_field = (
                question.field
            )

            if (
                not state.question_history
                or state.question_history[-1]
                != question.field
            ):
                state.question_history.append(
                    question.field
                )

            state.metadata[
                "next_question"
            ] = question.question

            state.metadata[
                "response"
            ] = question.question


        return state

    # ---------------------------------------------------------
    # Unknown action
    # ---------------------------------------------------------

    state.metadata["response"] = (
        "That action isn't available."
    )

    return state