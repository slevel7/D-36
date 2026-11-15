"""Explicit local-only schema bootstrap and synthetic users. Never run against production."""

import os

from main import Base, User, engine, hash_password
from sqlalchemy import select
from sqlalchemy.orm import Session


def seed():
    password = os.environ.get("DEMO_PASSWORD")
    if not password or len(password) < 12:
        raise SystemExit("Set DEMO_PASSWORD to a local demo password of at least 12 characters")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        for email, role, department in [
            ("employee@example.test", "employee", "DEMO Pension"),
            ("reviewer@example.test", "reviewer", "DEMO Pension"),
            ("admin@example.test", "platform_admin", "DEMO Administration"),
            ("other@example.test", "employee", "DEMO Other"),
        ]:
            if not session.scalar(select(User).where(User.email == email)):
                session.add(
                    User(
                        email=email,
                        role=role,
                        department=department,
                        password=hash_password(password),
                    )
                )
        session.commit()
        from workspace import seed_workspace

        seed_workspace(session)


if __name__ == "__main__":
    seed()
