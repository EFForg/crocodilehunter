#!/bin/bash

echo "Installing crocodile hunter"

if [ "$EUID" -ne 0 ]
  then echo "Please run as root"
  exit
fi

cd `pwd`/../..
if [ ! -d  /opt ]; then
  mkdir /opt
fi
rsync -au crocodilehunter /opt/
cp /opt/crocodilehunter/src/service /etc/systemd/system/crocodilehunter.service
systemctl enable crocodilehunter 
chmod +x /opt/crocodilehunter/src/crocodilehunter.py
