from langchain_core.documents import Document

from app.rag.vector_store import get_vector_store


def retrieve_documents(
    query: str,
    k: int = 4,
) -> list[Document]:
    vector_store = get_vector_store()

    return vector_store.similarity_search(
        query,
        k=k,
    )


def retrieve_documents_with_scores(
    query: str,
    k: int = 4,
) -> list[tuple[Document, float]]:
    vector_store = get_vector_store()

    return vector_store.similarity_search_with_score(
        query,
        k=k,
    )