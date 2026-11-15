import hashlib
import io
import re
import zipfile

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile
from main import Audit, Base, Document, User, Version, add_version, current, db, document_access
from pydantic import BaseModel, Field
from sqlalchemy import ForeignKey, LargeBinary, String, Text, select
from sqlalchemy.orm import Mapped, Session, mapped_column
from workspace_models import now, uid

router = APIRouter(prefix="/files", tags=["Document originals"])


class FileObject(Base):
    __tablename__ = "file_objects"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    version_id: Mapped[str] = mapped_column(ForeignKey("document_versions.id"), unique=True)
    name: Mapped[str] = mapped_column(String)
    mime: Mapped[str] = mapped_column(String)
    content: Mapped[bytes] = mapped_column(LargeBinary)
    digest: Mapped[str] = mapped_column(String)
    created: Mapped[int] = mapped_column(default=now)


class Passage(Base):
    __tablename__ = "source_passages"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    version_id: Mapped[str] = mapped_column(ForeignKey("document_versions.id"))
    paragraph: Mapped[int]
    page: Mapped[int | None]
    text: Mapped[str] = mapped_column(Text)
    method: Mapped[str] = mapped_column(String)
    confidence: Mapped[str] = mapped_column(
        String, default="Extracted text; requires source review"
    )


def extract(content, name):
    lower = name.lower()
    if content.startswith(b"%PDF-") and lower.endswith(".pdf"):
        import pymupdf

        try:
            pdf = pymupdf.open(stream=content, filetype="pdf")
            if pdf.is_encrypted or len(pdf) > 100:
                raise ValueError()
            passages = [
                (page.number + 1, block.strip(), "PDF text extraction", None)
                for page in pdf
                for block in page.get_text().split("\n\n")
                if block.strip()
            ]
            pdf.close()
        except Exception as error:
            raise HTTPException(422, "PDF is invalid, encrypted or exceeds 100 pages") from error
        mime = "application/pdf"
    elif content.startswith(b"PK") and lower.endswith(".docx"):
        from docx import Document as Word

        try:
            archive = zipfile.ZipFile(io.BytesIO(content))
            if sum(i.file_size for i in archive.infolist()) > 30 * 1024 * 1024 or any(
                n.endswith("vbaProject.bin") for n in archive.namelist()
            ):
                raise ValueError()
            document = Word(io.BytesIO(content))
            passages = [
                (None, p.text, "DOCX paragraph extraction", index + 1)
                for index, p in enumerate(document.paragraphs)
                if p.text.strip()
            ]
        except Exception as error:
            raise HTTPException(
                422, "DOCX is invalid, oversized or contains unsupported macros"
            ) from error
        mime = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    elif lower.endswith(".txt"):
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError as error:
            raise HTTPException(422, "Use a UTF-8 text file") from error
        if "\x00" in text:
            raise HTTPException(422, "Binary data is not a text file")
        passages = [
            (None, p.strip(), "UTF-8 text paragraphs", index + 1)
            for index, p in enumerate(text.split("\n\n"))
            if p.strip()
        ]
        mime = "text/plain"
    else:
        raise HTTPException(422, "Upload a genuine PDF, DOCX or UTF-8 TXT file")
    if not passages:
        raise HTTPException(
            422, "No readable text found. OCR is not configured; supply a reviewed text source."
        )
    return passages, mime


@router.post("/upload")
async def upload(
    file: UploadFile = File(...), user: User = Depends(current), session: Session = Depends(db)
):
    content = await file.read(10 * 1024 * 1024 + 1)
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(413, "Maximum file size is 10 MB")
    name = re.sub(r"[^a-zA-Z0-9._ -]", "_", file.filename or "document")[:150]
    passages, mime = extract(content, name)
    document = Document(title=name, source=True, department=user.department, owner=user.id)
    session.add(document)
    session.flush()
    version = add_version(document, "\n\n".join(text for _, text, _, _ in passages), session)
    original = FileObject(
        version_id=version.id,
        name=name,
        mime=mime,
        content=content,
        digest=hashlib.sha256(content).hexdigest(),
    )
    session.add(original)
    for i, (page, text, method, original_paragraph) in enumerate(passages, 1):
        session.add(
            Passage(
                version_id=version.id,
                paragraph=original_paragraph or i,
                page=page,
                text=text,
                method=method,
            )
        )
    session.add(Audit(actor=user.id, action="document:upload:" + document.id))
    session.commit()
    return {
        "id": document.id,
        "version_id": version.id,
        "filename": name,
        "passages": len(passages),
        "sha256": original.digest,
    }


@router.get("/versions/{id}/original")
def original_file(id: str, user: User = Depends(current), session: Session = Depends(db)):
    version = session.get(Version, id)
    if not version:
        raise HTTPException(404)
    document_access(version.document_id, user, session)
    file = session.scalar(select(FileObject).where(FileObject.version_id == id))
    if not file:
        raise HTTPException(404, "No original file; this source was entered as text")
    return Response(
        file.content,
        media_type=file.mime,
        headers={
            "Content-Disposition": 'inline; filename="' + file.name + '"',
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.get("/versions/{id}/passages")
def source_passages(id: str, user: User = Depends(current), session: Session = Depends(db)):
    version = session.get(Version, id)
    if not version:
        raise HTTPException(404)
    document_access(version.document_id, user, session)
    return session.scalars(
        select(Passage).where(Passage.version_id == id).order_by(Passage.paragraph)
    ).all()


class ReviewEvent(Base):
    __tablename__ = "review_events"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    approval_id: Mapped[str] = mapped_column(ForeignKey("approvals.id"))
    actor: Mapped[str] = mapped_column(ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(String)
    comment: Mapped[str] = mapped_column(Text)
    created: Mapped[int] = mapped_column(default=now)


class DraftSuggestion(Base):
    __tablename__ = "draft_suggestions"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"))
    category: Mapped[str] = mapped_column(String)
    text: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String, default="SUGGESTED")
    source_version: Mapped[str] = mapped_column(ForeignKey("document_versions.id"))


class SuggestionDecision(BaseModel):
    status: str = Field(pattern="^(ACCEPTED|DISMISSED)$")


@router.get("/documents/{id}/recommendations")
def recommendations(id: str, user: User = Depends(current), session: Session = Depends(db)):
    from main import get_document

    get_document(id, user, session)
    return session.scalars(select(DraftSuggestion).where(DraftSuggestion.document_id == id)).all()


@router.post("/recommendations/{id}")
def recommendation_decision(
    id: str, data: SuggestionDecision, user: User = Depends(current), session: Session = Depends(db)
):
    from main import RecordInput, get_document, save_version

    suggestion = session.get(DraftSuggestion, id)
    if not suggestion:
        raise HTTPException(404)
    doc = document_access(suggestion.document_id, user, session)
    get_document(doc.id, user, session)
    if doc.owner != user.id:
        raise HTTPException(403)
    if suggestion.status != "SUGGESTED":
        raise HTTPException(409, "Recommendation already reviewed")
    suggestion.status = data.status
    if data.status == "ACCEPTED":
        session.add(Audit(actor=user.id, action="recommendation:accept:" + id))
        latest = session.scalar(
            select(Version).where(Version.document_id == doc.id).order_by(Version.created.desc())
        )
        body = latest.body + "\nRecommendation (accepted suggestion): " + suggestion.text
        version = save_version(doc.id, RecordInput(title=doc.title, body=body), user, session)
        return {"status": data.status, "version_id": version.id}
    session.add(Audit(actor=user.id, action="recommendation:dismiss:" + id))
    session.commit()
    return {"status": data.status}


@router.get("/documents/{id}/compare")
def compare(
    id: str, before: str, after: str, user: User = Depends(current), session: Session = Depends(db)
):
    import difflib

    from main import get_document

    get_document(id, user, session)
    left, right = session.get(Version, before), session.get(Version, after)
    if not left or not right or left.document_id != id or right.document_id != id:
        raise HTTPException(404)
    return {
        "before": before,
        "after": after,
        "diff": "\n".join(
            difflib.unified_diff(
                left.body.splitlines(),
                right.body.splitlines(),
                fromfile="Before",
                tofile="After",
                lineterm="",
            )
        ),
    }


@router.get("/reviewers")
def reviewers(user: User = Depends(current), session: Session = Depends(db)):
    from workspace import reviewer_in_scope

    return [
        {"id": identity.id, "email": identity.email}
        for identity in session.scalars(select(User))
        if identity.id != user.id and reviewer_in_scope(identity, user.department, session)
    ]


@router.post("/documents/{id}/restore/{version_id}")
def restore_version(
    id: str, version_id: str, user: User = Depends(current), session: Session = Depends(db)
):
    from main import Citation, get_document

    document = document_access(id, user, session)
    get_document(id, user, session)
    version = session.get(Version, version_id)
    if document.owner != user.id or document.source:
        raise HTTPException(403)
    if not version or version.document_id != id:
        raise HTTPException(404)
    new = add_version(document, version.body, session)
    for citation in session.scalars(select(Citation).where(Citation.version_id == version_id)):
        source = session.get(Version, citation.source_version)
        document_access(source.document_id, user, session)
        session.add(
            Citation(
                version_id=new.id,
                source_version=citation.source_version,
                paragraph=citation.paragraph,
                excerpt=citation.excerpt,
                ordinal=citation.ordinal,
            )
        )
    session.add(Audit(actor=user.id, action="document:restore_as_new:" + id))
    session.commit()
    return {"id": new.id, "approval_inherited": False}
