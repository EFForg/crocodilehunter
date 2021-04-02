#!/usr/bin/env python3

from database import init_db, Tower, ApiUser
from datetime import datetime
import uuid

class ApiController():

    def __init__(self, args):
        self.db_name = args.db_name
        self.logger = args.logger
        self.config = args.config


    def user_tower_count(self, project, api_key):
        self.db_session = init_db(project)
        if Tower.query.filter(Tower.api_key == api_key).count():
            tower = Tower.query.filter(Tower.api_key == api_key).order_by(Tower.ext_id.desc())[0]
            last_id = tower.ext_id
        else:
            last_id =  0
        self.db_session.close()
        return last_id

    def all_tower_count(self, project):
        self.db_session = init_db(project)
        c = Tower.query.count()
        self.db_session.close()

    def user_count(self):
        self.db_session = init_db(self.db_name)
        user_count =  ApiUser.query.count()
        self.db_session.close()
        return user_count

    def add_towers(self, api_key, project, towers):
        self.db_session = init_db(project)
        old_tc = self.user_tower_count(project, api_key)
        for tower in towers:
            tower["ext_id"] = tower["id"]
            tower.pop("id")
            tower["api_key"] = api_key
            tower["uploaded"] = datetime.now()
            t = Tower(**tower)
            self.db_session.add(t)
            self.db_session.commit()
        tower_count = self.user_tower_count(project, api_key)
        delta_tc = tower_count - old_tc

        self.db_session.close()
        return (delta_tc, tower_count)


    def add_user(self, name, contact, description):
        self.db_session = init_db(self.db_name)
        self.db_session.expire_on_commit = False
        key = uuid.uuid4().hex
        user = ApiUser(
            name = name,
            contact = contact,
            description = description,
            api_key = key
        )

        self.db_session.add(user)
        self.db_session.commit()
        utpl = (user.name, user.contact, user.description, user.api_key)
        self.db_session.close()
        return utpl

    def is_key_authorized(self, api_key):
        self.db_session = init_db(self.db_name)
        auth =  ApiUser.query.filter(ApiUser.api_key == api_key).count()
        self.db_session.close()
        return auth
