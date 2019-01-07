#!/bin/bash
# Bootstrap srsUE, make sure all components are ready


# Test for root
if [[ $EUID -ne 0 ]]; then
   echo -e "\b===================================="
   echo -e "\bCrocodile Hunter must be run as root"
   echo -e "\b===================================="
   exit 1
fi
HD='\033[0;95m'
RD='\033[0;31m'
GR='\033[0;92m'
YL='\033[0;93m'
NC='\033[0m' # No Color

clear
echo
echo -en $RD
echo -e "\b ▄████▄   ██▀███   ▒█████   ▄████▄   ▒█████  ▓█████▄  ██▓ ██▓    ▓█████     ██░ ██  █    ██  ███▄    █ ▄▄▄█████▓▓█████  ██▀███  "
echo -e "\b▒██▀ ▀█  ▓██ ▒ ██▒▒██▒  ██▒▒██▀ ▀█  ▒██▒  ██▒▒██▀ ██▌▓██▒▓██▒    ▓█   ▀    ▓██░ ██▒ ██  ▓██▒ ██ ▀█   █ ▓  ██▒ ▓▒▓█   ▀ ▓██ ▒ ██▒"
echo -e "\b▒▓█    ▄ ▓██ ░▄█ ▒▒██░  ██▒▒▓█    ▄ ▒██░  ██▒░██   █▌▒██▒▒██░    ▒███      ▒██▀▀██░▓██  ▒██░▓██  ▀█ ██▒▒ ▓██░ ▒░▒███   ▓██ ░▄█ ▒"
echo -e "\b▒▓▓▄ ▄██▒▒██▀▀█▄  ▒██   ██░▒▓▓▄ ▄██▒▒██   ██░░▓█▄   ▌░██░▒██░    ▒▓█  ▄    ░▓█ ░██ ▓▓█  ░██░▓██▒  ▐▌██▒░ ▓██▓ ░ ▒▓█  ▄ ▒██▀▀█▄  "
echo -e "\b▒ ▓███▀ ░░██▓ ▒██▒░ ████▓▒░▒ ▓███▀ ░░ ████▓▒░░▒████▓ ░██░░██████▒░▒████▒   ░▓█▒░██▓▒▒█████▓ ▒██░   ▓██░  ▒██▒ ░ ░▒████▒░██▓ ▒██▒"
echo -e "\b░ ░▒ ▒  ░░ ▒▓ ░▒▓░░ ▒░▒░▒░ ░ ░▒ ▒  ░░ ▒░▒░▒░  ▒▒▓  ▒ ░▓  ░ ▒░▓  ░░░ ▒░ ░    ▒ ░░▒░▒░▒▓▒ ▒ ▒ ░ ▒░   ▒ ▒   ▒ ░░   ░░ ▒░ ░░ ▒▓ ░▒▓░"
echo -e "\b  ░  ▒     ░▒ ░ ▒░  ░ ▒ ▒░   ░  ▒     ░ ▒ ▒░  ░ ▒  ▒  ▒ ░░ ░ ▒  ░ ░ ░  ░    ▒ ░▒░ ░░░▒░ ░ ░ ░ ░░   ░ ▒░    ░     ░ ░  ░  ░▒ ░ ▒░"
echo -e "\b░          ░░   ░ ░ ░ ░ ▒  ░        ░ ░ ░ ▒   ░ ░  ░  ▒ ░  ░ ░      ░       ░  ░░ ░ ░░░ ░ ░    ░   ░ ░   ░         ░     ░░   ░ "
echo -e "\b░ ░         ░         ░ ░  ░ ░          ░ ░     ░     ░      ░  ░   ░  ░    ░  ░  ░   ░              ░             ░  ░   ░     "
echo -en $NC
echo -e

# test for srsLTE config file
echo -e "\b${GR}*${NC} Checking for config file"
if [ ! -f ./ue.conf ]; then
    echo -e "\b${RD}E${NC} ue.conf file not found"
    echo -e "\b${RD}E${NC} Copy ue.conf.example to ue.conf"
fi

# Test for and set up bladeRF
echo -e "\b${GR}*${NC} Checking for SDR"
BLADERF_FPGA_PATH=../data/hostedx40-latest.rbf
bladeRF-cli -p 1>/dev/null 2>&1
if [ $? -ne 0 ]; then
    echo -e "\b${YL}I${NC} No bladeRF devices connected. Assuming UHD device." >&2
    uhd_find_devices > /dev/null 2>&1
    if [ $? -ne 0 ]; then
      echo -e "\b${RD}E${NC} No UHD device found either"
      exit 1
    fi
else
    echo -e "\b${GR}*${NC} BladeRF Found"
    if [[ `bladeRF-cli -v critical -e version | grep -i "FPGA not loaded"` ]]; then
      if [[ ! -f $BLADERF_FPGA_PATH ]]; then
          echo -e "\b${GR}*${NC} Downloading FPGA for BladeRF"
          curl https://www.nuand.com/fpga/hostedx40-latest.rbf > $BLADERF_FPGA_PATH
      fi
      echo -e "\b${GR}*${NC} Loading FPGA for BladeRF"
      bladeRF-cli -v critical -l $BLADERF_FPGA_PATH > /dev/null
   fi
fi

# Test GPS
echo -e "\b${GR}*${NC} Testing GPS"
killall -9 gpsd 2> /dev/null
service gpsd stop

if [ -e /dev/ttyUSB0 ]; then
    gpsd /dev/ttyUSB0
    echo -e "\b${GR}*${NC} Waiting for GPS to sync"
    until ../experiments/gps.sh | grep -v null  > /dev/null; do
        echo -e "\b${RD}E${NC} GPS failed to sync."
        sleep 1
    done
    echo -e "\b${GR}*${NC} GPS successfully got location"
else
    echo -e "\b${RD}E${NC} No GPS device found"
    exit 1
fi

if [ ! -d ./srsLTE/build ]; then
    echo -e "\b${GR}*${NC} Building srsLTE for the first time"
    cd srsLTE
    mkdir build
    cd build
    cmake ../ > /dev/null
else
    cd srsLTE/build
fi
echo -e "\b${GR}*${NC} Compiling srsUE"
make > /dev/null
echo -e "\b${GR}*${NC} SrsUE built succesfully"
echo -e "\b${GR}*${NC} Reticulating Splines"

exit 0
