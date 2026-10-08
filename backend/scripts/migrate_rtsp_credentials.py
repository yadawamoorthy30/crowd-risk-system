import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import SessionLocal  # noqa: E402
from app.models.camera import Camera, SourceType  # noqa: E402
from app.services.credentials import encrypt_credentials, split_credentials  # noqa: E402

db = SessionLocal()
try:
    cameras = db.query(Camera).filter(
        Camera.source_type.in_([SourceType.RTSP, SourceType.HTTP])
    ).all()
    migrated = 0
    for camera in cameras:
        clean, creds = split_credentials(camera.source_path)
        if creds is None:
            continue
        camera.credentials_encrypted = encrypt_credentials(*creds)
        camera.source_path = clean
        migrated += 1
        print(f"camera {camera.id}: credentials moved out of source_path")
    db.commit()
    print(f"Checked {len(cameras)} network camera(s); migrated {migrated}.")
finally:
    db.close()