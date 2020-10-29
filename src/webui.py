#!/usr/bin/env python3
from flask import Flask, Response, render_template, redirect, url_for, request, jsonify
from flask_script import Manager
from flask_migrate import Migrate, MigrateCommand
from threading import Thread
from werkzeug import wrappers
import numpy
from database import Base
import os
import json

class Webui:
    def __init__(self, watchdog):
        os.environ['WERKZEUG_RUN_MAIN'] = 'true'
        self.app = Flask(__name__)
        self.watchdog = watchdog
        self.migrate = Migrate(self.app, Base)
        self.manager = Manager(self.app)
        self.manager.add_command('db', MigrateCommand)
        self.logger = self.watchdog.logger
        self.app.logger.addHandler(self.logger)

    def start_daemon(self):
        self.logger.info(f"Starting WebUI")

        #Add each endpoint manually
        self.add_endpoint("/", "index", self.enodeb_sightings)
        self.add_endpoint("/cell-sightings", "cell_sightings", self.cell_sightings)
        self.add_endpoint("/check_all", "checkall", self.check_all)
        self.add_endpoint("/detail/<row_id>", "detail", self.detail)
        self.add_endpoint("/enb_detail/<enodeb_id>", "enb_detail", self.enb_detail)
        self.add_endpoint("/cid_detail/<cid>", "cid_detail", self.cid_detail)
        self.add_endpoint("/map", "map", self.map)
        self.add_endpoint("/known-towers", "list_known_towers", self.list_known_towers)
        self.add_endpoint("/known-towers/add", "add_known_tower", self.add_known_tower)
        self.add_endpoint("/known-towers/delete/<id>", "del_known_tower", self.delete_known_tower)
        self.add_endpoint("/reclassify-towers", "reclassify_towers", self.reclassify_towers, methods=['POST'])
        self.add_endpoint("/gps", "get_gps", self.get_gps)
        self.add_endpoint("/logs", "get_logs", self.get_logs)

        app_thread = Thread(target=self.app.run, kwargs={'host':'0.0.0.0'})
        app_thread.start()

    def enodeb_sightings(self):
        trilat_pts = []
        enodebs = []
        known_towers = [kt.to_dict() for kt in self.watchdog.get_known_towers().all()]
        towers = self.watchdog.get_unique_enodebs()
        for t in towers:
            self.watchdog.get_max_column_by_enodeb
            sightings = self.watchdog.get_sightings_for_enodeb(t)

            trilat = self.watchdog.trilaterate_enodeb_location(sightings)
            enodebs.append({
                "trilat": list(trilat),
                "enodeb_id": t.enodeb_id,
                "plmn": t.plmn(),
                "closest_tower": self.watchdog.closest_known_tower(trilat[0], trilat[1]),
                "unique_cells": self.watchdog.get_cells_count_for_enodebid(t),
                "sightings": sightings.count(),
                "max_suspiciousness": self.watchdog.get_suspicious_percentage_by_enodeb(t),
                "first_seen": str(self.watchdog.get_min_column_by_enodeb(t, 'timestamp')),
                "last_seen": str(self.watchdog.get_max_column_by_enodeb(t, 'timestamp'))

            })
        return render_template('index.html', name=self.watchdog.project_name,
                                known_towers = json.dumps(known_towers),
                                key = 'enodeb_id',
                                enodebs=json.dumps(enodebs))

    def cell_sightings(self):
        trilat_pts = []
        cells = []
        known_towers = [kt.to_dict() for kt in self.watchdog.get_known_towers().all()]
        towers = self.watchdog.get_unique_cids()
        for t in towers:
            sightings = self.watchdog.get_sightings_for_cid(t)

            trilat = self.watchdog.trilaterate_enodeb_location(sightings)
            cells.append({
                "trilat": list(trilat),
                "cid": t.cid,
                "plmn": t.plmn(),
                "closest_tower": self.watchdog.closest_known_tower(trilat[0], trilat[1]),
                "sightings": sightings.count(),
                "max_suspiciousness": self.watchdog.get_suspicious_percentage_by_cid(t),
                "first_seen": str(self.watchdog.get_min_column_by_cid(t, 'timestamp')),
                "last_seen": str(self.watchdog.get_max_column_by_cid(t, 'timestamp'))

            })
        return render_template('by_cid.html', name=self.watchdog.project_name,
                                known_towers = json.dumps(known_towers),
                                key = 'cid',
                                enodebs=json.dumps(cells))

    def check_all(self):
        self.watchdog.check_all()
        return redirect('/')

    def detail(self, row_id):
        tower = self.watchdog.get_row_by_id(row_id)
        similar_towers = self.watchdog.get_towers_by_cid(tower.mnc, tower.mcc, tower.cid)
        trilat = self.watchdog.trilaterate_enodeb_location(similar_towers)
        centroid = self.watchdog.get_centroid(similar_towers)
        hidecols = [
            "raw_sib1",
            "id",
            "sector_id",
            "est_dist",
            "cid",
            "enodeb_id",
            "mcc",
            "mnc",
            "suspiciousness",
            "external_db",
            "tx_pwr"
        ]
        showcols = list(set(tower.params()) - set(hidecols))
        showcols.sort()

        return render_template('detail.html', name=self.watchdog.project_name,
                tower = tower,
                trilat = trilat,
                similar_towers = similar_towers,
                showcols = showcols,
                num_towers = similar_towers.count(),
                centroid = centroid)

    def enb_detail(self, enodeb_id):
        t = self.watchdog.get_enodeb(enodeb_id)
        known_towers = self.watchdog.get_known_towers().all()
        known_towers_json = [kt.to_dict() for kt in known_towers]
        sightings = self.watchdog.get_sightings_for_enodeb(t)
        sightings_json = json.dumps([s.to_dict() for s in sightings], default=str)
        trilat = self.watchdog.trilaterate_enodeb_location(sightings)
        hidecols = [
            "lat",
            "lon",
            "raw_sib1",
            "id",
            "mcc",
            "mnc",
            "tac",
            "enodeb_id",
        ]
        showcols = list(set(t.params()) - set(hidecols))
        showcols.sort()
        details = {
            "enodeb_id": t.enodeb_id,
            "max_suspiciousness": self.watchdog.get_max_column_by_enodeb(t, 'suspiciousness'),
            "closest_known_tower": self.watchdog.closest_known_tower(trilat[0], trilat[1]),
            "PLMN": t.plmn(),
            "TAC": t.tac,
            "min_power": self.watchdog.get_min_column_by_enodeb(t, 'tx_pwr'),
            "max_power": self.watchdog.get_max_column_by_enodeb(t, 'tx_pwr'),
            "unique_cells": self.watchdog.get_cells_count_for_enodebid(t),
            "number_of_sightings": sightings.count(),
            "first_seen": self.watchdog.get_min_column_by_enodeb(t, 'timestamp'),
            "last_seen": self.watchdog.get_max_column_by_enodeb(t, 'timestamp')

        }

        return render_template('enb_detail.html', name=self.watchdog.project_name,
                tower = t,
                trilat = trilat,
                type = "ENodeB",
                details = details,
                showcols = showcols,
                known_towers = known_towers_json,
                sightings = sightings_json)

    def cid_detail(self, cid):
        t = self.watchdog.get_cid(cid)
        known_towers = self.watchdog.get_known_towers().all()
        known_towers_json = [kt.to_dict() for kt in known_towers]
        sightings = self.watchdog.get_sightings_for_cid(t)
        sightings_json = json.dumps([s.to_dict() for s in sightings], default=str)
        trilat = self.watchdog.trilaterate_enodeb_location(sightings)
        hidecols = [
            "lat",
            "lon",
            "raw_sib1",
            "id",
            "cid",
        ]
        showcols = list(set(t.params()) - set(hidecols))
        showcols.sort()
        details = {
            "cell_id": t.cid,
            "enodeb_id": t.enodeb_id,
            "max_suspiciousness": self.watchdog.get_max_column_by_enodeb(t, 'suspiciousness'),
            "closest_known_tower": self.watchdog.closest_known_tower(trilat[0], trilat[1]),
            "PLMN": t.plmn(),
            "TAC": t.tac,
            "min_power": self.watchdog.get_min_column_by_cid(t, 'tx_pwr'),
            "max_power": self.watchdog.get_max_column_by_cid(t, 'tx_pwr'),
            "number_of_sightings": sightings.count(),
            "first_seen": self.watchdog.get_min_column_by_cid(t, 'timestamp'),
            "last_seen": self.watchdog.get_max_column_by_cid(t, 'timestamp')

        }

        return render_template('enb_detail.html', name=self.watchdog.project_name,
                tower = t,
                trilat = trilat,
                type = "Cell ID",
                details = details,
                showcols = showcols,
                known_towers = known_towers_json,
                sightings = sightings_json)

    def list_known_towers(self):
        known_towers = self.watchdog.get_known_towers().all()
        known_towers_json = [kt.to_dict() for kt in known_towers]
        flash = request.args.get('flash')
        return render_template('add_known_tower.html', name=self.watchdog.project_name,
                flash = flash,
                known_towers = known_towers_json)

    def add_known_tower(self):
        lat = request.args.get('lat')
        lon = request.args.get('lon')
        desc = request.args.get('desc')

        kt = self.watchdog.add_known_tower(lat, lon, desc)
        return redirect(url_for('list_known_towers', flash=f'Added Tower: {kt}'))

    def delete_known_tower(self, id):
        self.watchdog.delete_known_tower(id)
        return redirect(url_for('list_known_towers', flash=f'Deleted Tower {id}'))

    def reclassify_towers(self):
        ids = json.loads(request.form.get('ids'))
        classification = request.form.get('classification')
        for id in ids:
            self.logger.debug(f'reclassifying {id} as {classification}')
            self.watchdog.reclassify_tower(int(id), classification, True)
        self.watchdog.db_session.commit()
        return redirect(request.referrer)

    def get_gps(self):
        coords = self.watchdog.get_gps()._asdict()
        return jsonify(coords)

    def get_logs(self):
        logdir = '/var/log/crocodilehunter.log'
        if not os.path.isfile(logdir):
            return render_template('logs.html', name=self.watchdog.project_name,
                                   logs="no logfile exists.")


        with open(logdir, 'r') as f:
            log = f.read()
            return render_template('logs.html', name=self.watchdog.project_name,
                                   logs=log)


    def map(self):
        # trilat_points = [(lat, long, enodeb_id), ...]
        trilat_pts = self.watchdog.get_trilateration_points()
        known_towers = [kt.to_dict() for kt in self.watchdog.get_known_towers().all()]
        if len(trilat_pts) == 0:
            return("nothing to see yet")

        return render_template('map.html', name=self.watchdog.project_name,
                               key = 'enodeb_id',
                               trilat_pts = json.dumps(trilat_pts),
                               known_towers = known_towers)


    def add_endpoint(self, endpoint=None, endpoint_name=None, handler=None, **options):
        self.app.add_url_rule(endpoint, endpoint_name, EndpointAction(handler), **options)


class EndpointAction(object):

    def __init__(self, action):
        self.action = action

    def __call__(self, *args, **kwargs):
        action = self.action(*args, **kwargs)
        if isinstance(action, wrappers.Response):
            return action
        else:
            return Response(action, status=200, headers={})

if __name__ == "__main__":
    from watchdog import Watchdog
    import sys
    import os
    import coloredlogs, verboselogs
    import configparser

    logger = verboselogs.VerboseLogger("crocodile-hunter")
    fmt=f"\b * %(asctime)s crocodile-hunter - %(levelname)s %(message)s"
    coloredlogs.install(level="DEBUG", fmt=fmt, datefmt='%H:%M:%S')

    if not 'CH_PROJ' in os.environ:
        print("Please set the CH_PROJ environment variable")
        sys.exit()
    class Args:
        disable_gps = True
        disable_wigle = False
        debug = False
        project_name = os.environ['CH_PROJ']
        logger = logger
        config_fp = 'config.ini'
        config = configparser.ConfigParser(inline_comment_prefixes=('#', ';'))
        config.read(config_fp)

    w = Watchdog(Args)
    webui = Webui(w)
    SQL_PATH = f"mysql://root:toor@localhost:3306"
    DB_PATH = f"{SQL_PATH}/{Args.project_name}"
    webui.app.config['SQLALCHEMY_DATABASE_URI'] = DB_PATH

    if 'db' in sys.argv:
        webui.manager.run()
    else:
        webui.start_daemon()
