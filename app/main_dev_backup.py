from fastapi import FastAPI
from pydantic import BaseModel
from app.rag.retrieval import retrieve_documents_with_scores

from app.core.config import settings
from app.domain.enums import ConversationMode, ServiceType
from app.domain.flows.questions import get_next_question
from app.domain.state import ConversationState
from app.llm.groq_client import get_groq_client

from app.domain.classification import ClassificationResult
from app.llm.classifier import classify_message

from app.domain.state import ConversationState
from app.graph.runner import run_conversation
import uuid

from app.db.database import initialize_database

from app.db.leads import list_leads
from app.db.leads import find_lead

from app.domain.assignment import assign_team
from app.domain.assignment import get_team_name
from app.domain.priority import calculate_lead_priority
from app.domain.state import ConversationState


app = FastAPI(
    title=settings.app_name,
    description="AI customer-support and lead-capture backend for Sawai Associates.",
    version="0.2.0",
)

initialize_database()


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {
        "status": "ok",
        "environment": settings.app_env,
    }


@app.get("/health/llm")
async def llm_health_check() -> dict[str, str]:
    get_groq_client()

    return {
        "status": "ok",
        "provider": settings.llm_provider,
        "model": settings.llm_model,
    }


class StateDemoRequest(BaseModel):
    session_id: str = "demo-session"
    service: ServiceType = ServiceType.REAL_ESTATE


@app.post("/test/state")
async def test_state(request: StateDemoRequest):
    state = ConversationState(
        session_id=request.session_id,
        mode=ConversationMode.QUALIFICATION,
        service=request.service,
    )

    next_question = get_next_question(state)

    return {
        "session_id": state.session_id,
        "service": state.service,
        "mode": state.mode,
        "next_question": (
            {
                "field": next_question.field,
                "question": next_question.question,
            }
            if next_question
            else None
        ),
        "state": state.model_dump(mode="json"),
    }

class RAGTestRequest(BaseModel):
    query: str
    k: int = 4


@app.post("/test/rag")
async def test_rag(request: RAGTestRequest):
    results = retrieve_documents_with_scores(
        query=request.query,
        k=request.k,
    )

    return {
        "query": request.query,
        "results": [
            {
                "content": document.page_content,
                "score": score,
                "metadata": document.metadata,
            }
            for document, score in results
        ],
    }

class ClassificationRequest(BaseModel):
    message: str


@app.post("/test/classify")
async def test_classification(
    request: ClassificationRequest,
):
    result = classify_message(request.message)

    return result.as_dict()

class ConversationRequest(BaseModel):
    message: str
    session_id: str | None = None


@app.post("/test/conversation")
async def test_conversation(
    request: ConversationRequest,
):
    result = run_conversation(
        message=request.message,
        session_id=request.session_id,
    )

    return {
        "session_id": result.session_id,
        "mode": (
            result.mode.value
            if result.mode
            else None
        ),
        "intent": (
            result.intent.value
            if result.intent
            else None
        ),
        "service": (
            result.service.value
            if result.service
            else None
        ),
        "current_field": result.current_field,
        "qualification_complete": (
            result.qualification_complete
        ),
        "requirement_summary": (
            result.requirement_summary
        ),
        "metadata": result.metadata,
    }

@app.get("/test/leads")
async def test_list_leads():
    return {
        "count": len(list_leads()),
        "leads": list_leads(),
    }


@app.get("/test/leads/{lead_id}")
async def test_get_lead(lead_id: str):
    lead = find_lead(lead_id)

    if lead is None:
        return {
            "found": False,
            "lead": None,
        }

    return {
        "found": True,
        "lead": lead,
    }

@app.post("/test/lead-routing")
async def test_lead_routing(request: ConversationRequest):
    result = run_conversation(
        message=request.message,
        session_id=request.session_id,
    )

    priority = calculate_lead_priority(result)

    team = assign_team(result)

    return {
        "session_id": result.session_id,
        "service": (
            result.service.value
            if result.service
            else None
        ),
        "priority": priority.value,
        "assigned_team": team.value,
        "assigned_team_name": get_team_name(team),
        "qualification_complete": (
            result.qualification_complete
        ),
        "requirement_summary": (
            result.requirement_summary
        ),
    }

@app.get("/test/notification-config")
async def test_notification_config():
    return {
        "notification_channel": (
            settings.notification_channel
        ),
        "webhook_configured": bool(
            settings.notification_webhook_url
        ),
        "smtp_host_configured": bool(
            settings.smtp_host
        ),
        "smtp_destination_configured": bool(
            settings.lead_notification_to_email
        ),
    }