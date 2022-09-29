# Crocodile Hunter

Crocodile Hunter is a tool to hunt fake eNodeBs, also known commonly as hailstorm, stingray, cell site simulators, or IMSI catchers. It works by listening for broadcast messages from all of the 4G stations in the area, inferring their location, and looking for unusual activity. 

This repository is part of an EFF project studying the newest generation (i.e. 4G/LTE) of Cell Site Simulators. We recommend you read our guide to IMSI Catchers: [Gotta Catch 'Em All](https://www.eff.org/wp/gotta-catch-em-all-understanding-how-imsi-catchers-exploit-cell-networks). 

The main project is located in `/src` and is based off of [srsLTE](https://github.com/srsLTE/srsLTE) and our setup has been tested and is known to work on the Lime SDR, USRP B200, and the bladeRF x40, but should work with any hardware supported by srsLTE. 

For a complete list of necessary hardware check out our [hardware guide](https://github.com/cooperq/crocodilehunter/blob/master/HARDWARE-REQUIREMENTS.md). 

## Build instructions
Crocodile hunter works best on ubuntu 20.04 or later. On intel/amd based systems (most laptops) you can simply run the following command to get started:
```
git clone https://github.com/EFForg/crocodilehunter.git
cd crocodilehunter
sudo ./setup.sh 
```

Before you run this command we reccomend getting all of the hardware in place and a [Wigle.net](https://wigle.net) api key. 

## Usage
```
crocodilehunter.py [-h] [-p PROJECT_NAME] [-d] [-g] [-w]

Hunt stingrays. Get revenge for Steve.

optional arguments:
  -h, --help            show this help message and exit
  -p PROJECT_NAME, --project-name PROJECT_NAME
                        specify the project's name. defaults to 'default'
  -d, --debug           print debug messages
  -g, --disable-gps     disable GPS connection and return a default coordinate
  -w, --disable-wigle   disable Wigle API access
  -o, --web-only        only start the web interface

```

## Web UI
Once the project is running the Web UI to monitor results can be accessed at `http://localhost:5000`
The best way to keep an eye on it on the go is to connect your laptop or pi to a mobile hotspot and then use your phone to view the web UI (that way your computer will still have internet access for making wigle queries.)

If you want to run the webUI without running the scanner simply run the following command:
`./crocodilehunter -o <-p project name>`

## Help
If you want help or to connect with others using crocodile hunter check out our mattermost channel at: [opensource.eff.org](https://opensource.eff.org)
You may also wish to watch a video of @cooperq speaking about crocodile hunter at the [enigma conference](https://youtu.be/tCGCKzP9VBA)


## The nitty gritty stuff

### Hardware Setup 
You'll need to install the required drivers for your software defined radio.

[Driver installation for the USRP B200](https://files.ettus.com/manual/page_install.html#install_linux).

[Driver installation for the bladeRF x40](https://github.com/Nuand/bladeRF/wiki/Getting-Started%3A-Linux#Easy_installation_for_Ubuntu_The_bladeRF_PPA).

**Note:** our bootstrapping script will take care of updating the firmware + FPGA on your bladeRF to the latest version when you try to run the Crocodile Hunter project.

**Note:** installing from apt on Debian or Raspbian will install an incompatible version of libbladerf. The version must be at least 2018.0 or higher. If on a Raspberry Pi it is reccomended to install from source instead of from repos. 

**Note:** If you are on Ubuntu or the version of libbladerf is >= 2018 you can install from repos like so: `sudo apt install libbladerf-dev`

### Configuring GPSD
This project leverages [GPSD](https://gpsd.gitlab.io/gpsd/) which allows one or more applications to share a GPS on a host system, or to use a networked GPS. If GPSD is not set up you can't get real-time position information. If you haven't already installed and configured GPSD you should do so.

The instructions below details how to set GPSD up on a Debian-based system such as Raspbian, Debian Linux or Ubuntu Linux. If you're running a Raspberry Pi with Rasbian and have a GPS **attached to the UART** you can use [Adafruit's wonderful guide](https://learn.adafruit.com/adafruit-ultimate-gps-hat-for-raspberry-pi/) to get GPSD set up. Those instructions are specific to their product they should be generic enough to work with most GPS units connected the the UART once your hardware is properly connected.

If you're on a Debian-based system using a USB or other hardware serial device running `systemd` these instructions should work for you:
* Open a terminal.
* If using a USB GPS device:
  * Plug in your USB GPS device
  * Run `dmesg | tail -n 50` in your terminal.
  * You should see a message indicating that a new USB serial device has been connected. Its path should be something like `/dev/ttyUSB0`, `/dev/ttyAMA0`, or `/dev/ttyACM0`. The number on the end may or may not be zero. Take note of this of that device path for use when setting the `DEVICES` configuration proerty.
* Install GPSD and its client utilities using your terminal: `sudo apt-get install -y gpsd gpsd-clients`.
* Configure GPSD by editing `/etc/default/gpsd`.
  * You'll want to ensure `START_DAEMON` is set to `true`.
  * `USBAUTO` should be set to `false`.
  * Add your device path to `DEVICES` by setting `DEVICES="/dev/<whatever your GPS device is>"`. If you're not using a USB GPS device you'll likely have it attached to one of the serial ports `/dev/ttyS<n>` where `<n>` is the appropriate port number. 
  * Set `GPSD_OPTIONS` to `-n`. This tells GPSD to immediately acquire a position on start instead of waiting for a client to connect and request the location. This will speed up the process of getting a GPS fix.
  * An example configuration with a GPS device path of `/dev/ttyUSB0` is provided below.
* In your terminal tell GPSD to start with your system: `sudo systemctl enable gpsd`
* Start GPSD by issuing this command in your terminal: `sudo systemctl start gpsd`
* You can now test your configuration by running `cgps` in your terminal. You should see your position information appear once the GPS has a fix. You may need to move near a window or outodoors for the GPS to acquire a fix.

** note ** For advanced users running GPSD on a non-standard port or on a different host/IP you can use the `gpsd_host` and `gpsd_port` configuration properties in `config.ini` to specify your host and port.

Example `/etc/default/gpsd` configuration:
```
START_DAEMON="true"
GPSD_OPTIONS="-n"
DEVICES="/dev/ttyUSB0"
USBAUTO="false"
GPSD_SOCKET="/var/run/gpsd.sock"
```


### Project Setup

First, you'll need to install the packages required for srsLTE. [Instructions are here](https://github.com/srsLTE/srsLTE#build-instructions).

Then, after cloning the project, cd to the `src/srsLTE/` directory and initialize the git submodule:
```
git submodule init
git submodule update
```
Note: if afterwards during development you want to pull in changes from our `srsLTE` fork, run:
```
git submodule update --recursive
```

Please make sure you have python3.6 installed on your system. Additional packages you need to install if you're on Ubuntu:
```
sudo apt-get install python3-pip python3-scipy libpolarssl-dev jq  libfftw3-dev libboost-dev libboost-program-options-dev libconfig++-dev gpsd gpsd-clients mariadb-server python3-dev libmariadb-dev cmake libitpp-dev librtlsdr-dev libuhd-dev  libopenblas-dev libncurses5-dev libpcsclite-dev libatlas-base-dev lib32z1-dev
```
In case there is an error locating the package `libpolarssl-dev` it can be changed to `libmbedtls-dev`

Install the required python packages:
```
pip3 install -r src/requirements.txt
```

#### Database Setup
The easiest way to set up the database is through the included docker compose file, simply run 
```
sudo docker-compose up
``` 
in the project directory. 

If you want to set up the database without docker follow the [instructions for setting up MariaDB.](https://www.digitalocean.com/community/tutorials/how-to-install-mariadb-on-ubuntu-20-04)

if you get an error about a missing msyql_config run the following command:
`sudo ln -s /usr/bin/mariadb_config /usr/bin/mysql_config`

Additionally, you'll either need [Wigle](https://wigle.net/) [API credentials](https://api.wigle.net/) or you'll need to set the `enable_wigle` flag in `watchdog.py` to `False`. Note that the free API access only allows 10 `GET` queries per day.

You may also wish to get an [Open Cell ID](https://opencellid.org) API key for GPS location and a backup cell database. 

If you choose to enable Wigle and/or Open Cell ID access, you'll need to set the appropriate options in your config.ini file described below.

You may also wish to set up the API to sync data back to a central server. For information on that see the API section below. 

### Running
You'll need to make a copy of `/src/config.ini.example` in `/src` named `config.ini` and update it with your credentials for wigle, opencellid, and mysql, and default gps coordinates to use for testing, (get them from google maps.) You can also set your default project, this is necessary for starting crocodile hunter automatically using the provided init.d script. 

You will want to get wigle pro API keys or you will hit your request limit very quickly. You should be able to get those by emailing the wigle project and introducing yourself.


To run the full project, use:

```
cd src
./crocodilehunter.py <arguments>
```

### Migrations
If the database is changed or if you wish to change the database you can do so with migrations. **Note:** Migrations do not need to be run when setting up a new project, only when upgrading an existing project to a new database schema. 

To create a migration file:
Change the database schema in src/database.py then run
`export CH_PROJ=<projectname>; sudo -E python3 ./webui.py db migrate -m "migration message"`

To run migrations:
`export CH_PROJ=<projectname>; sudo -E python3 ./webui.py db upgrade`

### Importing known towers:
To import a list of FCC known towers in the US run the following commands:
```bash
cd src/
./get_fcc_towers.py
python3 src/add_known_towers.py <project> fccinfo-towers.csv
```

The script will use GPS data if available. If not it will use the coordinates from gps_default in config.ini to query the datasource.

### API:
To run the API Server set the appropriate paramaters in config.ini and then run `python3 api_server.py` 
To use the API first configure the host and port in config.ini and then get an API key by running
`export CH_PROJ=<projectname>; python3 api_client.py signup`
Then to push new towers to the server run
`export CH_PROJ=<projectname>; python3 api_client.py add_towers`

It is recommended to add this command to a cron job to regularly push towers. 

### Raspberry Pi
Crocodile hunter works on a Raspberry Pi 4! Some considerations to take into account:
* We do not support the Raspberry Pi 3. It may work but I suspect it doesn't have enough processing power. YMMV. 
* Fast Fourier Transforms, which are necessary for digital signal processing can be slow on the pi. The first few towers you find may take a while to process, after that the transforms are cached so it will go quicker. 
* You can speed up the process by overclocking the Raspberry Pi. Details can be found here:  https://www.tomshardware.com/reviews/raspberry-pi-4-b-overclocking,6188.html
* installing from apt Raspbian will install an incompatible version of libbladerf. The version must be at least 7.0 or higher. If on a Raspberry Pi it is recommended to install from source instead of from repos. 



### Important notes

\* Make sure you use mariadb and not mysql or very strange errors will occur! (e.g. this kind of error `SELECT list is not in GROUP BY clause and contains nonaggregated column` from here: https://dev.mysql.com/doc/refman/5.7/en/group-by-handling.html)

\* USB3 is powerful enough that when using a bladeRF with a usb cable that is not well shielded there can sometimes be radio interference which can lead to weird errors. Be sure to either use a well shielded USB cable or plug into a USB2 port.
