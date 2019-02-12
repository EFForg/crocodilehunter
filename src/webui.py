#!/usr/bin/env python3
from flask import Flask, Response, render_template, redirect, url_for
from threading import Thread
from werkzeug import wrappers

class Webui:
    def __init__(self, watchdog):
        self.app = Flask(__name__)
        self.watchdog = watchdog

    def start_daemon(self):
        print(f"\b* Starting WebUI")

        #Add each endpoint manually
        self.add_endpoint("/", "index", self.index)
        self.add_endpoint("/check_all", "checkall", self.check_all)
        self.add_endpoint("/detail/<row_id>", "detail", self.detail)

        app_thread = Thread(target=self.app.run, kwargs={'host':'0.0.0.0'})
        app_thread.start()

    def index(self):
        last_ten = self.watchdog.last_ten()
        for t in last_ten:
            setattr(t[1], 'timestamp', t[2])
        return render_template('index.html', name=self.watchdog.project_name,
                               towers=self.watchdog.get_all_by_suspicioussnes(),
                               last_ten=last_ten)
    def check_all(self):
        self.watchdog.check_all()
        return redirect('/')

    def detail(self, row_id):
        tower = self.watchdog.get_row_by_id(row_id)
        similar_towers = self.watchdog.get_towers_by_cid(tower.cid)
        return render_template('detail.html', tower = tower,
                similar_towers = similar_towers)

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
