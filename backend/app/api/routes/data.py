from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import Response
from uuid import UUID
from sqlalchemy.orm import Session

from ..deps import get_current_user
from ...core.database import get_db
from ...models.account_data import AccountDocument
from ...models.user import User

router = APIRouter(prefix="/api/v1/account", tags=["account-documents"])
MAX_DOCUMENT_BYTES = 10 * 1024 * 1024


def _content_disposition(filename: str) -> str:
    """Return a safe attachment name without allowing header injection."""

    safe_name = "".join(
        character if character.isalnum() or character in " .-_()" else "_"
        for character in filename
    ).strip() or "document.pdf"
    if not safe_name.lower().endswith(".pdf"):
        safe_name += ".pdf"
    return f'attachment; filename="{safe_name}"'


@router.post("/documents", status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    document_type: str = Form("certificate"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF documents are supported")
    content = await file.read(MAX_DOCUMENT_BYTES + 1)
    if len(content) > MAX_DOCUMENT_BYTES or not content.startswith(b"%PDF-"):
        raise HTTPException(status_code=400, detail="Invalid or oversized PDF document")
    document = AccountDocument(
        user_id=user.id,
        document_type=document_type[:40],
        filename=(file.filename or "document.pdf")[:255],
        mime_type=file.content_type,
        data=content,
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    return {
        "id": str(document.id),
        "filename": document.filename,
        "document_type": document.document_type,
        "mime_type": document.mime_type,
        "size_bytes": len(content),
        "created_at": document.created_at,
    }


@router.get("/documents")
def list_documents(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict[str, object]]:
    documents = (
        db.query(AccountDocument)
        .filter(AccountDocument.user_id == user.id)
        .order_by(AccountDocument.created_at.desc())
        .all()
    )
    return [
        {
            "id": str(document.id),
            "filename": document.filename,
            "document_type": document.document_type,
            "mime_type": document.mime_type,
            "size_bytes": len(document.data),
            "created_at": document.created_at,
        }
        for document in documents
    ]


@router.get("/documents/{document_id}")
def get_document(
    document_id: UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    document = (
        db.query(AccountDocument)
        .filter(AccountDocument.id == document_id, AccountDocument.user_id == user.id)
        .first()
    )
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return Response(
        content=document.data,
        media_type=document.mime_type,
        headers={
            "Content-Disposition": _content_disposition(document.filename),
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.get("/documents/{document_id}/download", include_in_schema=False)
def download_document(
    document_id: UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    return get_document(document_id=document_id, user=user, db=db)


@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document_id: UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    document = (
        db.query(AccountDocument)
        .filter(AccountDocument.id == document_id, AccountDocument.user_id == user.id)
        .first()
    )
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    db.delete(document)
    db.commit()
