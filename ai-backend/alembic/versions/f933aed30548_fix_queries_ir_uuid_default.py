"""fix_queries_ir_uuid_default

Revision ID: f933aed30548
Revises: 849b77b6dfe6
Create Date: 2025-04-23 11:35:40.644658

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f933aed30548"
down_revision: Union[str, None] = "849b77b6dfe6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("queries_ir", "id", server_default=sa.text("gen_random_uuid()"))


def downgrade() -> None:
    op.alter_column("queries_ir", "id", server_default=None)
