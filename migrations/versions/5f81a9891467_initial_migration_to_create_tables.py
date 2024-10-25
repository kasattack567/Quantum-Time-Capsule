"""Initial migration to create tables

Revision ID: 5f81a9891467
Revises: 
Create Date: 2024-10-25 11:37:29.804871

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5f81a9891467'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('message',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('message_id', sa.String(length=36), nullable=False),
    sa.Column('ciphertext', sa.Text(), nullable=False),
    sa.Column('key_gen_time', sa.Float(), nullable=False),
    sa.Column('encryption_time', sa.Float(), nullable=False),
    sa.Column('public_key_n', sa.Text(), nullable=False),
    sa.Column('public_exponent_e', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=120), nullable=True),
    sa.Column('email', sa.String(length=120), nullable=True),
    sa.Column('age', sa.Integer(), nullable=True),
    sa.Column('subject', sa.String(length=100), nullable=True),
    sa.Column('country', sa.String(length=100), nullable=True),
    sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('message', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_message_country'), ['country'], unique=False)
        batch_op.create_index(batch_op.f('ix_message_email'), ['email'], unique=False)
        batch_op.create_index(batch_op.f('ix_message_message_id'), ['message_id'], unique=True)

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('message', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_message_message_id'))
        batch_op.drop_index(batch_op.f('ix_message_email'))
        batch_op.drop_index(batch_op.f('ix_message_country'))

    op.drop_table('message')
    # ### end Alembic commands ###
