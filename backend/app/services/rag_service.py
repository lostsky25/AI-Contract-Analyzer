from pathlib import Path
from typing import Any

from app.config import settings

COLLECTION_NAME = "contract_chunks"

_embedding_model: Any | None = None
_chroma_client: Any | None = None


def get_embedding_model() -> Any:
    global _embedding_model
    if _embedding_model is None:
        from sentence_transformers import SentenceTransformer

        _embedding_model = SentenceTransformer(settings.embedding_model_name)
    return _embedding_model


def get_chroma_client() -> Any:
    global _chroma_client
    if _chroma_client is None:
        import chromadb

        chroma_path = Path(settings.chroma_db_dir)
        chroma_path.mkdir(parents=True, exist_ok=True)
        _chroma_client = chromadb.PersistentClient(path=str(chroma_path))
    return _chroma_client


def get_collection() -> Any:
    client = get_chroma_client()
    return client.get_or_create_collection(name=COLLECTION_NAME)


def create_embeddings(chunks: list[str]) -> list[list[float]]:
    if not chunks:
        return []
    model = get_embedding_model()
    embeddings = model.encode(chunks)
    return embeddings.tolist()


def _page_to_meta(page: int | None) -> int:
    if page is None:
        return 0
    return int(page)


def _page_from_meta(value: Any) -> int | None:
    if value is None:
        return None
    try:
        page = int(value)
    except (TypeError, ValueError):
        return None
    return None if page <= 0 else page


def save_chunk_records(document_id: str, records: list[dict]) -> int:
    if not records:
        return 0

    ids: list[str] = []
    texts: list[str] = []
    metadatas: list[dict] = []

    for index, record in enumerate(records):
        text = str(record.get("text", "")).strip()
        if not text:
            continue
        chunk_id = str(record.get("chunk_id") or f"{document_id}_{index}")
        ids.append(chunk_id)
        texts.append(text)
        metadatas.append(
            {
                "document_id": document_id,
                "chunk_id": chunk_id,
                "chunk_index": int(record.get("chunk_index", index)),
                "page": _page_to_meta(record.get("page")),
            }
        )

    if not texts:
        return 0

    collection = get_collection()
    embeddings = create_embeddings(texts)
    collection.upsert(
        ids=ids,
        documents=texts,
        metadatas=metadatas,
        embeddings=embeddings,
    )
    return len(ids)


def save_chunks(document_id: str, chunks: list[str]) -> int:
    records = [{"text": chunk, "page": None, "chunk_index": index} for index, chunk in enumerate(chunks)]
    return save_chunk_records(document_id, records)


def semantic_retrieval(
    query: str,
    document_id: str | None = None,
    top_k: int = 5,
) -> list[dict]:
    if not query.strip():
        return []

    collection = get_collection()
    query_embedding = create_embeddings([query])[0]

    where = {"document_id": document_id} if document_id else None
    result = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        where=where,
    )

    documents = result.get("documents", [[]])[0]
    metadatas = result.get("metadatas", [[]])[0]
    distances = result.get("distances", [[]])[0]
    ids = result.get("ids", [[]])[0]

    output: list[dict] = []
    for chunk_id, text, metadata, score in zip(ids, documents, metadatas, distances):
        metadata = metadata or {}
        resolved_chunk_id = str(metadata.get("chunk_id") or chunk_id or "")
        page = _page_from_meta(metadata.get("page"))
        output.append(
            {
                "text": text,
                "page": page,
                "chunk_id": resolved_chunk_id,
                "score": float(score),
                "metadata": metadata,
            }
        )
    return output
