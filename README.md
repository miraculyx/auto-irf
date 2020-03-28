# autoirf.py
Python Script for HPE Comware switches for automatically creating an HPE IRF Cluster during bootup.

All HPE network devices have to have a factory default configuration.<br>
The file "<b>inventory.txt</b>" holds the <i>Serial-Numbers</i>, the <i>IRF domain</i> and the <i>IRF ID</i> for each of the HPE network devices.

The "<b>autoirf.py</b>" file has to be saved in the directory of a <b>HTTP Server</b>. 

The "inventory.txt" and all the devices configurations has to saved on an <b>TFTP Server</b>.<br>
The Filename of the configurations of the network devices has to be the Serial-Number<br>
of each device (CN87X93021.cfg, CN87X93022.cfg, etc.).

A <b>DHCP Server</b> has to be configured with a DHCP Scope for the new network devices (attention of the device number)
and the DHCP option pointing for the bootfile to an HTTP Server.

Example for configuring a HPE Comware 7 device as an DHCP Server:

#<br>
 dhcp enable<br>
 dhcp server forbidden-ip 192.168.1.253<br>
 dhcp server forbidden-ip 192.168.1.254<br>
#<br>
dhcp server ip-pool VLAN1<br>
 gateway-list 192.168.1.253<br>
 network 192.168.1.0 mask 255.255.255.0<br>
 bootfile-name http://192.168.1.254/autoirf.py<br>
 expired day 0 hour 0 minute 30<br>
 tftp-server ip-address 192.168.1.254<br>
#<br>
