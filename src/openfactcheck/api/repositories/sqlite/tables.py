"""ORM table definitions for projects and workspaces."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKeyConstraint, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from openfactcheck.api.repositories.sqlite.engine import Base


class ProjectRow(Base):
    """ORM model for the ``projects`` table."""

    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(12), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(255), index=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime)
    updated_at: Mapped[datetime] = mapped_column(DateTime)


class WorkspaceRow(Base):
    """ORM model for the ``workspaces`` table."""

    __tablename__ = "workspaces"
    __table_args__ = (
        ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            ondelete="CASCADE",
        ),
    )

    id: Mapped[str] = mapped_column(String(12), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(255), index=True)
    project_id: Mapped[str] = mapped_column(String(12), index=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text, default="")
    locked: Mapped[bool] = mapped_column(Boolean, default=False)
    sort_order: Mapped[int] = mapped_column(Integer)
    settings_json: Mapped[str] = mapped_column(Text, default="{}")
    content_json: Mapped[str] = mapped_column(Text, default="{}")
    run_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime)
    updated_at: Mapped[datetime] = mapped_column(DateTime)


class SecretRow(Base):
    """ORM model for the ``secrets`` table.

    ``project_id`` is empty for the user's global secrets and the project id for
    a project override; it is part of the primary key so the two scopes coexist.
    """

    __tablename__ = "secrets"

    user_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(12), primary_key=True, default="")
    name: Mapped[str] = mapped_column(String(64), primary_key=True)
    ciphertext: Mapped[str] = mapped_column(Text)
    hint: Mapped[str] = mapped_column(String(8), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime)
    updated_at: Mapped[datetime] = mapped_column(DateTime)


class PreferencesRow(Base):
    """ORM model for the ``preferences`` table."""

    __tablename__ = "preferences"

    user_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    tour_completed: Mapped[bool] = mapped_column(Boolean, default=False)
