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


def test_update_contact_fields(db_session):
    contact = contact_service.create_contact(
        db_session,
        schemas.ContactCreate(
            name="Alice Example",
            company_name="Example Co",
            role="CTO",
            email="alice@example.com",
            source="referral",
            status="prospect",
        ),
    )

    updated = contact_service.update_contact(
        db_session,
        contact,
        schemas.ContactUpdate(
            name="Alice Example",
            company_name="Example Co",
            role="CEO",
            email="alice@example.com",
            linkedin_url="https://linkedin.com/in/alice",
            website_url=None,
            source="referral",
            status="client",
        ),
    )

    assert updated.role == "CEO"
    assert updated.status == "client"


def test_update_contact_duplicate_email_raises(db_session):
    contact_service.create_contact(
        db_session,
        schemas.ContactCreate(
            name="First",
            company_name="One",
            role="CTO",
            email="first@example.com",
            source="referral",
            status="prospect",
        ),
    )
    second = contact_service.create_contact(
        db_session,
        schemas.ContactCreate(
            name="Second",
            company_name="Two",
            role="COO",
            email="second@example.com",
            source="referral",
            status="prospect",
        ),
    )

    with pytest.raises(ContactAlreadyExistsError):
        contact_service.update_contact(
            db_session,
            second,
            schemas.ContactUpdate(
                name="Second",
                company_name="Two",
                role="COO",
                email="first@example.com",
                source="referral",
                status="prospect",
            ),
        )
