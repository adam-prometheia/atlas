from __future__ import annotations

from typing import Any, Dict

from sqlalchemy.orm import Session

from .. import models


def create_interaction(db: Session, contact_id: int, data: Dict[str, Any]) -> models.Interaction:
    interaction = models.Interaction(contact_id=contact_id, **data)
    db.add(interaction)
    return interaction


def update_interaction(interaction: models.Interaction, data: Dict[str, Any]) -> models.Interaction:
    for field, value in data.items():
        setattr(interaction, field, value)
    return interaction


def delete_interaction(db: Session, interaction: models.Interaction) -> None:
    db.delete(interaction)
