"""Organisation Portal: organisations, activation codes, shared knowledge hub and account state
(docs/ORGANISATION_PORTAL.md).

Additive and idempotent: on an empty database revision 0001 already builds `users` from the current model
(with the new columns but without the organisations foreign key), so every step checks first.
Existing users become active individual accounts.

Revision ID: 0006_organisations
Revises: 0005_embedding_provenance
Create Date: 2026-11-01
"""
from alembic import op
from sqlalchemy import inspect, text

revision = "0006_organisations"
down_revision = "0005_embedding_provenance"
branch_labels = None
depends_on = None

USER_COLUMNS = {
    "account_type": "VARCHAR(20) NOT NULL DEFAULT 'individual'",
    "organization_id": "VARCHAR(36)",
    "org_role": "VARCHAR(20)",
    "is_active": "BOOLEAN NOT NULL DEFAULT true",
    "must_change_password": "BOOLEAN NOT NULL DEFAULT false",
    "last_login_at": "TIMESTAMP",
}
USER_ORG_FK = "fk_users_organization_id"


def upgrade() -> None:
    bind = op.get_bind()
    bind.execute(text("""
        CREATE TABLE IF NOT EXISTS organizations (
            id VARCHAR(36) PRIMARY KEY,
            name VARCHAR(120) NOT NULL UNIQUE,
            slug VARCHAR(140) NOT NULL UNIQUE,
            contact_name VARCHAR(120),
            contact_email VARCHAR(255) NOT NULL,
            request_message TEXT,
            status VARCHAR(20) NOT NULL,
            created_by VARCHAR(36) REFERENCES users(id) ON DELETE SET NULL,
            activated_at TIMESTAMP,
            created_at TIMESTAMP NOT NULL,
            updated_at TIMESTAMP NOT NULL
        )
    """))
    # Names are unique regardless of case.
    bind.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ux_organizations_name_lower ON organizations (lower(name))"))
    bind.execute(text("CREATE INDEX IF NOT EXISTS ix_organizations_status ON organizations (status)"))

    bind.execute(text("""
        CREATE TABLE IF NOT EXISTS org_activation_codes (
            id VARCHAR(36) PRIMARY KEY,
            organization_id VARCHAR(36) NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
            code_hash VARCHAR(64) NOT NULL UNIQUE,
            code_hint VARCHAR(8) NOT NULL,
            admin_name VARCHAR(120) NOT NULL,
            admin_email VARCHAR(255) NOT NULL,
            expires_at TIMESTAMP NOT NULL,
            used_at TIMESTAMP,
            used_by VARCHAR(36) REFERENCES users(id) ON DELETE SET NULL,
            revoked_at TIMESTAMP,
            created_by VARCHAR(36) REFERENCES users(id) ON DELETE SET NULL,
            created_at TIMESTAMP NOT NULL
        )
    """))
    bind.execute(text(
        "CREATE INDEX IF NOT EXISTS ix_org_activation_codes_organization_id ON org_activation_codes (organization_id)"
    ))

    columns = {column["name"] for column in inspect(bind).get_columns("users")}
    for name, ddl in USER_COLUMNS.items():
        if name not in columns:
            bind.execute(text(f"ALTER TABLE users ADD COLUMN {name} {ddl}"))
    has_fk = bind.execute(text(
        "SELECT 1 FROM pg_constraint WHERE conname = :name AND conrelid = 'users'::regclass"
    ), {"name": USER_ORG_FK}).first()
    if not has_fk:
        bind.execute(text(
            f"ALTER TABLE users ADD CONSTRAINT {USER_ORG_FK} FOREIGN KEY (organization_id) "
            "REFERENCES organizations(id) ON DELETE SET NULL"
        ))
    bind.execute(text("CREATE INDEX IF NOT EXISTS ix_users_organization_id ON users (organization_id)"))

    bind.execute(text("""
        CREATE TABLE IF NOT EXISTS org_shared_answers (
            id VARCHAR(36) PRIMARY KEY,
            organization_id VARCHAR(36) NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
            message_id VARCHAR(36) REFERENCES messages(id) ON DELETE SET NULL,
            question TEXT NOT NULL,
            answer TEXT NOT NULL,
            category VARCHAR(64) NOT NULL,
            shared_by VARCHAR(36) REFERENCES users(id) ON DELETE SET NULL,
            shared_by_name VARCHAR(255) NOT NULL,
            created_at TIMESTAMP NOT NULL,
            updated_at TIMESTAMP NOT NULL,
            CONSTRAINT uq_org_shared_answers_org_message UNIQUE (organization_id, message_id)
        )
    """))
    bind.execute(text(
        "CREATE INDEX IF NOT EXISTS ix_org_shared_answers_organization_id ON org_shared_answers (organization_id)"
    ))
    bind.execute(text(
        "CREATE INDEX IF NOT EXISTS ix_org_shared_answers_org_created ON org_shared_answers (organization_id, created_at)"
    ))

    bind.execute(text("""
        CREATE TABLE IF NOT EXISTS org_answer_likes (
            id VARCHAR(36) PRIMARY KEY,
            shared_answer_id VARCHAR(36) NOT NULL REFERENCES org_shared_answers(id) ON DELETE CASCADE,
            user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            created_at TIMESTAMP NOT NULL,
            CONSTRAINT uq_org_answer_likes_answer_user UNIQUE (shared_answer_id, user_id)
        )
    """))

    bind.execute(text("""
        CREATE TABLE IF NOT EXISTS org_answer_comments (
            id VARCHAR(36) PRIMARY KEY,
            shared_answer_id VARCHAR(36) NOT NULL REFERENCES org_shared_answers(id) ON DELETE CASCADE,
            user_id VARCHAR(36) REFERENCES users(id) ON DELETE SET NULL,
            author_name VARCHAR(255) NOT NULL,
            body TEXT NOT NULL,
            created_at TIMESTAMP NOT NULL
        )
    """))
    bind.execute(text(
        "CREATE INDEX IF NOT EXISTS ix_org_answer_comments_shared_answer_id ON org_answer_comments (shared_answer_id)"
    ))


def downgrade() -> None:
    bind = op.get_bind()
    for table in ("org_answer_comments", "org_answer_likes", "org_shared_answers", "org_activation_codes"):
        bind.execute(text(f"DROP TABLE IF EXISTS {table}"))
    bind.execute(text(f"ALTER TABLE users DROP CONSTRAINT IF EXISTS {USER_ORG_FK}"))
    bind.execute(text("DROP INDEX IF EXISTS ix_users_organization_id"))
    for name in USER_COLUMNS:
        bind.execute(text(f"ALTER TABLE users DROP COLUMN IF EXISTS {name}"))
    bind.execute(text("DROP TABLE IF EXISTS organizations"))
