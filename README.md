# autoirf.py
Python Script for HPE Comware switches

The file "inventory.txt" holds the Serial-Numbers, the IRF domain and
the IRF ID for each of the HPE network devices.

The File "autoirf.py" and "inventory.txt" has to be saved in the directory of a
HTTP Server (or TFTP Server)
A DHCP Server has to be configured with a DHCP Scope for the new network devices
and the DHCP option pointing for the bootfile to an HTTP Server.

Example for configuring a Comware 7 device as an DHCP Server:

#
 dhcp enable
 dhcp server forbidden-ip 192.168.1.253
 dhcp server forbidden-ip 192.168.1.254
#
dhcp server ip-pool VLAN1
 gateway-list 192.168.1.253
 network 192.168.1.0 mask 255.255.255.0
 bootfile-name http://192.168.1.254/autoirf.py
 expired day 0 hour 0 minute 30
 tftp-server ip-address 192.168.1.254
#
