import database as db
import sys

conn = db.init_db(sys.argv[1])
fp = sys.argv[2]
towers = []

with open(fp) as kt_list:
    for line in kt_list:
        towers.append([str(n) for n in line.strip().split(',')])

dupes = 0
added = 0

for tower in towers:
    kt = db.KnownTower.query.filter(
            db.KnownTower.lat == tower[0],
            db.KnownTower.lon == tower[1])
    #print(kt, tower[0], tower[1])
    #print(kt.all())
    if kt.count() > 0 :
        dupes += 1
        continue

    kt = db.KnownTower(
        lat = tower[0],
        lon = tower[1],
        description = tower[2]
    )
    conn.add(kt)
    added += 1
    conn.commit()

print(f"added {added} known towers\nrejected {dupes} duplicate towers")
