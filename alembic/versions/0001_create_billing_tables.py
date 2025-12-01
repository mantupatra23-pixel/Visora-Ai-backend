"""create billing tables

Revision ID: 0001
Revises: 
Create Date: 2025-12-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '0001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table('users',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('email', sa.String(length=255), nullable=False, unique=True),
        sa.Column('name', sa.String(length=255)),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'))
    )
    op.create_table('subscriptions', 
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE')),
        sa.Column('stripe_subscription_id', sa.String(length=255), unique=True),
        sa.Column('price_id', sa.String(length=255)),
        sa.Column('status', sa.String(length=50)),
        sa.Column('current_period_start', sa.DateTime()),
        sa.Column('current_period_end', sa.DateTime()),
        sa.Column('cancel_at_period_end', sa.Boolean(), server_default=sa.text('false')),
        sa.Column('raw', sa.JSON())
    )
    op.create_table('invoices',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='SET NULL')),
        sa.Column('stripe_invoice_id', sa.String(length=255), unique=True),
        sa.Column('amount_due', sa.Numeric(12,2)),
        sa.Column('currency', sa.String(length=10)),
        sa.Column('paid', sa.Boolean(), server_default=sa.text('false')),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.Column('raw', sa.JSON())
    )
    op.create_table('stripe_events',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('stripe_event_id', sa.String(length=255), unique=True),
        sa.Column('type', sa.String(length=255)),
        sa.Column('payload', sa.JSON()),
        sa.Column('received_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.Column('processed', sa.Boolean(), server_default=sa.text('false'))
    )

def downgrade():
    op.drop_table('stripe_events')
    op.drop_table('invoices')
    op.drop_table('subscriptions')
    op.drop_table('users')
