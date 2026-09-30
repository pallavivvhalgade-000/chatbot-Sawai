from app.rag.loaders import (
    load_knowledge_base,
    split_documents,
)
from app.rag.vector_store import rebuild_vector_store


def main() -> None:
    print("Loading knowledge base...")

    documents = load_knowledge_base()

    print(f"Loaded documents: {len(documents)}")

    if not documents:
        raise RuntimeError(
            "No supported documents found in knowledge_base/"
        )

    print("Splitting documents into chunks...")

    chunks = split_documents(documents)

    print(f"Created chunks: {len(chunks)}")

    print("Building Chroma vector store...")

    rebuild_vector_store(chunks)

    print("Knowledge base ingestion complete.")


if __name__ == "__main__":
    main()