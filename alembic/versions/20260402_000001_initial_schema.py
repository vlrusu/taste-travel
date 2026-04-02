"""initial schema"""

import sqlalchemy as sa
from alembic import op


revision = "20260402_000001"
down_revision = None
branch_labels = None
depends_on = None


seed_restaurant_sentiment = sa.Enum(
    "love",
    "dislike",
    name="seed_restaurant_sentiment",
    native_enum=False,
)

feedback_type = sa.Enum(
    "perfect",
    "saved",
    "dismissed",
    "too_expensive",
    "too_touristy",
    "too_formal",
    "too_casual",
    "too_loud",
    "not_my_vibe",
    name="feedback_type",
    native_enum=False,
)


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("home_city", sa.String(length=255), nullable=True),
        sa.Column("onboarding_complete", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_home_city", "users", ["home_city"], unique=False)

    op.create_table(
        "seed_restaurants",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("city", sa.String(length=255), nullable=False),
        sa.Column("sentiment", seed_restaurant_sentiment, nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "name", "city", name="uq_seed_restaurants_user_name_city"),
    )
    op.create_index("ix_seed_restaurants_user_id", "seed_restaurants", ["user_id"], unique=False)
    op.create_index("ix_seed_restaurants_city", "seed_restaurants", ["city"], unique=False)
    op.create_index(
        "ix_seed_restaurants_user_sentiment",
        "seed_restaurants",
        ["user_id", "sentiment"],
        unique=False,
    )

    op.create_table(
        "taste_profiles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("attributes_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )
    op.create_index("ix_taste_profiles_user_id", "taste_profiles", ["user_id"], unique=True)

    op.create_table(
        "recommendations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("request_context_json", sa.JSON(), nullable=False),
        sa.Column("restaurant_json", sa.JSON(), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("why", sa.Text(), nullable=False),
        sa.Column("anchors_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_recommendations_user_id", "recommendations", ["user_id"], unique=False)
    op.create_index("ix_recommendations_score", "recommendations", ["score"], unique=False)
    op.create_index(
        "ix_recommendations_user_created_at",
        "recommendations",
        ["user_id", "created_at"],
        unique=False,
    )

    op.create_table(
        "feedback",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("recommendation_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("feedback_type", feedback_type, nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["recommendation_id"], ["recommendations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_feedback_recommendation_id", "feedback", ["recommendation_id"], unique=False)
    op.create_index("ix_feedback_user_id", "feedback", ["user_id"], unique=False)
    op.create_index("ix_feedback_feedback_type", "feedback", ["feedback_type"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_feedback_feedback_type", table_name="feedback")
    op.drop_index("ix_feedback_user_id", table_name="feedback")
    op.drop_index("ix_feedback_recommendation_id", table_name="feedback")
    op.drop_table("feedback")

    op.drop_index("ix_recommendations_user_created_at", table_name="recommendations")
    op.drop_index("ix_recommendations_score", table_name="recommendations")
    op.drop_index("ix_recommendations_user_id", table_name="recommendations")
    op.drop_table("recommendations")

    op.drop_index("ix_taste_profiles_user_id", table_name="taste_profiles")
    op.drop_table("taste_profiles")

    op.drop_index("ix_seed_restaurants_user_sentiment", table_name="seed_restaurants")
    op.drop_index("ix_seed_restaurants_city", table_name="seed_restaurants")
    op.drop_index("ix_seed_restaurants_user_id", table_name="seed_restaurants")
    op.drop_table("seed_restaurants")

    op.drop_index("ix_users_home_city", table_name="users")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
