"""align events cameras users with srs

Revision ID: fcfc53e51e99
Revises: e9c68d56b0b9
Create Date: 2026-10-05 23:35:02.210592

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fcfc53e51e99'
down_revision: Union[str, Sequence[str], None] = 'e9c68d56b0b9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
     # ---------------- USERS ----------------
    # enum -> plain text -> change values -> new enum (see MySQL enum note above)
    op.alter_column("users", "role", existing_type=sa.String(20),
                    type_=sa.String(20), existing_nullable=False)
    op.execute("UPDATE users SET role = UPPER(role)")
    op.alter_column("users", "role", existing_type=sa.String(20),
                    type_=sa.Enum("ADMIN", "OPERATOR", "MAINTENANCE", name="userrole"),
                    existing_nullable=False)
    op.add_column("users", sa.Column(
        "status", sa.Enum("ACTIVE", "INACTIVE", name="userstatus"),
        nullable=False, server_default="ACTIVE"))
    op.execute("UPDATE users SET status = CASE WHEN is_active = 1 THEN 'ACTIVE' ELSE 'INACTIVE' END")
    op.drop_column("users", "is_active")

    # ---------------- EVENTS ----------------
    op.alter_column("events", "location", new_column_name="venue",
                    existing_type=sa.String(255), existing_nullable=False)
    op.add_column("events", sa.Column("event_type", sa.String(50),
                                      nullable=False, server_default="GENERAL"))
    op.add_column("events", sa.Column("start_time", sa.DateTime(), nullable=True))
    op.add_column("events", sa.Column("end_time", sa.DateTime(), nullable=True))
    op.add_column("events", sa.Column(
        "status", sa.Enum("PLANNED", "ACTIVE", "CLOSED", name="eventstatus"),
        nullable=False, server_default="PLANNED"))
    op.add_column("events", sa.Column("created_by", sa.Integer(), nullable=True))
    op.execute("UPDATE events SET start_time = TIMESTAMP(event_date, '00:00:00'), "
               "end_time = TIMESTAMP(event_date, '23:59:59')")
    op.alter_column("events", "start_time", existing_type=sa.DateTime(), nullable=False)
    op.alter_column("events", "end_time", existing_type=sa.DateTime(), nullable=False)
    op.create_foreign_key("fk_events_created_by_users", "events", "users",
                          ["created_by"], ["id"], ondelete="SET NULL")
    op.drop_column("events", "event_date")

    # ---------------- CAMERAS ----------------
    op.alter_column("cameras", "source_type", existing_type=sa.String(20),
                    type_=sa.String(20), existing_nullable=False)
    op.execute("UPDATE cameras SET source_type = 'FILE' WHERE source_type = 'video_file'")
    op.execute("UPDATE cameras SET source_type = 'USB'  WHERE source_type = 'webcam'")
    op.execute("UPDATE cameras SET source_type = 'RTSP' WHERE source_type = 'rtsp'")
    op.alter_column("cameras", "source_type", existing_type=sa.String(20),
                    type_=sa.Enum("RTSP", "HTTP", "USB", "FILE", name="sourcetype"),
                    existing_nullable=False)

    op.add_column("cameras", sa.Column("area_length_m", sa.Numeric(8, 2), nullable=True))
    op.add_column("cameras", sa.Column("area_width_m", sa.Numeric(8, 2), nullable=True))
    op.add_column("cameras", sa.Column("area_sqm", sa.Numeric(10, 2), nullable=True))
    op.add_column("cameras", sa.Column("min_confidence", sa.Float(), nullable=False,
                                       server_default=sa.text("0.40")))
    op.add_column("cameras", sa.Column("processing_fps", sa.Integer(), nullable=False,
                                       server_default=sa.text("10")))
    op.add_column("cameras", sa.Column(
        "status",
        sa.Enum("CONNECTED", "DEGRADED", "DISCONNECTED", "DISABLED", name="camerastatus"),
        nullable=False, server_default="DISCONNECTED"))
    op.add_column("cameras", sa.Column("active_zone_id", sa.Integer(), nullable=True))
    op.execute("UPDATE cameras SET status = CASE WHEN is_active = 1 "
               "THEN 'DISCONNECTED' ELSE 'DISABLED' END")
    op.create_foreign_key("fk_cameras_active_zone", "cameras", "zones",
                          ["active_zone_id"], ["id"], ondelete="SET NULL")
    op.drop_column("cameras", "is_active")


def downgrade() -> None:
    # ---------------- CAMERAS ----------------
    op.add_column("cameras", sa.Column("is_active", sa.Boolean(), nullable=False,
                                       server_default=sa.text("1")))
    op.execute("UPDATE cameras SET is_active = CASE WHEN status = 'DISABLED' THEN 0 ELSE 1 END")
    op.drop_constraint("fk_cameras_active_zone", "cameras", type_="foreignkey")
    for col in ("active_zone_id", "status", "processing_fps", "min_confidence",
                "area_sqm", "area_width_m", "area_length_m"):
        op.drop_column("cameras", col)
    op.alter_column("cameras", "source_type", existing_type=sa.String(20),
                    type_=sa.String(20), existing_nullable=False)
    # HTTP has no old equivalent; it falls back to video_file (lossy, documented)
    op.execute("UPDATE cameras SET source_type = CASE source_type "
               "WHEN 'FILE' THEN 'video_file' WHEN 'USB' THEN 'webcam' "
               "WHEN 'RTSP' THEN 'rtsp' ELSE 'video_file' END")
    op.alter_column("cameras", "source_type", existing_type=sa.String(20),
                    type_=sa.Enum("video_file", "webcam", "rtsp", name="sourcetype"),
                    existing_nullable=False)

    # ---------------- EVENTS ----------------
    op.add_column("events", sa.Column("event_date", sa.Date(), nullable=True))
    op.execute("UPDATE events SET event_date = DATE(start_time)")
    op.alter_column("events", "event_date", existing_type=sa.Date(), nullable=False)
    op.drop_constraint("fk_events_created_by_users", "events", type_="foreignkey")
    for col in ("created_by", "status", "end_time", "start_time", "event_type"):
        op.drop_column("events", col)
    op.alter_column("events", "venue", new_column_name="location",
                    existing_type=sa.String(255), existing_nullable=False)

    # ---------------- USERS ----------------
    op.add_column("users", sa.Column("is_active", sa.Boolean(), nullable=False,
                                     server_default=sa.text("1")))
    op.execute("UPDATE users SET is_active = CASE WHEN status = 'ACTIVE' THEN 1 ELSE 0 END")
    op.drop_column("users", "status")
    op.alter_column("users", "role", existing_type=sa.String(20),
                    type_=sa.String(20), existing_nullable=False)
    # MAINTENANCE has no old equivalent; it falls back to operator (lossy)
    op.execute("UPDATE users SET role = CASE role WHEN 'ADMIN' THEN 'admin' ELSE 'operator' END")
    op.alter_column("users", "role", existing_type=sa.String(20),
                    type_=sa.Enum("admin", "operator", name="userrole"),
                    existing_nullable=False)
