"""Initial schema"""

from alembic import op
import sqlalchemy as sa


revision = "20241113_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "contacts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("company_name", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False, unique=True),
        sa.Column("linkedin_url", sa.String(length=512), nullable=True),
        sa.Column("website_url", sa.String(length=512), nullable=True),
        sa.Column("source", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=100), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    op.create_table(
        "interactions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("contact_id", sa.Integer(), nullable=False),
        sa.Column(
            "timestamp",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("type", sa.String(length=100), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("next_action", sa.Text(), nullable=True),
        sa.Column("next_action_due", sa.Date(), nullable=True),
        sa.Column(
            "outcome",
            sa.String(length=50),
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
        sa.Column("outcome_notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["contact_id"],
            ["contacts.id"],
            ondelete="CASCADE",
        ),
    )

    op.create_table(
        "notes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("contact_id", sa.Integer(), nullable=False),
        sa.Column("meeting_date", sa.Date(), nullable=False),
        sa.Column("raw_notes", sa.Text(), nullable=False),
        sa.Column("processed_summary", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["contact_id"],
            ["contacts.id"],
            ondelete="CASCADE",
        ),
    )

    op.create_table(
        "archived_next_actions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("interaction_id", sa.Integer(), nullable=False),
        sa.Column(
            "archived_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("next_action", sa.Text(), nullable=True),
        sa.Column("next_action_due", sa.Date(), nullable=True),
        sa.ForeignKeyConstraint(
            ["interaction_id"],
            ["interactions.id"],
            ondelete="CASCADE",
        ),
    )

    op.create_table(
        "crm_facts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("contact_id", sa.Integer(), nullable=False),
        sa.Column("source_type", sa.String(length=50), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=True),
        sa.Column("fact_payload", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["contact_id"],
            ["contacts.id"],
            ondelete="CASCADE",
        ),
    )

    op.create_index(
        "idx_crm_facts_contact_created",
        "crm_facts",
        ["contact_id", "created_at"],
    )
    op.create_index(
        "idx_crm_facts_source",
        "crm_facts",
        ["source_type", "source_id"],
    )


def downgrade() -> None:
    op.drop_index("idx_crm_facts_source", table_name="crm_facts")
    op.drop_index("idx_crm_facts_contact_created", table_name="crm_facts")
    op.drop_table("crm_facts")
    op.drop_table("archived_next_actions")
    op.drop_table("notes")
    op.drop_table("interactions")
    op.drop_table("contacts")
