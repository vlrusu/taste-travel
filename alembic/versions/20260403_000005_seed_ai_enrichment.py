"""add seed ai enrichment fields"""

import sqlalchemy as sa
from alembic import op


revision = "20260403_000005"
down_revision = "20260402_000004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("seed_restaurants", sa.Column("raw_seed_note_text", sa.Text(), nullable=True))
    op.add_column("seed_restaurants", sa.Column("raw_place_metadata_json", sa.JSON(), nullable=True))
    op.add_column("seed_restaurants", sa.Column("raw_review_text", sa.Text(), nullable=True))
    op.add_column("seed_restaurants", sa.Column("ai_summary_text", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("seed_restaurants", "ai_summary_text")
    op.drop_column("seed_restaurants", "raw_review_text")
    op.drop_column("seed_restaurants", "raw_place_metadata_json")
    op.drop_column("seed_restaurants", "raw_seed_note_text")
