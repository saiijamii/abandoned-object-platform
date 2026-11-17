"""phase 9 foundation"""
from alembic import op
import sqlalchemy as sa

revision = "0001_phase9"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("users", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("username", sa.String(128), nullable=False), sa.Column("password_hash", sa.String(256), nullable=False), sa.Column("role", sa.String(32), nullable=False), sa.Column("enabled", sa.Boolean(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()), sa.UniqueConstraint("username"))
    op.create_table("processing_sessions", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("session_id", sa.String(128), nullable=False), sa.Column("camera_id", sa.String(128), nullable=False), sa.Column("status", sa.String(32), nullable=False), sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now()), sa.Column("ended_at", sa.DateTime(timezone=True)), sa.UniqueConstraint("session_id"))
    op.create_table("events", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("event_id", sa.String(128), nullable=False), sa.Column("idempotency_key", sa.String(512), nullable=False), sa.Column("camera_id", sa.String(128), nullable=False), sa.Column("event_type", sa.String(128), nullable=False), sa.Column("payload", sa.Text(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()), sa.UniqueConstraint("event_id"), sa.UniqueConstraint("idempotency_key"))
    op.create_table("evidence", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("event_id", sa.String(128), nullable=False), sa.Column("object_uri", sa.String(1024), nullable=False), sa.Column("sha256", sa.String(64), nullable=False), sa.Column("content_type", sa.String(128), nullable=False), sa.Column("byte_size", sa.Integer(), nullable=False), sa.Column("retention_deadline", sa.DateTime(timezone=True)), sa.Column("deleted", sa.Boolean(), nullable=False))
    op.create_table("audit_logs", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("actor", sa.String(128)), sa.Column("action", sa.String(128), nullable=False), sa.Column("resource", sa.String(512)), sa.Column("detail", sa.Text(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()))


def downgrade() -> None:
    for table in ("audit_logs", "evidence", "events", "processing_sessions", "users"):
        op.drop_table(table)
