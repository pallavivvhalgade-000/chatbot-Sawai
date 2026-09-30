from fastapi import FastAPI
from pydantic import BaseModel

from app.core.config import settings
from app.domain.enums import ConversationMode, ServiceType
from app.domain.flows.questions import get_next_question
from app.domain.state import ConversationState
from app.llm.groq_client import get_groq_client


app = FastAPI(
    title=settings.app_name,
    description="AI customer-support and lead-capture backend for Sawai Associates.",
    version="0.2.0",
)


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