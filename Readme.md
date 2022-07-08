fru-print
=========

# Overview

## Introduction of fru-print

The Kria KV 260 Vision AI Starter Kit (KV260) has an EEPROM that stores board information, MAC address, etc. connected via I2C. The fru-print provided in this repository is a Python program that reads this EEPROM.


## What is FRU?

The contents of the EEPROM are stored based on the format defined by the Platform Management FRU Information Strage Definition in the standard called Intelligent Platform Management Interface (IPMI). By the way, FRU seems to be a Field Replaceable Unit. Please refer to the following page for details.

 * https://ja.wikipedia.org/wiki/Intelligent_Platform_Management_Interface
 * https://www.intel.com/content/www/us/en/products/docs/servers/ipmi/ipmi-second-gen-interface-spec-v2-rev1-1.html
 * https://www.intel.com/content/dam/www/public/us/en/documents/product-briefs/platform-management-fru-document-rev-1-2-feb-2013.pdf

## KV260 EEPROM

There are two KV260 EEPROMs, one for each of the System On Module (SOM) and Carrer Card (CC).
Each EEPROM is connected to ZynqMP via I2C.
The address on I2C is 0x50 for the SOM EEPROM and 0x51 for the CC EEPROM.
On Linux, you can simply read the EEPROM data as binary data as follows: ..

```console
fpga@debian-fpga:~/work/fru-print$ sudo dd if=/sys/bus/i2c/devices/1-0050/eeprom of=som_eeprom.bin bs=8192
0+2 records in
0+2 records out
8192 bytes (8.2 kB, 8.0 KiB) copied, 0.222683 s, 36.8 kB/s
fpga@debian-fpga:~/work/fru-print$ sudo dd if=/sys/bus/i2c/devices/1-0051/eeprom of=cc_eeprom.bin  bs=8192
0+2 records in
0+2 records out
8192 bytes (8.2 kB, 8.0 KiB) copied, 0.222681 s, 36.8 kB/s
```

## The fru-print provided by Xilinx

Petalinux provided by Xilinx has a Python script called fru-print.py installed.
If you are using Petalinux, you can use this fru-print.py to see the contents of the EEPROM.

The fru-print.py provided by Xilinx imports a Python module called fru.
The fru module is probably based on the one published in the following GitHub repository.

 * https://github.com/genotrance/fru-tool

However, it seems that Xilinx has added something to fru.py published by fru-tool.

## The fru-print provided by this repository

The fru-print.py provided by Xilinx does not have a license notation, so I do not know if I can bring it to another system as it is.
Also, fru.py for fru-tool is published under the MIT license, but since Xilinx has modified it independently, I don't know what the license is again.

So, although it is a "reinventing the wheel", I tried to make something similar as my hobby.

fru-tool was very helpful, but my fru-print.py doesn't use fru-tool.
It seems that fru-tool can write as well as read, but it is not so difficult if it is only read, so I made it with full scratch.

# Build Debian Package

```console
shell$ git clone --branch=v1.0.0 --depth=1 https://github.com/ikwzm/fru-print.git
shell$ cd fru-print
```

```console
shell$ sudo debian/rules binary
rm -rf debian/tmp
touch build
install -d debian/tmp/DEBIAN debian/tmp/usr/share/doc/fru-print debian/tmp/usr/bin
cp -a fru-print.py           debian/tmp/usr/bin
ln -s ./fru-print.py         debian/tmp/usr/bin/fru-print
cp -a debian/copyright       debian/tmp/usr/share/doc/fru-print/
cp -a debian/changelog       debian/tmp/usr/share/doc/fru-print/changelog.Debian
cp -a ChangeLog              debian/tmp/usr/share/doc/fru-print/changelog
dpkg-gencontrol
dpkg-gencontrol: warning: Depends field of package fru-print: unknown substitution variable ${misc:Depends}
dpkg-gencontrol: warning: Depends field of package fru-print: unknown substitution variable ${python3:Depends}
chown -R root:root debian/tmp
chmod -u+w,go=rX debian/tmp
dpkg-deb --build debian/tmp ..
dpkg-deb: building package 'fru-print' in '../fru-print_1.0.0_all.deb'.
```

# Thanks

fru-tool was very helpful in writing fru-print.py. Thank you.

