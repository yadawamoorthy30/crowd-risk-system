"""metric snapshots privacy fix

Revision ID: c1dc709c935b
Revises: d1b7646d16a0
Create Date: 2026-10-08 15:17:35.842593

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql


# revision identifiers, used by Alembic.
revision: str = 'c1dc709c935b'
down_revision: Union[str, Sequence[str], None] = 'd1b7646d16a0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "metric_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("camera_id", sa.Integer(), nullable=False),
        sa.Column("ts", mysql.DATETIME(fsp=3), nullable=False),
        sa.Column("person_count", sa.Integer(), nullable=False),
        sa.Column("density", sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(["camera_id"], ["cameras.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_metric_snapshots_camera_ts", "metric_snapshots", ["camera_id", "ts"])
    op.create_index(op.f("ix_metric_snapshots_id"), "metric_snapshots", ["id"])

    # keep the aggregated history; the camera comes from the run
    op.execute(
        "INSERT INTO metric_snapshots (camera_id, ts, person_count, density) "
        "SELECT r.camera_id, s.captured_at, s.people_count, NULL "
        "FROM detection_snapshots s JOIN detection_runs r ON r.id = s.run_id "
        "ORDER BY s.id"
    )

    # per-track data must not be stored (SRS: anonymous, transient IDs)
    op.drop_table("track_observations")
    op.drop_table("detection_snapshots")
    


def downgrade() -> None:
    # Recreates EMPTY tables. The deleted per-track data cannot come back;
    # restore backup_before_step7.sql if you really need it.
    op.create_table(
        "detection_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("run_id", sa.Integer(), nullable=False),
        sa.Column("frame_number", sa.Integer(), nullable=False),
        sa.Column("captured_at", sa.DateTime(), nullable=False),
        sa.Column("people_count", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["detection_runs.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_snapshots_run_captured", "detection_snapshots", ["run_id", "captured_at"])
    op.create_index(op.f("ix_detection_snapshots_id"), "detection_snapshots", ["id"])
    op.create_table(
        "track_observations",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("snapshot_id", sa.Integer(), nullable=False),
        sa.Column("track_id", sa.Integer(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("x", sa.Integer(), nullable=False),
        sa.Column("y", sa.Integer(), nullable=False),
        sa.Column("width", sa.Integer(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["snapshot_id"], ["detection_snapshots.id"], ondelete="CASCADE"),
    )
    op.create_index(op.f("ix_track_observations_id"), "track_observations", ["id"])
    op.create_index(op.f("ix_track_observations_snapshot_id"), "track_observations", ["snapshot_id"])
    op.drop_table("metric_snapshots")
