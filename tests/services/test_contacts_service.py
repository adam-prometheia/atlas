import pytest

from app import schemas
from app.services import contacts as contact_service
from app.services.contacts import ContactAlreadyExistsError


def test_create_contact_persists(db_session):
    contact_in = schemas.ContactCreate(
        name="Alice Example",
        company_name="Example Co",
        role="CTO",
        email="alice@example.com",
        source="referral",
        status="prospect",
    )

    contact = contact_service.create_contact(db_session, contact_in)

    assert contact.id is not None
    assert contact.email == "alice@example.com"


def test_create_contact_duplicate_email_raises(db_session):
    contact_in = schemas.ContactCreate(
        name="Alice Example",
        company_name="Example Co",
        role="CTO",
        email="duplicate@example.com",
        source="referral",
        status="prospect",
    )
    contact_service.create_contact(db_session, contact_in)

    with pytest.raises(ContactAlreadyExistsError):
        contact_service.create_contact(db_session, contact_in)
