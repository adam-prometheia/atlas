from __future__ import annotations

from typing import Dict

from sqlalchemy.orm import Session

from .. import models


def create_contact(db: Session, contact_data: Dict) -> models.Contact:
    """Persist a new contact without committing the transaction."""
    contact = models.Contact(**contact_data)
    db.add(contact)
    return contact
