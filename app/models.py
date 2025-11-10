from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, JSON, String, Text, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .database import Base


class Contact(Base):
    __tablename__ = "contacts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    company_name = Column(String(255), nullable=False)
    role = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, unique=True)
    linkedin_url = Column(String(512), nullable=True)
    website_url = Column(String(512), nullable=True)
    source = Column(String(100), nullable=False)
    status = Column(String(100), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    interactions = relationship(
        "Interaction",
        back_populates="contact",
        cascade="all, delete-orphan",
        order_by="desc(Interaction.timestamp)",
    )
    notes = relationship(
        "Note",
        back_populates="contact",
        cascade="all, delete-orphan",
        order_by="desc(Note.meeting_date)",
    )
    crm_facts = relationship(
        "CRMFact",
        back_populates="contact",
        cascade="all, delete-orphan",
        order_by="desc(CRMFact.created_at)",
        passive_deletes=True,
    )


class Interaction(Base):
    __tablename__ = "interactions"

    id = Column(Integer, primary_key=True, index=True)
    contact_id = Column(Integer, ForeignKey("contacts.id", ondelete="CASCADE"), nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    type = Column(String(100), nullable=False)
    summary = Column(Text, nullable=False)
    next_action = Column(Text, nullable=True)
    next_action_due = Column(Date, nullable=True)
    outcome = Column(String(50), nullable=False, default="pending")
    outcome_notes = Column(Text, nullable=True)

    contact = relationship("Contact", back_populates="interactions")


class Note(Base):
    __tablename__ = "notes"

    id = Column(Integer, primary_key=True, index=True)
    contact_id = Column(Integer, ForeignKey("contacts.id", ondelete="CASCADE"), nullable=False)
    meeting_date = Column(Date, nullable=False)
    raw_notes = Column(Text, nullable=False)
    processed_summary = Column(Text, nullable=True)

    contact = relationship("Contact", back_populates="notes")


class ArchivedNextAction(Base):
    __tablename__ = "archived_next_actions"

    id = Column(Integer, primary_key=True, index=True)
    interaction_id = Column(Integer, ForeignKey("interactions.id", ondelete="CASCADE"), nullable=False)
    archived_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    next_action = Column(Text, nullable=True)
    next_action_due = Column(Date, nullable=True)

    interaction = relationship("Interaction")


class CRMFact(Base):
    __tablename__ = "crm_facts"
    __table_args__ = (
        Index("idx_crm_facts_contact_created", "contact_id", "created_at"),
        Index("idx_crm_facts_source", "source_type", "source_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    contact_id = Column(Integer, ForeignKey("contacts.id", ondelete="CASCADE"), nullable=False)
    source_type = Column(String(50), nullable=False)
    source_id = Column(Integer, nullable=True)
    fact_payload = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    contact = relationship("Contact", back_populates="crm_facts")
