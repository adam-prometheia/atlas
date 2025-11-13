from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import Date, DateTime, ForeignKey, Index, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class Contact(Base):
    __tablename__ = "contacts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    linkedin_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    website_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    source: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    interactions: Mapped[List["Interaction"]] = relationship(
        "Interaction",
        back_populates="contact",
        cascade="all, delete-orphan",
        order_by="desc(Interaction.timestamp)",
    )
    notes: Mapped[List["Note"]] = relationship(
        "Note",
        back_populates="contact",
        cascade="all, delete-orphan",
        order_by="desc(Note.meeting_date)",
    )
    crm_facts: Mapped[List["CRMFact"]] = relationship(
        "CRMFact",
        back_populates="contact",
        cascade="all, delete-orphan",
        order_by="desc(CRMFact.created_at)",
        passive_deletes=True,
    )


class Interaction(Base):
    __tablename__ = "interactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    contact_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("contacts.id", ondelete="CASCADE"), nullable=False
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    type: Mapped[str] = mapped_column(String(100), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    next_action: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    next_action_due: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    outcome: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    outcome_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    contact: Mapped["Contact"] = relationship("Contact", back_populates="interactions")


class Note(Base):
    __tablename__ = "notes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    contact_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("contacts.id", ondelete="CASCADE"), nullable=False
    )
    meeting_date: Mapped[date] = mapped_column(Date, nullable=False)
    raw_notes: Mapped[str] = mapped_column(Text, nullable=False)
    processed_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    contact: Mapped["Contact"] = relationship("Contact", back_populates="notes")


class ArchivedNextAction(Base):
    __tablename__ = "archived_next_actions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    interaction_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("interactions.id", ondelete="CASCADE"), nullable=False
    )
    archived_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    next_action: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    next_action_due: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    interaction: Mapped["Interaction"] = relationship("Interaction")


class CRMFact(Base):
    __tablename__ = "crm_facts"
    __table_args__ = (
        Index("idx_crm_facts_contact_created", "contact_id", "created_at"),
        Index("idx_crm_facts_source", "source_type", "source_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    contact_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("contacts.id", ondelete="CASCADE"), nullable=False
    )
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    source_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    fact_payload: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    contact: Mapped["Contact"] = relationship("Contact", back_populates="crm_facts")
