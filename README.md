# crocodilehunter

This repository is part of a project studying the newest generation (i.e. 4G/LTE) of Cell Site Simulators.

The main project is located in `/src` and is based off of [srsLTE](https://github.com/srsLTE/srsLTE) and our setup currently supports the USRP B200 and the bladeRF x40.

### Hardware Setup You'll need to install the required drivers for either the bladeRF or USRP.

[Driver installation for the USRP B200](https://files.ettus.com/manual/page_install.html#install_linux).

[Driver installation for the bladeRF x40](https://github.com/Nuand/bladeRF/wiki/Getting-Started%3A-Linux#Easy_installation_for_Ubuntu_The_bladeRF_PPA). Note: our bootstrapping script will take care of updating the firmware + FPGA on your bladeRF to the latest version when you try to run the Crocodile Hunter project.

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
sudo apt-get install python3-pip gpsd gpsd-clients mariadb-server python3-dev libmysqlclient-dev cmake libitpp-dev librtlsdr-dev libopenblas-dev libncurses5-dev libpcsclite-dev
```

Note: for installation on a Raspberry Pi, you might also need:
```
sudo apt-get install libpolarssl-dev
```

Install the required python packages:
```
pip3 install -r src/requirements.txt
```

Additionally, you'll either need [Wigle](https://wigle.net/) [API credentials](https://api.wigle.net/) or you'll need to set the `enable_wigle` flag in `watchdog.py` to `False`. Note that the free API access only allows 10 `GET` queries per day.

If you choose to enable Wigle access, you'll need to set the following environment variables (probably in your `~/.bashrc` file): `WIGLE_NAME` and `WIGLE_KEY`.

### Running
You'll need to make a copy of `/src/config.ini.example` in `/src` named `config.ini` and update it with your credentials for wigle and mysql and a default gps coordinate to use for testing.  

You will want to get wigle pro API keys or you will hit your request limit very quickly.


To run the full project, use:

```
cd src
./crocodilehunter.py <arguments> -p <project name>
```

### Usage
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
```

### Web UI
Once the project is running the Web UI to monitor results can be accessed at `http://localhost:5000`
The best way to keep an eye on it on the go is to connect your laptop to a mobile hotspot and then use your phone to view the web UI (that way your computer will still have internet access for making wigle queries.)

If you want to run the webUI without running the scanner simply run the following command:
`export CH_PROJ=<project_name>; python3 webui.py`

### Migrations
If the database is changed or if you wish to change the database you can do so with migrations. **Note:** Migrations do not need to be run when setting up a new project, only when upgrading an existing project to a new database schema. 

To create a migration file:
Change the database schema in src/database.py then run
`export CH_PROJ=projectname; sudo -E python3 ./webui.py db migrate -m "migration message"`

To run migrations:
`export CH_PROJ=wardrive; sudo -E python3 ./webui.py db upgrade`

### Misc

\* It's named *Crocodile Hunter* because a stingray killed Steve Irwin.

\* USB3 is powerful enough that when using a bladeRF with a usb cable that is not well shielded there can sometimes be radio interference which can lead to weird errors. Be sure to either use a well shielded USB cable or plug into a USB2 port.
