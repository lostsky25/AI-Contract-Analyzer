from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    ChunkRequest,
    ChunkResponse,
    ExtractRequest,
    ExtractResponse,
    IndexRequest,
    IndexResponse,
    DocumentResponse,
    ProcessRequest,
    ProcessResponse,
    RetrieveRequest,
    RetrieveResponse,
    UploadResponse,
)
from app.services.chunking_service import chunk_text
from app.services.document_processor import process_document
from app.services.file_service import save_uploaded_file
from app.services.llm_service import analyze_contract
from app.services.document_repository import (
    create_document,
    get_document,
    list_documents,
    update_document_status,
)
from app.services.rag_service import save_chunks, semantic_retrieval
from app.services.text_extractor import extract_text

router = APIRouter()


@router.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/upload", response_model=UploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> UploadResponse:
    document_id, saved_path = await save_uploaded_file(file)
    try:
        create_document(
            db=db,
            document_id=document_id,
            filename=file.filename or "uploaded_file",
            file_path=saved_path,
            status="uploaded",
        )
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save document metadata.",
        ) from exc

    return UploadResponse(
        document_id=document_id,
        filename=file.filename or "uploaded_file",
        status="uploaded",
        file_path=saved_path,
    )


@router.post("/extract", response_model=ExtractResponse)
async def extract_document_text(payload: ExtractRequest) -> ExtractResponse:
    target_file = Path(payload.file_path)
    if not target_file.exists() or not target_file.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found.",
        )

    try:
        extracted_text = extract_text(payload.file_path)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to extract text from document.",
        ) from exc

    text_length = len(extracted_text)
    status_value = "extracted" if text_length > 0 else "empty_text"

    return ExtractResponse(
        document_id=payload.document_id,
        status=status_value,
        text_preview=extracted_text[:1000],
        text_length=text_length,
    )


@router.post("/process", response_model=ProcessResponse)
async def process_uploaded_document(
    payload: ProcessRequest,
    db: Session = Depends(get_db),
) -> ProcessResponse:
    target_file = Path(payload.file_path)
    if not target_file.exists() or not target_file.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found.",
        )

    try:
        result = process_document(payload.document_id, payload.file_path)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process document.",
        ) from exc

    try:
        saved_count = save_chunks(payload.document_id, result.get("chunks", []))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to index processed chunks.",
        ) from exc

    try:
        update_document_status(
            db=db,
            document_id=payload.document_id,
            status="processed",
            text_length=result["text_length"],
        )
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update document status.",
        ) from exc

    return ProcessResponse(
        document_id=result["document_id"],
        status=result["status"],
        text_preview=result["text_preview"],
        text_length=result["text_length"],
        chunks_count=saved_count,
        used_ocr=result["used_ocr"],
    )


@router.post("/chunk", response_model=ChunkResponse)
async def chunk_document_text(payload: ChunkRequest) -> ChunkResponse:
    try:
        chunks = chunk_text(
            text=payload.text,
            chunk_size=payload.chunk_size,
            overlap=payload.overlap,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return ChunkResponse(
        status="chunked",
        chunks_count=len(chunks),
        chunks=chunks,
    )


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_document_text(payload: AnalyzeRequest) -> AnalyzeResponse:
    try:
        chunks = chunk_text(payload.text)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    context = "\n\n".join(chunks)
    report = analyze_contract(context=context)

    return AnalyzeResponse(
        status="analyzed",
        summary=str(report.get("summary", "")),
        risks=list(report.get("risks", [])),
    )


@router.post("/index", response_model=IndexResponse)
async def index_document_text(
    payload: IndexRequest,
    db: Session = Depends(get_db),
) -> IndexResponse:
    try:
        chunks = chunk_text(payload.text)
        saved_count = save_chunks(payload.document_id, chunks)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to index document chunks.",
        ) from exc

    try:
        existing_document = get_document(db, payload.document_id)
        if existing_document is not None:
            update_document_status(
                db=db,
                document_id=payload.document_id,
                status="indexed",
            )
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update indexed document status.",
        ) from exc

    return IndexResponse(
        document_id=payload.document_id,
        status="indexed",
        chunks_count=saved_count,
    )


@router.post("/retrieve", response_model=RetrieveResponse)
async def retrieve_chunks(payload: RetrieveRequest) -> RetrieveResponse:
    if payload.top_k <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="top_k must be greater than 0.",
        )

    try:
        results = semantic_retrieval(
            query=payload.query,
            document_id=payload.document_id,
            top_k=payload.top_k,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve chunks.",
        ) from exc

    return RetrieveResponse(status="retrieved", results=results)


@router.get("/documents/{document_id}", response_model=DocumentResponse)
async def get_document_by_id(
    document_id: str,
    db: Session = Depends(get_db),
) -> DocumentResponse:
    document = get_document(db, document_id)
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        )

    return DocumentResponse(
        document_id=document.id,
        filename=document.filename,
        file_path=document.file_path,
        status=document.status,
        text_length=document.text_length,
        created_at=document.created_at,
    )


@router.get("/documents", response_model=list[DocumentResponse])
async def get_documents(db: Session = Depends(get_db)) -> list[DocumentResponse]:
    documents = list_documents(db)
    return [
        DocumentResponse(
            document_id=document.id,
            filename=document.filename,
            file_path=document.file_path,
            status=document.status,
            text_length=document.text_length,
            created_at=document.created_at,
        )
        for document in documents
    ]
