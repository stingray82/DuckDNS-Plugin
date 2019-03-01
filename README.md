# DuckDNS Updater Plugin for Engima2
This Plugin will allow your enigma2 box to update your DuckDNS hostname(s) with the IP address it is using
Can be set to update from 5 minutes up to 180 minutes.

# Features
Will update upto the standard maximum 5 hostnames
Setup from coniguration screen or by XML located in /etc/enigma2/
Setup from coniguration screen or by XML located in /etc/enigma2/
Will not update if there has been no change in IP Address since last recorded IP address even after a reboot which uses http://myexternalip.com/raw
Debug settings by placing a text file containing an IP address in the folder to put more error messages within the log
Can now be enabled and disabled using the enable and disable options in plugin.

## Screenshots:
![Plugin Icon](https://i.ibb.co/R7GDT8M/5002-0-1-8-B43-1821-B0-FE-0-0-0-0-20190223190416.jpg)
![Plugin Screenshot](https://i.ibb.co/rcbdjCY/5002-0-1-8-B43-1821-B0-FE-0-0-0-0-20190223190454.jpg)

### Installation
Install the latest release using this command

```sh
$ opkg install https://github.com/stingray82/DuckDNS-Plugin/releases/download/v0.11/enigma2-plugin-extensions-duckdnsupdater_0.11_all.ipk
```
