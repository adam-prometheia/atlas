from app import models


def _create_contact(db_session, **overrides):
    contact = models.Contact(
        name=overrides.get("name", "Initial Contact"),
        company_name=overrides.get("company_name", "Init Co"),
        role=overrides.get("role", "CTO"),
        email=overrides.get("email", "initial@example.com"),
        source=overrides.get("source", "referral"),
        status=overrides.get("status", "prospect"),
    )
    db_session.add(contact)
    db_session.commit()
    db_session.refresh(contact)
    return contact


def test_create_contact_success(client, db_session):
    response = client.post(
        "/contacts",
        data={
            "name": "Sam Contact",
            "company_name": "Atlas Labs",
            "role": "VP Ops",
            "email": "sam@example.com",
            "linkedin_url": "",
            "website_url": "",
            "source": "referral",
            "status": "prospect",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    stored = db_session.query(models.Contact).filter_by(email="sam@example.com").one()
    assert stored.name == "Sam Contact"


def test_create_contact_duplicate_email_renders_error(client, db_session):
    client.post(
        "/contacts",
        data={
            "name": "Sam Contact",
            "company_name": "Atlas Labs",
            "role": "VP Ops",
            "email": "sam@example.com",
            "linkedin_url": "",
            "website_url": "",
            "source": "referral",
            "status": "prospect",
        },
        follow_redirects=False,
    )

    response = client.post(
        "/contacts",
        data={
            "name": "Other Name",
            "company_name": "Atlas Labs",
            "role": "VP Ops",
            "email": "sam@example.com",
            "linkedin_url": "",
            "website_url": "",
            "source": "referral",
            "status": "prospect",
        },
    )

    assert response.status_code == 200
    assert "A contact with that email already exists." in response.text


def test_update_contact_success(client, db_session):
    contact = _create_contact(db_session)

    response = client.post(
        f"/contacts/{contact.id}/edit",
        data={
            "name": "Updated",
            "company_name": "Atlas Labs",
            "role": "VP Ops",
            "email": "updated@example.com",
            "linkedin_url": "",
            "website_url": "",
            "source": "referral",
            "status": "client",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    updated = db_session.query(models.Contact).filter(models.Contact.id == contact.id).one()
    assert updated.email == "updated@example.com"
    assert updated.status == "client"


def test_update_contact_duplicate_email_shows_error(client, db_session):
    first = _create_contact(db_session, email="first@example.com", name="First")
    second = _create_contact(db_session, email="second@example.com", name="Second")

    response = client.post(
        f"/contacts/{second.id}/edit",
        data={
            "name": "Second",
            "company_name": "Atlas Labs",
            "role": "COO",
            "email": "first@example.com",
            "linkedin_url": "",
            "website_url": "",
            "source": "referral",
            "status": "prospect",
        },
    )

    assert response.status_code == 200
    assert "A contact with that email already exists." in response.text
