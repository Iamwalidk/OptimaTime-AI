"""add plan item source

Revision ID: 1f6b2f8f9d3a
Revises: 885839fb6d00
Create Date: 2026-01-01 20:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "1f6b2f8f9d3a"
down_revision: Union[str, Sequence[str], None] = "885839fb6d00"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "plan_items",
        sa.Column("source", sa.String(), nullable=False, server_default="ai"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("plan_items", "source")
