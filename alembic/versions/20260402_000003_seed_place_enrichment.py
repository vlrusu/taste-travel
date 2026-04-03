"""add seed place enrichment fields"""

import sqlalchemy as sa
from alembic import op


revision = "20260402_000003"
down_revision = "20260402_000002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("seed_restaurants", sa.Column("price_level", sa.String(length=10), nullable=True))
    op.add_column("seed_restaurants", sa.Column("rating", sa.Float(), nullable=True))
    op.add_column("seed_restaurants", sa.Column("user_ratings_total", sa.Integer(), nullable=True))
    op.add_column("seed_restaurants", sa.Column("raw_types", sa.JSON(), nullable=True))
    op.add_column("seed_restaurants", sa.Column("place_traits_json", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("seed_restaurants", "place_traits_json")
    op.drop_column("seed_restaurants", "raw_types")
    op.drop_column("seed_restaurants", "user_ratings_total")
    op.drop_column("seed_restaurants", "rating")
    op.drop_column("seed_restaurants", "price_level")
