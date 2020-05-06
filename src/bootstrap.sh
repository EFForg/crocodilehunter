#!/bin/bash
# Bootstrap srsUE, make sure all components are ready

# test for srsLTE config file
echo -e "Checking for config file"
if [ ! -f ./config.ini ]; then
    echo -e "config.ini file not found"
    echo -e "creating config.ini from config.ini.example"
    cp config.ini.example config.ini
fi

# Test for and set up bladeRF
echo -e "Checking for SDR"
BLADERF_FPGA_PATH=../data/hostedx40-latest.rbf
bladeRF-cli -p 1>/dev/null 2>&1
if [ "$?" -ne "0" ]; then
    echo -e "No bladeRF devices connected. Assuming UHD device." >&2
    uhd_find_devices > /dev/null 2>&1
    if [ $? -ne 0 ]; then
      echo -e "No UHD device found either"
      exit 1
    fi
else
    echo -e "BladeRF Found"
    if [[ `bladeRF-cli -v critical -e version | grep -i "FPGA not loaded"` ]]; then
      if [[ ! -f $BLADERF_FPGA_PATH ]]; then
          echo -e "Downloading FPGA for BladeRF"
          curl https://www.nuand.com/fpga/hostedx40-latest.rbf > $BLADERF_FPGA_PATH
      fi
      echo -e "Loading FPGA for BladeRF"
      bladeRF-cli -v critical -l $BLADERF_FPGA_PATH > /dev/null
   fi
fi

# Test GPS
if [ ! -z $1 ]; then
    echo -e "Skipping GPS test"
else
    echo -e "Starting GPS"
    sudo killall -9 gpsd 2> /dev/null
    sudo service gpsd stop
    if [ -e /dev/ttyUSB0 ]; then
        sudo gpsd /dev/ttyUSB0
        echo -e "Waiting for GPS to sync"
        TRIES=0
        until ../experiments/gps.sh | grep -v null  > /dev/null; do
            echo -e "GPS failed to sync."
            sleep 1
            TRIES=$[ $TRIES + 1 ]
            if [ $TRIES -ge 10 ]; then
              echo -e "GPS couldn't get a fix, giving up"
              break;
            fi
        done
        echo -e "GPS successfully got location"
    else
        echo -e "No GPS device found"
        exit 1
    fi
fi


if [ ! -d ./srsLTE/build ]; then
    echo -e "Building srsLTE for the first time"
    cd srsLTE
    mkdir build
    cd build
    cmake ../ > /dev/null
else
    cd srsLTE/build
fi
echo -e "Compiling srsUE"
make > /dev/null
echo -e "SrsUE built succesfully"
echo -e "Reticulating Splines"

exit 0
