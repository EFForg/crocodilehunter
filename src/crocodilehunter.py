#!/usr/bin/env python3
""" 
Crocodile Hunter
Find stingrays in the wild. Hunt them down. Get revenge for Steve Irwen
"""

import subprocess
from subprocess import Popen
from time import sleep
import itertools
import sys

def main():
    """
    * Bootstrap srsUE
        * test gps
        * check for board
        * Load FPGA for hackrf
    * Start srsue with config file
    * on a loop check db for anomolies
    * generate web interface
    """
    subprocess.run("./bootstrap.sh", shell=True, check=True)
    print(f"{bcolors.OK}*{bcolors.ENDC} Running srsUE")
    pid = Popen(["./srsLTE/build/srsue/src/srsue", "./ue.conf"], \
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).pid
    print(f"{bcolors.OK}*{bcolors.ENDC} srsUE started with pid {pid}")
    print(f"{bcolors.OK}*{bcolors.ENDC} Tail /tmp/ue.log to see output")
    spinner = itertools.cycle(['-', '/', '|', '\\'])
    while True:
        sleep(0.1)
        sys.stdout.write(next(spinner))  # write the next character
        sys.stdout.flush()                # flush stdout buffer (actual character display)
        sys.stdout.write('\b')            # erase the last written char

class bcolors:
    HEADER = '\033[95m'
    OK = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

if __name__ == "__main__":
    main() 
