"""Align document version nanosecond timestamps with the existing model."""

import sqlalchemy as sa
from alembic import op

revision = "6ac7d9e25f10"
down_revision = "55bb5f6728b8"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("document_versions") as batch:
        batch.alter_column(
            "created", existing_type=sa.Integer(), type_=sa.BigInteger(), existing_nullable=False
        )


def downgrade():
    # Nanosecond values cannot fit PostgreSQL INTEGER; retain the widened storage.
    pass
