"""Relational additions for employee settings and tool discovery."""

import time
from uuid import uuid4

from main import Base
from sqlalchemy import JSON, BigInteger, ForeignKey, LargeBinary, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column


def uid():
    return str(uuid4())


def now():
    return int(time.time())


class Department(Base):
    __tablename__ = "departments"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    name: Mapped[str] = mapped_column(String, unique=True)
    active: Mapped[bool] = mapped_column(default=True)


class Division(Base):
    __tablename__ = "divisions"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    department_id: Mapped[str] = mapped_column(ForeignKey("departments.id"))
    name: Mapped[str] = mapped_column(String)
    __table_args__ = (UniqueConstraint("department_id", "name"),)


class Membership(Base):
    __tablename__ = "memberships"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    department_id: Mapped[str] = mapped_column(ForeignKey("departments.id"))
    division_id: Mapped[str] = mapped_column(ForeignKey("divisions.id"))
    role: Mapped[str] = mapped_column(String, default="employee")
    status: Mapped[str] = mapped_column(String, default="APPROVED")
    starts: Mapped[int] = mapped_column(default=now)
    expires: Mapped[int | None]
    __table_args__ = (UniqueConstraint("user_id", "department_id", "division_id"),)


class SessionScope(Base):
    __tablename__ = "session_scopes"
    token: Mapped[str] = mapped_column(
        ForeignKey("sessions.token", ondelete="CASCADE"), primary_key=True
    )
    membership_id: Mapped[str] = mapped_column(ForeignKey("memberships.id"))


class AccessRequest(Base):
    __tablename__ = "access_requests"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    department_id: Mapped[str] = mapped_column(ForeignKey("departments.id"))
    division_id: Mapped[str] = mapped_column(ForeignKey("divisions.id"))
    reason: Mapped[str] = mapped_column(Text)
    requested_role: Mapped[str] = mapped_column(String, default="employee")
    duration_days: Mapped[int | None]
    status: Mapped[str] = mapped_column(String, default="PENDING")
    comment: Mapped[str] = mapped_column(Text, default="")
    reviewer: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    created: Mapped[int] = mapped_column(default=now)
    decided: Mapped[int | None]


class EmployeeProfile(Base):
    __tablename__ = "employee_profiles"
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), primary_key=True)
    phone: Mapped[str] = mapped_column(String, default="")
    contact_email: Mapped[str] = mapped_column(String, default="")
    office_address: Mapped[str] = mapped_column(String, default="")
    bio: Mapped[str] = mapped_column(Text, default="")
    avatar: Mapped[bytes | None] = mapped_column(LargeBinary)
    avatar_type: Mapped[str | None] = mapped_column(String)


class ProfileFile(Base):
    __tablename__ = "profile_files"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    name: Mapped[str] = mapped_column(String)
    content: Mapped[bytes] = mapped_column(LargeBinary)
    digest: Mapped[str] = mapped_column(String)
    created: Mapped[int] = mapped_column(default=now)


class WorkspacePreference(Base):
    __tablename__ = "workspace_preferences"
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), primary_key=True)
    values: Mapped[dict] = mapped_column(JSON, default=dict)


class Notification(Base):
    __tablename__ = "notifications"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    category: Mapped[str] = mapped_column(String)
    title: Mapped[str] = mapped_column(String)
    href: Mapped[str] = mapped_column(String)
    read: Mapped[bool] = mapped_column(default=False)
    created: Mapped[int] = mapped_column(default=now)


class SupportTicket(Base):
    __tablename__ = "support_tickets"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    category: Mapped[str] = mapped_column(String)
    subject: Mapped[str] = mapped_column(String)
    message: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String, default="OPEN")
    response: Mapped[str] = mapped_column(Text, default="")
    created: Mapped[int] = mapped_column(default=now)


class ToolDefinition(Base):
    __tablename__ = "tool_definitions"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    title: Mapped[str] = mapped_column(String)
    description: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String)
    href: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, default="Available")
    department_id: Mapped[str | None] = mapped_column(ForeignKey("departments.id"))
    required_role: Mapped[str | None] = mapped_column(String)
    provider: Mapped[str | None] = mapped_column(String)


class ToolFavourite(Base):
    __tablename__ = "tool_favourites"
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), primary_key=True)
    tool_id: Mapped[str] = mapped_column(ForeignKey("tool_definitions.id"), primary_key=True)
    position: Mapped[int] = mapped_column(default=0)
    group: Mapped[str] = mapped_column(String, default="My tools")


class ToolUsage(Base):
    __tablename__ = "tool_usage"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    tool_id: Mapped[str] = mapped_column(ForeignKey("tool_definitions.id"))
    department: Mapped[str] = mapped_column(String)
    created: Mapped[int] = mapped_column(default=now)


class ToolDismissal(Base):
    __tablename__ = "tool_dismissals"
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), primary_key=True)
    tool_id: Mapped[str] = mapped_column(ForeignKey("tool_definitions.id"), primary_key=True)


class ToolRequest(Base):
    __tablename__ = "tool_requests"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    department: Mapped[str] = mapped_column(String)
    title: Mapped[str] = mapped_column(String)
    reason: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String, default="PENDING")
    created: Mapped[int] = mapped_column(default=now)


class ProviderRequest(Base):
    __tablename__ = "provider_requests"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    provider: Mapped[str] = mapped_column(String)
    reason: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String, default="PENDING")
    created: Mapped[int] = mapped_column(default=now)


class Conversation(Base):
    __tablename__ = "conversations"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    department: Mapped[str] = mapped_column(String)
    title: Mapped[str] = mapped_column(String)
    pinned: Mapped[bool] = mapped_column(default=False)
    archived: Mapped[bool] = mapped_column(default=False)
    created: Mapped[int] = mapped_column(default=now)


class Message(Base):
    __tablename__ = "conversation_messages"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    conversation_id: Mapped[str] = mapped_column(ForeignKey("conversations.id"))
    role: Mapped[str] = mapped_column(String)
    content: Mapped[str] = mapped_column(Text)
    created: Mapped[int] = mapped_column(BigInteger, default=time.time_ns)
