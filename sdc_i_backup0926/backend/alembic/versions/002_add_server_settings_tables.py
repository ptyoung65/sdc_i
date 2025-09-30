"""Add server settings tables

Revision ID: 002_server_settings
Revises:
Create Date: 2025-09-28 13:17:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '002_server_settings'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Internal Server Config Table
    op.create_table('internal_server_config',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('enable_internal_server', sa.Boolean(), nullable=True),
        sa.Column('internal_server_mode', sa.String(length=50), nullable=True),
        sa.Column('default_model', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_internal_server_config_id'), 'internal_server_config', ['id'], unique=False)

    # Embedding Server Config Table
    op.create_table('embedding_server_config',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('config_id', sa.Integer(), nullable=True),
        sa.Column('server_id', sa.String(length=100), nullable=True),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('url', sa.String(length=200), nullable=False),
        sa.Column('api_key', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('is_primary', sa.Boolean(), nullable=True),
        sa.Column('chunk_size', sa.Integer(), nullable=True),
        sa.Column('chunk_overlap', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['config_id'], ['internal_server_config.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('server_id')
    )
    op.create_index(op.f('ix_embedding_server_config_id'), 'embedding_server_config', ['id'], unique=False)
    op.create_index(op.f('ix_embedding_server_config_server_id'), 'embedding_server_config', ['server_id'], unique=False)

    # LLM Server Config Table
    op.create_table('llm_server_config',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('config_id', sa.Integer(), nullable=True),
        sa.Column('server_id', sa.String(length=100), nullable=True),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('url', sa.String(length=200), nullable=False),
        sa.Column('api_key', sa.Text(), nullable=True),
        sa.Column('model', sa.String(length=100), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('is_primary', sa.Boolean(), nullable=True),
        sa.Column('temperature', sa.Float(), nullable=True),
        sa.Column('max_tokens', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['config_id'], ['internal_server_config.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('server_id')
    )
    op.create_index(op.f('ix_llm_server_config_id'), 'llm_server_config', ['id'], unique=False)
    op.create_index(op.f('ix_llm_server_config_server_id'), 'llm_server_config', ['server_id'], unique=False)

    # Legacy Server Settings Table
    op.create_table('legacy_server_settings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('api_url', sa.String(length=200), nullable=True),
        sa.Column('ai_model', sa.String(length=50), nullable=True),
        sa.Column('temperature', sa.Float(), nullable=True),
        sa.Column('max_tokens', sa.Integer(), nullable=True),
        sa.Column('embedding_model', sa.String(length=50), nullable=True),
        sa.Column('chunk_size', sa.Integer(), nullable=True),
        sa.Column('chunk_overlap', sa.Integer(), nullable=True),
        sa.Column('enable_korean_processing', sa.Boolean(), nullable=True),
        sa.Column('debug_mode', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_legacy_server_settings_id'), 'legacy_server_settings', ['id'], unique=False)

def downgrade():
    op.drop_index(op.f('ix_legacy_server_settings_id'), table_name='legacy_server_settings')
    op.drop_table('legacy_server_settings')
    op.drop_index(op.f('ix_llm_server_config_server_id'), table_name='llm_server_config')
    op.drop_index(op.f('ix_llm_server_config_id'), table_name='llm_server_config')
    op.drop_table('llm_server_config')
    op.drop_index(op.f('ix_embedding_server_config_server_id'), table_name='embedding_server_config')
    op.drop_index(op.f('ix_embedding_server_config_id'), table_name='embedding_server_config')
    op.drop_table('embedding_server_config')
    op.drop_index(op.f('ix_internal_server_config_id'), table_name='internal_server_config')
    op.drop_table('internal_server_config')