"""Project collaboration, canonical tasks and distinct illustrative case workflows."""

from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException
from main import Base, Record, User, current, db, document_access
from pydantic import Field
from sqlalchemy import JSON, ForeignKey, String, Text, UniqueConstraint, select
from sqlalchemy.orm import Mapped, Session, mapped_column
from workspace import Input, active, audit, notify
from workspace_models import Department, Membership, now, uid

router = APIRouter(prefix="/work", tags=["Internal work"])


class Project(Base):
    __tablename__ = "projects"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    department: Mapped[str] = mapped_column(String)
    owner: Mapped[str] = mapped_column(ForeignKey("users.id"))
    title: Mapped[str] = mapped_column(String)
    purpose: Mapped[str] = mapped_column(Text)
    archived: Mapped[bool] = mapped_column(default=False)
    created: Mapped[int] = mapped_column(default=now)


class ProjectMember(Base):
    __tablename__ = "project_members"
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), primary_key=True)
    role: Mapped[str] = mapped_column(String, default="member")


class Case(Base):
    __tablename__ = "work_cases"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    kind: Mapped[str] = mapped_column(String)
    department: Mapped[str] = mapped_column(String)
    creator: Mapped[str] = mapped_column(ForeignKey("users.id"))
    assignee: Mapped[str] = mapped_column(ForeignKey("users.id"))
    reference: Mapped[str] = mapped_column(String, unique=True)
    subject: Mapped[str] = mapped_column(String)
    details: Mapped[dict] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String)
    response: Mapped[str] = mapped_column(Text, default="")
    created: Mapped[int] = mapped_column(default=now)


class CaseEvent(Base):
    __tablename__ = "case_events"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    case_id: Mapped[str] = mapped_column(ForeignKey("work_cases.id"))
    actor: Mapped[str] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String)
    note: Mapped[str] = mapped_column(Text)
    created: Mapped[int] = mapped_column(default=now)


class Checklist(Base):
    __tablename__ = "case_checklists"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    case_id: Mapped[str] = mapped_column(ForeignKey("work_cases.id"))
    title: Mapped[str] = mapped_column(String)
    checked: Mapped[bool] = mapped_column(default=False)


class Deficiency(Base):
    __tablename__ = "case_deficiencies"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    case_id: Mapped[str] = mapped_column(ForeignKey("work_cases.id"))
    description: Mapped[str] = mapped_column(Text)
    resolved: Mapped[bool] = mapped_column(default=False)


class Task(Base):
    __tablename__ = "tasks"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    department: Mapped[str] = mapped_column(String)
    creator: Mapped[str] = mapped_column(ForeignKey("users.id"))
    assignee: Mapped[str] = mapped_column(ForeignKey("users.id"))
    title: Mapped[str] = mapped_column(String)
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String, default="To Do")
    priority: Mapped[str] = mapped_column(String, default="Normal")
    due_date: Mapped[str | None] = mapped_column(String)
    project_id: Mapped[str | None] = mapped_column(ForeignKey("projects.id"))
    case_id: Mapped[str | None] = mapped_column(ForeignKey("work_cases.id"))
    reminder: Mapped[str | None] = mapped_column(String)


class TaskComment(Base):
    __tablename__ = "task_comments"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.id"))
    author: Mapped[str] = mapped_column(ForeignKey("users.id"))
    body: Mapped[str] = mapped_column(Text)
    created: Mapped[int] = mapped_column(default=now)


class ProjectPost(Base):
    __tablename__ = "project_posts"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"))
    author: Mapped[str] = mapped_column(ForeignKey("users.id"))
    body: Mapped[str] = mapped_column(Text)
    created: Mapped[int] = mapped_column(default=now)


class Meeting(Base):
    __tablename__ = "meetings"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"))
    creator: Mapped[str] = mapped_column(ForeignKey("users.id"))
    title: Mapped[str] = mapped_column(String)
    starts: Mapped[str] = mapped_column(String)
    agenda: Mapped[str] = mapped_column(Text)
    minutes: Mapped[str] = mapped_column(Text, default="")


class WorkFile(Base):
    __tablename__ = "work_file_links"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"))
    project_id: Mapped[str | None] = mapped_column(ForeignKey("projects.id"))
    case_id: Mapped[str | None] = mapped_column(ForeignKey("work_cases.id"))


class Campaign(Base):
    __tablename__ = "outreach_campaigns"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    department: Mapped[str] = mapped_column(String)
    owner: Mapped[str] = mapped_column(ForeignKey("users.id"))
    name: Mapped[str] = mapped_column(String)
    purpose: Mapped[str] = mapped_column(Text)
    script: Mapped[str] = mapped_column(Text)
    language: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, default="DRAFT")
    reviewer: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    language_reviewed: Mapped[bool] = mapped_column(default=False)


class Contact(Base):
    __tablename__ = "campaign_contacts"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    campaign_id: Mapped[str] = mapped_column(ForeignKey("outreach_campaigns.id"))
    alias: Mapped[str] = mapped_column(String)
    consent: Mapped[bool]
    opt_out: Mapped[bool] = mapped_column(default=False)
    feedback: Mapped[str] = mapped_column(Text, default="")


class Delivery(Base):
    __tablename__ = "simulated_deliveries"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    campaign_id: Mapped[str] = mapped_column(ForeignKey("outreach_campaigns.id"))
    contact_id: Mapped[str] = mapped_column(ForeignKey("campaign_contacts.id"))
    status: Mapped[str] = mapped_column(String)
    created: Mapped[int] = mapped_column(default=now)
    __table_args__ = (UniqueConstraint("campaign_id", "contact_id"),)


def scoped(model, id, user, session):
    value = session.get(model, id)
    if not value or value.department != user.department:
        raise HTTPException(404)
    return value


def project_access(id, user, session, write=False):
    project = scoped(Project, id, user, session)
    member = session.get(ProjectMember, (id, user.id))
    if not member or (write and member.role == "viewer"):
        raise HTTPException(403, "Project membership does not permit this action")
    return project


def authorised_user(email, user, session):
    target = session.scalar(select(User).where(User.email == email.strip().lower()))
    if not target:
        raise HTTPException(422, "Invite an existing authorised colleague")
    memberships = session.scalars(select(Membership).where(Membership.user_id == target.id)).all()
    valid = target.department == user.department and not memberships
    for m in memberships:
        if active(m) and session.get(Department, m.department_id).name == user.department:
            valid = True
    if not valid:
        raise HTTPException(403, "Colleague lacks approved department access")
    return target


class ProjectInput(Input):
    title: str = Field(min_length=3, max_length=160)
    purpose: str = Field(min_length=10, max_length=5000)


@router.get("/projects")
def projects(user: User = Depends(current), session: Session = Depends(db)):
    return session.scalars(
        select(Project)
        .join(ProjectMember, ProjectMember.project_id == Project.id)
        .where(Project.department == user.department, ProjectMember.user_id == user.id)
    ).all()


@router.post("/projects")
def create_project(
    data: ProjectInput, user: User = Depends(current), session: Session = Depends(db)
):
    project = Project(department=user.department, owner=user.id, **data.model_dump())
    session.add(project)
    session.flush()
    session.add(ProjectMember(project_id=project.id, user_id=user.id, role="owner"))
    audit(session, user, "project:create:" + project.id)
    session.commit()
    session.refresh(project)
    return project


@router.get("/projects/{id}")
def project_detail(id: str, user: User = Depends(current), session: Session = Depends(db)):
    project = project_access(id, user, session)
    members = [
        {"id": m.user_id, "email": session.get(User, m.user_id).email, "role": m.role}
        for m in session.scalars(select(ProjectMember).where(ProjectMember.project_id == id))
    ]
    return {
        "project": project,
        "members": members,
        "tasks": session.scalars(select(Task).where(Task.project_id == id)).all(),
        "meetings": session.scalars(select(Meeting).where(Meeting.project_id == id)).all(),
        "discussions": session.scalars(
            select(ProjectPost).where(ProjectPost.project_id == id).order_by(ProjectPost.created)
        ).all(),
        "files": permitted_files(id, None, user, session),
    }


class InviteInput(Input):
    email: str
    role: str = Field(default="member", pattern="^(manager|member|viewer)$")


@router.post("/projects/{id}/members")
def invite(
    id: str, data: InviteInput, user: User = Depends(current), session: Session = Depends(db)
):
    project = project_access(id, user, session, True)
    if project.owner != user.id:
        raise HTTPException(403, "Only the project owner manages roles")
    target = authorised_user(data.email, user, session)
    if target.id == project.owner:
        raise HTTPException(409, "Ownership cannot be replaced through an invitation")
    member = session.get(ProjectMember, (id, target.id))
    if not member:
        member = ProjectMember(project_id=id, user_id=target.id)
        session.add(member)
    member.role = data.role
    notify(
        session, target.id, "projects", "Project invitation: " + project.title, "/projects/" + id
    )
    audit(session, user, "project:invite:" + id)
    session.commit()
    return {"invited": True}


class TextInput(Input):
    body: str = Field(min_length=1, max_length=5000)


@router.post("/projects/{id}/discussions")
def post_discussion(
    id: str, data: TextInput, user: User = Depends(current), session: Session = Depends(db)
):
    project_access(id, user, session, True)
    session.add(ProjectPost(project_id=id, author=user.id, body=data.body))
    audit(session, user, "project:discussion:" + id)
    session.commit()
    return {"posted": True}


class MeetingInput(Input):
    title: str = Field(min_length=3, max_length=160)
    starts: datetime
    agenda: str = Field(min_length=5, max_length=5000)


@router.post("/projects/{id}/meetings")
def create_meeting(
    id: str, data: MeetingInput, user: User = Depends(current), session: Session = Depends(db)
):
    project_access(id, user, session, True)
    meeting = Meeting(
        project_id=id,
        creator=user.id,
        title=data.title,
        starts=data.starts.isoformat(),
        agenda=data.agenda,
    )
    session.add(meeting)
    for member in session.scalars(select(ProjectMember).where(ProjectMember.project_id == id)):
        notify(
            session,
            member.user_id,
            "meetings",
            "Internal meeting: " + data.title,
            "/projects/" + id,
        )
    audit(session, user, "meeting:create:" + id)
    session.commit()
    return {"scheduled": True, "provider": "Internal only; no external meeting URL"}


class TaskInput(Input):
    title: str = Field(min_length=3, max_length=160)
    description: str = Field(default="", max_length=5000)
    assignee_email: str | None = None
    priority: str = Field(default="Normal", pattern="^(Low|Normal|High|Urgent)$")
    due_date: date | None = None
    project_id: str | None = None
    case_id: str | None = None
    reminder: datetime | None = None


@router.post("/tasks")
def create_task(data: TaskInput, user: User = Depends(current), session: Session = Depends(db)):
    assignee = authorised_user(data.assignee_email or user.email, user, session)
    if data.project_id:
        project_access(data.project_id, user, session, True)
        if not session.get(ProjectMember, (data.project_id, assignee.id)):
            raise HTTPException(422, "Assignee must be a project member")
    if data.case_id:
        scoped(Case, data.case_id, user, session)
    task = Task(
        title=data.title,
        description=data.description,
        department=user.department,
        creator=user.id,
        assignee=assignee.id,
        priority=data.priority,
        due_date=data.due_date.isoformat() if data.due_date else None,
        reminder=data.reminder.isoformat() if data.reminder else None,
        project_id=data.project_id,
        case_id=data.case_id,
    )
    session.add(task)
    session.flush()
    notify(session, assignee.id, "tasks", "Task assigned: " + task.title, "/tasks/" + task.id)
    audit(session, user, "task:create:" + task.id)
    session.commit()
    session.refresh(task)
    return task


def task_access(id, user, session):
    task = scoped(Task, id, user, session)
    if user.id not in {task.creator, task.assignee}:
        if not task.project_id:
            raise HTTPException(403)
        project_access(task.project_id, user, session)
    return task


@router.get("/tasks")
def tasks(
    view: str = "mine",
    status: str = "",
    q: str = "",
    user: User = Depends(current),
    session: Session = Depends(db),
):
    result = []
    for task in session.scalars(select(Task).where(Task.department == user.department)):
        try:
            task_access(task.id, user, session)
        except HTTPException:
            continue
        if view == "assigned" and task.creator != user.id:
            continue
        if view == "mine" and task.assignee != user.id:
            continue
        if view == "completed" and task.status != "Completed":
            continue
        if status and task.status != status:
            continue
        if q.lower() not in task.title.lower():
            continue
        result.append(task)
    return sorted(result, key=lambda t: (t.due_date or "9999", t.title))


@router.get("/tasks/{id}")
def task_detail(id: str, user: User = Depends(current), session: Session = Depends(db)):
    task = task_access(id, user, session)
    return {
        "task": task,
        "assignee": session.get(User, task.assignee).email,
        "comments": session.scalars(
            select(TaskComment).where(TaskComment.task_id == id).order_by(TaskComment.created)
        ).all(),
        "source_url": "/projects/" + task.project_id
        if task.project_id
        else "/department/" + session.get(Case, task.case_id).kind + "/" + task.case_id
        if task.case_id
        else None,
    }


class StatusInput(Input):
    status: str = Field(pattern="^(To Do|In Progress|Pending Review|Completed|Paused|Cancelled)$")


@router.patch("/tasks/{id}")
def update_task(
    id: str, data: StatusInput, user: User = Depends(current), session: Session = Depends(db)
):
    task = task_access(id, user, session)
    if user.id not in {task.creator, task.assignee}:
        raise HTTPException(403)
    task.status = data.status
    audit(session, user, "task:status:" + id)
    session.commit()
    return {"saved": True}


@router.post("/tasks/{id}/comments")
def task_comment(
    id: str, data: TextInput, user: User = Depends(current), session: Session = Depends(db)
):
    task_access(id, user, session)
    session.add(TaskComment(task_id=id, author=user.id, body=data.body))
    audit(session, user, "task:comment:" + id)
    session.commit()
    return {"posted": True}


class PensionInput(Input):
    scheme: str = Field(
        default="Government employee", pattern="^(Government employee|Social welfare)$"
    )
    scheme_name: str = Field(default="", max_length=160)
    pensioner_alias: str = Field(min_length=3, max_length=100)
    case_type: str = Field(
        pattern="^(Retirement|Family|Revision|Clarification|New beneficiary|Renewal|Disability|Survivor)$"
    )
    retirement_date: date | None = None
    summary: str = Field(min_length=10, max_length=5000)


class GrievanceInput(Input):
    complainant_alias: str = Field(min_length=3, max_length=100)
    subject: str = Field(min_length=3, max_length=160)
    channel: str = Field(pattern="^(Internal demo|Letter|Email|Import)$")
    category: str = Field(min_length=3, max_length=100)
    jurisdiction: str = Field(min_length=3, max_length=160)
    description: str = Field(min_length=10, max_length=5000)


TRANSITIONS = {
    "pension": {
        "REGISTERED": ["COLLECTING"],
        "COLLECTING": ["VERIFICATION"],
        "VERIFICATION": ["DEFICIENCIES", "UNDER_REVIEW"],
        "DEFICIENCIES": ["VERIFICATION"],
        "UNDER_REVIEW": ["VERIFICATION", "FORWARDED"],
        "FORWARDED": ["CLOSED"],
        "CLOSED": [],
    },
    "grievances": {
        "RECEIVED": ["ASSIGNED"],
        "ASSIGNED": ["INVESTIGATING"],
        "INVESTIGATING": ["RESPONSE_DRAFTED"],
        "RESPONSE_DRAFTED": ["UNDER_REVIEW"],
        "UNDER_REVIEW": ["INVESTIGATING", "RESOLVED"],
        "RESOLVED": ["CLOSED"],
        "CLOSED": ["INVESTIGATING"],
    },
}


@router.get("/cases/{kind}")
def cases(kind: str, user: User = Depends(current), session: Session = Depends(db)):
    if kind not in TRANSITIONS:
        raise HTTPException(404)
    return session.scalars(
        select(Case)
        .where(Case.kind == kind, Case.department == user.department)
        .order_by(Case.created.desc())
    ).all()


@router.post("/cases/{kind}")
def new_case(
    kind: str,
    data: PensionInput | GrievanceInput,
    user: User = Depends(current),
    session: Session = Depends(db),
):
    if kind not in TRANSITIONS:
        raise HTTPException(404)
    if (kind == "pension") != isinstance(data, PensionInput):
        raise HTTPException(422, "Use the form for this case type")
    id = uid()
    details = data.model_dump(mode="json")
    if isinstance(data, PensionInput):
        details["register"] = {"scheme": data.scheme, "scheme_name": data.scheme_name}
    subject = (
        data.pensioner_alias + " - " + data.case_type
        if isinstance(data, PensionInput)
        else data.subject
    )
    value = Case(
        id=id,
        kind=kind,
        department=user.department,
        creator=user.id,
        assignee=user.id,
        reference="DEMO-" + ("PEN-" if kind == "pension" else "GRV-") + id[:8].upper(),
        subject=subject,
        details=details,
        status="REGISTERED" if kind == "pension" else "RECEIVED",
    )
    session.add(value)
    session.flush()
    if kind == "pension":
        for title in [
            "Sample identity details reviewed",
            "Sample supporting service record reviewed",
            "Sample correspondence reviewed",
        ]:
            session.add(Checklist(case_id=id, title=title))
    case_event(
        value,
        user,
        session,
        "REGISTERED",
        "Fictional case registered; workflow is illustrative, not a government rule",
    )
    session.commit()
    session.refresh(value)
    return value


def case_event(case, user, session, action, note):
    session.add(CaseEvent(case_id=case.id, actor=user.id, action=action, note=note))
    audit(session, user, "case:" + action.lower() + ":" + case.id)


@router.get("/cases/{kind}/{id}")
def case_detail(kind: str, id: str, user: User = Depends(current), session: Session = Depends(db)):
    value = scoped(Case, id, user, session)
    if value.kind != kind:
        raise HTTPException(404)
    return {
        "case": value,
        "checklist": session.scalars(select(Checklist).where(Checklist.case_id == id)).all(),
        "deficiencies": session.scalars(select(Deficiency).where(Deficiency.case_id == id)).all(),
        "events": session.scalars(
            select(CaseEvent).where(CaseEvent.case_id == id).order_by(CaseEvent.created)
        ).all(),
        "tasks": session.scalars(select(Task).where(Task.case_id == id)).all(),
        "files": permitted_files(None, id, user, session),
        "next": TRANSITIONS[kind][value.status],
        "assignee": session.get(User, value.assignee).email,
    }


class CaseTransition(Input):
    status: str
    note: str = Field(min_length=3, max_length=3000)


@router.post("/cases/{kind}/{id}/transition")
def transition_case(
    kind: str,
    id: str,
    data: CaseTransition,
    user: User = Depends(current),
    session: Session = Depends(db),
):
    case = scoped(Case, id, user, session)
    if case.kind != kind or data.status not in TRANSITIONS[kind].get(case.status, []):
        raise HTTPException(409, "Invalid workflow transition")
    if user.id not in {case.creator, case.assignee} and user.role != "reviewer":
        raise HTTPException(403)
    if data.status in {"FORWARDED", "RESOLVED"} and (
        user.role != "reviewer" or user.id == case.creator
    ):
        raise HTTPException(403, "A separate authorised human reviewer is required")
    if kind == "pension" and data.status == "UNDER_REVIEW":
        if any(
            not c.checked for c in session.scalars(select(Checklist).where(Checklist.case_id == id))
        ) or any(
            not d.resolved
            for d in session.scalars(select(Deficiency).where(Deficiency.case_id == id))
        ):
            raise HTTPException(422, "Complete the checklist and resolve deficiencies first")
    if kind == "grievances" and data.status == "UNDER_REVIEW" and not case.response.strip():
        raise HTTPException(422, "Save the proposed response before review")
    case.status = data.status
    case_event(case, user, session, data.status, data.note)
    notify(
        session,
        case.assignee,
        "department",
        "Case " + case.reference + ": " + data.status.replace("_", " "),
        "/department/" + kind + "/" + id,
    )
    session.commit()
    return {"status": case.status}


class CheckInput(Input):
    checked: bool


@router.patch("/cases/{id}/checklist/{check_id}")
def check_item(
    id: str,
    check_id: str,
    data: CheckInput,
    user: User = Depends(current),
    session: Session = Depends(db),
):
    case = scoped(Case, id, user, session)
    item = session.get(Checklist, check_id)
    if not item or item.case_id != id:
        raise HTTPException(404)
    if user.id not in {case.creator, case.assignee}:
        raise HTTPException(403)
    item.checked = data.checked
    case_event(case, user, session, "CHECKLIST", item.title)
    session.commit()
    return {"saved": True}


@router.post("/cases/{id}/deficiencies")
def add_deficiency(
    id: str, data: TextInput, user: User = Depends(current), session: Session = Depends(db)
):
    case = scoped(Case, id, user, session)
    if case.kind != "pension":
        raise HTTPException(422)
    session.add(Deficiency(case_id=id, description=data.body))
    case_event(case, user, session, "DEFICIENCY", data.body)
    session.commit()
    return {"saved": True}


@router.post("/cases/{id}/deficiencies/{deficiency_id}/resolve")
def resolve_deficiency(
    id: str, deficiency_id: str, user: User = Depends(current), session: Session = Depends(db)
):
    case = scoped(Case, id, user, session)
    value = session.get(Deficiency, deficiency_id)
    if not value or value.case_id != id:
        raise HTTPException(404)
    value.resolved = True
    case_event(case, user, session, "DEFICIENCY_RESOLVED", value.description)
    session.commit()
    return {"saved": True}


class AssignInput(Input):
    email: str


@router.post("/cases/{id}/assign")
def assign_case(
    id: str, data: AssignInput, user: User = Depends(current), session: Session = Depends(db)
):
    case = scoped(Case, id, user, session)
    if user.id != case.creator and user.role != "reviewer":
        raise HTTPException(403)
    target = authorised_user(data.email, user, session)
    case.assignee = target.id
    case_event(case, user, session, "ASSIGNED", "Assigned to an authorised colleague")
    notify(
        session,
        target.id,
        "department",
        "Case assigned: " + case.reference,
        "/department/" + case.kind + "/" + id,
    )
    session.commit()
    return {"assigned": True}


@router.put("/cases/{id}/correspondence")
def correspondence(
    id: str, data: TextInput, user: User = Depends(current), session: Session = Depends(db)
):
    case = scoped(Case, id, user, session)
    if user.id not in {case.creator, case.assignee}:
        raise HTTPException(403)
    case.response = data.body
    case_event(
        case, user, session, "CORRESPONDENCE", "Draft correspondence updated; no external dispatch"
    )
    session.commit()
    return {"saved": True}


class FileLinkInput(Input):
    document_id: str


@router.post("/projects/{id}/files")
def attach_project(
    id: str, data: FileLinkInput, user: User = Depends(current), session: Session = Depends(db)
):
    project_access(id, user, session, True)
    document_access(data.document_id, user, session)
    session.add(WorkFile(document_id=data.document_id, project_id=id))
    audit(session, user, "project:file:" + id)
    session.commit()
    return {"attached": True}


@router.post("/cases/{id}/files")
def attach_case(
    id: str, data: FileLinkInput, user: User = Depends(current), session: Session = Depends(db)
):
    case = scoped(Case, id, user, session)
    document_access(data.document_id, user, session)
    session.add(WorkFile(document_id=data.document_id, case_id=id))
    case_event(case, user, session, "ATTACHMENT", "Authorised source document attached")
    session.commit()
    return {"attached": True}


def permitted_files(project_id, case_id, user, session):
    query = (
        select(WorkFile).where(WorkFile.project_id == project_id)
        if project_id
        else select(WorkFile).where(WorkFile.case_id == case_id)
    )
    result = []
    for link in session.scalars(query):
        try:
            document = document_access(link.document_id, user, session)
        except HTTPException:
            continue
        result.append({"id": document.id, "title": document.title})
    return result


class CampaignEvent(Base):
    __tablename__ = "campaign_events"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    campaign_id: Mapped[str] = mapped_column(ForeignKey("outreach_campaigns.id"))
    actor: Mapped[str] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String)
    comment: Mapped[str] = mapped_column(Text)
    created: Mapped[int] = mapped_column(default=now)


class CampaignInput(Input):
    name: str = Field(min_length=3, max_length=160)
    purpose: str = Field(min_length=10, max_length=3000)
    script: str = Field(min_length=10, max_length=5000)
    language: str = Field(pattern="^(en|as|hi)$")
    language_reviewed: bool = False


@router.get("/campaigns")
def campaigns(user: User = Depends(current), session: Session = Depends(db)):
    return session.scalars(select(Campaign).where(Campaign.department == user.department)).all()


@router.post("/campaigns")
def create_campaign(
    data: CampaignInput, user: User = Depends(current), session: Session = Depends(db)
):
    value = Campaign(department=user.department, owner=user.id, **data.model_dump())
    session.add(value)
    audit(session, user, "outreach:create")
    session.commit()
    session.refresh(value)
    return value


@router.get("/campaigns/{id}")
def campaign_detail(id: str, user: User = Depends(current), session: Session = Depends(db)):
    value = scoped(Campaign, id, user, session)
    return {
        "campaign": value,
        "contacts": session.scalars(select(Contact).where(Contact.campaign_id == id)).all(),
        "deliveries": session.scalars(select(Delivery).where(Delivery.campaign_id == id)).all(),
        "events": session.scalars(
            select(CampaignEvent).where(CampaignEvent.campaign_id == id)
        ).all(),
        "provider": "SIMULATED - no messages sent",
    }


class ContactInput(Input):
    alias: str = Field(min_length=3, max_length=100)
    consent: bool


@router.post("/campaigns/{id}/contacts")
def add_contact(
    id: str, data: ContactInput, user: User = Depends(current), session: Session = Depends(db)
):
    campaign = scoped(Campaign, id, user, session)
    if campaign.owner != user.id or campaign.status != "DRAFT":
        raise HTTPException(403, "Only the owner may edit a draft audience")
    if any(
        c.alias.casefold() == data.alias.casefold()
        for c in session.scalars(select(Contact).where(Contact.campaign_id == id))
    ):
        raise HTTPException(409, "Duplicate contact alias")
    session.add(Contact(campaign_id=id, alias=data.alias, consent=data.consent))
    audit(session, user, "outreach:contact:" + id)
    session.commit()
    return {"saved": True}


class CampaignSubmit(Input):
    reviewer_email: str


@router.post("/campaigns/{id}/submit")
def submit_campaign(
    id: str, data: CampaignSubmit, user: User = Depends(current), session: Session = Depends(db)
):
    campaign = scoped(Campaign, id, user, session)
    reviewer = authorised_user(data.reviewer_email, user, session)
    if campaign.owner != user.id or campaign.status != "DRAFT":
        raise HTTPException(403)
    if reviewer.role != "reviewer" or reviewer.id == user.id:
        raise HTTPException(422, "A separate reviewer is required")
    if not campaign.language_reviewed:
        raise HTTPException(422, "Human language review must be recorded before submission")
    if not session.scalar(
        select(Contact).where(
            Contact.campaign_id == id, Contact.consent.is_(True), Contact.opt_out.is_(False)
        )
    ):
        raise HTTPException(422, "At least one eligible fictional contact is required")
    campaign.reviewer = reviewer.id
    campaign.status = "UNDER_REVIEW"
    notify(
        session,
        reviewer.id,
        "approvals",
        "Simulated campaign review: " + campaign.name,
        "/department/outreach/" + id,
    )
    session.add(
        CampaignEvent(
            campaign_id=id,
            actor=user.id,
            action="SUBMITTED",
            comment="Requested human review of fictional campaign",
        )
    )
    audit(session, user, "outreach:submit:" + id)
    session.commit()
    return {"status": campaign.status}


class CampaignDecision(Input):
    status: str = Field(pattern="^(APPROVED|REJECTED)$")
    comment: str = Field(min_length=3, max_length=3000)


@router.post("/campaigns/{id}/decision")
def campaign_decision(
    id: str, data: CampaignDecision, user: User = Depends(current), session: Session = Depends(db)
):
    campaign = scoped(Campaign, id, user, session)
    if campaign.reviewer != user.id or campaign.owner == user.id or user.role != "reviewer":
        raise HTTPException(403)
    if campaign.status != "UNDER_REVIEW":
        raise HTTPException(409)
    campaign.status = data.status
    session.add(
        CampaignEvent(campaign_id=id, actor=user.id, action=data.status, comment=data.comment)
    )
    notify(
        session,
        campaign.owner,
        "approvals",
        "Campaign " + data.status.lower(),
        "/department/outreach/" + id,
    )
    audit(session, user, "outreach:decision:" + id)
    session.commit()
    return {"status": campaign.status}


@router.post("/campaigns/{id}/simulate")
def simulate(id: str, user: User = Depends(current), session: Session = Depends(db)):
    campaign = scoped(Campaign, id, user, session)
    if campaign.owner != user.id:
        raise HTTPException(403)
    if campaign.status != "APPROVED":
        raise HTTPException(409, "Only an approved campaign can be simulated once")
    for contact in session.scalars(select(Contact).where(Contact.campaign_id == id)):
        session.add(
            Delivery(
                campaign_id=id,
                contact_id=contact.id,
                status="SIMULATED_DELIVERED"
                if contact.consent and not contact.opt_out
                else "SKIPPED_NO_CONSENT_OR_OPT_OUT",
            )
        )
    campaign.status = "SIMULATION_COMPLETED"
    session.add(
        CampaignEvent(
            campaign_id=id,
            actor=user.id,
            action="SIMULATED",
            comment="DEMO - no messages or calls sent",
        )
    )
    audit(session, user, "outreach:simulate:" + id)
    session.commit()
    return {"status": campaign.status, "real_messages_sent": 0}


class ContactUpdate(Input):
    opt_out: bool
    feedback: str = Field(default="", max_length=2000)


@router.patch("/campaigns/{id}/contacts/{contact_id}")
def update_contact(
    id: str,
    contact_id: str,
    data: ContactUpdate,
    user: User = Depends(current),
    session: Session = Depends(db),
):
    campaign = scoped(Campaign, id, user, session)
    contact = session.get(Contact, contact_id)
    if not contact or contact.campaign_id != id:
        raise HTTPException(404)
    if campaign.owner != user.id:
        raise HTTPException(403)
    if contact.opt_out and not data.opt_out:
        raise HTTPException(
            422,
            "Opt-out cannot be silently reversed; record fresh consent through a future consent workflow",
        )
    contact.opt_out = data.opt_out
    contact.feedback = data.feedback
    audit(session, user, "outreach:feedback_optout:" + id)
    session.commit()
    return {"saved": True}


def seed_legacy_work(session):
    from workspace_models import ToolDefinition

    outreach = session.get(ToolDefinition, "outreach")
    if outreach:
        outreach.status = "Available"
        outreach.description = "Consent-aware SIMULATED campaigns; no messages or calls sent."
    for record in session.scalars(select(Record).where(Record.kind == "projects")):
        if not session.get(Project, record.id):
            session.add(
                Project(
                    id=record.id,
                    department=record.department,
                    owner=record.owner,
                    title=record.title,
                    purpose=record.body or "Preserved legacy demo project",
                )
            )
            session.flush()
            session.add(ProjectMember(project_id=record.id, user_id=record.owner, role="owner"))
    for record in session.scalars(select(Record).where(Record.kind == "tasks")):
        if not session.get(Task, record.id):
            session.add(
                Task(
                    id=record.id,
                    department=record.department,
                    creator=record.owner,
                    assignee=record.owner,
                    title=record.title,
                    description=record.body,
                )
            )
    for record in session.scalars(select(Record).where(Record.kind.in_(["pension", "grievances"]))):
        if not session.get(Case, record.id):
            session.add(
                Case(
                    id=record.id,
                    kind=record.kind,
                    department=record.department,
                    creator=record.owner,
                    assignee=record.owner,
                    reference="DEMO-LEGACY-" + record.id[:8].upper(),
                    subject=record.title,
                    details={"legacy_note": record.body},
                    status="REGISTERED" if record.kind == "pension" else "RECEIVED",
                )
            )
    session.commit()


class ProjectUpdate(ProjectInput):
    archived: bool = False


@router.patch("/projects/{id}")
def update_project(
    id: str, data: ProjectUpdate, user: User = Depends(current), session: Session = Depends(db)
):
    project = project_access(id, user, session, True)
    if project.owner != user.id:
        raise HTTPException(403)
    project.title, project.purpose, project.archived = data.title, data.purpose, data.archived
    audit(session, user, "project:update:" + id)
    session.commit()
    return {"saved": True}


@router.put("/meetings/{id}/minutes")
def meeting_minutes(
    id: str, data: TextInput, user: User = Depends(current), session: Session = Depends(db)
):
    meeting = session.get(Meeting, id)
    if not meeting:
        raise HTTPException(404)
    project_access(meeting.project_id, user, session, True)
    meeting.minutes = data.body
    audit(session, user, "meeting:minutes:" + meeting.project_id)
    session.commit()
    return {"saved": True}


@router.get("/projects/{id}/activity")
def project_activity(id: str, user: User = Depends(current), session: Session = Depends(db)):
    from main import Audit

    project_access(id, user, session)
    return [
        {"action": e.action, "created": e.created}
        for e in session.scalars(
            select(Audit)
            .where(Audit.action.endswith(":" + id))
            .order_by(Audit.created.desc())
            .limit(100)
        )
    ]
