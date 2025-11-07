from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Sequence, Tuple

from fastapi import Depends, FastAPI, Form, HTTPException, Query, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from . import llm, models
from .database import Base, engine, get_db


app = FastAPI(title="ATLAS - AI Toolkit for Lead Activation & Stewardship")
templates = Jinja2Templates(directory="app/templates")


INTERACTION_TYPES = ["email", "linkedin", "call", "meeting", "note"]
INTERACTION_OUTCOMES = [
    ("pending", "Pending"),
    ("no_reply", "No reply"),
    ("positive_meeting", "Positive – meeting booked"),
    ("positive_intro", "Positive – intro made"),
    ("soft_negative", "Soft negative"),
    ("hard_negative", "Hard negative"),
]
CONTACT_SOURCES = ["referral", "cold_linkedin", "event", "other"]
CONTACT_STATUSES = ["prospect", "meeting_booked", "proposal_sent", "client"]
CUSTOM_EMAIL_PURPOSES = [
    ("intro", "Intro outreach"),
    ("follow_up", "Follow-up"),
    ("check_in", "Check-in"),
    ("other", "Other (specify in brief)"),
]
CUSTOM_EMAIL_TONES = [
    ("warm", "Warm"),
    ("direct", "Direct"),
    ("formal", "Formal"),
    ("enthusiastic", "Upbeat"),
]
DEFAULT_CUSTOM_EMAIL_FORM = {
    "purpose": "intro",
    "tone": "warm",
    "brief": "",
    "context": "",
}


def parse_date_or_error(value: Optional[str], *, field_name: str, fmt: str = "%Y-%m-%d") -> Tuple[Optional[date], Optional[str]]:
    if not value:
        return None, None
    try:
        parsed = datetime.strptime(value, fmt).date()
    except ValueError:
        return None, f"Invalid date format for {field_name}."
    return parsed, None


def _infer_first_name(full_name: str) -> Optional[str]:
    if not full_name:
        return None
    parts = [part for part in full_name.strip().split(" ") if part]
    return parts[0] if parts else None


def _build_greeting(contact: models.Contact) -> str:
    first_name = _infer_first_name(contact.name)
    if first_name:
        return f"Hi {first_name},"
    if contact.name:
        return f"Hi {contact.name},"
    return "Hi there,"


def _shorten_for_context(value: Optional[str], *, limit: int = 160, placeholder: str = "(unclear)") -> str:
    if not value:
        return placeholder
    compact = " ".join(value.split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3].rstrip() + "..."


def _format_selected_interaction_lines(interactions: Sequence[models.Interaction]) -> str:
    lines = []
    for interaction in interactions:
        timestamp = interaction.timestamp.strftime("%Y-%m-%d") if interaction.timestamp else "(undated)"
        interaction_type = (interaction.type or "interaction").replace("_", " ")
        outcome = interaction.outcome or "(unclear)"
        summary = _shorten_for_context(interaction.summary, limit=150)
        lines.append(f"- {timestamp}: {interaction_type} | outcome={outcome} | {summary}")
    return "\n".join(lines)


def _format_selected_note_lines(notes: Sequence[models.Note]) -> str:
    lines = []
    for note in notes:
        meeting_date = note.meeting_date.strftime("%Y-%m-%d") if note.meeting_date else "(undated)"
        structured = note.processed_summary.strip() if note.processed_summary else ""
        structured = _shorten_for_context(structured, limit=150, placeholder="") if structured else ""
        raw_excerpt = _shorten_for_context(note.raw_notes, limit=140)
        if structured:
            lines.append(f"- {meeting_date}: structured: {structured} / raw: {raw_excerpt}")
        else:
            lines.append(f"- {meeting_date}: raw: {raw_excerpt}")
    return "\n".join(lines)


def _ensure_contact_exists(contact_id: int, db: Session) -> models.Contact:
    contact = db.query(models.Contact).filter(models.Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    return contact


def _get_interaction_with_contact(interaction_id: int, db: Session) -> models.Interaction:
    interaction = (
        db.query(models.Interaction)
        .options(selectinload(models.Interaction.contact))
        .filter(models.Interaction.id == interaction_id)
        .first()
    )
    if not interaction:
        raise HTTPException(status_code=404, detail="Interaction not found")
    return interaction


def _get_note_with_contact(note_id: int, db: Session) -> models.Note:
    note = (
        db.query(models.Note)
        .options(selectinload(models.Note.contact))
        .filter(models.Note.id == note_id)
        .first()
    )
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    return note


def _get_contact_with_history(contact_id: int, db: Session) -> models.Contact:
    contact = (
        db.query(models.Contact)
        .options(
            selectinload(models.Contact.interactions),
            selectinload(models.Contact.notes),
        )
        .filter(models.Contact.id == contact_id)
        .first()
    )
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    return contact


def _contact_form_context(request: Request, *, errors, form_data: Optional[Dict], contact: Optional[models.Contact] = None):
    return {
        "request": request,
        "errors": errors,
        "form_data": form_data,
        "contact": contact,
        "contact_sources": CONTACT_SOURCES,
        "contact_statuses": CONTACT_STATUSES,
    }


def _interaction_form_context(
    request: Request,
    *,
    contact: models.Contact,
    errors,
    form_data: Dict,
):
    return {
        "request": request,
        "contact": contact,
        "errors": errors,
        "form_data": form_data,
        "interaction_types": INTERACTION_TYPES,
        "interaction_outcomes": INTERACTION_OUTCOMES,
    }


def _try_fetch_website_summary(contact: models.Contact) -> Optional[str]:
    if not contact.website_url:
        return None
    try:
        return llm.fetch_and_summarise_website(contact.website_url, contact.company_name)
    except RuntimeError:
        return None
    except Exception:
        return None


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/contacts", status_code=303)


@app.get("/contacts")
def list_contacts(
    request: Request,
    status: Optional[str] = Query(None),
    q: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(models.Contact)
    if status:
        query = query.filter(models.Contact.status == status)
    search_value = q.strip() if q else ""
    if search_value:
        like_value = f"%{search_value}%"
        query = query.filter(
            or_(
                models.Contact.name.ilike(like_value),
                models.Contact.company_name.ilike(like_value),
            )
        )
    contacts = query.order_by(models.Contact.created_at.desc()).all()
    return templates.TemplateResponse(
        "contacts_list.html",
        {
            "request": request,
            "contacts": contacts,
            "status": status,
            "q": search_value,
            "contact_statuses": CONTACT_STATUSES,
        },
    )


@app.get("/contacts/new")
def new_contact_form(request: Request):
    return templates.TemplateResponse(
        "contact_form.html",
        _contact_form_context(request, errors=[], form_data=None),
    )


@app.post("/contacts")
def create_contact(
    request: Request,
    name: str = Form(...),
    company_name: str = Form(...),
    role: str = Form(...),
    email: str = Form(...),
    linkedin_url: Optional[str] = Form(None),
    website_url: Optional[str] = Form(None),
    source: str = Form(...),
    status: str = Form(...),
    db: Session = Depends(get_db),
):
    contact = models.Contact(
        name=name,
        company_name=company_name,
        role=role,
        email=email,
        linkedin_url=linkedin_url,
        website_url=website_url,
        source=source,
        status=status,
    )
    db.add(contact)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        errors = ["A contact with that email already exists."]
        form_data = {
            "name": name,
            "company_name": company_name,
            "role": role,
            "email": email,
            "linkedin_url": linkedin_url,
            "website_url": website_url,
            "source": source,
            "status": status,
        }
        return templates.TemplateResponse(
            "contact_form.html",
            _contact_form_context(request, errors=errors, form_data=form_data),
        )

    db.refresh(contact)
    return RedirectResponse(
        url=request.url_for("get_contact_detail", contact_id=contact.id),
        status_code=303,
    )


@app.get("/contacts/{contact_id}/edit")
def edit_contact_form(contact_id: int, request: Request, db: Session = Depends(get_db)):
    contact = _ensure_contact_exists(contact_id, db)
    return templates.TemplateResponse(
        "contact_edit_form.html",
        _contact_form_context(request, errors=[], form_data=None, contact=contact),
    )


@app.post("/contacts/{contact_id}/edit")
def update_contact(
    contact_id: int,
    request: Request,
    name: str = Form(...),
    company_name: str = Form(...),
    role: str = Form(...),
    email: str = Form(...),
    linkedin_url: Optional[str] = Form(None),
    website_url: Optional[str] = Form(None),
    source: str = Form(...),
    status: str = Form(...),
    db: Session = Depends(get_db),
):
    contact = _ensure_contact_exists(contact_id, db)
    contact.name = name
    contact.company_name = company_name
    contact.role = role
    contact.email = email
    contact.linkedin_url = linkedin_url
    contact.website_url = website_url
    contact.source = source
    contact.status = status

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        contact = _ensure_contact_exists(contact_id, db)
        errors = ["A contact with that email already exists."]
        form_data = {
            "name": name,
            "company_name": company_name,
            "role": role,
            "email": email,
            "linkedin_url": linkedin_url,
            "website_url": website_url,
            "source": source,
            "status": status,
        }
        return templates.TemplateResponse(
            "contact_edit_form.html",
            _contact_form_context(request, errors=errors, form_data=form_data, contact=contact),
        )

    db.refresh(contact)
    return RedirectResponse(
        url=request.url_for("get_contact_detail", contact_id=contact.id),
        status_code=303,
    )


@app.get("/contacts/{contact_id}", name="get_contact_detail")
def get_contact_detail(contact_id: int, request: Request, db: Session = Depends(get_db)):
    contact = _get_contact_with_history(contact_id, db)
    return templates.TemplateResponse(
        "contact_detail.html",
        {
            "request": request,
            "contact": contact,
        },
    )


@app.get("/contacts/{contact_id}/interactions/new")
def new_interaction_form(contact_id: int, request: Request, db: Session = Depends(get_db)):
    contact = _ensure_contact_exists(contact_id, db)
    default_due = (date.today() + timedelta(days=7)).isoformat()
    form_data = {
        "interaction_type": INTERACTION_TYPES[0],
        "summary": "",
        "next_action": "",
        "next_action_due": default_due,
        "outcome": "pending",
        "outcome_notes": None,
    }
    return templates.TemplateResponse(
        "interaction_form.html",
        _interaction_form_context(request, contact=contact, errors=[], form_data=form_data),
    )


@app.post("/contacts/{contact_id}/interactions")
def create_interaction(
    contact_id: int,
    request: Request,
    interaction_type: str = Form(...),
    summary: str = Form(...),
    next_action: Optional[str] = Form(None),
    next_action_due: Optional[str] = Form(None),
    outcome: str = Form("pending"),
    outcome_notes: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    contact = _ensure_contact_exists(contact_id, db)
    form_data = {
        "interaction_type": interaction_type,
        "summary": summary,
        "next_action": next_action,
        "next_action_due": next_action_due,
        "outcome": outcome,
        "outcome_notes": outcome_notes,
    }

    parsed_due, due_error = parse_date_or_error(next_action_due, field_name="next action due")
    errors = [due_error] if due_error else []

    if errors:
        return templates.TemplateResponse(
            "interaction_form.html",
            _interaction_form_context(request, contact=contact, errors=errors, form_data=form_data),
        )

    interaction = models.Interaction(
        contact_id=contact.id,
        type=interaction_type,
        summary=summary,
        next_action=next_action,
        next_action_due=parsed_due,
        outcome=outcome,
        outcome_notes=outcome_notes,
    )
    db.add(interaction)
    db.commit()

    return RedirectResponse(
        url=request.url_for("get_contact_detail", contact_id=contact.id),
        status_code=303,
    )


@app.get("/interactions/{interaction_id}/edit")
def edit_interaction_form(interaction_id: int, request: Request, db: Session = Depends(get_db)):
    interaction = _get_interaction_with_contact(interaction_id, db)
    contact = interaction.contact or _ensure_contact_exists(interaction.contact_id, db)
    form_data = {
        "interaction_type": interaction.type,
        "summary": interaction.summary,
        "next_action": interaction.next_action or "",
        "next_action_due": interaction.next_action_due.isoformat() if interaction.next_action_due else "",
        "outcome": interaction.outcome,
        "outcome_notes": interaction.outcome_notes or "",
    }
    context = _interaction_form_context(
        request,
        contact=contact,
        errors=[],
        form_data=form_data,
    )
    context.update(
        {
            "form_action": f"/interactions/{interaction.id}/edit",
            "submit_label": "Update Interaction",
            "heading": f"Edit Interaction for {contact.name}",
        }
    )
    return templates.TemplateResponse("interaction_form.html", context)


@app.post("/interactions/{interaction_id}/edit")
def update_interaction(
    interaction_id: int,
    request: Request,
    interaction_type: str = Form(...),
    summary: str = Form(...),
    next_action: Optional[str] = Form(None),
    next_action_due: Optional[str] = Form(None),
    outcome: str = Form(...),
    outcome_notes: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    interaction = _get_interaction_with_contact(interaction_id, db)
    contact = interaction.contact or _ensure_contact_exists(interaction.contact_id, db)

    form_data = {
        "interaction_type": interaction_type,
        "summary": summary,
        "next_action": next_action or "",
        "next_action_due": next_action_due or "",
        "outcome": outcome,
        "outcome_notes": outcome_notes or "",
    }

    parsed_due, due_error = parse_date_or_error(next_action_due, field_name="next action due")
    errors = [due_error] if due_error else []

    if errors:
        context = _interaction_form_context(
            request,
            contact=contact,
            errors=errors,
            form_data=form_data,
        )
        context.update(
            {
                "form_action": f"/interactions/{interaction.id}/edit",
                "submit_label": "Update Interaction",
                "heading": f"Edit Interaction for {contact.name}",
            }
        )
        return templates.TemplateResponse("interaction_form.html", context)

    interaction.type = interaction_type
    interaction.summary = summary
    interaction.next_action = next_action
    interaction.next_action_due = parsed_due
    interaction.outcome = outcome
    interaction.outcome_notes = outcome_notes

    db.commit()

    return RedirectResponse(
        url=request.url_for("get_contact_detail", contact_id=contact.id),
        status_code=303,
    )


@app.post("/interactions/{interaction_id}/delete")
def delete_interaction(interaction_id: int, request: Request, db: Session = Depends(get_db)):
    interaction = (
        db.query(models.Interaction)
        .filter(models.Interaction.id == interaction_id)
        .first()
    )
    if not interaction:
        raise HTTPException(status_code=404, detail="Interaction not found")
    contact_id = interaction.contact_id
    db.delete(interaction)
    db.commit()
    return RedirectResponse(
        url=request.url_for("get_contact_detail", contact_id=contact_id),
        status_code=303,
    )


@app.get("/contacts/{contact_id}/notes/new")
def new_note_form(contact_id: int, request: Request, db: Session = Depends(get_db)):
    contact = _ensure_contact_exists(contact_id, db)
    return templates.TemplateResponse(
        "note_form.html",
        {
            "request": request,
            "contact": contact,
            "errors": [],
            "form_data": None,
        },
    )


@app.post("/contacts/{contact_id}/notes")
def create_note(
    contact_id: int,
    request: Request,
    meeting_date: str = Form(...),
    raw_notes: str = Form(...),
    processed_summary: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    contact = _ensure_contact_exists(contact_id, db)
    form_data = {
        "meeting_date": meeting_date,
        "raw_notes": raw_notes,
        "processed_summary": processed_summary,
    }

    parsed_meeting_date, date_error = parse_date_or_error(meeting_date, field_name="meeting date")
    errors = []
    if not meeting_date:
        errors.append("Meeting date is required.")
    elif date_error:
        errors.append(date_error)

    if errors:
        return templates.TemplateResponse(
            "note_form.html",
            {
                "request": request,
                "contact": contact,
                "errors": errors,
                "form_data": form_data,
            },
        )

    note = models.Note(
        contact_id=contact.id,
        meeting_date=parsed_meeting_date,
        raw_notes=raw_notes,
        processed_summary=processed_summary,
    )
    db.add(note)
    db.commit()

    return RedirectResponse(
        url=request.url_for("get_contact_detail", contact_id=contact.id),
        status_code=303,
    )


@app.get("/notes/{note_id}/edit")
def edit_note_form(note_id: int, request: Request, db: Session = Depends(get_db)):
    note = _get_note_with_contact(note_id, db)
    contact = note.contact or _ensure_contact_exists(note.contact_id, db)
    form_data = {
        "meeting_date": note.meeting_date.isoformat() if note.meeting_date else "",
        "raw_notes": note.raw_notes,
        "processed_summary": note.processed_summary or "",
    }
    return templates.TemplateResponse(
        "note_form.html",
        {
            "request": request,
            "contact": contact,
            "errors": [],
            "form_data": form_data,
            "form_action": f"/notes/{note.id}/edit",
            "submit_label": "Update Note",
            "heading": f"Edit Note for {contact.name}",
        },
    )


@app.post("/notes/{note_id}/edit")
def update_note(
    note_id: int,
    request: Request,
    meeting_date: str = Form(...),
    raw_notes: str = Form(...),
    processed_summary: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    note = _get_note_with_contact(note_id, db)
    contact = note.contact or _ensure_contact_exists(note.contact_id, db)

    form_data = {
        "meeting_date": meeting_date or "",
        "raw_notes": raw_notes,
        "processed_summary": processed_summary or "",
    }

    parsed_date, date_error = parse_date_or_error(meeting_date, field_name="meeting date")
    errors = []
    if not meeting_date:
        errors.append("Meeting date is required.")
    elif date_error:
        errors.append(date_error)

    if errors:
        return templates.TemplateResponse(
            "note_form.html",
            {
                "request": request,
                "contact": contact,
                "errors": errors,
                "form_data": form_data,
                "form_action": f"/notes/{note.id}/edit",
                "submit_label": "Update Note",
                "heading": f"Edit Note for {contact.name}",
            },
        )

    note.meeting_date = parsed_date
    note.raw_notes = raw_notes
    note.processed_summary = processed_summary

    db.commit()

    return RedirectResponse(
        url=request.url_for("get_contact_detail", contact_id=contact.id),
        status_code=303,
    )


@app.post("/notes/{note_id}/delete")
def delete_note(note_id: int, request: Request, db: Session = Depends(get_db)):
    note = (
        db.query(models.Note)
        .filter(models.Note.id == note_id)
        .first()
    )
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    contact_id = note.contact_id
    db.delete(note)
    db.commit()
    return RedirectResponse(
        url=request.url_for("get_contact_detail", contact_id=contact_id),
        status_code=303,
    )


@app.get("/next-actions")
def list_next_actions(request: Request, db: Session = Depends(get_db)):
    today = date.today()
    interactions = (
        db.query(models.Interaction)
        .join(models.Contact)
        .filter(models.Interaction.next_action_due.isnot(None))
        .filter(models.Interaction.next_action_due <= today)
        .order_by(models.Interaction.next_action_due.asc())
        .all()
    )
    return templates.TemplateResponse(
        "next_actions.html",
        {"request": request, "interactions": interactions, "today": today},
    )


@app.get("/metrics/outcomes")
def outcomes_metrics(request: Request, db: Session = Depends(get_db)):
    rows = (
        db.query(models.Interaction.outcome, func.count(models.Interaction.id))
        .group_by(models.Interaction.outcome)
        .order_by(models.Interaction.outcome.asc())
        .all()
    )
    metrics = [
        {"outcome": outcome or "unknown", "count": count}
        for outcome, count in rows
    ]
    return templates.TemplateResponse(
        "metrics_outcomes.html",
        {"request": request, "metrics": metrics},
    )


@app.post("/contacts/{contact_id}/draft_first_email")
def draft_first_email(contact_id: int, db: Session = Depends(get_db)):
    contact = _ensure_contact_exists(contact_id, db)
    website_summary = _try_fetch_website_summary(contact)
    try:
        email_text = llm.draft_first_email(contact, website_summary)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Email drafting service unavailable: {exc}") from exc
    return {"email": email_text}


@app.post("/contacts/{contact_id}/draft_followup")
def draft_followup_email(contact_id: int, db: Session = Depends(get_db)):
    contact = _ensure_contact_exists(contact_id, db)
    interactions = (
        db.query(models.Interaction)
        .filter(models.Interaction.contact_id == contact.id)
        .order_by(models.Interaction.timestamp.desc())
        .limit(10)
        .all()
    )
    notes = (
        db.query(models.Note)
        .filter(models.Note.contact_id == contact.id)
        .order_by(models.Note.meeting_date.desc())
        .limit(3)
        .all()
    )
    try:
        email_text = llm.draft_followup_email(contact, interactions, notes)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Email drafting service unavailable: {exc}") from exc
    return {"email": email_text}


@app.get("/contacts/{contact_id}/draft_custom_email")
def custom_email_form(contact_id: int, request: Request, db: Session = Depends(get_db)):
    contact = _ensure_contact_exists(contact_id, db)
    website_summary = _try_fetch_website_summary(contact)
    greeting = _build_greeting(contact)
    form_defaults = DEFAULT_CUSTOM_EMAIL_FORM.copy()
    interactions = (
        db.query(models.Interaction)
        .filter(models.Interaction.contact_id == contact.id)
        .order_by(models.Interaction.timestamp.desc())
        .all()
    )
    notes = (
        db.query(models.Note)
        .filter(models.Note.contact_id == contact.id)
        .order_by(models.Note.meeting_date.desc())
        .all()
    )
    return templates.TemplateResponse(
        "contact_custom_email.html",
        {
            "request": request,
            "contact": contact,
            "errors": [],
            "form_data": form_defaults,
            "generated_email": None,
            "greeting": greeting,
            "email_purposes": CUSTOM_EMAIL_PURPOSES,
            "email_tones": CUSTOM_EMAIL_TONES,
            "website_summary": website_summary,
            "interactions": interactions,
            "notes": notes,
            "selected_interaction_ids": [],
            "selected_note_ids": [],
            "selected_interaction_preview": "",
            "selected_note_preview": "",
        },
    )


@app.post("/contacts/{contact_id}/draft_custom_email")
def generate_custom_email(
    contact_id: int,
    request: Request,
    purpose: str = Form(...),
    tone: str = Form(...),
    brief: str = Form(...),
    context: Optional[str] = Form(None),
    interaction_ids: List[int] = Form([]),
    note_ids: List[int] = Form([]),
    db: Session = Depends(get_db),
):
    contact = _ensure_contact_exists(contact_id, db)
    greeting = _build_greeting(contact)
    website_summary = _try_fetch_website_summary(contact)
    interactions = (
        db.query(models.Interaction)
        .filter(models.Interaction.contact_id == contact.id)
        .order_by(models.Interaction.timestamp.desc())
        .all()
    )
    notes = (
        db.query(models.Note)
        .filter(models.Note.contact_id == contact.id)
        .order_by(models.Note.meeting_date.desc())
        .all()
    )

    interaction_id_set = set(interaction_ids or [])
    note_id_set = set(note_ids or [])
    selected_interactions = [interaction for interaction in interactions if interaction.id in interaction_id_set]
    selected_notes = [note for note in notes if note.id in note_id_set]
    selected_interaction_ids = [interaction.id for interaction in selected_interactions]
    selected_note_ids = [note.id for note in selected_notes]
    selected_interaction_preview = _format_selected_interaction_lines(selected_interactions)
    selected_note_preview = _format_selected_note_lines(selected_notes)

    errors = []
    valid_purposes = {value for value, _ in CUSTOM_EMAIL_PURPOSES}
    valid_tones = {value for value, _ in CUSTOM_EMAIL_TONES}
    if purpose not in valid_purposes:
        errors.append("Select a valid purpose.")
    if tone not in valid_tones:
        errors.append("Select a valid tone.")
    if not brief.strip():
        errors.append("Provide a brief so the model has direction.")

    form_data = {
        "purpose": purpose,
        "tone": tone,
        "brief": brief,
        "context": context or "",
    }

    base_context = {
        "request": request,
        "contact": contact,
        "greeting": greeting,
        "email_purposes": CUSTOM_EMAIL_PURPOSES,
        "email_tones": CUSTOM_EMAIL_TONES,
        "website_summary": website_summary,
        "interactions": interactions,
        "notes": notes,
        "selected_interaction_ids": selected_interaction_ids,
        "selected_note_ids": selected_note_ids,
        "selected_interaction_preview": selected_interaction_preview,
        "selected_note_preview": selected_note_preview,
        "form_data": form_data,
    }

    if errors:
        return templates.TemplateResponse(
            "contact_custom_email.html",
            {**base_context, "errors": errors, "generated_email": None},
        )

    email_text: Optional[str] = None
    try:
        email_text = llm.draft_custom_email(
            contact=contact,
            greeting=greeting,
            purpose=purpose,
            tone=tone,
            brief=brief,
            additional_context=context,
            website_summary=website_summary,
            selected_interactions=selected_interactions,
            selected_notes=selected_notes,
        )
    except RuntimeError as exc:
        errors.append(f"Unable to generate custom draft: {exc}")
    except Exception as exc:
        errors.append(f"Unable to generate custom draft: {exc}")

    if errors:
        return templates.TemplateResponse(
            "contact_custom_email.html",
            {**base_context, "errors": errors, "generated_email": None},
        )

    return templates.TemplateResponse(
        "contact_custom_email.html",
        {**base_context, "errors": [], "generated_email": email_text},
    )


@app.post("/notes/{note_id}/summarise")
def summarise_note(note_id: int, db: Session = Depends(get_db)):
    note = (
        db.query(models.Note)
        .options(selectinload(models.Note.contact))
        .filter(models.Note.id == note_id)
        .first()
    )
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    contact = note.contact or _ensure_contact_exists(note.contact_id, db)

    try:
        summary_text = llm.summarise_note(note, contact)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Note summarisation unavailable: {exc}") from exc

    note.processed_summary = summary_text
    db.commit()

    db.refresh(note)
    return JSONResponse({"summary": note.processed_summary or ""})
