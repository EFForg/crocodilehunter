#!/usr/bin/env python3

from database import init_db, ApiTower, ApiUser
from datetime import datetime
import uuid

class ApiController():

    def __init__(self, args):
        self.db_name = args.db_name
        self.db_session = init_db(self.db_name)
        self.logger = args.logger
        self.config = args.config

    def user_tower_count(self, api_key):
        if ApiTower.query.filter(ApiTower.api_key == api_key).count():
            tower = ApiTower.query.filter(ApiTower.api_key == api_key).order_by(ApiTower.ext_id.desc())[0]
            return tower.ext_id
        else:
            return 0

    def all_tower_count(self):
        return ApiTower.query.count()

    def user_count(self):
        return ApiUser.query.count()

    def add_towers(self, api_key, towers):
        old_tc = self.all_tower_count()
        for tower in towers:
            tower["ext_id"] = tower["id"]
            tower.pop("id")
            tower["api_key"] = api_key
            tower["uploaded"] = datetime.now()
            t = ApiTower(**tower)
            self.db_session.add(t)
            self.db_session.commit()
            self.db_session.close()
        delta_tc = self.all_tower_count() - old_tc

        return (delta_tc, self.user_tower_count(api_key))


    def add_user(self, name, contact, description):
        key = uuid.uuid4().hex
        user = ApiUser(
            name = name,
            contact = contact,
            description = description,
            api_key = key
        )

        self.db_session.add(user)
        self.db_session.commit()
        self.db_session.close()
        return user

    def is_key_authorized(self, api_key):
        return ApiUser.query.filter(ApiUser.api_key == api_key).count()
