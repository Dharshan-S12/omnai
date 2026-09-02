"""Initial schema

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-09-01 12:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_initial_schema'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    task_type_enum = postgresql.ENUM('ocr', 'text_gen', 'code_exec', 'doc_gen', name='tasktype', create_type=False)
    task_type_enum.create(op.get_bind(), checkfirst=True)
    
    task_status_enum = postgresql.ENUM('pending', 'running', 'done', 'failed', name='taskstatus', create_type=False)
    task_status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        'tasks',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('task_type', postgresql.ENUM('ocr', 'text_gen', 'code_exec', 'doc_gen', name='tasktype', create_type=False), nullable=False),
        sa.Column('status', postgresql.ENUM('pending', 'running', 'done', 'failed', name='taskstatus', create_type=False), nullable=False),
        sa.Column('input_ref', sa.String(), nullable=False),
        sa.Column('output_ref', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table(
        'task_steps',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('task_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('step_number', sa.Integer(), nullable=False),
        sa.Column('description', sa.String(), nullable=False),
        sa.Column('tool_called', sa.String(), nullable=True),
        sa.Column('tool_result', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table(
        'documents',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('filename', sa.String(), nullable=False),
        sa.Column('filetype', sa.String(), nullable=False),
        sa.Column('storage_path', sa.String(), nullable=False),
        sa.Column('uploaded_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('task_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], ),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('documents')
    op.drop_table('task_steps')
    op.drop_table('tasks')
    
    task_status_enum = postgresql.ENUM('pending', 'running', 'done', 'failed', name='taskstatus')
    task_status_enum.drop(op.get_bind(), checkfirst=True)

    task_type_enum = postgresql.ENUM('ocr', 'text_gen', 'code_exec', 'doc_gen', name='tasktype')
    task_type_enum.drop(op.get_bind(), checkfirst=True)
