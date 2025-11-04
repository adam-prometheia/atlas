from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field, ConfigDict


class InteractionBase(BaseModel):
    type: str
    summary: str
    next_action: Optional[str] = None
    next_action_due: Optional[date] = None


class InteractionCreate(InteractionBase):
    timestamp: Optional[datetime] = None


class InteractionRead(InteractionBase):
    id: int
    contact_id: int
    timestamp: datetime
    model_config = ConfigDict(from_attributes=True)


class NoteBase(BaseModel):
    meeting_date: date
    raw_notes: str
    processed_summary: Optional[str] = None


class NoteCreate(NoteBase):
    pass


class NoteRead(NoteBase):
    id: int
    contact_id: int
    model_config = ConfigDict(from_attributes=True)


class ContactBase(BaseModel):
    name: str
    company_name: str
    role: str
    email: EmailStr
    linkedin_url: Optional[str] = None
    website_url: Optional[str] = None
    source: str
    status: str


class ContactCreate(ContactBase):
    pass


class ContactRead(ContactBase):
    id: int
    created_at: datetime
    updated_at: datetime
    interactions: List[InteractionRead] = Field(default_factory=list)
    notes: List[NoteRead] = Field(default_factory=list)
    model_config = ConfigDict(from_attributes=True)
