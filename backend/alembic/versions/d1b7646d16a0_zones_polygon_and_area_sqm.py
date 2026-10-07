"""zones polygon and area_sqm

Revision ID: d1b7646d16a0
Revises: fcfc53e51e99
Create Date: 2026-10-06 12:17:52.087189

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd1b7646d16a0'
down_revision: Union[str, Sequence[str], None] = 'fcfc53e51e99'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("zones", "area_sq_m", new_column_name="area_sqm",
                    existing_type=sa.Numeric(10, 2), existing_nullable=False)
    op.add_column("zones", sa.Column("polygon", sa.JSON(), nullable=True))
    # placeholder = full frame, to be replaced by the admin
    op.execute("UPDATE zones SET polygon = "
               "JSON_ARRAY(JSON_ARRAY(0,0), JSON_ARRAY(1,0), JSON_ARRAY(1,1), JSON_ARRAY(0,1))")
    op.alter_column("zones", "polygon", existing_type=sa.JSON(), nullable=False)



def downgrade() -> None:
    op.drop_column("zones", "polygon")
    op.alter_column("zones", "area_sqm", new_column_name="area_sq_m",
                    existing_type=sa.Numeric(10, 2), existing_nullable=False)
