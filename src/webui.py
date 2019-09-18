#!/usr/bin/env python3
from flask import Flask, Response, render_template, redirect, url_for
from flask_script import Manager
from flask_migrate import Migrate, MigrateCommand
from threading import Thread
from werkzeug import wrappers
import numpy
from database import Base
import os

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
        self.add_endpoint("/", "index", self.index)
        self.add_endpoint("/check_all", "checkall", self.check_all)
        self.add_endpoint("/detail/<row_id>", "detail", self.detail)
        self.add_endpoint("/map", "map", self.map)

        app_thread = Thread(target=self.app.run, kwargs={'host':'0.0.0.0'})
        app_thread.start()

    def index(self):
        last_ten = self.watchdog.get_unique_enodebs()
        return render_template('index.html', name=self.watchdog.project_name,
                               towers=self.watchdog.get_all_by_suspicioussnes(),
                               last_ten=last_ten)
    def check_all(self):
        self.watchdog.check_all()
        return redirect('/')

    def detail(self, row_id):
        tower = self.watchdog.get_row_by_id(row_id)
        similar_towers = self.watchdog.get_similar_towers(tower)
        trilat = self.watchdog.trilaterate_enodeb_location(similar_towers)
        centroid = self.watchdog.get_centroid(similar_towers)

        return render_template('detail.html', name=self.watchdog.project_name,
                tower = tower,
                trilat = trilat,
                similar_towers = similar_towers,
                num_towers = similar_towers.count(),
                centroid = centroid)
    def map(self):
        # trilat_points = [(lat, long, enodeb_id), ...]
        trilat_pts = self.watchdog.get_trilateration_points()
        known_towers = self.watchdog.get_known_towers()
        if len(trilat_pts) == 0:
            return("nothing to see yet")

        return render_template('map.html', name=self.watchdog.project_name,
                               trilat_pts = trilat_pts,
                               known_towers = known_towers)


    def add_endpoint(self, endpoint=None, endpoint_name=None, handler=None):
        self.app.add_url_rule(endpoint, endpoint_name, EndpointAction(handler))


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

    if os.environ['CH_PROJ'] is None:
        print("Please set the CH_PROJ environment variable")
        sys.exit()
    class Args:
        disable_gps = False
        disable_wigle = False
        debug = False
        project_name = os.environ['CH_PROJ']
        logger = logger
        config = configparser.ConfigParser()
        config.read('config.ini')

    w = Watchdog(Args)
    webui = Webui(w)
    SQL_PATH = f"mysql://root:toor@localhost:3306"
    DB_PATH = f"{SQL_PATH}/{Args.project_name}"
    webui.app.config['SQLALCHEMY_DATABASE_URI'] = DB_PATH

    if 'db' in sys.argv:
        webui.manager.run()
    else:
        webui.start_daemon()
