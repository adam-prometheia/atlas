from datetime import date

from app import models, schemas
from app.services import contacts as contact_service
from app.services import interactions as interaction_service


def _create_contact(db_session):
    return contact_service.create_contact(
        db_session,
        schemas.ContactCreate(
            name="Sam Contact",
            company_name="Atlas Labs",
            role="VP Ops",
            email="sam@example.com",
            source="referral",
            status="prospect",
        ),
    )


def test_create_interaction(db_session):
    contact = _create_contact(db_session)
    interaction_in = schemas.InteractionCreate(
        type="email",
        summary="Initial outreach",
        next_action="Follow up",
        next_action_due=date.today(),
        outcome="pending",
        outcome_notes=None,
    )

    interaction = interaction_service.create_interaction(db_session, contact, interaction_in)

    assert interaction.id is not None
    assert interaction.contact_id == contact.id


def test_update_interaction(db_session):
    contact = _create_contact(db_session)
    interaction = interaction_service.create_interaction(
        db_session,
        contact,
        schemas.InteractionCreate(
            type="email",
            summary="Initial outreach",
            outcome="pending",
        ),
    )

    updated = interaction_service.update_interaction(
        db_session,
        interaction,
        schemas.InteractionUpdate(
            type="email",
            summary="Updated summary",
            next_action="Send proposal",
            outcome="positive_meeting",
        ),
    )

    assert updated.summary == "Updated summary"
    assert updated.outcome == "positive_meeting"


def test_delete_interaction(db_session):
    contact = _create_contact(db_session)
    interaction = interaction_service.create_interaction(
        db_session,
        contact,
        schemas.InteractionCreate(type="email", summary="Hello"),
    )

    interaction_service.delete_interaction(db_session, interaction)

    assert db_session.query(models.Interaction).count() == 0
