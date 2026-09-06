"""Equipment Knowledge Graph Schema

Revision ID: 004_equipment_knowledge_graph
Revises: 003_safety_quality_gate
Create Date: 2026-09-02 14:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '004_equipment_knowledge_graph'
down_revision: Union[str, Sequence[str], None] = '003_safety_quality_gate'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'equipment_nodes',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('equipment_id', sa.String(), nullable=False),
        sa.Column('equipment_name', sa.String(), nullable=True),
        sa.Column('unit', sa.String(), nullable=True),
        sa.Column('equipment_type', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_equipment_nodes_equipment_id', 'equipment_nodes', ['equipment_id'], unique=True)
    op.create_index('ix_equipment_nodes_unit', 'equipment_nodes', ['unit'])
    op.create_index('ix_equipment_nodes_equipment_type', 'equipment_nodes', ['equipment_type'])

    op.create_table(
        'equipment_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('equipment_node_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('source_task_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('event_type', sa.String(), nullable=False),
        sa.Column('event_data', sa.JSON(), nullable=False),
        sa.Column('event_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['equipment_node_id'], ['equipment_nodes.id'], ),
        sa.ForeignKeyConstraint(['source_task_id'], ['tasks.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_equipment_events_equipment_node_id', 'equipment_events', ['equipment_node_id'])
    op.create_index('ix_equipment_events_event_type', 'equipment_events', ['event_type'])


def downgrade() -> None:
    op.drop_table('equipment_events')
    op.drop_table('equipment_nodes')
