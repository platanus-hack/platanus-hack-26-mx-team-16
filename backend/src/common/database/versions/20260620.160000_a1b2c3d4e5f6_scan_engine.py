"""scan_engine

Revision ID: a1b2c3d4e5f6
Revises: 42ba1238b08f
Create Date: 2026-06-20 16:00:00.000000

06-data-model: the frozen Postgres schema of the pentest engine — tables
sites, scans, findings, agentic_surface, scan_events, watchlist, alerts,
notification_prefs, public_reports plus their key indexes and idempotency
constraints (spec §2-§4). The circular FK sites.latest_scan_id <-> scans.site_id
is resolved with use_alter (the FK is added after both tables exist).
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "42ba1238b08f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- sites --------------------------------------------------------------
    op.create_table(
        "sites",
        sa.Column("url", sa.String(length=2048), nullable=False),
        sa.Column("hostname", sa.String(length=255), nullable=False),
        sa.Column("is_gov", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("country", sa.String(length=2), nullable=True),
        sa.Column("owner_user_id", sa.UUID(), nullable=True),
        sa.Column("latest_scan_id", sa.UUID(), nullable=True),
        sa.Column("uuid", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.uuid"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("uuid"),
    )
    op.create_index(op.f("ix_sites_hostname"), "sites", ["hostname"], unique=False)
    op.create_index(op.f("ix_sites_is_gov"), "sites", ["is_gov"], unique=False)
    op.create_index(
        op.f("ix_sites_owner_user_id"), "sites", ["owner_user_id"], unique=False
    )

    # --- scans --------------------------------------------------------------
    op.create_table(
        "scans",
        sa.Column("site_id", sa.UUID(), nullable=False),
        sa.Column("level", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("visibility", sa.String(length=20), nullable=False),
        sa.Column("requested_by", sa.UUID(), nullable=True),
        sa.Column(
            "authorized", sa.Boolean(), server_default="false", nullable=False
        ),
        sa.Column("authorized_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("progress", sa.Integer(), server_default="0", nullable=False),
        sa.Column("current_phase", sa.Text(), nullable=True),
        sa.Column(
            "tools_status", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column("coverage", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("web_score", sa.Integer(), nullable=True),
        sa.Column("agentic_score", sa.Integer(), nullable=True),
        sa.Column("overall_score", sa.Integer(), nullable=True),
        sa.Column("overall_grade", sa.CHAR(length=1), nullable=True),
        sa.Column("agentic_status", sa.String(length=25), nullable=True),
        sa.Column("penalty_raw", sa.Integer(), nullable=True),
        sa.Column("summary", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("uuid", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["site_id"], ["sites.uuid"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["requested_by"], ["users.uuid"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("uuid"),
    )
    op.create_index(op.f("ix_scans_site_id"), "scans", ["site_id"], unique=False)
    # Idempotency of POST /scans: only one active scan per (site, level) (§4).
    op.create_index(
        "uq_scans_active_per_site_level",
        "scans",
        ["site_id", "level"],
        unique=True,
        postgresql_where=sa.text("status IN ('queued','running')"),
    )
    # Leaderboard "worst first": grade ASC, penalty_raw DESC (§4).
    op.create_index(
        "ix_scans_leaderboard",
        "scans",
        ["overall_grade", sa.text("penalty_raw DESC")],
        unique=False,
    )

    # Circular FK: sites.latest_scan_id -> scans.uuid (added after both tables).
    op.create_foreign_key(
        "fk_sites_latest_scan_id",
        "sites",
        "scans",
        ["latest_scan_id"],
        ["uuid"],
        ondelete="SET NULL",
        use_alter=True,
    )

    # --- findings -----------------------------------------------------------
    op.create_table(
        "findings",
        sa.Column("scan_id", sa.UUID(), nullable=False),
        sa.Column("site_id", sa.UUID(), nullable=False),
        sa.Column("source", sa.String(length=20), nullable=False),
        sa.Column("tool", sa.String(length=100), nullable=False),
        sa.Column("category", sa.String(length=20), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("cvss", sa.Float(), nullable=True),
        sa.Column("confidence", sa.String(length=20), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column(
            "evidence",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="{}",
            nullable=False,
        ),
        sa.Column("affected_url", sa.Text(), nullable=True),
        sa.Column("endpoint", sa.Text(), nullable=True),
        sa.Column("param", sa.String(length=255), nullable=True),
        sa.Column("impact", sa.Text(), nullable=False),
        sa.Column("remediation", sa.Text(), nullable=False),
        sa.Column(
            "references",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="[]",
            nullable=False,
        ),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("dedupe_key", sa.CHAR(length=64), nullable=False),
        sa.Column(
            "first_seen",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "last_seen",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("uuid", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["scan_id"], ["scans.uuid"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["site_id"], ["sites.uuid"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("uuid"),
        # UPSERT key for temporal monitoring (§4).
        sa.UniqueConstraint("site_id", "dedupe_key", name="uq_findings_site_dedupe"),
    )
    op.create_index(op.f("ix_findings_scan_id"), "findings", ["scan_id"], unique=False)
    op.create_index(op.f("ix_findings_site_id"), "findings", ["site_id"], unique=False)

    # --- agentic_surface ----------------------------------------------------
    op.create_table(
        "agentic_surface",
        sa.Column("scan_id", sa.UUID(), nullable=False),
        sa.Column("site_id", sa.UUID(), nullable=False),
        sa.Column("type", sa.String(length=20), nullable=False),
        sa.Column("vendor", sa.String(length=100), nullable=True),
        sa.Column("location_url", sa.Text(), nullable=False),
        sa.Column("inferred_model", sa.String(length=100), nullable=True),
        sa.Column(
            "detected_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("uuid", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["scan_id"], ["scans.uuid"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["site_id"], ["sites.uuid"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("uuid"),
    )
    op.create_index(
        op.f("ix_agentic_surface_scan_id"), "agentic_surface", ["scan_id"], unique=False
    )
    op.create_index(
        op.f("ix_agentic_surface_site_id"), "agentic_surface", ["site_id"], unique=False
    )

    # --- scan_events --------------------------------------------------------
    op.create_table(
        "scan_events",
        sa.Column("scan_id", sa.UUID(), nullable=False),
        sa.Column("seq", sa.Integer(), nullable=False),
        sa.Column(
            "ts",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("type", sa.String(length=20), nullable=False),
        sa.Column("agent", sa.String(length=100), nullable=True),
        sa.Column("tool", sa.String(length=100), nullable=True),
        sa.Column("severity", sa.String(length=20), nullable=True),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="{}",
            nullable=False,
        ),
        sa.Column("progress", sa.Integer(), nullable=True),
        sa.Column("uuid", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["scan_id"], ["scans.uuid"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("uuid"),
        # Single source of order; deterministic replay (§4).
        sa.UniqueConstraint("scan_id", "seq", name="uq_scan_events_scan_seq"),
    )
    op.create_index(
        op.f("ix_scan_events_scan_id"), "scan_events", ["scan_id"], unique=False
    )

    # --- watchlist ----------------------------------------------------------
    op.create_table(
        "watchlist",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("site_id", sa.UUID(), nullable=False),
        sa.Column("monitor", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("uuid", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.uuid"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["site_id"], ["sites.uuid"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("uuid"),
        sa.UniqueConstraint("user_id", "site_id", name="uq_watchlist_user_site"),
    )
    op.create_index(
        op.f("ix_watchlist_user_id"), "watchlist", ["user_id"], unique=False
    )
    op.create_index(
        op.f("ix_watchlist_site_id"), "watchlist", ["site_id"], unique=False
    )

    # --- alerts -------------------------------------------------------------
    op.create_table(
        "alerts",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("site_id", sa.UUID(), nullable=False),
        sa.Column("scan_id", sa.UUID(), nullable=True),
        sa.Column("type", sa.String(length=50), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("channel", sa.String(length=20), nullable=False),
        sa.Column(
            "sent_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("uuid", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.uuid"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["site_id"], ["sites.uuid"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["scan_id"], ["scans.uuid"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("uuid"),
    )
    op.create_index(op.f("ix_alerts_user_id"), "alerts", ["user_id"], unique=False)
    op.create_index(op.f("ix_alerts_site_id"), "alerts", ["site_id"], unique=False)

    # --- notification_prefs (PK = user_id) ---------------------------------
    op.create_table(
        "notification_prefs",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column(
            "email_enabled", sa.Boolean(), server_default="true", nullable=False
        ),
        sa.Column("slack_webhook_url", sa.String(length=2048), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.uuid"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id"),
    )

    # --- public_reports -----------------------------------------------------
    op.create_table(
        "public_reports",
        sa.Column("token", sa.String(length=64), nullable=False),
        sa.Column("scan_id", sa.UUID(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("uuid", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["scan_id"], ["scans.uuid"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("uuid"),
    )
    op.create_index(
        op.f("ix_public_reports_token"), "public_reports", ["token"], unique=True
    )
    op.create_index(
        op.f("ix_public_reports_scan_id"), "public_reports", ["scan_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_public_reports_scan_id"), table_name="public_reports")
    op.drop_index(op.f("ix_public_reports_token"), table_name="public_reports")
    op.drop_table("public_reports")

    op.drop_table("notification_prefs")

    op.drop_index(op.f("ix_alerts_site_id"), table_name="alerts")
    op.drop_index(op.f("ix_alerts_user_id"), table_name="alerts")
    op.drop_table("alerts")

    op.drop_index(op.f("ix_watchlist_site_id"), table_name="watchlist")
    op.drop_index(op.f("ix_watchlist_user_id"), table_name="watchlist")
    op.drop_table("watchlist")

    op.drop_index(op.f("ix_scan_events_scan_id"), table_name="scan_events")
    op.drop_table("scan_events")

    op.drop_index(op.f("ix_agentic_surface_site_id"), table_name="agentic_surface")
    op.drop_index(op.f("ix_agentic_surface_scan_id"), table_name="agentic_surface")
    op.drop_table("agentic_surface")

    op.drop_index(op.f("ix_findings_site_id"), table_name="findings")
    op.drop_index(op.f("ix_findings_scan_id"), table_name="findings")
    op.drop_table("findings")

    # Drop the circular FK before dropping scans.
    op.drop_constraint("fk_sites_latest_scan_id", "sites", type_="foreignkey")
    op.drop_index("ix_scans_leaderboard", table_name="scans")
    op.drop_index("uq_scans_active_per_site_level", table_name="scans")
    op.drop_index(op.f("ix_scans_site_id"), table_name="scans")
    op.drop_table("scans")

    op.drop_index(op.f("ix_sites_owner_user_id"), table_name="sites")
    op.drop_index(op.f("ix_sites_is_gov"), table_name="sites")
    op.drop_index(op.f("ix_sites_hostname"), table_name="sites")
    op.drop_table("sites")
