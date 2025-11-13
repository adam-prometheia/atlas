from datetime import date, timedelta

from app import models


def _create_contact(db_session):
    contact = models.Contact(
        name="Sam Contact",
        company_name="Atlas Labs",
        role="VP Ops",
        email="sam@example.com",
        source="referral",
        status="prospect",
    )
    db_session.add(contact)
    db_session.commit()
    db_session.refresh(contact)
    return contact


def test_create_interaction_success(client, db_session):
    contact = _create_contact(db_session)
    due_date = (date.today() + timedelta(days=7)).isoformat()

    response = client.post(
        f"/contacts/{contact.id}/interactions",
        data={
            "interaction_type": "email",
            "summary": "Initial outreach",
            "next_action": "Follow up",
            "next_action_due": due_date,
            "outcome": "pending",
            "outcome_notes": "",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    stored = db_session.query(models.Interaction).one()
    assert stored.summary == "Initial outreach"


def test_create_interaction_invalid_date(client, db_session):
    contact = _create_contact(db_session)

    response = client.post(
        f"/contacts/{contact.id}/interactions",
        data={
            "interaction_type": "email",
            "summary": "Initial outreach",
            "next_action": "Follow up",
            "next_action_due": "not-a-date",
            "outcome": "pending",
            "outcome_notes": "",
        },
    )

    assert response.status_code == 200
    assert "Invalid date format for next action due." in response.text


def test_update_interaction_success(client, db_session):
    contact = _create_contact(db_session)
    interaction = models.Interaction(contact_id=contact.id, type="email", summary="Init", outcome="pending")
    db_session.add(interaction)
    db_session.commit()
    db_session.refresh(interaction)

    response = client.post(
        f"/interactions/{interaction.id}/edit",
        data={
            "interaction_type": "email",
            "summary": "Updated summary",
            "next_action": "Next step",
            "next_action_due": "",
            "outcome": "positive_meeting",
            "outcome_notes": "",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    updated = db_session.query(models.Interaction).filter(models.Interaction.id == interaction.id).one()
    assert updated.summary == "Updated summary"
    assert updated.outcome == "positive_meeting"
