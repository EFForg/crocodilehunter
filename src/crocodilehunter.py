#!/usr/bin/env python3
"""
Crocodile Hunter
Find stingrays in the wild. Hunt them down. Get revenge for Steve Irwin

TODO Create logging subsystem
"""
import argparse
import configparser
import itertools
import os
import signal
import subprocess
import sys

from subprocess import Popen
from time import sleep, strftime
from threading import Thread
import coloredlogs, verboselogs

from watchdog import Watchdog
from webui import Webui
from nbstreamreader import NonBlockingStreamReader as NBSR

# Global flag to exit forever running threads
EXIT = False

class CrocodileHunter():
    def __init__(self, args):
        """
        1. Bootstrap dependencies
            a. test gps
            b. check for SDR
        2. Start srsue with config file
            a. watch srsue for crashes and restart
        3. Start watchdog daemon
        4. Start web daemon
        """
        self.threads = []
        self.subprocs = []
        self.project_name = args.project_name
        self.debug = args.debug
        self.disable_gps = args.disable_gps
        self.disable_wigle = args.disable_wigle
        self.config_fp = 'config.ini'
        self.config = args.config = configparser.ConfigParser()
        self.config.read(self.config_fp)
        self.earfcn_list = []
        signal.signal(signal.SIGINT, self.signal_handler)

        if self.project_name not in self.config:
            self.config[self.project_name] = {}

        # Set up logging
        self.logger = args.logger = verboselogs.VerboseLogger("crocodile-hunter")
        fmt=f"\b * %(asctime)s {self.project_name} - %(levelname)s %(message)s"
        if(self.debug):
            log_level = "DEBUG"
        else:
            log_level = "VERBOSE"
        coloredlogs.install(level=log_level, fmt=fmt, datefmt='%H:%M:%S')

        self.watchdog = Watchdog(args)

    def start(self):
        if not self.debug:
            spn = Thread(target=self.show_spinner)
            spn.start()
            self.threads.append(spn)

        # Bootstrap srsUE dependencies
        if self.disable_gps:
            args = "./bootstrap.sh -g"
        else:
            args = "./bootstrap.sh"

        proc = subprocess.Popen(args, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

        for stdout_line in iter(proc.stdout.readline, b""):
            self.logger.info(stdout_line.decode("utf-8").rstrip())
        proc.stdout.close()
        return_code = proc.wait()

        if return_code:
            self.logger.critical("Bootstrapping failed")
            self.cleanup(True)

        #Start watchdog dæmon
        self.watchdog.start_daemon()

        #Start web ui dæmon
        webui = Webui(self.watchdog)
        webui.start_daemon()

        # Monitor and restart srsUE if it crashes
        self.update_earfcn_list()
        proc = self.start_srslte()
        self.subprocs.append(proc)
        monitor = Thread(target=self.monitor_srslte, args=(proc,))
        monitor.start()
        self.threads.append(monitor)

    def signal_handler(self, sig, frame):
        """ Exit gracefully on SIGINT """
        self.logger.critical("You pressed Ctrl+C!")
        self.cleanup()

    def update_earfcn_list(self):
        """ call to wigle to update the local EARFCN list or use a statically configured list """
        if 'earfcns' in self.config[self.project_name]:
            self.earfcn_list = map(int, self.config[self.project_name]['earfcns'].split(','))
        else:
            if self.disable_wigle:
                self.logger.critical("Wigle is disabled so we cant fetch an EARFCN list, either run again with wigle enabled or copy an EARFCN list from another project in config.ini")
                self.cleanup()
            self.logger.warning("Getting earcn list for the first time, this might take a while")
            gps = self.watchdog.get_gps()
            self.earfcn_list = self.watchdog.wigle.earfcn_search(gps.lat, gps.lon, 0.2)
            self.config[self.project_name]['earfcns'] = ",".join(map(str, self.earfcn_list))
        self.logger.notice(f"Using earfcn list {self.config[self.project_name]['earfcns']}")

    def start_srslte(self):
        # TODO Intelligently handle srsUE output (e.g. press a key to view output or something, maybe in another window)
        """ Start srsUE """
        earfcns = ",".join(map(str, self.earfcn_list))
        self.logger.info(f"EARFCNS: {earfcns}")
        self.logger.info(f"Running srsUE")
        proc = Popen(["./srsLTE/build/lib/examples/cell_measurement", "-z", earfcns], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        self.logger.success(f"srsUE started with pid {proc.pid}")
        return proc

    def monitor_srslte(self, proc):
        """ Monitor for crashes and restart srsLTE"""
        # TODO
        global EXIT
        out = []
        sleep(1)
        nbsr = NBSR(proc.stdout)
        line = ''
        while not EXIT:
            line = nbsr.readline(int(self.config["general"]["crash_timeout"]))
            if line is not None:
                self.logger.debug(line.decode("ascii").rstrip())
            out.append(line)

            if proc.poll() is not None or line is None:
                self.logger.warning(f"srsUE has exited unexpectedly")
                try:
                    self.logger.warning(f"It's dying words were: {out[-2].decode('ascii').rstrip()}")
                except IndexError as e:
                    pass
                proc.kill()
                self.update_earfcn_list()
                proc = self.start_srslte()
                self.monitor_srslte(proc)

    def show_spinner(self):
        """ show a spinning cursor """
        global EXIT
        spinner = itertools.cycle(['-', '/', '|', '\\'])
        while not EXIT:
            sys.stdout.write(next(spinner))   # write the next character
            sys.stdout.flush()                # flush stdout buffer (actual character display)
            sys.stdout.write('\b')            # erase the last written char
            sleep(0.1)

    def cleanup(self, error=False):
        """ Gracefully exit when program is quit """
        global EXIT

        self.logger.error(f"Exiting...")

        with open(self.config_fp, 'w') as cf:
            self.config.write(cf)

        EXIT = True
        for thread in self.threads:
            thread.join()
        for proc in self.subprocs:
            proc.kill()
        subprocess.run("killall gpsd", shell=True, stderr=subprocess.DEVNULL)
        self.watchdog.shutdown()
        self.logger.success(f"See you space cowboy...")
        os._exit(int(error))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Hunt stingrays. Get revenge for Steve.")
    parser.add_argument('-p', '--project-name', dest='project_name', default='default', help="specify the project's name. defaults to 'default'", action='store')
    parser.add_argument('-d', '--debug', dest='debug', help="print debug messages", action='store_true',)
    parser.add_argument('-g', '--disable-gps', dest='disable_gps', help="disable GPS connection and return a default coordinate", action='store_true')
    parser.add_argument('-w', '--disable-wigle', dest='disable_wigle', help='disable Wigle API access', action='store_true')


    # Clear screen
    print(chr(27)+'[2j')
    print('\033c')
    print('\x1bc')

    print("\033[0;31m") #Red
    print(" ▄████▄   ██▀███   ▒█████   ▄████▄   ▒█████  ▓█████▄  ██▓ ██▓    ▓█████     ██░ ██  █    ██  ███▄    █ ▄▄▄█████▓▓█████  ██▀███  ")
    print("▒██▀ ▀█  ▓██ ▒ ██▒▒██▒  ██▒▒██▀ ▀█  ▒██▒  ██▒▒██▀ ██▌▓██▒▓██▒    ▓█   ▀    ▓██░ ██▒ ██  ▓██▒ ██ ▀█   █ ▓  ██▒ ▓▒▓█   ▀ ▓██ ▒ ██▒")
    print("▒▓█    ▄ ▓██ ░▄█ ▒▒██░  ██▒▒▓█    ▄ ▒██░  ██▒░██   █▌▒██▒▒██░    ▒███      ▒██▀▀██░▓██  ▒██░▓██  ▀█ ██▒▒ ▓██░ ▒░▒███   ▓██ ░▄█ ▒")
    print("▒▓▓▄ ▄██▒▒██▀▀█▄  ▒██   ██░▒▓▓▄ ▄██▒▒██   ██░░▓█▄   ▌░██░▒██░    ▒▓█  ▄    ░▓█ ░██ ▓▓█  ░██░▓██▒  ▐▌██▒░ ▓██▓ ░ ▒▓█  ▄ ▒██▀▀█▄  ")
    print("▒ ▓███▀ ░░██▓ ▒██▒░ ████▓▒░▒ ▓███▀ ░░ ████▓▒░░▒████▓ ░██░░██████▒░▒████▒   ░▓█▒░██▓▒▒█████▓ ▒██░   ▓██░  ▒██▒ ░ ░▒████▒░██▓ ▒██▒")
    print("░ ░▒ ▒  ░░ ▒▓ ░▒▓░░ ▒░▒░▒░ ░ ░▒ ▒  ░░ ▒░▒░▒░  ▒▒▓  ▒ ░▓  ░ ▒░▓  ░░░ ▒░ ░    ▒ ░░▒░▒░▒▓▒ ▒ ▒ ░ ▒░   ▒ ▒   ▒ ░░   ░░ ▒░ ░░ ▒▓ ░▒▓░")
    print("  ░  ▒     ░▒ ░ ▒░  ░ ▒ ▒░   ░  ▒     ░ ▒ ▒░  ░ ▒  ▒  ▒ ░░ ░ ▒  ░ ░ ░  ░    ▒ ░▒░ ░░░▒░ ░ ░ ░ ░░   ░ ▒░    ░     ░ ░  ░  ░▒ ░ ▒░")
    print("░          ░░   ░ ░ ░ ░ ▒  ░        ░ ░ ░ ▒   ░ ░  ░  ▒ ░  ░ ░      ░       ░  ░░ ░ ░░░ ░ ░    ░   ░ ░   ░         ░     ░░   ░ ")
    print("░ ░         ░         ░ ░  ░ ░          ░ ░     ░     ░      ░  ░   ░  ░    ░  ░  ░   ░              ░             ░  ░   ░     ")
    print("\033[0m") # No Color

    args = parser.parse_args()
    crocodile_hunter = CrocodileHunter(args)
    crocodile_hunter.start()
