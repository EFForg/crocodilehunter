#!/bin/bash
# Bootstrap srsUE, make sure all components are ready


# Test for root
if [[ $EUID -ne 0 ]]; then
   echo -e "===================================="
   echo -e "Crocodile Hunter must be run as root" 
   echo -e "===================================="
   exit 1
fi
HD='\033[0;95m'
RD='\033[0;31m'
GR='\033[0;92m'
NC='\033[0m' # No Color

clear
echo
echo -en $RD
echo -e " ▄████▄   ██▀███   ▒█████   ▄████▄   ▒█████  ▓█████▄  ██▓ ██▓    ▓█████     ██░ ██  █    ██  ███▄    █ ▄▄▄█████▓▓█████  ██▀███  "
echo -e "▒██▀ ▀█  ▓██ ▒ ██▒▒██▒  ██▒▒██▀ ▀█  ▒██▒  ██▒▒██▀ ██▌▓██▒▓██▒    ▓█   ▀    ▓██░ ██▒ ██  ▓██▒ ██ ▀█   █ ▓  ██▒ ▓▒▓█   ▀ ▓██ ▒ ██▒"
echo -e "▒▓█    ▄ ▓██ ░▄█ ▒▒██░  ██▒▒▓█    ▄ ▒██░  ██▒░██   █▌▒██▒▒██░    ▒███      ▒██▀▀██░▓██  ▒██░▓██  ▀█ ██▒▒ ▓██░ ▒░▒███   ▓██ ░▄█ ▒"
echo -e "▒▓▓▄ ▄██▒▒██▀▀█▄  ▒██   ██░▒▓▓▄ ▄██▒▒██   ██░░▓█▄   ▌░██░▒██░    ▒▓█  ▄    ░▓█ ░██ ▓▓█  ░██░▓██▒  ▐▌██▒░ ▓██▓ ░ ▒▓█  ▄ ▒██▀▀█▄  "
echo -e "▒ ▓███▀ ░░██▓ ▒██▒░ ████▓▒░▒ ▓███▀ ░░ ████▓▒░░▒████▓ ░██░░██████▒░▒████▒   ░▓█▒░██▓▒▒█████▓ ▒██░   ▓██░  ▒██▒ ░ ░▒████▒░██▓ ▒██▒"
echo -e "░ ░▒ ▒  ░░ ▒▓ ░▒▓░░ ▒░▒░▒░ ░ ░▒ ▒  ░░ ▒░▒░▒░  ▒▒▓  ▒ ░▓  ░ ▒░▓  ░░░ ▒░ ░    ▒ ░░▒░▒░▒▓▒ ▒ ▒ ░ ▒░   ▒ ▒   ▒ ░░   ░░ ▒░ ░░ ▒▓ ░▒▓░"
echo -e "  ░  ▒     ░▒ ░ ▒░  ░ ▒ ▒░   ░  ▒     ░ ▒ ▒░  ░ ▒  ▒  ▒ ░░ ░ ▒  ░ ░ ░  ░    ▒ ░▒░ ░░░▒░ ░ ░ ░ ░░   ░ ▒░    ░     ░ ░  ░  ░▒ ░ ▒░"
echo -e "░          ░░   ░ ░ ░ ░ ▒  ░        ░ ░ ░ ▒   ░ ░  ░  ▒ ░  ░ ░      ░       ░  ░░ ░ ░░░ ░ ░    ░   ░ ░   ░         ░     ░░   ░ "
echo -e "░ ░         ░         ░ ░  ░ ░          ░ ░     ░     ░      ░  ░   ░  ░    ░  ░  ░   ░              ░             ░  ░   ░     "
echo -en $NC
echo -e

# test for srsLTE config file 
echo -e "${GR}*${NC} Checking for config file"
if [ ! -f ./ue.conf ]; then
    echo -e "${RD}E${NC} ue.conf file not found"
    echo -e "${RD}E${NC} Copy ue.conf.example to ue.conf"
fi

# Test for and set up bladeRF
echo -e "${GR}*${NC} Checking for SDR"
BLADERF_FPGA_PATH=../data/hostedx40-latest.rbf
bladeRF-cli -p 1>/dev/null 2>&1
if [ $? -ne 0 ]; then
    echo -e "${GR}*${NC} No bladeRF devices connected. Assuming Ettus." >&2
else
    echo -e "${GR}*${NC} BladeRF Found"
    if [[ ! -f $BLADERF_FPGA_PATH ]]; then
        echo -e "${GR}*${NC} Downloading FPGA for BladeRF"
        curl https://www.nuand.com/fpga/hostedx40-latest.rbf > $BLADERF_FPGA_PATH
    fi
    echo -e "${GR}*${NC} Loading FPGA for BladeRF"
    bladeRF-cli -v critical -l $BLADERF_FPGA_PATH > /dev/null
fi

# Test GPS 
echo -e "${GR}*${NC} Testing GPS"
killall -9 gpsd 
service gpsd stop
if [ -e /dev/ttyUSB0 ]; then 
    gpsd /dev/ttyUSB0
    echo -e "${GR}*${NC} Waiting for GPS to sync"
    ../experiments/gps.sh | grep null  > /dev/null
    until [ $? -eq 1 ]; do
        echo -e "${RD}E${NC} GPS failed to sync."
    done
    echo -e "${GR}*${NC} GPS successfully got location"
else
    echo -e "${RD}E${NC} No GPS device found"
    exit 1
fi

if [ ! -d ./srsLTE/build ]; then
    echo -e "${GR}*${NC} Building srsLTE for the first time"
    cd srsLTE
    mkdir build
    cd build 
    cmake ../ > /dev/null
else
    cd srsLTE/build 
fi
echo -e "${GR}*${NC} Compiling srsUE"
make > /dev/null
echo -e "${GR}*${NC} SrsUE built succesfully"
echo -e "${GR}*${NC} Reticulating Splines"

exit 0
