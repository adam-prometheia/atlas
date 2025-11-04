from datetime import date, datetime
from typing import Optional

from fastapi import Depends, FastAPI, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from . import models
from .database import Base, engine, get_db


app = FastAPI(title="ATLAS - AI Toolkit for Lead Activation & Stewardship")
templates = Jinja2Templates(directory="app/templates")


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/contacts", status_code=303)


@app.get("/contacts")
def list_contacts(request: Request, db: Session = Depends(get_db)):
    contacts = (
        db.query(models.Contact)
        .order_by(models.Contact.created_at.desc())
        .all()
    )
    return templates.TemplateResponse(
        "contacts_list.html",
        {"request": request, "contacts": contacts},
    )


@app.get("/contacts/new")
def new_contact_form(request: Request):
    return templates.TemplateResponse(
        "contact_form.html",
        {"request": request, "errors": [], "form_data": None},
    )


@app.post("/contacts")
def create_contact(
    request: Request,
    name: str = Form(...),
    company_name: str = Form(...),
    role: str = Form(...),
    email: str = Form(...),
    linkedin_url: Optional[str] = Form(None),
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
        source=source,
        status=status,
    )
    db.add(contact)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        # Re-render the form with an error message if the email already exists.
        return templates.TemplateResponse(
            "contact_form.html",
            {
                "request": request,
                "errors": ["A contact with that email already exists."],
                "form_data": {
                    "name": name,
                    "company_name": company_name,
                    "role": role,
                    "email": email,
                    "linkedin_url": linkedin_url,
                    "source": source,
                    "status": status,
                },
            },
            status_code=400,
        )

    db.refresh(contact)
    return RedirectResponse(
        url=request.url_for("get_contact_detail", contact_id=contact.id),
        status_code=303,
    )


def _get_contact_or_404(contact_id: int, db: Session) -> models.Contact:
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


@app.get("/contacts/{contact_id}", name="get_contact_detail")
def get_contact_detail(contact_id: int, request: Request, db: Session = Depends(get_db)):
    contact = _get_contact_or_404(contact_id, db)
    return templates.TemplateResponse(
        "contact_detail.html",
        {
            "request": request,
            "contact": contact,
        },
    )


@app.get("/contacts/{contact_id}/interactions/new")
def new_interaction_form(contact_id: int, request: Request, db: Session = Depends(get_db)):
    contact = _get_contact_or_404(contact_id, db)
    return templates.TemplateResponse(
        "interaction_form.html",
        {"request": request, "contact": contact, "errors": [], "form_data": None},
    )


@app.post("/contacts/{contact_id}/interactions")
def create_interaction(
    contact_id: int,
    request: Request,
    interaction_type: str = Form(...),
    summary: str = Form(...),
    next_action: Optional[str] = Form(None),
    next_action_due: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    contact = _get_contact_or_404(contact_id, db)

    parsed_due_date: Optional[date] = None
    if next_action_due:
        try:
            parsed_due_date = datetime.strptime(next_action_due, "%Y-%m-%d").date()
        except ValueError:
            return templates.TemplateResponse(
                "interaction_form.html",
                {
                    "request": request,
                    "contact": contact,
                    "errors": ["Invalid date format for next action due."],
                    "form_data": {
                        "interaction_type": interaction_type,
                        "summary": summary,
                        "next_action": next_action,
                        "next_action_due": next_action_due,
                    },
                },
                status_code=400,
            )

    interaction = models.Interaction(
        contact_id=contact.id,
        type=interaction_type,
        summary=summary,
        next_action=next_action,
        next_action_due=parsed_due_date,
    )
    db.add(interaction)
    db.commit()

    return RedirectResponse(
        url=request.url_for("get_contact_detail", contact_id=contact.id),
        status_code=303,
    )


@app.get("/contacts/{contact_id}/notes/new")
def new_note_form(contact_id: int, request: Request, db: Session = Depends(get_db)):
    contact = _get_contact_or_404(contact_id, db)
    return templates.TemplateResponse(
        "note_form.html",
        {"request": request, "contact": contact, "errors": [], "form_data": None},
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
    contact = _get_contact_or_404(contact_id, db)

    try:
        parsed_meeting_date = datetime.strptime(meeting_date, "%Y-%m-%d").date()
    except ValueError:
        return templates.TemplateResponse(
            "note_form.html",
            {
                "request": request,
                "contact": contact,
                "errors": ["Invalid date format for meeting date."],
                "form_data": {
                    "raw_notes": raw_notes,
                    "processed_summary": processed_summary,
                    "meeting_date": meeting_date,
                },
            },
            status_code=400,
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


def _ensure_contact_exists(contact_id: int, db: Session) -> models.Contact:
    contact = db.query(models.Contact).filter(models.Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    return contact


@app.post("/contacts/{contact_id}/draft_first_email")
def draft_first_email(contact_id: int, db: Session = Depends(get_db)):
    _ensure_contact_exists(contact_id, db)
    return {"email": "TODO first email draft"}


@app.post("/contacts/{contact_id}/draft_followup")
def draft_followup_email(contact_id: int, db: Session = Depends(get_db)):
    _ensure_contact_exists(contact_id, db)
    return {"email": "TODO followup draft"}
