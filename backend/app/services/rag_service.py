from pathlib import Path

import chromadb
from chromadb.api import ClientAPI
from chromadb.api.models.Collection import Collection
from sentence_transformers import SentenceTransformer

from app.config import settings

COLLECTION_NAME = "contract_chunks"

_embedding_model: SentenceTransformer | None = None
_chroma_client: ClientAPI | None = None


def get_embedding_model() -> SentenceTransformer:
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = SentenceTransformer(settings.embedding_model_name)
    return _embedding_model


def get_chroma_client() -> ClientAPI:
    global _chroma_client
    if _chroma_client is None:
        chroma_path = Path(settings.chroma_db_dir)
        chroma_path.mkdir(parents=True, exist_ok=True)
        _chroma_client = chromadb.PersistentClient(path=str(chroma_path))
    return _chroma_client


def get_collection() -> Collection:
    client = get_chroma_client()
    return client.get_or_create_collection(name=COLLECTION_NAME)


def create_embeddings(chunks: list[str]) -> list[list[float]]:
    if not chunks:
        return []
    model = get_embedding_model()
    embeddings = model.encode(chunks)
    return embeddings.tolist()


def save_chunks(document_id: str, chunks: list[str]) -> int:
    if not chunks:
        return 0

    collection = get_collection()
    embeddings = create_embeddings(chunks)
    ids = [f"{document_id}_{index}" for index in range(len(chunks))]
    metadatas = [
        {
            "document_id": document_id,
            "chunk_index": index,
        }
        for index in range(len(chunks))
    ]

    collection.upsert(
        ids=ids,
        documents=chunks,
        metadatas=metadatas,
        embeddings=embeddings,
    )
    return len(chunks)


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

    output: list[dict] = []
    for text, metadata, score in zip(documents, metadatas, distances):
        output.append(
            {
                "text": text,
                "score": float(score),
                "metadata": metadata or {},
            }
        )
    return output
