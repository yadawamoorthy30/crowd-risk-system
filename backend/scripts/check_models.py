from sqlalchemy.orm import configure_mappers

import app.models  # noqa: F401
from app.database import SessionLocal
from app.models import Camera, Event, User, Zone

configure_mappers()  # fails here if any relationship is ambiguous
print("Mappers OK")

with SessionLocal() as db:
    print("events :", [(e.id, e.venue, e.status.value) for e in db.query(Event).all()])
    print("cameras:", [(c.id, c.source_type.value, c.status.value, c.min_confidence)
                       for c in db.query(Camera).all()])
    print("zones  :", [(z.id, z.camera_id, z.name) for z in db.query(Zone).all()])
    print("users  :", db.query(User).count())
    cam = db.get(Camera, 1)
    print("camera 1 zones:", [z.name for z in cam.zones], "| active:", cam.active_zone)