"""Record which provider and model wrote each answer and which regeneration of its question it is.

Additive and idempotent: on an empty database revision 0001 already builds `messages` from the current
model (with these columns), so every step checks first. Existing answers keep NULL provider/model (unknown)
and regeneration 0.

Revision ID: 0007_message_llm_tracking
Revises: 0006_organisations
Create Date: 2026-11-03
"""
from alembic import op
from sqlalchemy import inspect, text

revision = "0007_message_llm_tracking"
down_revision = "0006_organisations"
branch_labels = None
depends_on = None

MESSAGE_COLUMNS = {
    "llm_provider": "VARCHAR(50)",
    "llm_model": "VARCHAR(100)",
    "regeneration_count": "INTEGER DEFAULT 0",
}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if not inspector.has_table("messages"):
        return
    columns = {column["name"] for column in inspector.get_columns("messages")}
    for name, definition in MESSAGE_COLUMNS.items():
        if name not in columns:
            bind.execute(text(f"ALTER TABLE messages ADD COLUMN {name} {definition}"))


def downgrade() -> None:
    bind = op.get_bind()
    for name in MESSAGE_COLUMNS:
        bind.execute(text(f"ALTER TABLE messages DROP COLUMN IF EXISTS {name}"))
