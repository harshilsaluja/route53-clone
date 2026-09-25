"""create database foundation

Revision ID: 0001
Revises:
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = '0001'
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table('users',
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('email', sa.String(), nullable=False),
    sa.Column('password_hash', sa.String(), nullable=False),
    sa.Column('display_name', sa.String(), nullable=False),
    sa.CheckConstraint('email = lower(trim(email)) AND length(email) > 0', name='ck_users_email_normalized'),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_users_email'), ['email'], unique=True)

    op.create_table('hosted_zones',
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('type', sa.Enum('PUBLIC', 'PRIVATE', name='ck_hosted_zones_type', native_enum=False, create_constraint=True), nullable=False),
    sa.Column('comment', sa.String(), nullable=True),
    sa.CheckConstraint("name = lower(trim(name)) AND length(name) > 0 AND name NOT LIKE '%.'", name='ck_hosted_zones_name_normalized'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id', 'name', 'type', name='uq_hosted_zones_owner_name_type')
    )
    with op.batch_alter_table('hosted_zones', schema=None) as batch_op:
        batch_op.create_index('ix_hosted_zones_user_type', ['user_id', 'type'], unique=False)

    op.create_table('sessions',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('token_hash', sa.String(), nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('expires_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('sessions', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_sessions_expires_at'), ['expires_at'], unique=False)
        batch_op.create_index(batch_op.f('ix_sessions_token_hash'), ['token_hash'], unique=True)
        batch_op.create_index(batch_op.f('ix_sessions_user_id'), ['user_id'], unique=False)

    op.create_table('dns_record_sets',
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('hosted_zone_id', sa.Uuid(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('record_type', sa.Enum('A', 'AAAA', 'CNAME', 'TXT', 'MX', 'NS', 'PTR', 'SRV', 'CAA', name='ck_dns_record_sets_record_type', native_enum=False, create_constraint=True), nullable=False),
    sa.Column('ttl', sa.Integer(), nullable=False),
    sa.Column('routing_policy', sa.Enum('SIMPLE', name='ck_dns_record_sets_routing_policy', native_enum=False, create_constraint=True), server_default='SIMPLE', nullable=False),
    sa.CheckConstraint("name = lower(trim(name)) AND name NOT LIKE '%.'", name='ck_dns_record_sets_name_normalized'),
    sa.CheckConstraint('ttl > 0', name='ck_dns_record_sets_ttl_positive'),
    sa.ForeignKeyConstraint(['hosted_zone_id'], ['hosted_zones.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('hosted_zone_id', 'name', 'record_type', name='uq_dns_record_sets_zone_name_type')
    )
    with op.batch_alter_table('dns_record_sets', schema=None) as batch_op:
        batch_op.create_index('ix_dns_record_sets_zone_type', ['hosted_zone_id', 'record_type'], unique=False)

    op.create_table('dns_record_values',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('record_set_id', sa.Uuid(), nullable=False),
    sa.Column('position', sa.Integer(), nullable=False),
    sa.Column('value', sa.Text(), nullable=False),
    sa.CheckConstraint('position >= 0', name='ck_dns_record_values_position_nonnegative'),
    sa.ForeignKeyConstraint(['record_set_id'], ['dns_record_sets.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('record_set_id', 'position', name='uq_dns_record_values_set_position')
    )


def downgrade() -> None:
    op.drop_table('dns_record_values')
    with op.batch_alter_table('dns_record_sets', schema=None) as batch_op:
        batch_op.drop_index('ix_dns_record_sets_zone_type')

    op.drop_table('dns_record_sets')
    with op.batch_alter_table('sessions', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_sessions_user_id'))
        batch_op.drop_index(batch_op.f('ix_sessions_token_hash'))
        batch_op.drop_index(batch_op.f('ix_sessions_expires_at'))

    op.drop_table('sessions')
    with op.batch_alter_table('hosted_zones', schema=None) as batch_op:
        batch_op.drop_index('ix_hosted_zones_user_type')

    op.drop_table('hosted_zones')
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_users_email'))

    op.drop_table('users')
