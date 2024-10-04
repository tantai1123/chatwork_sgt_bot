"""initialize migration

Revision ID: 75f7be72d806
Revises: 
Create Date: 2024-10-03 21:41:41.069737

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "75f7be72d806"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "configs",
        sa.Column("key", sa.String(length=50), nullable=False),
        sa.Column("value", sa.Text(), nullable=True),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("date_created", sa.DateTime(), nullable=True),
        sa.Column("date_modified", sa.DateTime(), nullable=True),
        sa.Column("date_deleted", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key"),
    )
    with op.batch_alter_table("configs", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_configs_id"), ["id"], unique=False)

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table("configs", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_configs_id"))

    op.drop_table("configs")
    # ### end Alembic commands ###
