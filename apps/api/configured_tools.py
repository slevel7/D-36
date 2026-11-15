"""Versioned departmental form tools and explicit, idempotent agent task previews."""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from main import Base, User, current, db
from pydantic import Field
from sqlalchemy import JSON, ForeignKey, String, Text, select, update
from sqlalchemy.orm import Mapped, Session, mapped_column
from work import (
    Case,
    ProjectMember,
    Task,
    TaskInput,
    authorised_user,
    project_access,
    scoped,
)
from workspace import Input, admin, audit, notify
from workspace_models import Department, ToolDefinition, now, uid

router = APIRouter(prefix="/configured", tags=["Configured tools and action previews"])


class ToolConfiguration(Base):
    __tablename__ = "tool_configurations"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    tool_id: Mapped[str] = mapped_column(ForeignKey("tool_definitions.id"), unique=True)
    creator: Mapped[str] = mapped_column(ForeignKey("users.id"))
    fields: Mapped[list] = mapped_column(JSON)
    roles: Mapped[list] = mapped_column(JSON)
    states: Mapped[list] = mapped_column(JSON)
    version: Mapped[int] = mapped_column(default=1)
    status: Mapped[str] = mapped_column(String, default="DRAFT")
    approved_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    review_comment: Mapped[str] = mapped_column(Text, default="")


class ToolEntry(Base):
    __tablename__ = "tool_entries"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    configuration_id: Mapped[str] = mapped_column(ForeignKey("tool_configurations.id"))
    creator: Mapped[str] = mapped_column(ForeignKey("users.id"))
    values: Mapped[dict] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String)
    created: Mapped[int] = mapped_column(default=now)


class AgentAction(Base):
    __tablename__ = "agent_actions"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    actor: Mapped[str] = mapped_column(ForeignKey("users.id"))
    department: Mapped[str] = mapped_column(String)
    payload: Mapped[dict] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String, default="PROPOSED")
    result_id: Mapped[str | None] = mapped_column(String)
    expires: Mapped[int]


class ToolField(Input):
    name: str = Field(pattern="^[a-z][a-z0-9_]{0,39}$")
    label: str = Field(min_length=2, max_length=100)
    type: str = Field(pattern="^(text|number|date|select|checkbox)$")
    required: bool = True
    options: list[str] = Field(default_factory=list, max_length=30)


class ConfigurationInput(Input):
    title: str = Field(min_length=3, max_length=100)
    description: str = Field(min_length=10, max_length=1000)
    department_id: str
    fields: list[ToolField] = Field(min_length=1, max_length=20)
    roles: list[str] = Field(min_length=1, max_length=5)
    states: list[str] = Field(
        default_factory=lambda: ["Received", "Assigned", "Closed"], min_length=1, max_length=10
    )


@router.get("/admin/tools")
def configurations(user: User = Depends(current), session: Session = Depends(db)):
    admin(user)
    return [
        {
            "id": c.id,
            "tool_id": c.tool_id,
            "title": session.get(ToolDefinition, c.tool_id).title,
            "status": c.status,
            "fields": c.fields,
            "roles": c.roles,
            "states": c.states,
            "version": c.version,
            "review_comment": c.review_comment,
        }
        for c in session.scalars(select(ToolConfiguration))
    ]


@router.post("/admin/tools")
def configure_tool(
    data: ConfigurationInput, user: User = Depends(current), session: Session = Depends(db)
):
    admin(user)
    department = session.get(Department, data.department_id)
    if not department or not department.active:
        raise HTTPException(422, "Choose an active department")
    if set(data.roles) - {"employee", "reviewer", "department_admin"}:
        raise HTTPException(422, "Choose a supported departmental role")
    if len({f.name for f in data.fields}) != len(data.fields) or any(
        f.type == "select" and not f.options for f in data.fields
    ):
        raise HTTPException(422, "Use unique field names and options for select fields")
    id = uid()
    tool = ToolDefinition(
        id=id,
        title=data.title,
        description=data.description,
        category="Department Work",
        href="/department/tools/" + id,
        status="Requires Approval",
        department_id=data.department_id,
    )
    session.add(tool)
    session.flush()
    config = ToolConfiguration(
        tool_id=id,
        creator=user.id,
        fields=[f.model_dump() for f in data.fields],
        roles=data.roles,
        states=data.states,
    )
    session.add(config)
    audit(session, user, "tool:configure:" + id)
    session.commit()
    session.refresh(config)
    return {"id": config.id, "tool_id": id, "status": config.status}


class Activate(Input):
    comment: str = Field(min_length=3, max_length=2000)


@router.post("/admin/tools/{id}/activate")
def activate(
    id: str, data: Activate, user: User = Depends(current), session: Session = Depends(db)
):
    admin(user)
    config = session.get(ToolConfiguration, id)
    if not config:
        raise HTTPException(404)
    if config.status != "DRAFT":
        raise HTTPException(409, "Configuration has already been activated")
    config.status = "ACTIVE"
    config.approved_by = user.id
    config.review_comment = data.comment
    session.get(ToolDefinition, config.tool_id).status = "Available"
    audit(session, user, "tool:activate:" + config.tool_id)
    session.commit()
    return {"active": True, "configuration_version": config.version}


def tool_config(id, user, session):
    from workspace import get_tool

    get_tool(id, user, session)
    config = session.scalar(select(ToolConfiguration).where(ToolConfiguration.tool_id == id))
    if not config or config.status != "ACTIVE" or user.role not in config.roles:
        raise HTTPException(403, "Active tool and authorised role required")
    return config


@router.get("/tools/{id}")
def configured_tool(id: str, user: User = Depends(current), session: Session = Depends(db)):
    config = tool_config(id, user, session)
    tool = session.get(ToolDefinition, id)
    return {
        "title": tool.title,
        "description": tool.description,
        "configuration": {
            "fields": config.fields,
            "states": config.states,
            "version": config.version,
        },
        "entries": session.scalars(
            select(ToolEntry)
            .where(ToolEntry.configuration_id == config.id)
            .order_by(ToolEntry.created.desc())
        ).all(),
    }


class EntryInput(Input):
    values: dict


@router.post("/tools/{id}/entries")
def create_entry(
    id: str, data: EntryInput, user: User = Depends(current), session: Session = Depends(db)
):
    config = tool_config(id, user, session)
    if set(data.values) - {f["name"] for f in config.fields}:
        raise HTTPException(422, "Unexpected form fields")
    for field in config.fields:
        value = data.values.get(field["name"])
        if field["required"] and (value is None or value == ""):
            raise HTTPException(422, field["label"] + " is required")
        if value in (None, ""):
            continue
        kind = field["type"]
        if kind == "number" and (not isinstance(value, (int, float)) or isinstance(value, bool)):
            raise HTTPException(422, "Enter a valid number")
        if kind == "checkbox" and not isinstance(value, bool):
            raise HTTPException(422, "Checkbox value must be boolean")
        if kind == "select" and value not in field["options"]:
            raise HTTPException(422, "Choose an allowed value")
        if kind == "date":
            try:
                date.fromisoformat(value)
            except (TypeError, ValueError) as error:
                raise HTTPException(422, "Enter a valid ISO date") from error
        if kind == "text" and (not isinstance(value, str) or len(value) > 5000):
            raise HTTPException(422, "Text maximum is 5000 characters")
    entry = ToolEntry(
        configuration_id=config.id, creator=user.id, values=data.values, status=config.states[0]
    )
    session.add(entry)
    audit(session, user, "tool:entry:" + id)
    session.commit()
    session.refresh(entry)
    return entry


class EntryState(Input):
    status: str


@router.patch("/tools/{id}/entries/{entry_id}")
def update_entry(
    id: str,
    entry_id: str,
    data: EntryState,
    user: User = Depends(current),
    session: Session = Depends(db),
):
    config = tool_config(id, user, session)
    entry = session.get(ToolEntry, entry_id)
    if not entry or entry.configuration_id != config.id:
        raise HTTPException(404)
    if data.status not in config.states:
        raise HTTPException(422, "Unknown configured state")
    current_index = config.states.index(entry.status)
    next_index = config.states.index(data.status)
    if abs(next_index - current_index) > 1:
        raise HTTPException(409, "Move one configured workflow step at a time")
    entry.status = data.status
    audit(session, user, "tool:entry_state:" + id)
    session.commit()
    return {"saved": True}


def validate_task(data, user, session):
    assignee = authorised_user(data.assignee_email or user.email, user, session)
    if data.project_id:
        project_access(data.project_id, user, session, True)
        if not session.get(ProjectMember, (data.project_id, assignee.id)):
            raise HTTPException(422, "Assignee must be a project member")
    if data.case_id:
        scoped(Case, data.case_id, user, session)
    return assignee


@router.post("/actions/propose-task")
def propose_task(data: TaskInput, user: User = Depends(current), session: Session = Depends(db)):
    validate_task(data, user, session)
    proposal = AgentAction(
        actor=user.id,
        department=user.department,
        payload=data.model_dump(mode="json"),
        expires=now() + 600,
    )
    session.add(proposal)
    audit(session, user, "agent:proposed_task")
    session.commit()
    session.refresh(proposal)
    return {
        "id": proposal.id,
        "status": proposal.status,
        "preview": proposal.payload,
        "expires": proposal.expires,
        "mode": "Deterministic typed action; no LLM inference",
    }


@router.post("/actions/{id}/confirm")
def confirm_action(id: str, user: User = Depends(current), session: Session = Depends(db)):
    action = session.get(AgentAction, id)
    if not action or action.actor != user.id or action.department != user.department:
        raise HTTPException(404)
    if action.status == "COMPLETED":
        return {
            "status": "COMPLETED",
            "id": action.result_id,
            "href": "/tasks/" + action.result_id,
            "replayed": True,
        }
    if action.expires < now():
        raise HTTPException(409, "Preview expired; create a new proposal")
    data = TaskInput.model_validate(action.payload)
    assignee = validate_task(data, user, session)
    claimed = session.execute(
        update(AgentAction)
        .where(AgentAction.id == id, AgentAction.status == "PROPOSED")
        .values(status="EXECUTING")
    ).rowcount
    if claimed != 1:
        raise HTTPException(409, "Action is already executing or completed")
    task = Task(
        title=data.title,
        description=data.description,
        department=user.department,
        creator=user.id,
        assignee=assignee.id,
        priority=data.priority,
        due_date=data.due_date.isoformat() if data.due_date else None,
        project_id=data.project_id,
        case_id=data.case_id,
        reminder=data.reminder.isoformat() if data.reminder else None,
    )
    session.add(task)
    session.flush()
    action.status = "COMPLETED"
    action.result_id = task.id
    notify(session, assignee.id, "tasks", "Task assigned: " + task.title, "/tasks/" + task.id)
    audit(session, user, "agent:confirmed_task:" + task.id)
    session.commit()
    return {"status": "COMPLETED", "id": task.id, "href": "/tasks/" + task.id, "replayed": False}
