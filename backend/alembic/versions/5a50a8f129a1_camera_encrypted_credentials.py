"""camera encrypted credentials

Revision ID: 5a50a8f129a1
Revises: c1dc709c935b
Create Date: 2026-10-08 17:11:29.528793

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5a50a8f129a1'
down_revision: Union[str, Sequence[str], None] = 'c1dc709c935b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
     op.add_column("cameras", sa.Column("credentials_encrypted", sa.Text(), nullable=True))


def downgrade() -> None:
     op.drop_column("cameras", "credentials_encrypted")
