import pytest

from fastapi import HTTPException
from fastapi.security import (
    HTTPAuthorizationCredentials,
)
from pydantic import ValidationError

from app.api.analytics import (
    AnalyticsEventRequest,
)

from app.core.config import settings

from app.domain.classification import (
    ClassificationResult,
)

from app.domain.enums import (
    ConversationMode,
    MainIntent,
    ServiceType,
)

from app.domain.state import (
    ConversationState,
)

from app.graph.nodes import (
    finalize_lead_node,
)

from app.security.admin_auth import (
    require_admin,
)


# =========================================================
# Classification
# =========================================================


def test_expert_request_allows_no_service():
    """
    Regression test for the Step 20 bug where:

        Talk to an Expert

    returned:
        service = null

    and Pydantic rejected it.
    """

    result = ClassificationResult(
        intent=MainIntent.TALK_TO_EXPERT,
        service=None,
    )

    assert (
        result.intent
        == MainIntent.TALK_TO_EXPERT
    )

    assert result.service is None


def test_service_request_accepts_valid_service():

    result = ClassificationResult(
        intent=MainIntent.SERVICE_REQUEST,
        service=ServiceType.REAL_ESTATE,
    )

    assert (
        result.service
        == ServiceType.REAL_ESTATE
    )


# =========================================================
# Privacy / consent
# =========================================================


def test_finalizer_blocks_lead_without_consent(
    monkeypatch,
):
    """
    A lead must not be submitted when contact consent
    is required but has not been granted.
    """

    monkeypatch.setattr(
        settings,
        "require_contact_consent",
        True,
    )

    state = ConversationState()

    state.qualification_complete = True

    state.contact.name = (
        "Test Customer"
    )

    state.contact.mobile = (
        "+919876543210"
    )

    state.contact.consent_to_contact = (
        None
    )


    result = finalize_lead_node(
        state
    )


    assert (
        result.qualification_complete
        is False
    )

    assert (
        result.mode
        == ConversationMode.QUALIFICATION
    )

    assert result.lead is None


    actions = result.metadata.get(
        "action_options",
        [],
    )

    action_names = {
        item.get("action")
        for item in actions
    }


    assert (
        "consent_contact"
        in action_names
    )


# =========================================================
# Admin authentication
# =========================================================


def test_admin_rejects_missing_token(
    monkeypatch,
):

    monkeypatch.setattr(
        settings,
        "admin_api_enabled",
        True,
    )

    monkeypatch.setattr(
        settings,
        "admin_api_token",
        "test-admin-secret",
    )


    with pytest.raises(
        HTTPException
    ) as exc:

        require_admin(
            None
        )


    assert (
        exc.value.status_code
        == 401
    )


def test_admin_rejects_wrong_token(
    monkeypatch,
):

    monkeypatch.setattr(
        settings,
        "admin_api_enabled",
        True,
    )

    monkeypatch.setattr(
        settings,
        "admin_api_token",
        "correct-test-secret",
    )


    credentials = (
        HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials=(
                "wrong-test-secret"
            ),
        )
    )


    with pytest.raises(
        HTTPException
    ) as exc:

        require_admin(
            credentials
        )


    assert (
        exc.value.status_code
        == 401
    )


def test_admin_accepts_correct_token(
    monkeypatch,
):

    monkeypatch.setattr(
        settings,
        "admin_api_enabled",
        True,
    )

    monkeypatch.setattr(
        settings,
        "admin_api_token",
        "correct-test-secret",
    )


    credentials = (
        HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials=(
                "correct-test-secret"
            ),
        )
    )


    assert (
        require_admin(
            credentials
        )
        is None
    )


# =========================================================
# Analytics event allow-list
# =========================================================


def test_allowed_analytics_event():

    payload = AnalyticsEventRequest(
        event_type="chatbot_open"
    )

    assert (
        payload.event_type
        == "chatbot_open"
    )


def test_unknown_analytics_event_is_rejected():

    with pytest.raises(
        ValidationError
    ):
        AnalyticsEventRequest(
            event_type="something_random"
        )