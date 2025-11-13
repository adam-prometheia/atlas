from __future__ import annotations

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .. import models, schemas
from ..repositories import contacts as contacts_repo


class ContactAlreadyExistsError(Exception):
    """Raised when attempting to create a contact with a duplicate email."""


def create_contact(db: Session, contact_in: schemas.ContactCreate) -> models.Contact:
    """Create a contact through the repository layer and commit the transaction."""
    contact = contacts_repo.create_contact(db, contact_in.model_dump())
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ContactAlreadyExistsError from exc
    db.refresh(contact)
    return contact
