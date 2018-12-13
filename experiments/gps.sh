#!/bin/bash
gpsdata=$( gpspipe -w | grep -m 1 TPV )
lat=$( echo "$gpsdata"  | jq -r '.lat' )
lon=$( echo "$gpsdata"  | jq -r '.lon' )
echo "$lat, $lon"
