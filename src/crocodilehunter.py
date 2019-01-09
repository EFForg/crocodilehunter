#!/usr/bin/env python3
"""
Crocodile Hunter
Find stingrays in the wild. Hunt them down. Get revenge for Steve Irwin

TODO Create logging subsystem
"""

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
from nbstreamreader import NonBlockingStreamReader as NBSR, UnexpectedEndOfStream

# Global flag to exit forever running threads
EXIT = False

def main():
    """
    1. Bootstrap dependencies
        a. test gps
        b. check for SDR
    2. Start srsue with config file
        a. watch srsue for crashes and restart
    3. Start watchdog daemon
    4. Start web daemon
    """
    threads = []
    subprocs = []

    spn = Thread(target=show_spinner)
    spn.start()
    threads.append(spn)

    # Exit gracefully on SIGINT
    def signal_handler(sig, frame):
        print(f"\b\b{bcolors.WARNING}I{bcolors.ENDC} You pressed Ctrl+C!")
        cleanup(threads, subprocs)
    signal.signal(signal.SIGINT, signal_handler)

    # Bootstrap srsUE dependencies
    try:
        subprocess.run("./bootstrap.sh", shell=True, check=True)
    except subprocess.CalledProcessError:
        cleanup(threads, subprocs, True)

    #Start watchdog dæmon
    Watchdog.start_daemon()

    #Start web ui dæmon
    Webui.start_daemon()

    # Monitor and restart srsUE if it crashes
    proc = start_srslte()
    subprocs.append(proc)
    monitor = Thread(target=monitor_srslte, args=(proc,))
    monitor.start()
    threads.append(monitor)

def start_srslte():
    # TODO Intelligently handle srsUE output (e.g. press a key to view output or something, maybe in another window)
    """ Start srsUE """
    print(f"\b{bcolors.OK}*{bcolors.ENDC} Running srsUE")
    proc = Popen(["./srsLTE/build/srsue/src/srsue", "./ue.conf"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    print(f"\b{bcolors.OK}*{bcolors.ENDC} srsUE started with pid {proc.pid}")
    print(f"\b{bcolors.OK}*{bcolors.ENDC} Tail /tmp/ue.log to see output")
    return proc

def monitor_srslte(proc):
    """ Monitor for crashes and restart srsLTE"""
    # TODO
    global EXIT
    out = []
    sleep(1)
    nbsr = NBSR(proc.stdout)
    line = ''
    while not EXIT:
        try:
            line = nbsr.readline(10)
        except UnexpectedEndOfStream:
            print("Output stream ended")
        out.append(str(line))

        if proc.poll() is not None or line is None:
            print(f"\b{bcolors.FAIL}E{bcolors.ENDC} srsUE has exited unexpectedly")
            print(f"\bI {out[-1]}")
            proc.kill()
            proc = start_srslte()
            monitor_srslte(proc)

def show_spinner():
    """ show a spinning cursor """
    global EXIT
    spinner = itertools.cycle(['-', '/', '|', '\\'])
    while not EXIT:
        sys.stdout.write(next(spinner))   # write the next character
        sys.stdout.flush()                # flush stdout buffer (actual character display)
        sys.stdout.write('\b')            # erase the last written char
        sleep(0.1)

def cleanup(threads, subprocs, error=False):
    """ Gracefully exit when program is quit """
    print(f"\b{bcolors.WARNING}I{bcolors.ENDC} Exiting...")
    global EXIT
    EXIT = True
    for thread in threads:
        thread.join()
    for proc in subprocs:
        proc.kill()
    subprocess.run("killall gpsd", shell=True, stderr=subprocess.DEVNULL)
    Watchdog.shutdown()
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
    main()
