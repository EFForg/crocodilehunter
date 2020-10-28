#!/usr/bin/env python3
from flask import Flask, Response, render_template, redirect, url_for, request, jsonify, abort
from threading import Thread
from werkzeug import wrappers
import os

class ApiView:
    def __init__(self, api_controller):
        os.environ['WERKZEUG_RUN_MAIN'] = 'true'
        self.app = Flask(__name__)
        self.api_controller = api_controller
        self.config = self.api_controller.config
        self.logger = self.api_controller.logger
        self.app.logger.addHandler(self.logger)

    def add_endpoint(self, endpoint=None, endpoint_name=None, handler=None, **options):
        self.app.add_url_rule(endpoint, endpoint_name, EndpointAction(handler), **options)

    def start_daemon(self):
        self.logger.info(f"Starting Crocodile Hunter API Server")

        #Add each endpoint manually
        self.add_endpoint("/", "index", self.index)
        self.add_endpoint("/api/add-towers", "add_towers", self.add_towers, methods=['POST'])
        self.add_endpoint("/api/statistics", "api_statistics", self.get_statistics, methods=['POST'])
        self.add_endpoint("/api/signup", "api_signup", self.api_signup, methods=['POST'])
        self.app.errorhandler(400)(self.err_bad_req)
        self.app.errorhandler(403)(self.err_forbidden)

        app_thread = Thread(target=self.app.run, kwargs={'host': self.config['api']['host'],
                                                         'port': self.config['api']['port']
                                                         })
        app_thread.start()

    # Begin Routes

    def err_bad_req(self, e):
        return jsonify({
            "error": "Malformed API Request",
            "response": {}
        }), 400

    def err_forbidden(self, e):
        return jsonify({
            "error": f"That key is not authorized. Please contact {self.config['api']['contact']}",
            "response": {}
        }), 403


    def index(self):
        return render_template('api/index.html',
                                contact=self.config['api']['contact'])

    def add_towers(self):
        if not (request.json and ('api_key' in request.json)):
            abort(400)

        api_key = request.json['api_key']
        towers = request.json['towers']
        self.check_key_auth(api_key)

        (towers_added, last_record) = self.api_controller.add_towers(api_key, towers)
        return jsonify({
            "error": None,
            "response": {
                "towers_sent": len(towers),
                "towers_added": towers_added,
                "last_record": last_record
            }
        })

    def get_statistics(self):
        if not (request.json and ('api_key' in request.json)):
            abort(400)

        api_key = request.json['api_key']
        self.check_key_auth(api_key)


        tower_count = self.api_controller.all_tower_count()
        user_tower_count = self.api_controller.user_tower_count(api_key)
        return jsonify({
            "error": None,
            "response": {
                "user_last_tower": user_tower_count,
                "total_towers": tower_count,
            }
        })

    def api_signup(self):
        if not request.json:
            abort(400)
        signup = request.json
        if not set(('name', 'contact', 'description')) <= signup.keys():
            logger.error(f'malformed signup {signup}')
            abort(400)

        user = self.api_controller.add_user(signup['name'], signup['contact'], signup['description'])
        self.logger.success(f'add user {user}')

        return jsonify({
            "error": None,
            "response": {
                "api_key": user.api_key,
                "name": user.name,
                "contact": user.contact,
                "description": user.description,
            }
        })

    def check_key_auth(self, api_key):
        if not self.api_controller.is_key_authorized(api_key):
            abort(403)


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
    from api_controller import ApiController
    import sys
    import os
    import coloredlogs, verboselogs
    import configparser

    logger = verboselogs.VerboseLogger("CH-API-server")
    fmt=f"\b * %(asctime)s CH-API-server - %(levelname)s %(message)s"
    coloredlogs.install(level="DEBUG", fmt=fmt, datefmt='%H:%M:%S')

    class Args:
        db_name = "crocodilehunter_api"
        logger = logger
        config_fp = 'config.ini'
        config = configparser.ConfigParser(inline_comment_prefixes=('#', ';'))
        config.read(config_fp)

    controller = ApiController(Args)
    apiView = ApiView(controller)

    apiView.app.config['SQLALCHEMY_DATABASE_URI'] = f"{Args.config['general']['mysql_path']}/{Args.db_name}"

    apiView.start_daemon()
