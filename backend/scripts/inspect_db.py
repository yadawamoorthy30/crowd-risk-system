import os
import re
from urllib.parse import quote_plus

from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text

load_dotenv()

url = (
    f"mysql+pymysql://{os.getenv('DB_USER')}:{quote_plus(os.getenv('DB_PASSWORD'))}"
    f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
)
engine = create_engine(url)
insp = inspect(engine)


def mask(value):
    # hides any user:password@ part of a URL so secrets never get printed
    return re.sub(r"://[^@/]+@", "://***@", str(value))


with engine.connect() as c:
    print("== alembic_version ==")
    print(c.execute(text("SELECT version_num FROM alembic_version")).fetchall())

    for t in sorted(insp.get_table_names()):
        n = c.execute(text(f"SELECT COUNT(*) FROM `{t}`")).scalar()
        print(f"\n== {t} ({n} rows) ==")
        for col in insp.get_columns(t):
            null = "NULL" if col["nullable"] else "NOT NULL"
            print(f"  {col['name']:<20} {str(col['type']):<28} {null} default={col.get('default')}")
        for fk in insp.get_foreign_keys(t):
            print(f"  FK {fk['name']}: {fk['constrained_columns']} -> "
                  f"{fk['referred_table']}{fk['referred_columns']} {fk.get('options')}")
        for ix in insp.get_indexes(t):
            print(f"  IX {ix['name']}: {ix['column_names']} unique={ix['unique']}")

    print("\n== events ==")
    for r in c.execute(text("SELECT id, name, venue, event_type, start_time, end_time, status, created_by FROM events")):
        print(" ", tuple(r))

    print("\n== cameras ==")
    for r in c.execute(text("SELECT id, event_id, name, source_type, source_path, status, min_confidence, processing_fps, area_sqm, active_zone_id FROM cameras")):
        print(" ", tuple(mask(x) for x in r))

    print("\n== users (role / status counts) ==")
    for r in c.execute(text("SELECT role, status, COUNT(*) FROM users GROUP BY role, status")):
        print(" ", tuple(r))

    print("\n== zones ==")
    for r in c.execute(text("SELECT id, camera_id, name, area_sq_m FROM zones")):
        print(" ", tuple(r))