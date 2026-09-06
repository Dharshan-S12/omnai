"""Memory Evolution Layer Schema

Revision ID: 002_memory_evolution
Revises: 001_initial_schema
Create Date: 2026-09-02 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '002_memory_evolution'
down_revision: Union[str, Sequence[str], None] = '001_initial_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'memory_entries',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('source_task_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('entity_key', sa.String(), nullable=False),
        sa.Column('summary_text', sa.String(), nullable=False),
        sa.Column('embedding_id', sa.String(), nullable=True),
        sa.Column('strength_score', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('last_accessed_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('access_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('superseded_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(['source_task_id'], ['tasks.id'], ),
        sa.ForeignKeyConstraint(['superseded_by'], ['memory_entries.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_memory_entries_entity_key', 'memory_entries', ['entity_key'])

    op.create_table(
        'memory_links',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('source_memory_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('target_memory_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('relation_type', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['source_memory_id'], ['memory_entries.id'], ),
        sa.ForeignKeyConstraint(['target_memory_id'], ['memory_entries.id'], ),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('memory_links')
    op.drop_index('ix_memory_entries_entity_key', table_name='memory_entries')
    op.drop_table('memory_entries')
