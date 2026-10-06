import json
from typing import Any

from pydantic import BaseModel, Field

from app.core.config import settings
from app.domain.enums import ServiceType
from app.llm.groq_client import get_groq_client
from app.llm.prompts import RAG_SYSTEM_PROMPT
from app.rag.retrieval import (
    RetrievalResult,
    retrieve_relevant_documents,
)


class GroundedAnswer(BaseModel):
    """
    Internal RAG result.

    `reason` and retrieval diagnostics are not intended
    for direct customer display.
    """

    answer: str

    grounded: bool = False

    handoff_recommended: bool = False

    reason: str | None = None

    sources: list[str] = Field(
        default_factory=list
    )

    best_relevance_score: float | None = None

    retrieved_chunks: int = 0

    rejected_chunks: int = 0


def _service_value(
    service: ServiceType | str | None,
) -> str:
    if service is None:
        return "general"

    if hasattr(service, "value"):
        return str(service.value)

    return str(service)


def _source_name(
    metadata: dict[str, Any],
) -> str | None:
    """
    Get a safe internal source label.

    Prefer filename over absolute filesystem paths.
    """

    filename = metadata.get(
        "filename"
    )

    if filename:
        return str(filename)

    source = metadata.get(
        "source"
    )

    if source:
        return str(source)

    return None


def _build_sources(
    retrieval: RetrievalResult,
) -> list[str]:
    sources: list[str] = []

    for document, _ in retrieval.matches:
        source = _source_name(
            document.metadata
        )

        if (
            source
            and source not in sources
        ):
            sources.append(
                source
            )

    return sources


def _build_context(
    retrieval: RetrievalResult,
) -> str:
    """
    Build verified context for the LLM while limiting
    prompt size.
    """

    blocks: list[str] = []

    total_chars = 0


    for index, (
        document,
        score,
    ) in enumerate(
        retrieval.matches,
        start=1,
    ):
        metadata = document.metadata

        source = (
            _source_name(metadata)
            or "approved knowledge source"
        )

        service = metadata.get(
            "service",
            "unknown",
        )


        block = (
            f"[VERIFIED CONTEXT {index}]\n"
            f"Source: {source}\n"
            f"Service: {service}\n"
            f"Relevance: {score:.3f}\n"
            f"Content:\n"
            f"{document.page_content.strip()}\n"
        )


        remaining = (
            settings.rag_max_context_chars
            - total_chars
        )


        if remaining <= 0:
            break


        if len(block) > remaining:
            block = block[
                :remaining
            ]


        blocks.append(
            block
        )


        total_chars += len(
            block
        )


    return "\n\n".join(
        blocks
    )


def _insufficient_context_answer(
    best_score: float | None = None,
    rejected_chunks: int = 0,
) -> GroundedAnswer:
    """
    Safe response when the knowledge base does not provide
    sufficiently relevant verified information.
    """

    return GroundedAnswer(
        answer=(
            "I don't have enough verified information "
            "in the available Sawai Associates knowledge "
            "base to answer that confidently. "
            "I can help connect you with the appropriate "
            "team for confirmation."
        ),
        grounded=False,
        handoff_recommended=True,
        reason=(
            "No retrieved knowledge-base chunks met "
            "the required relevance threshold."
        ),
        sources=[],
        best_relevance_score=best_score,
        retrieved_chunks=0,
        rejected_chunks=rejected_chunks,
    )


def answer_knowledge_question(
    question: str,
    service: ServiceType | str | None = None,
) -> GroundedAnswer:
    """
    Answer a business knowledge question using only
    sufficiently relevant, verified RAG context.
    """

    clean_question = (
        question.strip()
    )


    if not clean_question:
        return GroundedAnswer(
            answer=(
                "Please enter a question and I'll try "
                "to help."
            ),
            grounded=False,
            handoff_recommended=False,
            reason="Empty question.",
        )


    retrieval = (
        retrieve_relevant_documents(
            query=clean_question,
            service=service,
        )
    )


    if not retrieval.matches:
        return _insufficient_context_answer(
            best_score=(
                retrieval.best_score
            ),
            rejected_chunks=(
                retrieval.rejected_count
            ),
        )


    context = _build_context(
        retrieval
    )


    if not context.strip():
        return _insufficient_context_answer(
            best_score=(
                retrieval.best_score
            ),
            rejected_chunks=(
                retrieval.rejected_count
            ),
        )


    client = get_groq_client()


    service_value = (
        _service_value(
            service
        )
    )


    user_prompt = f"""
ACTIVE SERVICE SCOPE:
{service_value}

USER QUESTION:
{clean_question}

VERIFIED CONTEXT:
----------------
{context}
----------------

Answer the user's question using only business-specific facts
supported by VERIFIED CONTEXT.

If the context does not contain enough information to answer
the question confidently:
- do not guess,
- set grounded to false,
- recommend human handoff.

Return only JSON in this exact structure:

{{
  "answer": "customer-facing answer",
  "grounded": true,
  "handoff_recommended": false,
  "reason": "short internal explanation"
}}
""".strip()


    try:
        response = (
            client.chat.completions.create(
                model=settings.llm_model,

                messages=[
                    {
                        "role": "system",
                        "content":
                            RAG_SYSTEM_PROMPT,
                    },
                    {
                        "role": "user",
                        "content":
                            user_prompt,
                    },
                ],

                temperature=0,

                response_format={
                    "type":
                        "json_object"
                },
            )
        )


        content = (
            response
            .choices[0]
            .message
            .content
        )


        if not content:
            return _insufficient_context_answer(
                best_score=(
                    retrieval.best_score
                ),
                rejected_chunks=(
                    retrieval.rejected_count
                ),
            )


        raw = json.loads(
            content
        )


        result = (
            GroundedAnswer.model_validate(
                raw
            )
        )


        # Sources are controlled by our retrieval code,
        # never by model output.
        result.sources = (
            _build_sources(
                retrieval
            )
        )


        result.best_relevance_score = (
            retrieval.best_score
        )


        result.retrieved_chunks = len(
            retrieval.matches
        )


        result.rejected_chunks = (
            retrieval.rejected_count
        )


        # If the model itself says the answer is not
        # grounded, force handoff recommendation.
        if not result.grounded:
            result.handoff_recommended = True


        return result


    except Exception as exc:
        return GroundedAnswer(
            answer=(
                "I couldn't verify enough information "
                "to answer that confidently right now. "
                "I can help connect you with the "
                "appropriate team."
            ),

            grounded=False,

            handoff_recommended=True,

            reason=(
                "RAG answer generation failed: "
                + type(exc).__name__
            ),

            sources=(
                _build_sources(
                    retrieval
                )
            ),

            best_relevance_score=(
                retrieval.best_score
            ),

            retrieved_chunks=len(
                retrieval.matches
            ),

            rejected_chunks=(
                retrieval.rejected_count
            ),
        )