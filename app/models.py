from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, String, Text
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


class Interaction(Base):
    __tablename__ = "interactions"

    id = Column(Integer, primary_key=True, index=True)
    contact_id = Column(Integer, ForeignKey("contacts.id", ondelete="CASCADE"), nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    type = Column(String(100), nullable=False)
    summary = Column(Text, nullable=False)
    next_action = Column(Text, nullable=True)
    next_action_due = Column(Date, nullable=True)

    contact = relationship("Contact", back_populates="interactions")


class Note(Base):
    __tablename__ = "notes"

    id = Column(Integer, primary_key=True, index=True)
    contact_id = Column(Integer, ForeignKey("contacts.id", ondelete="CASCADE"), nullable=False)
    meeting_date = Column(Date, nullable=False)
    raw_notes = Column(Text, nullable=False)
    processed_summary = Column(Text, nullable=True)

    contact = relationship("Contact", back_populates="notes")
