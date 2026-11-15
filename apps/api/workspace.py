"""Employee profile, membership and catalogue services. Core auth remains enforced."""

import csv
import hashlib
import io
import re
from types import SimpleNamespace

from fastapi import APIRouter, Depends, File, HTTPException, Request, Response, UploadFile
from main import Audit, LoginSession, Preference, User, current, db, hash_password, verify
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from workspace_models import (
    AccessRequest,
    Conversation,
    Department,
    Division,
    EmployeeProfile,
    Membership,
    Message,
    Notification,
    ProfileFile,
    ProviderRequest,
    SessionScope,
    SupportTicket,
    ToolDefinition,
    ToolDismissal,
    ToolFavourite,
    ToolRequest,
    ToolUsage,
    WorkspacePreference,
    now,
)

router = APIRouter(prefix="/workspace", tags=["Employee workspace"])


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ProfileInput(Input):
    display_name: str = Field(min_length=1, max_length=100)
    phone: str = Field(default="", max_length=40)
    contact_email: str = Field(default="", max_length=254)
    office_address: str = Field(default="", max_length=300)
    bio: str = Field(default="", max_length=2000)


class PreferencesInput(Input):
    theme: str = Field(default="system", pattern="^(light|dark|system)$")
    language: str = Field(default="en", pattern="^(en|as|hi)$")
    text_size: str = Field(default="standard", pattern="^(standard|large)$")
    date_format: str = Field(default="DD/MM/YYYY", pattern="^(DD/MM/YYYY|YYYY-MM-DD)$")
    time_format: str = Field(default="24h", pattern="^(12h|24h)$")
    sidebar: str = Field(default="expanded", pattern="^(expanded|compact)$")
    home_summary: bool = True
    task_view: str = Field(default="list", pattern="^(list|calendar)$")
    week_start: str = Field(default="monday", pattern="^(monday|sunday)$")
    reduced_motion: bool = False
    document_default: str = Field(default="office_note", pattern="^(office_note|letter|minutes)$")
    draft_only_actions: bool = True
    default_model: str = Field(default="demo-excerpts", pattern="^demo-excerpts$")
    notifications: dict[str, bool] = Field(
        default_factory=lambda: {
            name: True
            for name in [
                "tasks",
                "approvals",
                "documents",
                "projects",
                "meetings",
                "department",
                "integrations",
                "security",
            ]
        }
    )
    digest: str = Field(default="off", pattern="^(off|daily|weekly)$")
    quiet_start: str = Field(default="", pattern="^$|^([01][0-9]|2[0-3]):[0-5][0-9]$")
    quiet_end: str = Field(default="", pattern="^$|^([01][0-9]|2[0-3]):[0-5][0-9]$")


def audit(session, user, action):
    session.add(Audit(actor=user.id, action=action))


def token_of(request):
    return hashlib.sha256(request.cookies.get("brahma_session", "").encode()).hexdigest()


def active(m):
    return m.status == "APPROVED" and m.starts <= now() and (m.expires is None or m.expires > now())


def member_data(m, session):
    department = session.get(Department, m.department_id)
    division = session.get(Division, m.division_id)
    return {
        "id": m.id,
        "department_id": department.id,
        "department": department.name,
        "division_id": division.id,
        "division": division.name,
        "role": m.role,
        "status": m.status,
        "starts": m.starts,
        "expires": m.expires,
    }


def resolve_actor(user, token, session):
    scope = session.get(SessionScope, token)
    memberships = session.scalars(select(Membership).where(Membership.user_id == user.id)).all()
    member = (
        session.get(Membership, scope.membership_id)
        if scope
        else next(
            (
                m
                for m in memberships
                if active(m) and session.get(Department, m.department_id).name == user.department
            ),
            None,
        )
    )
    if (scope and (not member or member.user_id != user.id or not active(member))) or (
        memberships and not member
    ):
        raise HTTPException(403, "Active membership expired or revoked")
    if member:
        data = member_data(member, session)
        return SimpleNamespace(
            id=user.id,
            email=user.email,
            role=user.role if user.role == "platform_admin" else member.role,
            department=data["department"],
            division=data["division"],
            membership_id=member.id,
        )
    return (
        user  # Existing accounts without migrated memberships retain their original single scope.
    )


def preference_data(user, session):
    stored = session.get(WorkspacePreference, user.id)
    values = PreferencesInput().model_dump()
    if stored:
        values.update(stored.values)
    legacy = session.get(Preference, user.id)
    if legacy:
        values["theme"] = legacy.theme
    return values


def notify(session, user_id, category, title, href):
    receiver = session.get(User, user_id)
    if category != "security" and not preference_data(receiver, session)["notifications"].get(
        category, True
    ):
        return
    session.add(Notification(user_id=user_id, category=category, title=title, href=href))


def admin(user):
    if user.role != "platform_admin":
        raise HTTPException(403, "Platform administrator required")


@router.get("/bootstrap")
def bootstrap(user: User = Depends(current), session: Session = Depends(db)):
    memberships = [
        member_data(m, session)
        for m in session.scalars(select(Membership).where(Membership.user_id == user.id))
        if active(m)
    ]
    pref = session.get(Preference, user.id)
    return {
        "user": {
            "id": user.id,
            "email": user.email,
            "role": user.role,
            "display_name": pref.display_name
            if pref and pref.display_name
            else "Demo " + user.role.replace("_", " "),
            "department": user.department,
            "division": getattr(user, "division", "General"),
        },
        "memberships": memberships,
        "preferences": preference_data(user, session),
        "unread": len(
            session.scalars(
                select(Notification).where(
                    Notification.user_id == user.id, Notification.read.is_(False)
                )
            ).all()
        ),
    }


@router.get("/profile")
def profile(user: User = Depends(current), session: Session = Depends(db)):
    value = session.get(EmployeeProfile, user.id)
    pref = session.get(Preference, user.id)
    return {
        "id": user.id,
        "email": user.email,
        "display_name": pref.display_name
        if pref and pref.display_name
        else "Demo " + user.role.replace("_", " "),
        "role": user.role,
        "department": user.department,
        "division": getattr(user, "division", "General"),
        "designation": None,
        "employee_id": None,
        "phone": value.phone if value else "",
        "contact_email": value.contact_email if value else "",
        "office_address": value.office_address if value else "",
        "bio": value.bio if value else "",
        "avatar_url": "/api/workspace/profile/avatar" if value and value.avatar else None,
        "identity_status": "Fictional demo account; official employment not verified",
    }


@router.put("/profile")
def update_profile(
    data: ProfileInput, user: User = Depends(current), session: Session = Depends(db)
):
    if data.contact_email and not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", data.contact_email):
        raise HTTPException(422, "Enter a valid contact email")
    value = session.get(EmployeeProfile, user.id)
    if not value:
        value = EmployeeProfile(user_id=user.id)
        session.add(value)
    for key in ["phone", "contact_email", "office_address", "bio"]:
        setattr(value, key, getattr(data, key))
    pref = session.get(Preference, user.id)
    if not pref:
        pref = Preference(user_id=user.id, theme="system", language="en")
        session.add(pref)
    pref.display_name = data.display_name
    audit(session, user, "profile:update")
    session.commit()
    return profile(user, session)


@router.post("/profile/avatar")
async def upload_avatar(
    file: UploadFile = File(...), user: User = Depends(current), session: Session = Depends(db)
):
    from PIL import Image, UnidentifiedImageError

    content = await file.read(2 * 1024 * 1024 + 1)
    if len(content) > 2 * 1024 * 1024:
        raise HTTPException(413, "Avatar maximum is 2 MB")
    try:
        image = Image.open(io.BytesIO(content))
        image.verify()
        if image.format not in {"PNG", "JPEG"} or image.width > 2048 or image.height > 2048:
            raise ValueError()
        image = Image.open(io.BytesIO(content)).convert("L")
        image.thumbnail((256, 256))
        out = io.BytesIO()
        image.save(out, format="PNG")
    except (UnidentifiedImageError, ValueError, OSError, Image.DecompressionBombError) as error:
        raise HTTPException(422, "Use valid PNG/JPEG up to 2048 pixels") from error
    value = session.get(EmployeeProfile, user.id)
    if not value:
        value = EmployeeProfile(user_id=user.id)
        session.add(value)
    value.avatar = out.getvalue()
    value.avatar_type = "image/png"
    audit(session, user, "profile:avatar")
    session.commit()
    return {"saved": True}


@router.get("/profile/avatar")
def avatar(user: User = Depends(current), session: Session = Depends(db)):
    value = session.get(EmployeeProfile, user.id)
    if not value or not value.avatar:
        raise HTTPException(404)
    return Response(
        value.avatar,
        media_type=value.avatar_type,
        headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"},
    )


@router.get("/profile/files")
def profile_files(user: User = Depends(current), session: Session = Depends(db)):
    return [
        {"id": f.id, "name": f.name, "created": f.created, "digest": f.digest}
        for f in session.scalars(select(ProfileFile).where(ProfileFile.user_id == user.id))
    ]


@router.post("/profile/files")
async def add_profile_file(
    file: UploadFile = File(...), user: User = Depends(current), session: Session = Depends(db)
):
    content = await file.read(5 * 1024 * 1024 + 1)
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(413, "Maximum 5 MB")
    if not content.startswith(b"%PDF-"):
        raise HTTPException(422, "Profile documents currently accept PDF only")
    import pymupdf

    try:
        pdf = pymupdf.open(stream=content, filetype="pdf")
        if pdf.is_encrypted or pdf.page_count == 0:
            raise ValueError()
        pdf.close()
    except Exception as error:
        raise HTTPException(422, "Invalid or encrypted PDF") from error
    name = re.sub(r"[^a-zA-Z0-9._ -]", "_", file.filename or "profile.pdf")[:120]
    value = ProfileFile(
        user_id=user.id, name=name, content=content, digest=hashlib.sha256(content).hexdigest()
    )
    session.add(value)
    audit(session, user, "profile:file_upload")
    session.commit()
    session.refresh(value)
    return {"id": value.id, "name": value.name}


@router.get("/profile/files/{id}")
def download_profile_file(id: str, user: User = Depends(current), session: Session = Depends(db)):
    value = session.get(ProfileFile, id)
    if not value or value.user_id != user.id:
        raise HTTPException(404)
    return Response(
        value.content,
        media_type="application/pdf",
        headers={
            "Content-Disposition": 'attachment; filename="' + value.name + '"',
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "private, no-store",
        },
    )


@router.get("/preferences")
def get_preferences(user: User = Depends(current), session: Session = Depends(db)):
    return preference_data(user, session)


@router.put("/preferences")
def set_preferences(
    data: PreferencesInput, user: User = Depends(current), session: Session = Depends(db)
):
    if data.notifications.get("security") is False:
        raise HTTPException(422, "Security notifications are mandatory")
    allowed = {
        "tasks",
        "approvals",
        "documents",
        "projects",
        "meetings",
        "department",
        "integrations",
        "security",
    }
    if set(data.notifications) - allowed:
        raise HTTPException(422, "Unknown notification category")
    value = session.get(WorkspacePreference, user.id)
    if not value:
        value = WorkspacePreference(user_id=user.id)
        session.add(value)
    values = data.model_dump()
    values["notifications"]["security"] = True
    value.values = values
    legacy = session.get(Preference, user.id)
    if not legacy:
        legacy = Preference(user_id=user.id, display_name="")
        session.add(legacy)
    legacy.theme = data.theme
    legacy.language = data.language
    audit(session, user, "profile:preferences")
    session.commit()
    return preference_data(user, session)


@router.get("/departments")
def departments(user: User = Depends(current), session: Session = Depends(db)):
    return [
        {
            "id": d.id,
            "name": d.name,
            "divisions": [
                {"id": v.id, "name": v.name}
                for v in session.scalars(select(Division).where(Division.department_id == d.id))
            ],
        }
        for d in session.scalars(select(Department).where(Department.active.is_(True)))
    ]


class AccessInput(Input):
    department_id: str
    division_id: str
    reason: str = Field(min_length=10, max_length=2000)
    requested_role: str = Field(default="employee", pattern="^(employee|reviewer)$")
    duration_days: int | None = Field(default=None, ge=1, le=365)


@router.post("/access-requests")
def request_access(
    data: AccessInput, user: User = Depends(current), session: Session = Depends(db)
):
    division = session.get(Division, data.division_id)
    department = session.get(Department, data.department_id)
    if (
        not division
        or division.department_id != data.department_id
        or not department
        or not department.active
    ):
        raise HTTPException(422, "Choose a valid department and division")
    if session.scalar(
        select(AccessRequest).where(
            AccessRequest.user_id == user.id,
            AccessRequest.department_id == data.department_id,
            AccessRequest.division_id == data.division_id,
            AccessRequest.status == "PENDING",
        )
    ):
        raise HTTPException(409, "A request is already pending for this division")
    for m in session.scalars(
        select(Membership).where(
            Membership.user_id == user.id,
            Membership.department_id == data.department_id,
            Membership.division_id == data.division_id,
        )
    ):
        if active(m):
            raise HTTPException(409, "You already have approved access")
    value = AccessRequest(user_id=user.id, **data.model_dump())
    session.add(value)
    session.flush()
    for administrator in session.scalars(select(User).where(User.role == "platform_admin")):
        notify(
            session,
            administrator.id,
            "department",
            "Department access request",
            "/admin?tab=access",
        )
    audit(session, user, "access:request:" + value.id)
    session.commit()
    session.refresh(value)
    return value


@router.get("/access-requests")
def access_requests(user: User = Depends(current), session: Session = Depends(db)):
    return session.scalars(
        select(AccessRequest)
        .where(AccessRequest.user_id == user.id)
        .order_by(AccessRequest.created.desc())
    ).all()


class SwitchInput(Input):
    membership_id: str


@router.post("/switch")
def switch_workspace(
    data: SwitchInput,
    request: Request,
    user: User = Depends(current),
    session: Session = Depends(db),
):
    member = session.get(Membership, data.membership_id)
    if not member or member.user_id != user.id or not active(member):
        raise HTTPException(403, "Approved active membership required")
    scope = session.get(SessionScope, token_of(request))
    if not scope:
        scope = SessionScope(token=token_of(request))
        session.add(scope)
    scope.membership_id = member.id
    audit(session, user, "workspace:switch:" + member.id)
    session.commit()
    return member_data(member, session)


@router.get("/admin/access-requests")
def admin_requests(user: User = Depends(current), session: Session = Depends(db)):
    admin(user)
    return [
        {
            "id": r.id,
            "email": session.get(User, r.user_id).email,
            "department": session.get(Department, r.department_id).name,
            "division": session.get(Division, r.division_id).name,
            "reason": r.reason,
            "requested_role": r.requested_role,
            "duration_days": r.duration_days,
            "status": r.status,
            "comment": r.comment,
        }
        for r in session.scalars(
            select(AccessRequest).order_by(AccessRequest.created.desc()).limit(200)
        )
    ]


class AccessDecision(Input):
    status: str = Field(pattern="^(APPROVED|REJECTED)$")
    comment: str = Field(min_length=3, max_length=2000)


@router.post("/admin/access-requests/{id}/decision")
def access_decision(
    id: str, data: AccessDecision, user: User = Depends(current), session: Session = Depends(db)
):
    admin(user)
    value = session.get(AccessRequest, id)
    if not value:
        raise HTTPException(404)
    if value.user_id == user.id:
        raise HTTPException(403, "A different administrator must review your own access")
    if value.status != "PENDING":
        raise HTTPException(409, "This request has already been decided")
    value.status, value.comment, value.reviewer, value.decided = (
        data.status,
        data.comment,
        user.id,
        now(),
    )
    if data.status == "APPROVED":
        member = session.scalar(
            select(Membership).where(
                Membership.user_id == value.user_id,
                Membership.department_id == value.department_id,
                Membership.division_id == value.division_id,
            )
        )
        if not member:
            member = Membership(
                user_id=value.user_id,
                department_id=value.department_id,
                division_id=value.division_id,
            )
            session.add(member)
        member.status = "APPROVED"
        member.role = value.requested_role
        member.starts = now()
        member.expires = now() + value.duration_days * 86400 if value.duration_days else None
    notify(
        session,
        value.user_id,
        "department",
        "Department access " + data.status.lower(),
        "/profile?section=access",
    )
    audit(session, user, "access:" + data.status + ":" + id)
    session.commit()
    return {"status": value.status}


@router.post("/admin/memberships/{id}/revoke")
def revoke_membership(id: str, user: User = Depends(current), session: Session = Depends(db)):
    admin(user)
    value = session.get(Membership, id)
    if not value:
        raise HTTPException(404)
    if value.user_id == user.id:
        raise HTTPException(403, "Cannot revoke your own membership here")
    value.status = "REVOKED"
    notify(
        session, value.user_id, "security", "Workspace access revoked", "/profile?section=access"
    )
    audit(session, user, "membership:revoke:" + id)
    session.commit()
    return {"revoked": True}


@router.get("/security/sessions")
def sessions(request: Request, user: User = Depends(current), session: Session = Depends(db)):
    token = token_of(request)
    return [
        {"id": s.token[:16], "current": s.token == token, "expires": s.expires}
        for s in session.scalars(
            select(LoginSession).where(
                LoginSession.user_id == user.id, LoginSession.expires > now()
            )
        )
    ]


@router.delete("/security/sessions/{id}")
def revoke_session(
    id: str, request: Request, user: User = Depends(current), session: Session = Depends(db)
):
    match = next(
        (
            s
            for s in session.scalars(select(LoginSession).where(LoginSession.user_id == user.id))
            if s.token[:16] == id
        ),
        None,
    )
    if not match:
        raise HTTPException(404)
    if match.token == token_of(request):
        raise HTTPException(409, "Use Sign out to end this session")
    scope = session.get(SessionScope, match.token)
    if scope:
        session.delete(scope)
    session.delete(match)
    audit(session, user, "security:session_revoked")
    session.commit()
    return {"revoked": True}


class PasswordInput(BaseModel):
    current_password: str = Field(min_length=1, max_length=256)
    new_password: str = Field(min_length=12, max_length=256)


@router.post("/security/password")
def change_password(
    data: PasswordInput,
    request: Request,
    user: User = Depends(current),
    session: Session = Depends(db),
):
    identity = session.get(User, user.id)
    if not verify(data.current_password, identity.password):
        raise HTTPException(403, "Current password is incorrect")
    if data.current_password == data.new_password:
        raise HTTPException(422, "Choose a different password")
    identity.password = hash_password(data.new_password)
    for other in session.scalars(
        select(LoginSession).where(
            LoginSession.user_id == user.id, LoginSession.token != token_of(request)
        )
    ):
        scope = session.get(SessionScope, other.token)
        if scope:
            session.delete(scope)
        session.delete(other)
    notify(
        session,
        user.id,
        "security",
        "Password changed; other sessions revoked",
        "/profile?section=security",
    )
    audit(session, user, "security:password_changed")
    session.commit()
    return {"changed": True, "other_sessions_revoked": True}


@router.get("/activity")
def activity(
    category: str = "",
    limit: int = 100,
    user: User = Depends(current),
    session: Session = Depends(db),
):
    if limit < 1 or limit > 200:
        raise HTTPException(422)
    query = select(Audit).where(Audit.actor == user.id)
    if category:
        query = query.where(Audit.action.icontains(category, autoescape=True))
    return [
        {"id": a.id, "action": a.action, "created": a.created}
        for a in session.scalars(query.order_by(Audit.created.desc(), Audit.id).limit(limit))
    ]


@router.get("/activity/export")
def export_activity(user: User = Depends(current), session: Session = Depends(db)):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Event", "Timestamp"])
    for a in session.scalars(
        select(Audit).where(Audit.actor == user.id).order_by(Audit.created.desc()).limit(5000)
    ):
        writer.writerow([a.action, a.created])
    audit(session, user, "activity:export")
    session.commit()
    return Response(
        output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="my-activity.csv"'},
    )


GUIDES = [
    {
        "id": "drafting",
        "title": "Prepare a source-grounded draft",
        "body": "Open Documents, select authorised references, inspect the exact citations and save a review version. Submit to a separate reviewer; Brahma cannot approve.",
    },
    {
        "id": "access",
        "title": "Request another workspace",
        "body": "Select a department and division, state your reason and duration. An administrator must approve before it appears in your selector.",
    },
    {
        "id": "tools",
        "title": "Organise your tools",
        "body": "Favourite available tools, reorder using Move up/Move down, and open a tool to record recent use.",
    },
    {
        "id": "providers",
        "title": "Why an app is not connected",
        "body": "Providers require deployment credentials and departmental authorisation. A request records your need; it does not connect or send data.",
    },
    {
        "id": "release",
        "title": "Recovery release notes",
        "body": "Routed profile and tool discovery workflows are under recovery. Read the acceptance matrix for remaining features.",
    },
]


@router.get("/help")
def help_guides(q: str = "", user: User = Depends(current)):
    return [g for g in GUIDES if q.lower() in (g["title"] + " " + g["body"]).lower()]


class TicketInput(Input):
    category: str = Field(pattern="^(issue|question|tool_request)$")
    subject: str = Field(min_length=4, max_length=160)
    message: str = Field(min_length=10, max_length=5000)


@router.post("/support")
def support(data: TicketInput, user: User = Depends(current), session: Session = Depends(db)):
    value = SupportTicket(user_id=user.id, **data.model_dump())
    session.add(value)
    session.flush()
    audit(session, user, "support:create:" + value.id)
    session.commit()
    session.refresh(value)
    return value


@router.get("/support")
def tickets(user: User = Depends(current), session: Session = Depends(db)):
    return session.scalars(
        select(SupportTicket)
        .where(SupportTicket.user_id == user.id)
        .order_by(SupportTicket.created.desc())
    ).all()


PROVIDERS = [
    {
        "id": "google",
        "title": "Google Workspace",
        "description": "Calendar, Meet and Drive",
        "scopes": ["Calendar events", "Selected Drive files"],
    },
    {
        "id": "microsoft",
        "title": "Microsoft 365",
        "description": "Outlook, Teams and SharePoint",
        "scopes": ["Calendar", "Selected sites"],
    },
    {
        "id": "slack",
        "title": "Slack",
        "description": "Workspace messaging and search",
        "scopes": ["Approved channels"],
    },
    {"id": "zoom", "title": "Zoom", "description": "Meetings", "scopes": ["Meetings"]},
    {
        "id": "eoffice",
        "title": "eOffice / NIC",
        "description": "Authorised departmental APIs only",
        "scopes": ["Requires departmental authorisation"],
    },
    {
        "id": "glean",
        "title": "Glean",
        "description": "Enterprise search; not a raw model endpoint",
        "scopes": ["Permission-filtered search"],
    },
    {
        "id": "copilot",
        "title": "Microsoft Copilot",
        "description": "Enterprise assistant; supported API required",
        "scopes": ["Tenant policy dependent"],
    },
]


@router.get("/providers")
def providers(user: User = Depends(current), session: Session = Depends(db)):
    requests = session.scalars(
        select(ProviderRequest).where(ProviderRequest.user_id == user.id)
    ).all()
    return {
        "providers": [
            {
                **p,
                "status": "Not configured",
                "configured": False,
                "account": None,
                "last_sync": None,
                "owner": "Deployment administrator",
                "requests": [
                    {"id": r.id, "status": r.status, "created": r.created}
                    for r in requests
                    if r.provider == p["id"]
                ],
            }
            for p in PROVIDERS
        ],
        "connections": [],
        "department_connections": [],
    }


class ProviderInput(Input):
    reason: str = Field(min_length=10, max_length=2000)


@router.post("/providers/{id}/request")
def provider_request(
    id: str, data: ProviderInput, user: User = Depends(current), session: Session = Depends(db)
):
    if id not in {p["id"] for p in PROVIDERS}:
        raise HTTPException(404)
    if session.scalar(
        select(ProviderRequest).where(
            ProviderRequest.user_id == user.id,
            ProviderRequest.provider == id,
            ProviderRequest.status == "PENDING",
        )
    ):
        raise HTTPException(409, "Request already pending")
    value = ProviderRequest(user_id=user.id, provider=id, reason=data.reason)
    session.add(value)
    audit(session, user, "connection:request:" + id)
    session.commit()
    session.refresh(value)
    return value


@router.get("/models")
def models(user: User = Depends(current), session: Session = Depends(db)):
    actions = session.scalars(
        select(Audit).where(Audit.actor == user.id, Audit.action.startswith("agent:"))
    ).all()
    return {
        "models": [
            {
                "id": "demo-excerpts",
                "name": "Brahma - deterministic demo",
                "status": "DEMO",
                "capabilities": ["Keyword search", "Explicit source excerpts"],
                "external_transfer": False,
            }
        ],
        "default": preference_data(user, session)["default_model"],
        "hosted_providers": [],
        "enterprise_services": ["Copilot and Glean require supported APIs and authorisation"],
        "usage": {"tracked_agent_actions": len(actions), "cost": None, "tokens": None},
        "policy": "Only authorised sources. Draft-only proposals; a separate human must approve. No model training.",
        "local_inference": "Future extension; not configured",
    }


@router.get("/notifications")
def notifications(
    filter: str = "all", user: User = Depends(current), session: Session = Depends(db)
):
    query = select(Notification).where(Notification.user_id == user.id)
    if filter == "unread":
        query = query.where(Notification.read.is_(False))
    elif filter in {"approvals", "mentions"}:
        query = query.where(Notification.category == filter)
    elif filter != "all":
        raise HTTPException(422)
    return session.scalars(query.order_by(Notification.created.desc()).limit(200)).all()


@router.post("/notifications/{id}/read")
def read_notification(id: str, user: User = Depends(current), session: Session = Depends(db)):
    value = session.get(Notification, id)
    if not value or value.user_id != user.id:
        raise HTTPException(404)
    value.read = True
    session.commit()
    return {"read": True}


def allowed_tool(tool, user, session):
    if tool.department_id and session.get(Department, tool.department_id).name != user.department:
        return False
    return not tool.required_role or user.role == tool.required_role


def tool_data(tool, user, session):
    favourite = session.get(ToolFavourite, (user.id, tool.id))
    usage = session.scalars(
        select(ToolUsage)
        .where(
            ToolUsage.user_id == user.id,
            ToolUsage.tool_id == tool.id,
            ToolUsage.department == user.department,
        )
        .order_by(ToolUsage.created.desc())
    ).first()
    return {
        "id": tool.id,
        "title": tool.title,
        "description": tool.description,
        "category": tool.category,
        "href": tool.href,
        "status": tool.status,
        "provider": tool.provider,
        "department_tool": bool(tool.department_id),
        "favourite": bool(favourite),
        "position": favourite.position if favourite else None,
        "group": favourite.group if favourite else None,
        "last_used": usage.created if usage else None,
        "why": "Available to your approved " + user.department + " workspace"
        if tool.department_id
        else "Supports your " + user.role.replace("_", " ") + " work",
    }


@router.get("/tools")
def tools(
    tab: str = "recommended",
    q: str = "",
    category: str = "",
    user: User = Depends(current),
    session: Session = Depends(db),
):
    if tab not in {"recommended", "favourites", "recent", "all", "connected", "department"}:
        raise HTTPException(422)
    result = []
    for tool in session.scalars(select(ToolDefinition)):
        if not allowed_tool(tool, user, session):
            continue
        value = tool_data(tool, user, session)
        if q.lower() not in (tool.title + " " + tool.description).lower() or (
            category and category != tool.category
        ):
            continue
        if tab == "recommended" and (
            session.get(ToolDismissal, (user.id, tool.id)) or tool.status != "Available"
        ):
            continue
        if tab == "favourites" and not value["favourite"]:
            continue
        if tab == "recent" and not value["last_used"]:
            continue
        if tab == "connected":
            continue
        if tab == "department" and not tool.department_id:
            continue
        result.append(value)
    if tab == "favourites":
        result.sort(key=lambda v: (v["position"], v["title"]))
    elif tab == "recent":
        result.sort(key=lambda v: v["last_used"], reverse=True)
    return result


def get_tool(id, user, session):
    value = session.get(ToolDefinition, id)
    if not value or not allowed_tool(value, user, session):
        raise HTTPException(404, "Tool unavailable in this workspace")
    return value


@router.post("/tools/{id}/favourite")
def favourite(id: str, user: User = Depends(current), session: Session = Depends(db)):
    tool = get_tool(id, user, session)
    if tool.status != "Available":
        raise HTTPException(409, "Only available tools can become executable shortcuts")
    if not session.get(ToolFavourite, (user.id, id)):
        position = len(
            session.scalars(select(ToolFavourite).where(ToolFavourite.user_id == user.id)).all()
        )
        session.add(ToolFavourite(user_id=user.id, tool_id=id, position=position))
    audit(session, user, "tool:favourite:" + id)
    session.commit()
    return {"favourite": True}


@router.delete("/tools/{id}/favourite")
def unfavourite(id: str, user: User = Depends(current), session: Session = Depends(db)):
    get_tool(id, user, session)
    value = session.get(ToolFavourite, (user.id, id))
    if value:
        session.delete(value)
    audit(session, user, "tool:unfavourite:" + id)
    session.commit()
    return {"favourite": False}


class Reorder(Input):
    ids: list[str] = Field(max_length=100)


@router.put("/favourites/order")
def order_favourites(data: Reorder, user: User = Depends(current), session: Session = Depends(db)):
    if len(set(data.ids)) != len(data.ids):
        raise HTTPException(422, "Duplicate tool")
    own = session.scalars(select(ToolFavourite).where(ToolFavourite.user_id == user.id)).all()
    allowed = [
        f for f in own if allowed_tool(session.get(ToolDefinition, f.tool_id), user, session)
    ]
    if set(data.ids) != {f.tool_id for f in allowed}:
        raise HTTPException(422, "Supply every authorised favourite exactly once")
    for f in allowed:
        f.position = data.ids.index(f.tool_id)
    audit(session, user, "tool:reorder")
    session.commit()
    return {"saved": True}


@router.post("/tools/{id}/open")
def open_tool(id: str, user: User = Depends(current), session: Session = Depends(db)):
    tool = get_tool(id, user, session)
    if tool.status != "Available":
        raise HTTPException(409, "This tool is " + tool.status.lower())
    session.add(ToolUsage(user_id=user.id, tool_id=id, department=user.department))
    audit(session, user, "tool:open:" + id)
    session.commit()
    return {"href": tool.href}


@router.post("/tools/{id}/dismiss")
def dismiss_tool(id: str, user: User = Depends(current), session: Session = Depends(db)):
    get_tool(id, user, session)
    if not session.get(ToolDismissal, (user.id, id)):
        session.add(ToolDismissal(user_id=user.id, tool_id=id))
    audit(session, user, "tool:dismiss:" + id)
    session.commit()
    return {"dismissed": True}


@router.delete("/tools/recent")
def clear_recent(user: User = Depends(current), session: Session = Depends(db)):
    for usage in session.scalars(select(ToolUsage).where(ToolUsage.user_id == user.id)):
        session.delete(usage)
    audit(session, user, "tool:clear_optional_recent")
    session.commit()
    return {"cleared": True}


class ToolRequestInput(Input):
    title: str = Field(min_length=3, max_length=160)
    reason: str = Field(min_length=10, max_length=2000)


@router.post("/tool-requests")
def request_tool(
    data: ToolRequestInput, user: User = Depends(current), session: Session = Depends(db)
):
    value = ToolRequest(user_id=user.id, department=user.department, **data.model_dump())
    session.add(value)
    audit(session, user, "tool:request")
    session.commit()
    session.refresh(value)
    return value


@router.get("/tool-requests")
def tool_requests(user: User = Depends(current), session: Session = Depends(db)):
    return session.scalars(select(ToolRequest).where(ToolRequest.user_id == user.id)).all()


@router.get("/tool-summary")
def tool_summary(user: User = Depends(current), session: Session = Depends(db)):
    available = tools("all", "", "", user, session)
    return {
        "favourites": sum(t["favourite"] for t in available),
        "recent": sum(t["last_used"] is not None for t in available),
        "connected": 0,
        "available": sum(t["status"] == "Available" for t in available),
        "pending_requests": len(
            session.scalars(
                select(ToolRequest).where(
                    ToolRequest.user_id == user.id, ToolRequest.status == "PENDING"
                )
            ).all()
        ),
    }


class MessageInput(Input):
    content: str = Field(min_length=1, max_length=10000)


@router.get("/conversations")
def conversations(
    q: str = "",
    archived: bool = False,
    user: User = Depends(current),
    session: Session = Depends(db),
):
    return session.scalars(
        select(Conversation)
        .where(
            Conversation.user_id == user.id,
            Conversation.department == user.department,
            Conversation.archived == archived,
            Conversation.title.icontains(q, autoescape=True),
        )
        .order_by(Conversation.pinned.desc(), Conversation.created.desc())
        .limit(100)
    ).all()


def get_conversation(id, user, session):
    value = session.get(Conversation, id)
    if not value or value.user_id != user.id or value.department != user.department:
        raise HTTPException(404)
    return value


@router.post("/conversations")
def create_conversation(
    data: MessageInput, user: User = Depends(current), session: Session = Depends(db)
):
    value = Conversation(user_id=user.id, department=user.department, title=data.content[:80])
    session.add(value)
    session.flush()
    append_message(value, data, user, session)
    session.commit()
    session.refresh(value)
    return value


def append_message(conversation, data, user, session):
    session.add(Message(conversation_id=conversation.id, role="user", content=data.content))
    session.flush()
    session.add(
        Message(
            conversation_id=conversation.id,
            role="assistant",
            content="AI not configured. Your message is saved in this conversation. For deterministic source-based drafting, open Documents and select authorised sources. No independent AI answer has been generated.",
        )
    )
    audit(session, user, "chat:message:" + conversation.id)


@router.get("/conversations/{id}")
def conversation(id: str, user: User = Depends(current), session: Session = Depends(db)):
    value = get_conversation(id, user, session)
    return {
        "conversation": value,
        "messages": session.scalars(
            select(Message)
            .where(Message.conversation_id == id)
            .order_by(Message.created, Message.id)
        ).all(),
    }


@router.post("/conversations/{id}/messages")
def post_message(
    id: str, data: MessageInput, user: User = Depends(current), session: Session = Depends(db)
):
    value = get_conversation(id, user, session)
    if value.archived:
        raise HTTPException(409, "Restore conversation before continuing")
    append_message(value, data, user, session)
    session.commit()
    return conversation(id, user, session)


class ConversationInput(Input):
    title: str = Field(min_length=1, max_length=160)
    pinned: bool = False
    archived: bool = False


@router.patch("/conversations/{id}")
def update_conversation(
    id: str, data: ConversationInput, user: User = Depends(current), session: Session = Depends(db)
):
    value = get_conversation(id, user, session)
    value.title, value.pinned, value.archived = data.title, data.pinned, data.archived
    audit(session, user, "chat:update:" + id)
    session.commit()
    return {"saved": True}


def seed_workspace(session):
    for name in [
        "DEMO Pension",
        "DEMO Administration",
        "DEMO Other",
        "DEMO General Administration",
    ]:
        department = session.scalar(select(Department).where(Department.name == name))
        if not department:
            department = Department(name=name)
            session.add(department)
            session.flush()
        division = session.scalar(
            select(Division).where(
                Division.department_id == department.id, Division.name == "General"
            )
        )
        if not division:
            session.add(Division(department_id=department.id, name="General"))
    session.flush()
    for user in session.scalars(select(User)):
        department = session.scalar(select(Department).where(Department.name == user.department))
        if not department:
            continue
        division = session.scalar(select(Division).where(Division.department_id == department.id))
        if not session.scalar(
            select(Membership).where(
                Membership.user_id == user.id,
                Membership.department_id == department.id,
                Membership.division_id == division.id,
            )
        ):
            session.add(
                Membership(
                    user_id=user.id,
                    department_id=department.id,
                    division_id=division.id,
                    role=user.role,
                )
            )
    definitions = [
        (
            "documents",
            "Document workspace",
            "Create source-grounded drafts, inspect citations and route review.",
            "Documents",
            "/documents",
            "Available",
            None,
        ),
        (
            "tasks",
            "My Tasks",
            "Manage your personal work records.",
            "Productivity",
            "/tasks",
            "Available",
            None,
        ),
        (
            "projects",
            "Projects",
            "Organise project records.",
            "Collaboration",
            "/projects",
            "Available",
            None,
        ),
        (
            "approvals",
            "Review queue",
            "Inspect immutable versions assigned for review.",
            "Documents",
            "/approvals",
            "Available",
            None,
        ),
        (
            "calendar",
            "Google Calendar",
            "Schedule meetings using a configured Google account.",
            "Connected apps",
            "/profile?section=apps",
            "Requires Connection",
            "google",
        ),
        (
            "pension",
            "Pension",
            "Open pension records in your approved department.",
            "Department Work",
            "/department/pension",
            "Available",
            None,
        ),
        (
            "grievances",
            "Public Grievances",
            "Open grievance records in your approved department.",
            "Department Work",
            "/department/grievances",
            "Available",
            None,
        ),
        (
            "outreach",
            "Outreach Agent",
            "Campaign simulation is not yet implemented.",
            "Department Work",
            "/department/outreach",
            "Temporarily Unavailable",
            None,
        ),
    ]
    pension = session.scalar(select(Department).where(Department.name == "DEMO Pension"))
    for id, title, description, category, href, status, provider in definitions:
        if not session.get(ToolDefinition, id):
            session.add(
                ToolDefinition(
                    id=id,
                    title=title,
                    description=description,
                    category=category,
                    href=href,
                    status=status,
                    provider=provider,
                    department_id=pension.id
                    if id in {"pension", "grievances", "outreach"}
                    else None,
                )
            )
    session.commit()


@router.get("/search")
def workspace_search(q: str, user: User = Depends(current), session: Session = Depends(db)):
    from main import Document, Record, Version, document_access

    if len(q) < 2 or len(q) > 200:
        raise HTTPException(422, "Enter 2-200 search characters")
    results = []
    for document in session.scalars(select(Document).where(Document.department == user.department)):
        try:
            document_access(document.id, user, session)
        except HTTPException:
            continue
        versions = session.scalars(
            select(Version)
            .where(Version.document_id == document.id)
            .order_by(Version.created.desc())
        ).all()
        if q.lower() in document.title.lower() or any(
            q.lower() in v.body.lower() for v in versions
        ):
            # Recheck every source dependency before exposing an extracted draft excerpt.
            permitted = True
            from main import Citation

            for v in versions:
                for citation in session.scalars(
                    select(Citation).where(Citation.version_id == v.id)
                ):
                    source = session.get(Version, citation.source_version)
                    try:
                        document_access(source.document_id, user, session)
                    except HTTPException:
                        permitted = False
            if permitted:
                results.append(
                    {
                        "id": document.id,
                        "title": document.title,
                        "kind": "document",
                        "url": "/documents/" + document.id,
                        "snippet": versions[0].body[:180] if versions else "",
                    }
                )
    mapping = {
        "projects": "projects",
        "tasks": "tasks",
        "pension": "department/pension",
        "grievances": "department/grievances",
    }
    for record in session.scalars(select(Record).where(Record.department == user.department)):
        if (
            record.kind not in mapping
            or q.lower() not in (record.title + " " + record.body).lower()
        ):
            continue
        results.append(
            {
                "id": record.id,
                "title": record.title,
                "kind": record.kind,
                "url": "/" + mapping[record.kind] + "/" + record.id,
                "snippet": record.body[:180],
            }
        )
    for chat in session.scalars(
        select(Conversation).where(
            Conversation.user_id == user.id,
            Conversation.department == user.department,
            Conversation.title.icontains(q, autoescape=True),
        )
    ):
        results.append(
            {
                "id": chat.id,
                "title": chat.title,
                "kind": "chat",
                "url": "/chat/" + chat.id,
                "snippet": "Your private conversation",
            }
        )
    return results[:100]


@router.get("/admin/support")
def support_queue(user: User = Depends(current), session: Session = Depends(db)):
    admin(user)
    return [
        {
            "id": t.id,
            "email": session.get(User, t.user_id).email,
            "subject": t.subject,
            "message": t.message,
            "status": t.status,
            "response": t.response,
        }
        for t in session.scalars(
            select(SupportTicket).order_by(SupportTicket.created.desc()).limit(200)
        )
    ]


class SupportDecision(Input):
    status: str = Field(pattern="^(OPEN|IN_PROGRESS|RESOLVED)$")
    response: str = Field(min_length=3, max_length=3000)


@router.post("/admin/support/{id}")
def answer_ticket(
    id: str, data: SupportDecision, user: User = Depends(current), session: Session = Depends(db)
):
    admin(user)
    ticket = session.get(SupportTicket, id)
    if not ticket:
        raise HTTPException(404)
    ticket.status, ticket.response = data.status, data.response
    notify(session, ticket.user_id, "department", "Support ticket updated", "/profile?section=help")
    audit(session, user, "support:respond:" + id)
    session.commit()
    return {"saved": True}
