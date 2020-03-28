#!usr/bin/python

import comware
from time import strftime,gmtime,sleep
import signal
import os
import string
import commands
import hashlib

# python_config_file_mode = "serial_number"

#Required space to copy config kickstart and system image in KB
required_space = 150000

# TFTP file transfer information      
username = ""
password = ""
tftp_server = "192.168.1.254"
protocol = "tftp"
vrf = ""
config_timeout = 120
irf_timeout = 120
image_timeout = 2100

# Server (TFTP Server?) File Path         
server_path = ""

# Local File path
local_path = "flash:/"

# Local config name             
config_local_name = "startup.cfg"

# Server config name
config_server_name = "startup.cfg"

# Local irf name     
irf_local_name = "inventory.txt"

# Server irf name
irf_server_name = "inventory.txt"

python_log_name = ""

# Write Log File
def write2Log(info):
  global python_log_name, local_path
  if python_log_name == "":
    try:
      python_log_name = "%s%s_%s.log" %(local_path, strftime("%Y%m%d%H%M%S", gmtime()), os.getpid())
    except Exception as inst:
      print inst
  fd = open(python_log_name, "a")
  fd.write(info)
  fd.flush()
  fd.close()

# get path according to the Chassis and Slot  
def getPath(chassisID, slotID):
  global local_path
  path = ""
  # print "Path %s" % path
  obj = comware.get_self_slot()
  if (obj[0] == chassisID) and (obj[1] == slotID):
    return local_path
  if chassisID != -1:
    path = "chassis%d#" % chassisID
  if slotID != -1:
    path = "%sslot%d#%s" %(path, slotID, local_path)
  # Changed on 02/10/2018
  print "Path %s" % path
  return path

# Remove File
def removeFile(filename):
  try:
    os.remove(filename)
  except os.error:
    pass
    
# Cleanup the temp files on the device 
def cleanDeviceFiles(str, oDevNode):
  global config_local_name, irf_local_name
  sFilePath = getPath(oDevNode[0], oDevNode[1])
  if str == "error":
    removeFile("%s%s" %(sFilePath, config_local_name))
  removeFile("%s%s" %(sFilePath, irf_local_name)) 
  write2Log("\ndelete all temporary files on %s\n" %sFilePath) 
  print "\ndelete all temporary files on %s\n" %sFilePath

# Cleanup files
def cleanupFiles(str):
  aSlotRange = []
  if ("get_standby_slot" in dir(comware)):
    aSlotRange = aSlotRange + comware.get_standby_slot()	
  aSlotRange.append(comware.get_self_slot())
  i = 0
  while i < len(aSlotRange):
    if(aSlotRange[i] != None):
      cleanDeviceFiles(str, aSlotRange[i])
    i = i + 1
    
def doExit(exit_status):
  if ( exit_status == "success" ):
    write2Log("\nThe script has finished successfully!")
    print "\n#### The script has finished successfully! ####"  
    cleanupFiles("success")
    comd = "reboot force"
    write2Log("\n## Rebooting device")
    print "\n#### REBOOTING DEVICE NOW ####" 
    comware.CLI(comd, False)  
    exit(0)
  if ( exit_status == "error" ):
    write2Log("\nThe script failed!")
    print "\n#### The script failed! ####"
    cleanupFiles("error")
    exit(1)
  else:
    exit(0)

# Get Chassis and Slot
def getChassisSlot(style):
  if style == "master":
    obj = comware.get_self_slot()
  if len(obj) <= 0:
    write2Log("get %s chassis and slot failed" % style)
    print "\n####get %s chassis and slot failed####" % style
    return None
  return obj

# Signal terminal handler function
def sig_handler_no_exit(signum, function):
  write2Log("\nSIGTERM Handler while configuring boot-loader variables")
  print "\n#### SIGTERM Handler while configuring boot-loader variables ####"

# Signal terminal handler
def sigterm_handler(signum, function):
  write2Log("\nSIGTERM Handler")
  print "\n#### SIGTERM Handler ####"
  cleanupFiles("error")
  doExit("error")
  
# Transfer file
def doCopyFile(src = "", des = "", login_timeout = 10):
  global username, password, tftp_server, protocol, vrf
  print "INFO: Starting Copy of %s" % src
  try:
    removeFile(des)
    obj = comware.Transfer(protocol, tftp_server, src, des, vrf, login_timeout, username, password)
    if obj.get_error() != None:
      write2Log("copy %s failed: %s" % (src, obj.get_error()))
      print "\n#### copy %s failed: %s ####" % (src, obj.get_error())
      return False
  except Exception as inst:
    write2Log("\ncopy %s exception: %s" % (src, inst))
    print "\n#### copy %s exception: %s ####" % (src, inst)
    return False
  write2Log("\ncopy file %s to %s success" % (src, des))
  print "INFO: Completed Copy of %s" % src
  return True

  
def getSerialNumber(): 
  result = comware.CLI('screen-length disable ; display device manuinfo | in DEVICE_SERIAL_NUMBER ; ', False).get_output()
  return result[2].split(":")[1].strip()
  
  
# Get config file according to the mode
def getCfgFileName():
  global config_server_name
  config_server_name = "%s.cfg" % getSerialNumber()
  return config_server_name

  
# Copy file to all standby slot
def syncFileToStandby(sSrcFile, sFileName):
  try:
    aSlotRange = []
    if ("get_standby_slot" in dir(comware)):
      aSlotRange = aSlotRange + comware.get_standby_slot()	
    i = 0
    while i < len(aSlotRange):
      if(aSlotRange[i] != None):
        sDestFile = "%s%s" %(getPath(aSlotRange[i][0], aSlotRange[i][1]), sFileName)
        removeFile(sDestFile)
        open(sDestFile,"wb").write(open(sSrcFile,"rb").read())
        write2Log("\nsync file to standby %s" % (sDestFile))
        print "\n#### sync file to standby %s####" % (sDestFile)
      i = i + 1
  except Exception as inst:
    write2Log("\nsync file to standby %s exception: %s" % (sSrcFile, inst))
    print "\n#### sync file to standby %s exception: %s ####" % (sSrcFile, inst)
 
 
# Procedure to copy config file using global information 
def copyAndCheckFile(src, dest, timeout):
  global server_path, local_path, config_server_name
  srcTmp = "%s%s" % (server_path, src)
  sDestFile = "%s%s" % (local_path, dest)
  if (True == doCopyFile(srcTmp, sDestFile, timeout)):
    syncFileToStandby(sDestFile, dest)
    return True
  else:
    # No Configuration file for the Serial-Number found; try to get the file "template.cfg"
    srcTmp = "template.cfg" 
    print "\nUsing %s instead of file %s" % (srcTmp,config_server_name)
    write2Log("\nUsing %s instead of file %s" % (srcTmp,config_server_name))
    if (True == doCopyFile(srcTmp, sDestFile, timeout)):
      # syncFileToStandby(dest)
      syncFileToStandby(sDestFile, dest)
      return True
  return False

# Split the Chassis and Slot  
def splitChassisSlot(chassisID, slotID):
  chassis_slot = ""
  if chassisID != -1:
    chassis_slot = " chassis %d"  % chassisID
  if slotID != -1:
    chassis_slot = "%s slot %d" %(chassis_slot, slotID)
  return chassis_slot


def copyCfgFile():
  global config_timeout, local_path, config_local_name
  src = "%s" % getCfgFileName()
  return copyAndCheckFile(src, config_local_name, config_timeout)
  # return True

def copyIrfStack():
  global irf_timeout, local_path, irf_local_name, irf_server_name
  src = "%s" % irf_server_name
  return copyAndCheckFile(src, irf_local_name, config_timeout)


def startupCfg():
  global local_path, config_local_name
  result = None
  dest = "%s%s" %(local_path, config_local_name)
  write2Log("\nstartup saved-configuration %s begin" %dest)
  print "INFO: Startup Saved-configuration Start"
  comd = "startup saved-configuration %s main" % dest
  try:
    result = comware.CLI(comd, False)
    if result == None:
      write2Log("\nstartup saved-configuration %s failed" % dest)
      print "\n#### startup saved-configuration %s failed####" % dest
      return False
  except Exception as inst:
    write2Log("\nstartup %s exception: %s" % (dest, inst))
    print "\n#### startup %s exception: %s####" % (dest, inst)
    return False
  write2Log("\nstartup saved-configuration %s success" % dest)
  print "INFO: Completed Startup Saved-configuration"
  return True

  
def getIrfCfg(line, num):
  line = line.split()
  number = None
  # Do we have 3 parameters for each line of the inventory file?
  if ( len(line) == 3 ):
    number = line[num]
  else :
    number = None
  return number  

def getMemberID():
  aMemId = comware.get_self_slot()
  memId = None
  if aMemId[0] == -1 :
    memId = aMemId[1]
  else :
    memId = aMemId[0]
  return memId


def getNewMemberID():
  global irf_local_name, local_path, env
  filename = "%s%s" %(local_path, irf_local_name)
  serNum = getSerialNumber()
  write2Log("\nDevice Serial-Number: %s" % serNum)
  print "\n#### Chassis or Slot SN : %s" % serNum
  # The default IRF ID is 1
  reNum = 1
  try:
    file = open(filename, "r")
    line = file.readline()
    while "" != line:
      if (serNum == getIrfCfg(line, 0)):
        file.close()
        reNum = getIrfCfg(line, 2)
        return reNum
      line = file.readline()
    file.close()
  except Exception as inst:
    write2Log("\nget renumberID exception: %s" % inst)
    print "\n####get renumberID exception: %s####" % inst
  write2Log("\nNo IRF ID found in file %s" % filename)
  print "\n#### No IRF ID found in file %s ####" % filename
  return reNum

def isIrfDevice():
  try: 
    result = comware.CLI("display irf", False) 
    if result == None: 
      return False
  except Exception as inst: 
    return False
  return True

def getIrfComd():
  comd = None
  newMemberID = getNewMemberID()
  aMemId = comware.get_self_slot()
  if None == newMemberID:
    return None
  if False == isIrfDevice():
    comd = "system-view ; irf member %s ; chassis convert mode irf" % newMemberID
  else:
    comd = "system-view ; irf member %s renumber %s" % (getMemberID(), newMemberID)
  return comd
    
def stackIrfCfg():
  global env
  if (not os.environ.has_key('DEV_SERIAL')):
    write2Log("\nenviron variable 'DEV_SERIAL' is not found!")
    print "\n####environ variable 'DEV_SERIAL' is not found!####"  
    return False
  comd = getIrfComd()
  if None == comd:
    return False
  result = None
  write2Log("\nstartup stack IRF begin")
  print "INFO: Startup stack IRF Start"
  try:
    result = comware.CLI(comd, False)
    if result == None:
      write2Log("\nstartup stack IRF failed: %s" % comd)
      print "\n####startup stack IRF failed: %s####" %comd
      return False
  except Exception as inst: 
    write2Log("\nstartup stack IRF exception: %s command: %s" % (inst, comd))
    print "\n#### startup stack IRF exception: %s command: %s ####" % (inst, comd)
    return False
  write2Log("\nstartup stack IRF success")
  print "INFO: Completed Startup Stack IRF"
  return True

# Check if all standby slots are ready
def ifAllStandbyReady():
  if (("get_slot_range" in dir(comware)) == False):
    return True
    
  aSlotRange = comware.get_slot_range()
  bAllReady = True
  for i in range(aSlotRange["MinSlot"], aSlotRange["MaxSlot"]):
    oSlotInfo =  comware.get_slot_info(i)
    if (oSlotInfo != None) and (oSlotInfo["Role"] == "Standby") and (oSlotInfo["Status"] == "Fail"):
      bAllReady = False
      write2Log("\nSlot %s is not ready!" %i)
      print "\n#### Slot %s is not ready! ####" %i
  return bAllReady
  

# If any standby slot was not ready sleep for waiting
def waitStandbyReady():
  while ifAllStandbyReady() == False:
    sleep(10)

  
# Python Main Script

# when download file user can stop script
waitStandbyReady()
signal.signal(signal.SIGTERM, sigterm_handler)

if (True == copyCfgFile()) and (True == copyIrfStack()):
  # after download file user can not stop script
  signal.signal(signal.SIGTERM, sig_handler_no_exit)
  # if (True == installBootImage()) and (True == startupCfg()) and (True == stackIrfCfg()):
  if (True == startupCfg()) and (True == stackIrfCfg()):
    doExit("success")
doExit("error")
