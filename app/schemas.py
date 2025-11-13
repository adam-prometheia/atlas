from datetime import date, datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, EmailStr, Field, ConfigDict


class InteractionBase(BaseModel):
    type: str
    summary: str
    next_action: Optional[str] = None
    next_action_due: Optional[date] = None
    outcome: str = "pending"
    outcome_notes: Optional[str] = None


class InteractionCreate(InteractionBase):
    timestamp: Optional[datetime] = None


class InteractionUpdate(InteractionBase):
    pass


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


class ContactUpdate(ContactBase):
    pass


class ContactRead(ContactBase):
    id: int
    created_at: datetime
    updated_at: datetime
    interactions: List[InteractionRead] = Field(default_factory=list)
    notes: List[NoteRead] = Field(default_factory=list)
    model_config = ConfigDict(from_attributes=True)


class CRMFactPayload(BaseModel):
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    org: Optional[str] = None
    intent: Literal[
        "interested_in_ai_audit",
        "wants_training",
        "outreach_workflow",
        "lss_green_belt_with_ai",
        "followup_needed",
        "general_interest",
        "unclear",
    ] = "unclear"
    mentioned_process: str = Field(default="other/unclear", max_length=120)
    timeline: Literal["this_month", "next_quarter", "later", "unknown"] = "unknown"
    next_action_hint: Optional[str] = None
    summary: str = "(unclear)"
    raw_text: Optional[str] = None
    model_config = ConfigDict(extra="ignore")


class NextActionSuggestion(BaseModel):
    next_action_type: Literal[
        "followup_email",
        "book_call",
        "send_proposal",
        "share_case_study",
        "nurture_checkin",
        "no_action_recommended",
    ] = "no_action_recommended"
    next_action_title: str = ""
    next_action_description: str = ""
    proposed_email_subject: Optional[str] = None
    proposed_email_body: Optional[str] = None
    suggested_due_date: Optional[date] = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    notes_for_adam: Optional[str] = None
    model_config = ConfigDict(extra="ignore")
