"""add seed place metadata"""

import sqlalchemy as sa
from alembic import op


revision = "20260402_000002"
down_revision = "20260402_000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("seed_restaurants", sa.Column("source", sa.String(length=50), nullable=True))
    op.add_column("seed_restaurants", sa.Column("source_place_id", sa.String(length=255), nullable=True))
    op.add_column("seed_restaurants", sa.Column("formatted_address", sa.Text(), nullable=True))
    op.add_column("seed_restaurants", sa.Column("lat", sa.Float(), nullable=True))
    op.add_column("seed_restaurants", sa.Column("lon", sa.Float(), nullable=True))
    op.add_column(
        "seed_restaurants",
        sa.Column("is_verified_place", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.create_index("ix_seed_restaurants_source_place_id", "seed_restaurants", ["source_place_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_seed_restaurants_source_place_id", table_name="seed_restaurants")
    op.drop_column("seed_restaurants", "is_verified_place")
    op.drop_column("seed_restaurants", "lon")
    op.drop_column("seed_restaurants", "lat")
    op.drop_column("seed_restaurants", "formatted_address")
    op.drop_column("seed_restaurants", "source_place_id")
    op.drop_column("seed_restaurants", "source")
