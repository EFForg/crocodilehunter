#!/bin/bash
# Bootstrap srsUE, make sure all components are ready

# Test for root
if [[ $EUID -ne 0 ]]; then
   echo "Crocodile Hunter must be run as root" 
   exit 1
fi

# test for srsLTE config file 
if [ ! -f ./ue.conf ]; then
    echo "E ue.conf file not found"
    echo "E copy ue.conf.example to ue.conf"
fi

# Test for and set up bladeRF
BLADERF_FPGA_PATH=../data/hostedx40-latest.rbf
bladeRF-cli -p 1>/dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "* No bladeRF devices connected. Assuming Ettus." >&2
else
    echo "* Loading FPGA for BladeRF"
    if [[ ! -f $BLADERF_FPGA_PATH ]]; then
        curl https://www.nuand.com/fpga/hostedx40-latest.rbf > $BLADERF_FPGA_PATH
    fi
    bladeRF-cli -l $BLADERF_FPGA_PATH
fi

# Test GPS 
killall -9 gpsd 
service gpsd stop
if [ ! -f /dev/ttyUSB0]; then 
    echo "E No GPS device found"
    exit 1
else
    gpsd /dev/ttyUSB0
    echo "* Waiting for gps to sync"
    ../experiments/gps.sh
    if [ $? -ne 0 ]; then
        echo "E gps failed to sync."
        exit 1
    fi
fi

echo "* building srsUE"
if [ ! -d ./srsLTE/build ]; then
    echo "* Building srsLTE for the first time"
    cd srsLTE
    mkdir build
    cd build 
    cmake ../
else
   cd srsLTE/build 
fi
make > /dev/null


exit 0
