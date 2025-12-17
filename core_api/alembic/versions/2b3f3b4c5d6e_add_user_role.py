"""add user role (viewer/editor)

Revision ID: 2b3f3b4c5d6e
Revises: 92e15d5e5a27
Create Date: 2025-12-17

"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "2b3f3b4c5d6e"
down_revision: Union[str, None] = "92e15d5e5a27"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    user_role = postgresql.ENUM("viewer", "editor", name="user_role")
    user_role.create(op.get_bind(), checkfirst=True)

    op.add_column(
        "users",
        sa.Column("role", sa.Enum("viewer", "editor", name="user_role"), nullable=False, server_default="editor"),
    )

    # optional: remove server_default to keep schema clean (role must be set explicitly by app)
    op.alter_column("users", "role", server_default=None)


def downgrade() -> None:
    op.drop_column("users", "role")
    user_role = postgresql.ENUM("viewer", "editor", name="user_role")
    user_role.drop(op.get_bind(), checkfirst=True)


