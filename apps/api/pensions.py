"""Pension operations and reviewed file-based legacy system imports."""

import csv
import hashlib
import io
import zipfile
from datetime import date, datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile
from main import Base, User, current, db
from openpyxl import load_workbook
from pydantic import Field, ValidationError
from sqlalchemy import JSON, ForeignKey, String, Text, UniqueConstraint, select, update
from sqlalchemy.orm import Mapped, Session, mapped_column
from work import (
    Campaign,
    CampaignEvent,
    Case,
    Checklist,
    Contact,
    Delivery,
    PensionInput,
    authorised_user,
    case_event,
    scoped,
)
from workspace import Input, audit, notify
from workspace_models import now, uid

router = APIRouter(prefix="/pension", tags=["Pension and legacy imports"])
OPERATIONS = [
    "Service verification",
    "Family pension",
    "Pension revision",
    "Commutation",
    "Gratuity",
    "Arrears",
    "Life certificate",
    "Bank change",
    "Payment reconciliation",
    "Restoration",
    "Recovery",
    "Transfer",
    "Scheme eligibility",
    "Beneficiary verification",
    "Renewal",
    "Suspension or resumption",
]


class PensionOperation(Base):
    __tablename__ = "pension_operations"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    case_id: Mapped[str] = mapped_column(ForeignKey("work_cases.id"))
    creator: Mapped[str] = mapped_column(ForeignKey("users.id"))
    kind: Mapped[str] = mapped_column(String)
    due_date: Mapped[str | None] = mapped_column(String)
    notes: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String, default="DRAFT")
    reviewer: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    review_note: Mapped[str] = mapped_column(Text, default="")
    created: Mapped[int] = mapped_column(default=now)


class LegacyBatch(Base):
    __tablename__ = "legacy_import_batches"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    department: Mapped[str] = mapped_column(String)
    owner: Mapped[str] = mapped_column(ForeignKey("users.id"))
    source: Mapped[str] = mapped_column(String)
    target: Mapped[str] = mapped_column(String)
    campaign_id: Mapped[str | None] = mapped_column(ForeignKey("outreach_campaigns.id"))
    file_hash: Mapped[str] = mapped_column(String)
    rows: Mapped[list] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String, default="PREVIEW")
    result: Mapped[dict] = mapped_column(JSON, default=dict)
    created: Mapped[int] = mapped_column(default=now)


class LegacyLink(Base):
    __tablename__ = "legacy_pension_links"
    __table_args__ = (UniqueConstraint("department", "source", "external_id"),)
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    department: Mapped[str] = mapped_column(String)
    source: Mapped[str] = mapped_column(String)
    external_id: Mapped[str] = mapped_column(String)
    case_id: Mapped[str] = mapped_column(ForeignKey("work_cases.id"))


class RegisterInput(Input):
    scheme: str = Field(pattern="^(Government employee|Social welfare)$")
    scheme_name: str = Field(default="", max_length=160)
    ppo_reference: str = Field(default="", max_length=100)
    service_start: date | None = None
    service_end: date | None = None
    life_certificate_received: date | None = None
    life_certificate_due: date | None = None
    payment_period: str = Field(default="", pattern=r"^(|\d{4}-(0[1-9]|1[0-2]))$")
    payment_status: str = Field(
        default="Not checked", pattern="^(Not checked|Matched|Missing|Mismatch|Held)$"
    )
    reconciliation_note: str = Field(default="", max_length=3000)


class OperationInput(Input):
    kind: str
    notes: str = Field(min_length=10, max_length=5000)
    due_date: date | None = None


def pension_case(id, user, session, write=False):
    value = scoped(Case, id, user, session)
    if value.kind != "pension":
        raise HTTPException(404)
    if write and user.id not in {value.creator, value.assignee}:
        raise HTTPException(403, "Only the case owner or assigned officer may edit")
    return value


@router.get("/cases/{id}/register")
def register(id: str, user: User = Depends(current), session: Session = Depends(db)):
    case = pension_case(id, user, session)
    return {
        "register": case.details.get("register", {}),
        "operations": session.scalars(
            select(PensionOperation).where(PensionOperation.case_id == id)
        ).all(),
        "operation_types": OPERATIONS,
    }


@router.put("/cases/{id}/register")
def save_register(
    id: str, data: RegisterInput, user: User = Depends(current), session: Session = Depends(db)
):
    case = pension_case(id, user, session, True)
    if data.service_start and data.service_end and data.service_end < data.service_start:
        raise HTTPException(422, "Service end must follow service start")
    if (
        data.life_certificate_received
        and data.life_certificate_due
        and data.life_certificate_due < data.life_certificate_received
    ):
        raise HTTPException(422, "Certificate due date must follow receipt")
    case.details = {**case.details, "register": data.model_dump(mode="json")}
    case_event(
        case,
        user,
        session,
        "REGISTER_UPDATED",
        "Pension register updated; no eligibility or payment authorised",
    )
    session.commit()
    return {"saved": True}


@router.post("/cases/{id}/operations")
def operation(
    id: str, data: OperationInput, user: User = Depends(current), session: Session = Depends(db)
):
    case = pension_case(id, user, session, True)
    if data.kind not in OPERATIONS:
        raise HTTPException(422, "Choose a supported pension operation")
    value = PensionOperation(
        case_id=id,
        creator=user.id,
        kind=data.kind,
        notes=data.notes,
        due_date=data.due_date.isoformat() if data.due_date else None,
    )
    session.add(value)
    case_event(case, user, session, "OPERATION_CREATED", data.kind)
    session.commit()
    session.refresh(value)
    return value


class OperationDecision(Input):
    action: str = Field(pattern="^(submit|approve|return|complete)$")
    reviewer_email: str = ""
    note: str = Field(min_length=3, max_length=3000)


@router.post("/operations/{id}/decision")
def decide_operation(
    id: str, data: OperationDecision, user: User = Depends(current), session: Session = Depends(db)
):
    value = session.get(PensionOperation, id)
    if not value:
        raise HTTPException(404)
    case = pension_case(value.case_id, user, session)
    owner = user.id in {case.creator, case.assignee}
    if data.action == "submit" and value.status in {"DRAFT", "RETURNED"} and owner:
        reviewer = authorised_user(data.reviewer_email, user, session)
        from workspace import reviewer_in_scope

        if reviewer.id in {user.id, value.creator} or not reviewer_in_scope(
            reviewer, user.department, session
        ):
            raise HTTPException(422, "Choose a separate authorised reviewer")
        value.reviewer, value.status = reviewer.id, "UNDER_REVIEW"
        notify(
            session,
            reviewer.id,
            "approvals",
            "Pension work review: " + value.kind,
            "/department/pension/" + case.id,
        )
    elif (
        data.action in {"approve", "return"}
        and value.status == "UNDER_REVIEW"
        and value.reviewer == user.id
        and user.role == "reviewer"
        and user.id != value.creator
    ):
        value.status = "APPROVED" if data.action == "approve" else "RETURNED"
    elif data.action == "complete" and value.status == "APPROVED" and owner:
        value.status = "COMPLETED"
    else:
        raise HTTPException(403, "Action is unavailable for this officer or workflow state")
    value.review_note = data.note
    case_event(case, user, session, "PENSION_" + value.status, value.kind + ": " + data.note)
    session.commit()
    return {"status": value.status}


@router.get("/imports")
def batches(user: User = Depends(current), session: Session = Depends(db)):
    return [
        {
            "id": b.id,
            "source": b.source,
            "target": b.target,
            "status": b.status,
            "created": b.created,
            "result": b.result,
            "file_hash": b.file_hash,
        }
        for b in session.scalars(
            select(LegacyBatch)
            .where(LegacyBatch.department == user.department, LegacyBatch.owner == user.id)
            .order_by(LegacyBatch.created.desc())
        )
    ]


def read_rows(content, filename):
    if filename.lower().endswith(".csv"):
        try:
            reader = csv.DictReader(io.StringIO(content.decode("utf-8-sig")))
            if len(reader.fieldnames or []) != len(set(reader.fieldnames or [])):
                raise ValueError("Duplicate headers")
            rows = []
            for row in reader:
                if len(rows) >= 500:
                    raise ValueError("Maximum 500 rows per import")
                if None in row:
                    raise ValueError("Row contains more values than headers")
                rows.append({k: (v or "").strip() for k, v in row.items()})
            return rows
        except (UnicodeError, csv.Error, ValueError) as exc:
            raise HTTPException(422, str(exc)) from exc
    if not filename.lower().endswith(".xlsx"):
        raise HTTPException(422, "Use UTF-8 CSV or XLSX")
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            if sum(i.file_size for i in archive.infolist()) > 20_000_000:
                raise ValueError("Expanded workbook exceeds limit")
        book = load_workbook(io.BytesIO(content), read_only=True, data_only=False)
        sheet = book.active
        iterator = sheet.iter_rows()
        headers = [str(c.value or "").strip() for c in next(iterator)]
        if len(headers) != len(set(headers)):
            raise ValueError("Duplicate headers")
        rows = []
        for cells in iterator:
            if len(rows) >= 500:
                raise ValueError("Maximum 500 rows per import")
            if any(c.data_type == "f" for c in cells):
                raise ValueError("Formula cells are unsupported; export literal values")
            if any(c.value is not None for c in cells):
                rows.append(
                    dict(
                        zip(
                            headers,
                            [
                                c.value.date().isoformat()
                                if isinstance(c.value, datetime)
                                else str(c.value).strip()
                                if c.value is not None
                                else ""
                                for c in cells
                            ],
                            strict=True,
                        )
                    )
                )
        book.close()
        return rows
    except Exception as exc:
        raise HTTPException(422, "Unreadable workbook: " + str(exc)) from exc


@router.post("/imports/preview")
async def preview_import(
    source: str = Form(...),
    target: str = Form("pension"),
    campaign_id: str = Form(""),
    file: UploadFile = File(...),
    user: User = Depends(current),
    session: Session = Depends(db),
):
    source = source.strip()
    if not 3 <= len(source) <= 160 or target not in {"pension", "audience"}:
        raise HTTPException(422, "Provide a source system name and supported target")
    if target == "audience":
        campaign = scoped(Campaign, campaign_id, user, session)
        if campaign.owner != user.id or campaign.status != "DRAFT":
            raise HTTPException(403, "Audience imports require your draft campaign")
    content = await file.read(2_000_001)
    if len(content) > 2_000_000:
        raise HTTPException(413, "Maximum upload size is 2 MB")
    raw = read_rows(content, file.filename or "")
    if not raw:
        raise HTTPException(422, "The file has no records")
    rows, seen = [], set()
    for number, row in enumerate(raw, 2):
        errors, duplicate = [], False
        if target == "pension":
            external = row.get("external_id", "")
            if not external or len(external) > 120:
                errors.append("external_id is required, up to 120 characters")
            if row.get("scheme") not in {"Government employee", "Social welfare"}:
                errors.append("scheme must be Government employee or Social welfare")
            try:
                PensionInput.model_validate(
                    {
                        k: row.get(k) or None
                        for k in ["pensioner_alias", "case_type", "retirement_date", "summary"]
                    }
                )
            except ValidationError:
                errors.append("Check pensioner_alias, case_type, retirement_date and summary")
            duplicate = bool(
                session.scalar(
                    select(LegacyLink.id).where(
                        LegacyLink.department == user.department,
                        LegacyLink.source == source,
                        LegacyLink.external_id == external,
                    )
                )
            )
            key = external
        else:
            key = row.get("alias", "").casefold()
            if not 3 <= len(row.get("alias", "")) <= 100 or row.get("consent", "").lower() not in {
                "true",
                "false",
            }:
                errors.append(
                    "alias (3–100 characters) and explicit consent true/false are required"
                )
            duplicate = any(
                c.alias.casefold() == key
                for c in session.scalars(select(Contact).where(Contact.campaign_id == campaign_id))
            )
        if key in seen:
            duplicate = True
        seen.add(key)
        rows.append({"line": number, "data": row, "errors": errors, "duplicate": duplicate})
    batch = LegacyBatch(
        department=user.department,
        owner=user.id,
        source=source,
        target=target,
        campaign_id=campaign_id if target == "audience" else None,
        file_hash=hashlib.sha256(content).hexdigest(),
        rows=rows,
    )
    session.add(batch)
    audit(session, user, "legacy:preview")
    session.commit()
    session.refresh(batch)
    return {"id": batch.id, "rows": rows, "file_hash": batch.file_hash}


@router.post("/imports/{id}/confirm")
def confirm_import(id: str, user: User = Depends(current), session: Session = Depends(db)):
    batch = session.get(LegacyBatch, id)
    if not batch or batch.department != user.department or batch.owner != user.id:
        raise HTTPException(404)
    if batch.status == "IMPORTED":
        return batch.result
    if any(r["errors"] for r in batch.rows):
        raise HTTPException(422, "Correct the invalid rows and preview a new file")
    if batch.target == "audience":
        campaign = scoped(Campaign, batch.campaign_id, user, session)
        if campaign.owner != user.id or campaign.status != "DRAFT":
            raise HTTPException(409, "Campaign is no longer editable")
    claim = session.execute(
        update(LegacyBatch)
        .where(LegacyBatch.id == id, LegacyBatch.status == "PREVIEW")
        .values(status="IMPORTING")
    )
    if claim.rowcount != 1:
        raise HTTPException(409, "Import already in progress")
    imported, skipped = 0, 0
    for entry in batch.rows:
        row = entry["data"]
        if entry["duplicate"]:
            skipped += 1
            continue
        if batch.target == "pension":
            if session.scalar(
                select(LegacyLink.id).where(
                    LegacyLink.department == user.department,
                    LegacyLink.source == batch.source,
                    LegacyLink.external_id == row["external_id"],
                )
            ):
                skipped += 1
                continue
            value = Case(
                id=uid(),
                kind="pension",
                department=user.department,
                creator=user.id,
                assignee=user.id,
                reference="IMP-" + uid()[:12].upper(),
                subject=row["pensioner_alias"] + " - " + row["case_type"],
                status="REGISTERED",
                details={
                    **{
                        k: row.get(k, "")
                        for k in ["pensioner_alias", "case_type", "retirement_date", "summary"]
                    },
                    "register": {
                        "scheme": row["scheme"],
                        "scheme_name": row.get("scheme_name", ""),
                    },
                    "source_system": batch.source,
                    "external_id": row["external_id"],
                    "import_batch": id,
                },
            )
            session.add(value)
            session.flush()
            session.add(
                LegacyLink(
                    department=user.department,
                    source=batch.source,
                    external_id=row["external_id"],
                    case_id=value.id,
                )
            )
            for title in [
                "Imported identity verified against original",
                "Imported service or scheme evidence reviewed",
                "Imported record reconciled with source system",
            ]:
                session.add(Checklist(case_id=value.id, title=title))
            case_event(
                value, user, session, "IMPORTED", "Source: " + batch.source + "; batch: " + id
            )
        else:
            if any(
                c.alias.casefold() == row["alias"].casefold()
                for c in session.scalars(
                    select(Contact).where(Contact.campaign_id == batch.campaign_id)
                )
            ):
                skipped += 1
                continue
            session.add(
                Contact(
                    campaign_id=batch.campaign_id,
                    alias=row["alias"],
                    consent=row["consent"].lower() == "true",
                )
            )
            session.flush()
        imported += 1
    if batch.target == "audience":
        session.add(
            CampaignEvent(
                campaign_id=batch.campaign_id,
                actor=user.id,
                action="AUDIENCE_IMPORTED",
                comment=f"Reviewed batch {id}: {imported} contacts; {skipped} duplicates skipped",
            )
        )
    batch.status, batch.result = "IMPORTED", {"imported": imported, "skipped": skipped}
    audit(session, user, "legacy:confirm:" + id)
    session.commit()
    return batch.result


@router.get("/campaigns/{id}/report")
def campaign_report(id: str, user: User = Depends(current), session: Session = Depends(db)):
    campaign = scoped(Campaign, id, user, session)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["campaign", "alias", "consent", "opt_out", "simulation_status", "feedback"])

    def safe(value):
        text = str(value)
        return "'" + text if text.lstrip().startswith(("=", "+", "-", "@")) else text

    for contact in session.scalars(select(Contact).where(Contact.campaign_id == id)):
        delivery = session.scalar(
            select(Delivery).where(Delivery.campaign_id == id, Delivery.contact_id == contact.id)
        )
        writer.writerow(
            [
                safe(campaign.name),
                safe(contact.alias),
                contact.consent,
                contact.opt_out,
                delivery.status if delivery else "NOT_SIMULATED",
                safe(contact.feedback),
            ]
        )
    audit(session, user, "outreach:export:" + id)
    session.commit()
    return Response(
        output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="outreach-simulation-report.csv"'},
    )


class ConnectionInput(Input):
    name: str = Field(min_length=3, max_length=160)
    website: str = Field(min_length=8, max_length=500)
    method: str = Field(pattern="^(API|Website export|Database export)$")
    purpose: str = Field(min_length=10, max_length=2000)


@router.get("/connections")
def connections(user: User = Depends(current), session: Session = Depends(db)):
    import json

    from main import Record

    return [
        {"id": r.id, "name": r.title, "status": r.status, **json.loads(r.body)}
        for r in session.scalars(
            select(Record).where(
                Record.kind == "legacy_connection",
                Record.department == user.department,
                Record.owner == user.id,
            )
        )
    ]


@router.post("/connections")
def request_connection(
    data: ConnectionInput, user: User = Depends(current), session: Session = Depends(db)
):
    import json
    from urllib.parse import urlsplit

    from main import Record

    url = urlsplit(data.website)
    if (
        url.scheme not in {"http", "https"}
        or not url.hostname
        or url.username
        or url.password
        or url.query
        or url.fragment
    ):
        raise HTTPException(
            422, "Use a site URL without embedded credentials, query strings or fragments"
        )
    value = Record(
        department=user.department,
        owner=user.id,
        kind="legacy_connection",
        title=data.name,
        body=json.dumps(data.model_dump(exclude={"name"})),
        status="REQUESTED_NOT_CONNECTED",
    )
    session.add(value)
    audit(session, user, "legacy:connection_request")
    session.commit()
    return {"status": value.status}
