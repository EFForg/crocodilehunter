#!/bin/bash
# Bootstrap srsUE, make sure all components are ready

# test for srsLTE config file
echo -e "Checking for config file"
if [ ! -f ./config.ini ]; then
    echo -e "config.ini file not found"
    echo -e "creating config.ini from config.ini.example"
    cp config.ini.example config.ini
fi

if [ ! -d ./srsLTE/build ]; then
    echo -e "Building srsLTE for the first time"
    cd srsLTE
    mkdir build
    cd build
    cmake ../ > /dev/null
else
    cd srsLTE/build/lib/examples
fi
echo -e "Compiling srsUE"
make > /dev/null
echo -e "SrsUE built succesfully"
echo -e "Reticulating Splines"

exit 0
