from watchdog import Watchdog
import sys
import os
import coloredlogs, verboselogs
import configparser
import requests
import json

class ApiClient:
    def __init__(self, watchdog):
        self.watchdog = watchdog
        self.logger = self.watchdog.logger
        self.config = self.watchdog.config

        try:
            self.api_host = self.config["api"]["host"]
            self.api_port = self.config["api"]["port"]
        except KeyError:
            self.logger.error("Please define an API host and port in your config.ini")
            sys.exit(1)

    def signup(self):
        if self.config.has_option('api', 'api_key') \
                and self.config['api']['api_key']:
            self.logger.success(f"Your API key is {self.config['api']['api_key']}")
            return
        packet = {}
        packet["name"] = input("Enter Your Name: ")
        packet["contact"] = input("Enter Your Email: ")
        packet["description"] = input("Describe your project: ")

        self.logger.info(f"signing up with {packet}")
        r = requests.post(self._make_api_url('signup'), json=packet)
        resp = r.json()
        self.logger.info(f"response:\n{resp}")
        if resp['error']:
            self.logger.error(f"The API server said: {resp['error']}")
            sys.exit(1)
        self.config.set('api', 'api_key', str(resp['response']['api_key']))
        with open('config.ini', 'w') as configfile:
            self.config.write(configfile)
        self.logger.success(f"API Key set to {self.config['api']['api_key']}")

    def statistics(self):
        self.check_api_key()
        j = {
            'api_key': self.api_key,
            'project': self.watchdog.project_name
        }
        r = requests.post(self._make_api_url("statistics"), json=j)
        resp = r.json()
        if r.ok:
            self.logger.info(f"Success: {resp}")
            return resp
        else:
            self.logger.error(f"There was an error in the requst: {r.status_code} {resp['error']}")
            return None

    def add_towers(self):
        self.check_api_key()
        starting_id = self.statistics()['response']['user_last_tower']
        self.logger.info(f"adding towers starting after {starting_id}")
        towers = self.watchdog.get_all_towers_after(starting_id)
        towers = [t.to_dict() for t in self.watchdog.get_all_towers_after(starting_id)]
        j = {
            'api_key': self.api_key,
            'project': self.watchdog.project_name,
            'towers': towers,
        }
        #self.logger.debug(j)
        r = requests.post(self._make_api_url("add-towers"), json=j)
        resp = r.json()
        if r.ok:
            self.logger.info(f"Success: {resp}")
            sys.exit(0)
        else:
            self.logger.error(f"There was an error in the requst: {r.status_code} {resp['error']}")
            sys.exit(1)


    def check_api_key(self):
        if not self.config.has_option('api', 'api_key'):
            print(f"please run `{sys.argv[0]} signup` first to generate an API key")
            sys.exit(1)
        self.api_key = self.config['api']['api_key']

    def _make_api_url(self, fragment):
        return f"http://{self.api_host}:{self.api_port}/api/{fragment}"

if __name__ == "__main__":
    from watchdog import Watchdog
    import sys
    import os
    import coloredlogs, verboselogs
    import configparser
    import argparse

    logger = verboselogs.VerboseLogger("crocodile-hunter")
    fmt=f"\b * %(asctime)s crocodile-hunter - %(levelname)s %(message)s"
    coloredlogs.install(level="DEBUG", fmt=fmt, datefmt='%H:%M:%S')

    parser = argparse.ArgumentParser(description="Hunt stingrays. Get revenge for Steve.")
    parser.add_argument('-p', '--project-name', dest='project_name', default=None,
                        help="specify the project's name. defaults to 'default'", action='store')
    subparsers = parser.add_subparsers(dest="command", help="command")
    subparsers.add_parser('signup', help="sign up for an API key")
    subparsers.add_parser('add_towers', help="submit new towers to the API Server")
    subparsers.add_parser('statistics', help="get some statisitcs from teh API server")
    args = parser.parse_args()

    class Args:
        disable_gps = True
        disable_wigle = False
        debug = False
        project_name = args.project_name
        logger = logger
        config_fp = 'config.ini'
        config = configparser.ConfigParser(inline_comment_prefixes=('#', ';'))
        config.read(config_fp)

    if not Args.project_name:
        args.project_name = Args.config['general']['default_project']

    w = Watchdog(Args)
    apic = ApiClient(w)

    if args.command is None:
        parser.print_help(sys.stderr)
        sys.exit(1)
    else:
        getattr(apic, args.command)()

