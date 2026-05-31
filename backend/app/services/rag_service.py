import logging
from pathlib import Path
from typing import Any

from app.config import settings

COLLECTION_NAME = "contract_chunks"
REMOTE_EMBEDDING_PREFIXES = ("text-embedding-",)
REMOTE_EMBEDDING_MODELS = {
    "text-embedding-3-large",
    "text-embedding-3-small",
    "text-embedding-ada-002",
}

_embedding_model: Any | None = None
_chroma_client: Any | None = None
logger = logging.getLogger(__name__)


def _short_doc(document_id: str | None) -> str:
    value = str(document_id or "").strip()
    if not value:
        return "unknown"
    return value[:8]


def _validate_embedding_model_name(model_name: str) -> str:
    normalized = str(model_name or "").strip()
    lowered = normalized.lower()
    if not normalized:
        raise ValueError("EMBEDDING_MODEL_NAME is empty. Set a local SentenceTransformer model.")
    if lowered in REMOTE_EMBEDDING_MODELS or lowered.startswith(REMOTE_EMBEDDING_PREFIXES):
        raise ValueError(
            f"{normalized} is a remote embedding model and cannot be used as local SentenceTransformer. "
            "Use sentence-transformers/all-MiniLM-L6-v2 or implement BotHub embeddings provider."
        )
    return normalized


def _dimension_mismatch_message(exc: Exception) -> str | None:
    text = str(exc).lower()
    if "dimension" in text and ("mismatch" in text or "expected" in text or "invalid" in text):
        return (
            "ChromaDB embedding dimension mismatch detected. "
            "Rebuild Chroma index after changing EMBEDDING_MODEL_NAME."
        )
    return None


def get_embedding_model() -> Any:
    global _embedding_model
    if _embedding_model is None:
        from sentence_transformers import SentenceTransformer

        model_name = _validate_embedding_model_name(settings.embedding_model_name)
        _embedding_model = SentenceTransformer(model_name)
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
    embeddings = model.encode(
        chunks,
        batch_size=64,
        show_progress_bar=False,
        convert_to_numpy=True,
    )
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

    logger.info(
        "rag_index_start doc=%s collection=%s embedding_model_name=%s chunks_to_save=%d",
        _short_doc(document_id),
        COLLECTION_NAME,
        settings.embedding_model_name,
        len(texts),
    )
    try:
        collection = get_collection()
        embeddings = create_embeddings(texts)
        vector_dim = len(embeddings[0]) if embeddings else 0
        collection.upsert(
            ids=ids,
            documents=texts,
            metadatas=metadatas,
            embeddings=embeddings,
        )
        logger.info(
            "rag_index_success doc=%s collection=%s embedding_vector_dim=%d chunks_saved=%d",
            _short_doc(document_id),
            COLLECTION_NAME,
            vector_dim,
            len(ids),
        )
        return len(ids)
    except ValueError:
        raise
    except Exception as exc:
        mismatch_message = _dimension_mismatch_message(exc)
        if mismatch_message:
            logger.exception(
                "rag_index_failed doc=%s collection=%s reason=dimension_mismatch",
                _short_doc(document_id),
                COLLECTION_NAME,
            )
            raise ValueError(mismatch_message) from exc
        logger.exception(
            "rag_index_failed doc=%s collection=%s reason=unexpected_error",
            _short_doc(document_id),
            COLLECTION_NAME,
        )
        raise


def save_chunks(document_id: str, chunks: list[str]) -> int:
    records = [{"text": chunk, "page": None, "chunk_index": index} for index, chunk in enumerate(chunks)]
    return save_chunk_records(document_id, records)


def _parse_retrieval_rows(
    ids: list,
    documents: list,
    metadatas: list,
    distances: list,
) -> list[dict]:
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


def semantic_retrieval(
    query: str,
    document_id: str | None = None,
    top_k: int = 5,
) -> list[dict]:
    if not query.strip():
        return []
    results = batch_semantic_retrieval(
        queries=[query],
        document_id=document_id,
        top_k=top_k,
    )
    return results[0] if results else []


def batch_semantic_retrieval(
    queries: list[str],
    document_id: str | None = None,
    top_k: int = 5,
) -> list[list[dict]]:
    normalized = [query.strip() for query in queries if query.strip()]
    if not normalized:
        return [[] for _ in queries]

    logger.info(
        "rag_retrieval_start doc=%s collection=%s embedding_model_name=%s retrieval_query_count=%d top_k=%d document_filter_used=%s",
        _short_doc(document_id),
        COLLECTION_NAME,
        settings.embedding_model_name,
        len(normalized),
        int(top_k),
        str(bool(document_id)).lower(),
    )
    collection = get_collection()
    query_embeddings = create_embeddings(normalized)
    where = {"document_id": document_id} if document_id else None

    outputs: list[list[dict]] = []
    try:
        for embedding in query_embeddings:
            result = collection.query(
                query_embeddings=[embedding],
                n_results=top_k,
                where=where,
            )
            documents = result.get("documents", [[]])[0]
            metadatas = result.get("metadatas", [[]])[0]
            distances = result.get("distances", [[]])[0]
            ids = result.get("ids", [[]])[0]
            outputs.append(_parse_retrieval_rows(ids, documents, metadatas, distances))
    except Exception as exc:
        mismatch_message = _dimension_mismatch_message(exc)
        if mismatch_message:
            logger.exception(
                "rag_retrieval_failed doc=%s collection=%s reason=dimension_mismatch",
                _short_doc(document_id),
                COLLECTION_NAME,
            )
            raise ValueError(mismatch_message) from exc
        logger.exception(
            "rag_retrieval_failed doc=%s collection=%s reason=unexpected_error",
            _short_doc(document_id),
            COLLECTION_NAME,
        )
        raise

    if len(outputs) < len(queries):
        outputs.extend([[]] * (len(queries) - len(outputs)))
    retrieved_chunks_count = sum(len(items) for items in outputs)
    logger.info(
        "rag_retrieval_done doc=%s collection=%s retrieved_chunks_count=%d retrieval_empty_reason=%s",
        _short_doc(document_id),
        COLLECTION_NAME,
        retrieved_chunks_count,
        "none" if retrieved_chunks_count else "no_matches_for_document_filter_or_index_unavailable",
    )
    return outputs
