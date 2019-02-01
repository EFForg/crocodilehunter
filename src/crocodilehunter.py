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
from time import sleep
from threading import Thread

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
        signal.signal(signal.SIGINT, self.signal_handler)
        self.watchdog = Watchdog(args)

        # Create project folder if necessary
        self.project_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../data", self.project_name)
        if not os.path.exists(self.project_path):
            print("Creating new project directory: " + self.project_path)
            os.mkdir(self.project_path)

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
        try:
            subprocess.run(args, shell=True, check=True)
        except subprocess.CalledProcessError:
            self.cleanup(True)

        #Start watchdog dæmon
        self.watchdog.start_daemon()

        #Start web ui dæmon
        Webui.start_daemon()

        # Monitor and restart srsUE if it crashes
        proc = start_srslte()
        self.subprocs.append(proc)
        monitor = Thread(target=monitor_srslte, args=(proc))
        monitor.start()
        self.threads.append(monitor)

    # Exit gracefully on SIGINT
    def signal_handler(self, sig, frame):
        print(f"\b\b{bcolors.WARNING}I{bcolors.ENDC} You pressed Ctrl+C!")
        self.cleanup()

    def start_srslte(self):
        # TODO Intelligently handle srsUE output (e.g. press a key to view output or something, maybe in another window)
        """ Start srsUE """
        print(f"\b{bcolors.OK}*{bcolors.ENDC} Running srsUE")
        proc = Popen(["./srsLTE/build/srsue/src/srsue", "./ue.conf"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        print(f"\b{bcolors.OK}*{bcolors.ENDC} srsUE started with pid {proc.pid}")
        print(f"\b{bcolors.OK}*{bcolors.ENDC} Tail /tmp/ue.log to see output")
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
                print(line.decode("ascii").rstrip())
            out.append(line)

            if proc.poll() is not None or line is None:
                print(f"\b{bcolors.FAIL}E{bcolors.ENDC} srsUE has exited unexpectedly")
                print(f"\b{bcolors.FAIL}E{bcolors.ENDC} It's dying words were: {out[-2].decode('ascii').rstrip()}")
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
        print(f"\b{bcolors.WARNING}I{bcolors.ENDC} Exiting...")
        global EXIT
        EXIT = True
        for thread in self.threads:
            thread.join()
        for proc in self.subprocs:
            proc.kill()
        subprocess.run("killall gpsd", shell=True, stderr=subprocess.DEVNULL)
        self.watchdog.shutdown()
        Webui.shutdown()
        print(f"\b{bcolors.WARNING}I{bcolors.ENDC} Goodbye for now.")
        os._exit(int(error))

class bcolors:
    """ colors for text """
    HEADER = '\033[95m'
    OK = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Hunt stingrays. Get revenge for Steve.")
    parser.add_argument('-p', '--project-name', dest='project_name', default='default', help="specify the project's name. defaults to 'default'", action='store')
    parser.add_argument('-d', '--debug', dest='debug', help="print debug messages", action='store_true',)
    parser.add_argument('-g', '--disable-gps', dest='disable_gps', help="disable GPS connection and return a default coordinate", action='store_true')
    parser.add_argument('-w', '--disable-wigle', dest='disable_wigle', help='disable Wigle API access', action='store_true')
    args = parser.parse_args()
    crocodile_hunter = CrocodileHunter(args)
    crocodile_hunter.start()
