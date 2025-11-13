from __future__ import annotations

from typing import Any, Dict, cast

from sqlalchemy.orm import Session

from .. import models, schemas
from ..repositories import interactions as interactions_repo


def create_interaction(
    db: Session,
    contact: models.Contact,
    interaction_in: schemas.InteractionCreate,
) -> models.Interaction:
    data: Dict[str, Any] = interaction_in.model_dump(exclude_unset=True)
    contact_id = cast(int, contact.id)
    interaction = interactions_repo.create_interaction(db, contact_id, data)
    db.commit()
    db.refresh(interaction)
    return interaction


def update_interaction(
    db: Session,
    interaction: models.Interaction,
    interaction_in: schemas.InteractionUpdate,
) -> models.Interaction:
    interactions_repo.update_interaction(
        interaction,
        interaction_in.model_dump(exclude_unset=True),
    )
    db.commit()
    db.refresh(interaction)
    return interaction


def delete_interaction(
    db: Session,
    interaction: models.Interaction,
) -> None:
    interactions_repo.delete_interaction(db, interaction)
    db.commit()
