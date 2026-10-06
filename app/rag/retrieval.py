from dataclasses import dataclass
from typing import Any

from langchain_core.documents import Document

from app.core.config import settings
from app.domain.enums import ServiceType
from app.rag.vector_store import get_vector_store


@dataclass
class RetrievalResult:
    """
    Result of a RAG retrieval operation.
    """

    matches: list[
        tuple[Document, float]
    ]

    best_score: float | None

    service_filter: dict[str, Any] | None

    rejected_count: int = 0


def _service_value(
    service: ServiceType | str | None,
) -> str | None:
    """
    Convert ServiceType or string into the value stored
    in Chroma metadata.
    """

    if service is None:
        return None

    if hasattr(service, "value"):
        return str(service.value)

    return str(service)


def build_service_filter(
    service: ServiceType | str | None,
) -> dict[str, Any] | None:
    """
    Create the Chroma metadata filter.

    Service-specific questions may use:
      - that service's documents
      - general business documents

    GENERAL questions may search across all documents.
    """

    service_value = _service_value(
        service
    )

    if service_value in {
        ServiceType.REAL_ESTATE.value,
        ServiceType.INSURANCE.value,
        ServiceType.IT_SERVICES.value,
    }:
        return {
            "service": {
                "$in": [
                    service_value,
                    ServiceType.GENERAL.value,
                ]
            }
        }

    return None


def retrieve_relevant_documents(
    query: str,
    service: ServiceType | str | None = None,
    k: int | None = None,
    min_relevance_score: float | None = None,
) -> RetrievalResult:
    """
    Retrieve relevant verified knowledge-base documents.

    Chunks below the configured relevance threshold are
    rejected before they reach the LLM.
    """

    clean_query = query.strip()

    if not clean_query:
        return RetrievalResult(
            matches=[],
            best_score=None,
            service_filter=None,
        )


    top_k = (
        k
        if k is not None
        else settings.rag_top_k
    )


    threshold = (
        min_relevance_score
        if min_relevance_score is not None
        else settings.rag_min_relevance_score
    )


    vector_store = get_vector_store()

    service_filter = (
        build_service_filter(
            service
        )
    )


    kwargs: dict[str, Any] = {
        "k": top_k,
    }


    if service_filter is not None:
        kwargs["filter"] = (
            service_filter
        )


    raw_results = (
        vector_store
        .similarity_search_with_relevance_scores(
            clean_query,
            **kwargs,
        )
    )


    accepted: list[
        tuple[Document, float]
    ] = []


    rejected_count = 0


    best_score: float | None = None


    for document, raw_score in raw_results:

        score = float(
            raw_score
        )


        # Defensive clamp. Relevance scores are expected to
        # behave like 0..1 values.
        score = max(
            0.0,
            min(
                1.0,
                score,
            ),
        )


        if (
            best_score is None
            or score > best_score
        ):
            best_score = score


        if score < threshold:
            rejected_count += 1
            continue


        accepted.append(
            (
                document,
                score,
            )
        )


    return RetrievalResult(
        matches=accepted,
        best_score=best_score,
        service_filter=service_filter,
        rejected_count=rejected_count,
    )


# ---------------------------------------------------------
# Compatibility helpers
#
# Keep these because other scripts/code may already import
# the old retrieval functions.
# ---------------------------------------------------------


def retrieve_documents(
    query: str,
    k: int = 4,
) -> list[Document]:
    result = retrieve_relevant_documents(
        query=query,
        k=k,
        min_relevance_score=0.0,
    )

    return [
        document
        for document, _ in result.matches
    ]


def retrieve_documents_with_scores(
    query: str,
    k: int = 4,
) -> list[
    tuple[Document, float]
]:
    result = retrieve_relevant_documents(
        query=query,
        k=k,
        min_relevance_score=0.0,
    )

    return result.matches