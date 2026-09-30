from pathlib import Path

from langchain_community.document_loaders import (
    Docx2txtLoader,
    PyPDFLoader,
    TextLoader,
)
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.core.config import settings


SUPPORTED_EXTENSIONS = {
    ".pdf",
    ".docx",
    ".txt",
    ".md",
}


def load_single_file(path: Path) -> list[Document]:
    suffix = path.suffix.lower()

    if suffix == ".pdf":
        loader = PyPDFLoader(str(path))

    elif suffix == ".docx":
        loader = Docx2txtLoader(str(path))

    elif suffix in {".txt", ".md"}:
        loader = TextLoader(
            str(path),
            encoding="utf-8",
        )

    else:
        return []

    documents = loader.load()

    service = path.parent.name

    for document in documents:
        document.metadata.update(
            {
                "source": str(path),
                "filename": path.name,
                "file_type": suffix.lstrip("."),
                "service": service,
            }
        )

    return documents


def load_knowledge_base() -> list[Document]:
    root = Path(settings.knowledge_base_dir)

    if not root.exists():
        raise FileNotFoundError(
            f"Knowledge base directory does not exist: {root}"
        )

    documents: list[Document] = []

    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue

        if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue

        documents.extend(load_single_file(path))

    return documents


def split_documents(documents: list[Document]) -> list[Document]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        separators=[
            "\n\n",
            "\n",
            ". ",
            " ",
            "",
        ],
    )

    chunks = splitter.split_documents(documents)

    for index, chunk in enumerate(chunks):
        chunk.metadata["chunk_index"] = index

    return chunks