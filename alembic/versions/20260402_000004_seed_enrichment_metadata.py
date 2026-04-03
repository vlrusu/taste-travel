"""add seed enrichment metadata"""

import sqlalchemy as sa
from alembic import op


revision = "20260402_000004"
down_revision = "20260402_000003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("seed_restaurants", sa.Column("review_summary_text", sa.Text(), nullable=True))
    op.add_column("seed_restaurants", sa.Column("editorial_summary_text", sa.Text(), nullable=True))
    op.add_column("seed_restaurants", sa.Column("menu_summary_text", sa.Text(), nullable=True))
    op.add_column("seed_restaurants", sa.Column("derived_traits_json", sa.JSON(), nullable=True))
    op.add_column("seed_restaurants", sa.Column("enrichment_status", sa.String(length=50), nullable=True))
    op.add_column("seed_restaurants", sa.Column("enriched_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("seed_restaurants", "enriched_at")
    op.drop_column("seed_restaurants", "enrichment_status")
    op.drop_column("seed_restaurants", "derived_traits_json")
    op.drop_column("seed_restaurants", "menu_summary_text")
    op.drop_column("seed_restaurants", "editorial_summary_text")
    op.drop_column("seed_restaurants", "review_summary_text")
