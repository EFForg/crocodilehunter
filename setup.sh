#!/bin/bash
# Test for root
HD='\033[0;95m'
RD='\033[0;31m'
GR='\033[0;92m'
YL='\033[0;93m'
NC='\033[0m' # No Color

if [[ $EUID -ne 0 ]]; then
   echo -e "$RD===================================="
   echo -e "Crocodile Hunter must be run as root"
   echo -e "==================================== $NC"
   exit 1
fi

print_header() {
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
echo -e

}


setup_blade() {
  echo "Installing bladeRF Drivers..."
  sudo apt install -y libbladerf-dev bladerf bladerf-fpga-hostedx115  bladerf-fpga-hostedx40   bladerf-fpga-hostedxa4   bladerf-fpga-hostedxa9
  echo -e "$YL* NOTE: You may need to take extra steps to get your bladeRF up and running, please check the documentation here if you have any problems: 
https://github.com/Nuand/bladeRF/wiki/Getting-Started%3A-Linux#Easy_installation_for_Ubuntu_The_bladeRF_PPA$NC"
  press_enter

}

setup_lime() {
  echo "Installing LimeSDR (SoapySDR) Drivers..."
  sudo apt install -y libsoapysdr-dev soapysdr-module-lms7 soapysdr-tools
}

setup_uhd() {
  echo "Installing UHD Drivers..."
  sudo apt-get install -y libuhd-dev libuhd004 uhd-host
  echo -e "$YL NOTE: You may need to take extra steps to get your Ettus device up and running, please check the documentation here if you are unsure: https://files.ettus.com/manual/page_install.html#install_linux $NC"
  press_enter
}

press_enter() {
  echo ""
  echo -en "$RD* Press Enter to continue $NC"
  read
}

incorrect_selection() {
  echo "Incorrect selection! Try again."
}

print_header
echo ""
echo "Which SDR platform will crocodile hunter be using?"
echo "    	1  -  Blade RF"
echo "    	2  -  Lime RF"
echo "    	3  -  Ettus UHD"
echo "    	0  -  Other"
echo ""
echo -n "  Enter selection: "
read selection
echo ""
case $selection in
1 ) clear ; setup_blade ;; 
2 ) clear ; setup_lime ;; 
3 ) clear ; setup_uhd ;; 
0 ) clear ; setup_other ;;
* ) clear ; incorrect_selection ; press_enter ;;
esac

print_header
echo "* Installing dependencies"
sudo apt update
sudo apt install -y cmake libfftw3-dev libmbedtls-dev libboost-program-options-dev libconfig++-dev libsctp-dev build-essential python3-pip python3-scipy libmbedtls-dev jq  libfftw3-dev libboost-dev libboost-program-options-dev libconfig++-dev gpsd gpsd-clients mariadb-server python3-dev libmariadb-dev cmake libitpp-dev libopenblas-dev libncurses5-dev libpcsclite-dev libatlas-base-dev lib32z1-dev

#set up database
sudo apt install mariadb-server
sudo mysql_secure_installation
if [ ! -e /usr/bin/mysql_config ]; then
  sudo ln -s /usr/bin/mariadb_config /usr/bin/mysql_config
fi
sudo systemctl restart mariadb

# install python reqs
pip3 install -r src/requirements.txt


#compile
print_header
echo "* Ready to compile srslte"
press_enter
cd src/srsLTE
git submodule init
git submodule update
mkdir build 
cd build 
if ! cmake ../; then
  echo "build process failed, please check the above output for errors and file a bug report"
  exit
fi

if ! make; then
  echo "build process failed, please check the above output for errors and file a bug report"
  exit
fi
  echo "* Build process complete!"

#cd back to src/
cd ../.. 

#set up gps
print_header
test_gps() {
  echo -n "  Enter gps device path (e.g. /dev/ttyUSB0): "
  read gps_path
  echo ""
  if [ ! -e $gps_path ]; then
    echo "* Couldn't find a device at $gps_path, plug in your device and check dmesg for the correct path"
    press_enter
    return 1
  fi
}
test_gps
while [ ! $? ] ; do
  test_gps
done

sudo echo "# Devices gpsd should collect to at boot time.
# They need to be read/writeable, either by user gpsd or the group dialout.
DEVICES=\"$gps_path\"

# Other options you want to pass to gpsd
GPSD_OPTIONS=\"-n\"
USBAUTO=\"true\"
START_DAEMON=\"true\"
GPSD_SOCKET=\"/var/run/gpsd.sock\"
" > /etc/default/gpsd

echo "* check your GPS config and make sure everything looks correct\n(if you don't know whats going on here its probably fine.)"
press_enter
edit /etc/default/gpsd
sudo systemctl restart gpsd

#set_up_config
print_header
echo "* We will now edit the config file for your setup"
press_enter
cp config.ini.example config.ini
edit config.ini

#print further instructions
echo -e "$GR* You have successfully installed Crocodile Hunter! $NC"
./crocodilehunter.py -h 
