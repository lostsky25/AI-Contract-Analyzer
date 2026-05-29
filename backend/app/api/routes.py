from pathlib import Path

from fastapi import APIRouter, Body, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    AuthResponse,
    ChunkRequest,
    ChunkResponse,
    ExtractRequest,
    ExtractResponse,
    IndexRequest,
    IndexResponse,
    DocumentResponse,
    OcrRequest,
    OcrResponse,
    LoginRequest,
    RegisterRequest,
    ProcessRequest,
    ProcessResponse,
    RetrieveRequest,
    RetrieveResponse,
    UserResponse,
    UploadResponse,
    OrchestrateRequest,
    OrchestrateResponse,
    DocumentUploadResponse,
    DocumentStatusResponse,
    DocumentAnalyzeRequest,
    DocumentAskRequest,
    DocumentAskResponse,
)
from app.agents.orchestrator import Orchestrator
from app.agents.document_qa_agent import DocumentQAAgent
from app.services.chunking_service import chunk_text
from app.services.document_processor import process_document
from app.services.file_service import save_uploaded_file
from app.services.llm_service import analyze_contract
from app.services.auth_service import (
    authenticate_user,
    create_access_token,
    get_current_user,
    get_password_hash,
    get_user_by_email,
    get_user_by_username,
)
from app.services.document_repository import (
    create_analysis_report,
    create_document,
    get_document,
    list_documents,
    update_document_status,
)
from app.services.rag_service import save_chunk_records, save_chunks, semantic_retrieval
from app.services.text_extractor import extract_text
from app.services.ocr_service import run_ocr
from app.services.report_store import get_report
from app.models.db_models import User

router = APIRouter()
orchestrator = Orchestrator()
document_qa_agent = DocumentQAAgent()


def _get_owned_document_or_404(db: Session, document_id: str, current_user: User):
    document = get_document(db, document_id, user_id=current_user.id)
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        )
    return document


@router.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/orchestrate", response_model=OrchestrateResponse)
async def run_orchestrator(
    payload: OrchestrateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OrchestrateResponse:
    owned_document = _get_owned_document_or_404(db, payload.document_id, current_user)
    try:
        report = orchestrator.run(
            db=db,
            document_id=payload.document_id,
            file_path=owned_document.file_path,
            user_id=current_user.id,
            legal_web_search_enabled=payload.legal_web_search_enabled,
        )
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to run orchestrated analysis workflow.",
        ) from exc

    return OrchestrateResponse(**report)


@router.post("/auth/register", response_model=UserResponse)
async def register_user(
    payload: RegisterRequest,
    db: Session = Depends(get_db),
) -> UserResponse:
    if get_user_by_username(db, payload.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username is already taken.",
        )
    if get_user_by_email(db, payload.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is already registered.",
        )

    user = User(
        username=payload.username,
        email=payload.email,
        hashed_password=get_password_hash(payload.password),
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        is_active=user.is_active,
    )


@router.post("/auth/login", response_model=AuthResponse)
async def login_user(
    payload: LoginRequest,
    db: Session = Depends(get_db),
) -> AuthResponse:
    user = authenticate_user(db, payload.username, payload.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
        )

    access_token = create_access_token(subject=user.username)
    return AuthResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            is_active=user.is_active,
        ),
    )


@router.get("/auth/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)) -> UserResponse:
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        is_active=current_user.is_active,
    )


@router.post("/upload", response_model=UploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UploadResponse:
    document_id, saved_path = await save_uploaded_file(file)
    try:
        create_document(
            db=db,
            document_id=document_id,
            user_id=current_user.id,
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
    )


@router.post("/documents", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DocumentUploadResponse:
    result = await upload_file(file=file, db=db, current_user=current_user)
    return DocumentUploadResponse(
        document_id=result.document_id,
        filename=result.filename,
        status=result.status,
    )


@router.get("/documents/{document_id}/status", response_model=DocumentStatusResponse)
async def get_document_status(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DocumentStatusResponse:
    document = _get_owned_document_or_404(db, document_id, current_user)
    return DocumentStatusResponse(document_id=document.id, status=document.status)


@router.post("/documents/{document_id}/analyze", response_model=OrchestrateResponse)
async def analyze_document_with_agents(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    payload: DocumentAnalyzeRequest = Body(default_factory=DocumentAnalyzeRequest),
) -> OrchestrateResponse:
    return await run_orchestrator(
        payload=OrchestrateRequest(
            document_id=document_id,
            legal_web_search_enabled=payload.legal_web_search_enabled,
        ),
        db=db,
        current_user=current_user,
    )


@router.get("/documents/{document_id}/report", response_model=OrchestrateResponse)
async def get_document_report(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OrchestrateResponse:
    _get_owned_document_or_404(db, document_id, current_user)
    report = get_report(document_id, db=db)
    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found. Run /api/documents/{document_id}/analyze first.",
        )
    return OrchestrateResponse(**report)


@router.post("/documents/{document_id}/ask", response_model=DocumentAskResponse)
async def ask_document_question(
    document_id: str,
    payload: DocumentAskRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DocumentAskResponse:
    _get_owned_document_or_404(db, document_id, current_user)

    if not payload.question.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question must not be empty.",
        )

    try:
        result = document_qa_agent.run(
            document_id=document_id,
            question=payload.question,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate document answer.",
        ) from exc

    return DocumentAskResponse(**result)


@router.get("/documents/{document_id}/legal-sources")
async def get_document_legal_sources(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    _get_owned_document_or_404(db, document_id, current_user)
    report = get_report(document_id, db=db)
    if report is None:
        return {"document_id": document_id, "legal_sources": [], "warnings": []}
    return {
        "document_id": document_id,
        "legal_sources": list(report.get("legal_sources", [])),
        "warnings": list(report.get("warnings", [])),
    }


@router.post("/extract", response_model=ExtractResponse)
async def extract_document_text(
    payload: ExtractRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ExtractResponse:
    owned_document = _get_owned_document_or_404(db, payload.document_id, current_user)
    target_file = Path(owned_document.file_path)
    if not target_file.exists() or not target_file.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found.",
        )

    try:
        extracted_text = extract_text(owned_document.file_path)
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
    current_user: User = Depends(get_current_user),
) -> ProcessResponse:
    owned_document = _get_owned_document_or_404(db, payload.document_id, current_user)
    target_file = Path(owned_document.file_path)
    if not target_file.exists() or not target_file.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found.",
        )

    try:
        result = process_document(payload.document_id, owned_document.file_path)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
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
        chunk_records = result.get("chunk_records") or []
        if chunk_records:
            saved_count = save_chunk_records(payload.document_id, chunk_records)
        else:
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
            user_id=current_user.id,
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
        full_text=result["full_text"],
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
async def analyze_document_text(
    payload: AnalyzeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AnalyzeResponse:
    try:
        chunks = chunk_text(payload.text)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    retrieval_query = (
        "contract risks, obligations, penalties, payment terms, termination conditions"
    )

    context_chunks: list[str] = chunks[:5]
    if payload.document_id:
        _get_owned_document_or_404(db, payload.document_id, current_user)
        try:
            # Uses deterministic ids with upsert, so repeated indexing is safe.
            save_chunks(payload.document_id, chunks)
            retrieved = semantic_retrieval(
                query=retrieval_query,
                document_id=payload.document_id,
                top_k=5,
            )
            if retrieved:
                context_chunks = [str(item.get("text", "")) for item in retrieved]
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to prepare retrieval context.",
            ) from exc

    context = "\n\n".join([chunk for chunk in context_chunks if chunk])
    if not context.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No text available for analysis.",
        )

    try:
        report = analyze_contract(context=context)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to run AI analysis.",
        ) from exc

    if payload.document_id:
        try:
            existing_document = get_document(
                db,
                payload.document_id,
                user_id=current_user.id,
            )
            if existing_document is not None:
                create_analysis_report(
                    db=db,
                    document_id=payload.document_id,
                    summary=str(report.get("summary", "")),
                    risks=list(report.get("risks", [])),
                )
                update_document_status(
                    db=db,
                    document_id=payload.document_id,
                    status="analyzed",
                    user_id=current_user.id,
                )
        except SQLAlchemyError as exc:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to persist analysis report.",
            ) from exc

    return AnalyzeResponse(
        status="analyzed",
        summary=str(report.get("summary", "")),
        risks=list(report.get("risks", [])),
    )


@router.post("/index", response_model=IndexResponse)
async def index_document_text(
    payload: IndexRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> IndexResponse:
    _get_owned_document_or_404(db, payload.document_id, current_user)
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
        existing_document = get_document(db, payload.document_id, user_id=current_user.id)
        if existing_document is not None:
            update_document_status(
                db=db,
                document_id=payload.document_id,
                status="indexed",
                user_id=current_user.id,
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
async def retrieve_chunks(
    payload: RetrieveRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RetrieveResponse:
    if payload.top_k <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="top_k must be greater than 0.",
        )

    if payload.document_id:
        _get_owned_document_or_404(db, payload.document_id, current_user)

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


@router.post("/ocr", response_model=OcrResponse)
async def run_document_ocr(
    payload: OcrRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OcrResponse:
    owned_document = _get_owned_document_or_404(db, payload.document_id, current_user)
    target_file = Path(owned_document.file_path)
    if not target_file.exists() or not target_file.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found.",
        )

    try:
        text = run_ocr(owned_document.file_path)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to run OCR.",
        ) from exc

    text_length = len(text)
    return OcrResponse(
        document_id=payload.document_id,
        status="ocr_completed" if text_length > 0 else "empty_text",
        text_preview=text[:1000],
        text_length=text_length,
    )


@router.get("/documents/{document_id}", response_model=DocumentResponse)
async def get_document_by_id(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DocumentResponse:
    document = get_document(db, document_id, user_id=current_user.id)
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        )

    return DocumentResponse(
        document_id=document.id,
        filename=document.filename,
        status=document.status,
        text_length=document.text_length,
        created_at=document.created_at,
    )


@router.get("/documents", response_model=list[DocumentResponse])
async def get_documents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[DocumentResponse]:
    documents = list_documents(db, user_id=current_user.id)
    return [
        DocumentResponse(
            document_id=document.id,
            filename=document.filename,
            status=document.status,
            text_length=document.text_length,
            created_at=document.created_at,
        )
        for document in documents
    ]
