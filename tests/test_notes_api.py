from datetime import date

from app import models


def _create_contact(db_session):
    contact = models.Contact(
        name="Sam Contact",
        company_name="Atlas Labs",
        role="VP Ops",
        email="sam-notes@example.com",
        source="referral",
        status="prospect",
    )
    db_session.add(contact)
    db_session.commit()
    db_session.refresh(contact)
    return contact


def test_create_note_success(client, db_session):
    contact = _create_contact(db_session)

    response = client.post(
        f"/contacts/{contact.id}/notes",
        data={
            "meeting_date": "2024-01-15",
            "raw_notes": "Discussed pilot scope",
            "processed_summary": "",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    stored = db_session.query(models.Note).one()
    assert stored.raw_notes == "Discussed pilot scope"


def test_create_note_invalid_date(client, db_session):
    contact = _create_contact(db_session)

    response = client.post(
        f"/contacts/{contact.id}/notes",
        data={
            "meeting_date": "not-a-date",
            "raw_notes": "Discussed pilot scope",
            "processed_summary": "",
        },
    )

    assert response.status_code == 200
    assert "Invalid date format for meeting date." in response.text


def test_delete_note(client, db_session):
    contact = _create_contact(db_session)
    note = models.Note(contact_id=contact.id, meeting_date=date(2024, 1, 15), raw_notes="Initial")
    db_session.add(note)
    db_session.commit()
    db_session.refresh(note)

    response = client.post(
        f"/notes/{note.id}/delete",
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert db_session.query(models.Note).count() == 0
