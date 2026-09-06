"""Safety and Quality Gate Schema

Revision ID: 003_safety_quality_gate
Revises: 002_memory_evolution
Create Date: 2026-09-02 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '003_safety_quality_gate'
down_revision: Union[str, Sequence[str], None] = '002_memory_evolution'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add confidence_score column to tasks table
    op.add_column('tasks', sa.Column('confidence_score', sa.Float(), nullable=True))

    # In PostgreSQL, add new enum values to taskstatus enum
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        try:
            op.execute("ALTER TYPE taskstatus ADD VALUE IF NOT EXISTS 'pending_approval';")
            op.execute("ALTER TYPE taskstatus ADD VALUE IF NOT EXISTS 'rejected';")
        except Exception:
            pass


def downgrade() -> None:
    op.drop_column('tasks', 'confidence_score')
