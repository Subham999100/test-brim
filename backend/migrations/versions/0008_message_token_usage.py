"""Store each streamed answer's estimated token use and generic-chatbot baseline (token savings shown to users).

Additive and idempotent: on an empty database revision 0001 already builds `messages` from the current model
(with these columns), so every step checks first. Existing answers keep NULL (unknown; nothing is guessed).

Revision ID: 0008_message_token_usage
Revises: 0007_message_llm_tracking
Create Date: 2026-11-04
"""
from alembic import op
from sqlalchemy import inspect, text

revision = "0008_message_token_usage"
down_revision = "0007_message_llm_tracking"
branch_labels = None
depends_on = None

MESSAGE_COLUMNS = {
    "tokens_used": "INTEGER",
    "tokens_baseline": "INTEGER",
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
