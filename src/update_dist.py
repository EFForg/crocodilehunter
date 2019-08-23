import database as db
import sys

conn = db.init_db(sys.argv[1])
towers = conn.query(db.Tower).all()

for t in towers:
    print(f"{t.est_dist}\t{t.est_distance()})")
    t.est_dist = t.est_distance()

conn.commit()
