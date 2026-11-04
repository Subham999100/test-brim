"""Projects on the server, and chats saved inside a project (owner request 2026-11-04).

Projects used to live only in the browser (localStorage), with no link to any chat. Adds `projects` and
`chats.project_id`. Deleting a project keeps its chats (ON DELETE SET NULL); deleting a user removes their
projects (ON DELETE CASCADE).

Additive and idempotent: on an empty database revision 0001 already builds `chats` from the current model
(with `project_id` and its index, but without the foreign key), so every step checks first.

Revision ID: 0009_projects
Revises: 0008_message_token_usage
Create Date: 2026-11-04
"""
from alembic import op
from sqlalchemy import inspect, text

revision = "0009_projects"
down_revision = "0008_message_token_usage"
branch_labels = None
depends_on = None

CHAT_PROJECT_FK = "fk_chats_project_id"


def upgrade() -> None:
    bind = op.get_bind()
    bind.execute(text("""
        CREATE TABLE IF NOT EXISTS projects (
            id VARCHAR(36) PRIMARY KEY,
            user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            name VARCHAR(100) NOT NULL,
            description TEXT,
            is_pinned BOOLEAN NOT NULL DEFAULT false,
            created_at TIMESTAMP NOT NULL,
            updated_at TIMESTAMP NOT NULL
        )
    """))
    bind.execute(text("CREATE INDEX IF NOT EXISTS ix_projects_user_id ON projects (user_id)"))

    if not inspect(bind).has_table("chats"):
        return
    if "project_id" not in {column["name"] for column in inspect(bind).get_columns("chats")}:
        bind.execute(text("ALTER TABLE chats ADD COLUMN project_id VARCHAR(36)"))
    has_fk = bind.execute(text(
        "SELECT 1 FROM pg_constraint WHERE conname = :name AND conrelid = 'chats'::regclass"
    ), {"name": CHAT_PROJECT_FK}).first()
    if not has_fk:
        bind.execute(text(
            f"ALTER TABLE chats ADD CONSTRAINT {CHAT_PROJECT_FK} FOREIGN KEY (project_id) "
            "REFERENCES projects(id) ON DELETE SET NULL"
        ))
    bind.execute(text("CREATE INDEX IF NOT EXISTS ix_chats_project_id ON chats (project_id)"))


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(text(f"ALTER TABLE chats DROP CONSTRAINT IF EXISTS {CHAT_PROJECT_FK}"))
    bind.execute(text("DROP INDEX IF EXISTS ix_chats_project_id"))
    bind.execute(text("ALTER TABLE chats DROP COLUMN IF EXISTS project_id"))
    bind.execute(text("DROP TABLE IF EXISTS projects"))
