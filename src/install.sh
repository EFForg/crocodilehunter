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
cp /opt/crocodilehunter/src/init.d.sh /etc/init.d/crocodilehunter
chmod +x /etc/init.d/crocodilehunter
chmod +x /opt/crocodilehunter/src/crocodilehunter.py
