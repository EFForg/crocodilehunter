#!/usr/bin/env python3
"""
Crocodile Hunter
Find stingrays in the wild. Hunt them down. Get revenge for Steve Irwin

TODO Create logging subsystem
"""
import argparse
import itertools
import os
import signal
import subprocess
import sys

from subprocess import Popen
from time import sleep, strftime
from threading import Thread
import coloredlogs, logging

from watchdog import Watchdog
from webui import Webui
from nbstreamreader import NonBlockingStreamReader as NBSR

# Global flag to exit forever running threads
EXIT = False
CRASH_TIMEOUT = 25

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
        self.scan_earfcns = args.scan_earfcns
        signal.signal(signal.SIGINT, self.signal_handler)

        # Set up logging
        self.logger = args.logger = logging.getLogger("crocodile-hunter")
        fmt='\b * %(asctime)s - %(levelname)s %(message)s'
        if(self.debug):
            log_level = "DEBUG"
        else:
            log_level = "INFO"
        coloredlogs.install(level=log_level, fmt=fmt, datefmt='%H:%M:%S')

        # Create project folder if necessary
        self.project_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../data", self.project_name)
        if not os.path.exists(self.project_path):
            self.logger.info(f"Creating new project directory: {self.project_path}")
            os.mkdir(self.project_path)


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
        if self.scan_earfcns:
            self.earfcn_list = map(int, self.scan_earfcns.split(','))
            return
        gps = self.watchdog.get_gps()
        self.earfcn_list = self.watchdog.wigle.earfcn_search(gps.lat, gps.lon, 0.2)

    def start_srslte(self):
        # TODO Intelligently handle srsUE output (e.g. press a key to view output or something, maybe in another window)
        """ Start srsUE """
        earfcns = ",".join(map(str, self.earfcn_list))
        self.logger.debug(f"EARFCNS {earfcns}")
        self.logger.info(f"Running srsUE")
        proc = Popen(["./srsLTE/build/lib/examples/cell_measurement", "-z", earfcns], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        self.logger.info(f"srsUE started with pid {proc.pid}")
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
            line = nbsr.readline(CRASH_TIMEOUT)
            if self.debug and (line is not None):
                self.logger.debug(line.decode("ascii").rstrip())
            out.append(line)

            if proc.poll() is not None or line is None:
                self.logger.warning(f"srsUE has exited unexpectedly")
                try:
                    self.logger.warning(f"It's dying words were: {out[-2].decode('ascii').rstrip()}")
                except IndexError as e:
                    pass
                proc.kill()
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
        self.logger.info(f"Exiting...")
        global EXIT
        EXIT = True
        for thread in self.threads:
            thread.join()
        for proc in self.subprocs:
            proc.kill()
        subprocess.run("killall gpsd", shell=True, stderr=subprocess.DEVNULL)
        self.watchdog.shutdown()
        self.logger.info(f"See you space cowboy...")
        os._exit(int(error))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Hunt stingrays. Get revenge for Steve.")
    parser.add_argument('-p', '--project-name', dest='project_name', default='default', help="specify the project's name. defaults to 'default'", action='store')
    parser.add_argument('-d', '--debug', dest='debug', help="print debug messages", action='store_true',)
    parser.add_argument('-g', '--disable-gps', dest='disable_gps', help="disable GPS connection and return a default coordinate", action='store_true')
    parser.add_argument('-w', '--disable-wigle', dest='disable_wigle', help='disable Wigle API access', action='store_true')
    parser.add_argument('--scan-earfcns', dest='scan_earfcns', help='comma seperated list of earfcns to scan, will disable automatic earfcn detection', action='store')


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
