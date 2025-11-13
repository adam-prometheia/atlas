from app import models


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
        allow_redirects=False,
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
        allow_redirects=False,
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
