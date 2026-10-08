import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import SessionLocal  # noqa: E402
from app.models.camera import Camera, SourceType  # noqa: E402
from app.services.credentials import (  # noqa: E402
    build_stream_url, decrypt_credentials, encrypt_credentials, split_credentials,
)

token = encrypt_credentials("user", "p@ss:word/1")
assert decrypt_credentials(token) == ("user", "p@ss:word/1")
print("Encrypt/decrypt round trip: OK")

clean, creds = split_credentials("rtsp://user:p%40ss@10.0.0.5:554/s1")
assert clean == "rtsp://10.0.0.5:554/s1" and creds == ("user", "p@ss")
assert build_stream_url(clean, encrypt_credentials(*creds)) == "rtsp://user:p%40ss@10.0.0.5:554/s1"
print("URL split/rebuild: OK")

db = SessionLocal()
try:
    for cam in db.query(Camera).filter(Camera.source_type.in_([SourceType.RTSP, SourceType.HTTP])):
        leaked = split_credentials(cam.source_path)[1] is not None
        decrypts = "n/a"
        if cam.credentials_encrypted:
            decrypt_credentials(cam.credentials_encrypted)
            decrypts = "yes"
        print(f"camera {cam.id}: source_path={cam.source_path} | "
              f"has_credentials={cam.has_credentials} | decrypts={decrypts} | "
              f"{'PASSWORD IN source_path!' if leaked else 'source_path clean'}")
finally:
    db.close()