# crocodilehunter
*Taking one back for Steve Irwin.*

This repository is part of a project studying the newest generation (i.e. 4G/LTE) of Cell Site Simulators.

The main project is located in `/src` and is based off of [srsLTE](https://github.com/srsLTE/srsLTE) and our setup currently supports the USRP B200 and the bladeRF x40.

### Hardware Setup

You'll need to install the required drivers for either the bladeRF or USRP.

[Driver installation for the USRP B200](https://files.ettus.com/manual/page_install.html#install_linux).

[Driver installation for the bladeRF x40](https://github.com/Nuand/bladeRF/wiki/Getting-Started%3A-Linux#Easy_installation_for_Ubuntu_The_bladeRF_PPA). Note: our bootstrapping script will take care of updating the firmware + FPGA on your bladeRF to the latest version when you try to run the Crocodile Hunter project.

### Project Setup

First, you'll need to install the packages required for srsLTE. [Instructions are here](https://github.com/srsLTE/srsLTE#build-instructions).

Then, after cloning the project, cd to the `src/srsLTE/` directory and initialize the git submodule:
```
git submodule init
git submodule update
```

Additional packages you need to install if you're on Ubuntu:
```
sudo apt-get install gpsd gpsd-clients

```

### Running
You'll need to make a copy of `/src/ue.conf.example` in `/src` named `ue.conf` and update it to use the EARFCNs in your area. To easily figure out what EARFCNs are in use, we'd recommend installing the [Netmonitor app](https://play.google.com/store/apps/details?id=com.parizene.netmonitor) on an Android device.

To run the full project, use:

```
cd src
sudo ./crocodilehunter.py
```

### Misc

\* It's named *Crocodile Hunter* because a stingray killed Steve Irwin.
