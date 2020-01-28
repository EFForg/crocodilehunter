#!/usr/bin/env python3
from flask import Flask, Response, render_template, redirect, url_for, request
from threading import Thread
from werkzeug import wrappers
import os
import json

class Webui:
    def __init__(self, watchdog):
        os.environ['WERKZEUG_RUN_MAIN'] = 'true'
        self.app = Flask(__name__)
        self.watchdog = watchdog
        self.config = self.watchdog.config
        self.logger = self.watchdog.logger
        self.app.logger.addHandler(self.logger)

    def add_endpoint(self, endpoint=None, endpoint_name=None, handler=None, **options):
        self.app.add_url_rule(endpoint, endpoint_name, EndpointAction(handler), **options)

    def start_daemon(self):
        self.logger.info(f"Starting Crocodile Hunter API Server")

        #Add each endpoint manually
        self.add_endpoint("/", "index", self.index)
        self.add_endpoint("/towers/add", "add_towers", self.add_towers, methods=['POST'])
        self.add_endpoint("/api/statistics", "api_statistics", self.get_statistics)
        self.add_endpoint("/api/signup", "api_signup", self.api_signup, methods=['POST'])

        app_thread = Thread(target=self.app.run, kwargs={'host': self.config['api']['host'],
                                                         'port': self.config['api']['port']
                                                         })
        app_thread.start()

    # Begin Routes

    def index(self):
        return render_template('api/index.html')

    def add_towers(self):
        return 'okay'

    def get_statistics(self):
        return {
            "users": 0,
            "towers": 100,
        }

    def api_signup(self):
        return 'okay'

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

    logger = verboselogs.VerboseLogger("CH-API-server")
    fmt=f"\b * %(asctime)s CH-API-server - %(levelname)s %(message)s"
    coloredlogs.install(level="DEBUG", fmt=fmt, datefmt='%H:%M:%S')

    class Args:
        disable_gps = True
        disable_wigle = True
        debug = False
        project_name = 'API'
        logger = logger
        config = configparser.ConfigParser()
        config.read('config.ini')

    w = Watchdog(Args)
    webui = Webui(w)
    DB_PATH = f"{w.config['general']['mysql_path']}/{Args.project_name}"
    webui.app.config['SQLALCHEMY_DATABASE_URI'] = DB_PATH

    webui.start_daemon()
