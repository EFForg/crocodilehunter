#!/usr/bin/env python3
from flask import Flask, Response, render_template, redirect, url_for
from threading import Thread

class Webui:
    def __init__(self, watchdog):
        self.app = Flask(__name__)
        self.watchdog = watchdog

    def start_daemon(self):
        print(f"\b* Starting WebUI")

        #Add each endpoint manually
        self.add_endpoint("/", "index", self.index)
        self.add_endpoint("/check_all", "checkall", self.calculate_all)
        self.add_endpoint("/detail/<row_id>", "detail", self.detail)

        app_thread = Thread(target=self.app.run)
        app_thread.start()

    def index(self):
        return render_template('index.html', name=self.watchdog.project_name,
                               towers=self.watchdog.get_all_by_suspicioussnes())
    def calculate_all(self):
        self.watchdog.calculate_all()
        return redirect(url_for('index'))

    def detail(self, row_id):
        tower = self.watchdog.get_row_by_id(row_id)
        return render_template('detail.html', tower = tower)

    def add_endpoint(self, endpoint=None, endpoint_name=None, handler=None):
        self.app.add_url_rule(endpoint, endpoint_name, EndpointAction(handler))


class EndpointAction(object):

    def __init__(self, action):
        self.action = action

    def __call__(self, *args, **kwargs):
        action = self.action(*args, **kwargs)
        response = Response(action, status=200, headers={})
        return response
