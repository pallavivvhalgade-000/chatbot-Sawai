from pathlib import Path

import chromadb
from langchain_chroma import Chroma
from langchain_core.documents import Document

from app.core.config import settings
from app.rag.embeddings import get_embedding_model


def get_vector_store() -> Chroma:
    Path(settings.chroma_persist_dir).mkdir(
        parents=True,
        exist_ok=True,
    )

    client = chromadb.PersistentClient(
        path=settings.chroma_persist_dir
    )

    return Chroma(
        client=client,
        collection_name=settings.chroma_collection,
        embedding_function=get_embedding_model(),
    )


def rebuild_vector_store(documents: list[Document]) -> Chroma:
    Path(settings.chroma_persist_dir).mkdir(
        parents=True,
        exist_ok=True,
    )

    client = chromadb.PersistentClient(
        path=settings.chroma_persist_dir
    )

    try:
        client.delete_collection(
            settings.chroma_collection
        )
    except Exception:
        pass

    vector_store = Chroma(
        client=client,
        collection_name=settings.chroma_collection,
        embedding_function=get_embedding_model(),
    )

    ids = [
        f"chunk-{index}"
        for index in range(len(documents))
    ]

    vector_store.add_documents(
        documents=documents,
        ids=ids,
    )

    return vector_store