# utils.py
#
# Utility functions for use with the CGR-101 USB oscilloscope 

import logging  # The python logging module
import serial   # Provides serial class Serial
import time     # For making pauses
from datetime import datetime # For finding calibration time differences
import binascii # For hex string conversion
import pickle # For writing and reading calibration data
import sys # For sys.exit()
import collections # For rotatable lists
import shutil # For copying files

import ConfigParser # For writing and reading the config file
from configobj import ConfigObj # For writing and reading config file


utilnum = 42

# create logger
module_logger = logging.getLogger('root.utils')
module_logger.setLevel(logging.DEBUG)

# comports() returns a list of comports available in the system
from serial.tools.list_ports import comports 


cmdterm = '\r\n' # Terminates each command

# Specify a default calibration dictionary.  This dictionary
# definition is also where all the calibration factors are defined.
# If you want to add another factor, this is the place to do it.
caldict_default = {'chA_1x_offset': 0,
                   'chA_1x_offset_caldate': 'none',
                   'chA_1x_slope': 0.0445,
                   'chA_1x_slope_caldate': 'none',
                   'chA_10x_offset': 0,
                   'chA_10x_offset_caldate': 'none',
                   'chA_10x_slope': 0.0445,
                   'chA_10x_slope_caldate': 'none',
                   'chB_1x_offset': 0,
                   'chB_1x_offset_caldate': 'none',
                   'chB_1x_slope': 0.0445,
                   'chB_1x_slope_caldate': 'none',
                   'chB_10x_offset': 0,
                   'chB_10x_offset_caldate': 'none',
                   'chB_10x_slope': 0.0445,
                   'chB_10x_slope_caldate': 'none'
}


# write_cal(calfile, caldict)
#
# Writes the unit's calibration constants.  See the caldict_default
# definition for a list of dictionary entries.  If the specified
# calfile exists, it will be saved as calfile_old and a new calfile
# will be written.
#
# Inputs:
#     calfile: Filename for pickled calibration constants.  This
#              filename should be specified in the application's
#              configuration file.
#
#     caldict: A dictionary of (calibration factor names) : values
#
# Returns:
#     None
def write_cal(calfile, caldict):
    try:
        with open(calfile):
            # If this succeeds, the file already exists.  Copy the
            # existing file to an old version.
            calfile_old = (calfile.split('.')[0] + '_old.' + 
                           calfile.split('.')[1])
            module_logger.info(
                'Backing up calibration file ' + calfile + 
                ' to ' + calfile_old
            )
            shutil.copyfile(calfile,(
                calfile.split('.')[0] + '_old.' + calfile.split('.')[1]
            ))
            module_logger.info('Writing calibration to ' + calfile)
            with open(calfile,'w') as fout:
                pickle.dump(caldict,fout)
                fout.close()
    except IOError:
        module_logger.info('Writing calibration to ' + calfile)
        with open(calfile,'w') as fout:
            pickle.dump(caldict,fout)
            fout.close()
        

# load_cal(calibration file)
#
# Loads and returns the calibration constants.  Loads some defaults
# into the calibration dictionary if a calibration file isn't found.
#
# Inputs:
#     calfile: Filename for pickled calibration constants.  This
#              filename should be specified in the application's
#              configuration file.
#
# Returns:
#     caldict: A dictionary of (calibration factor names) : values
# 
def load_cal(calfile):
    try:
        module_logger.info('Loading calibration file ' + calfile)
        fin = open(calfile,'rb')
        caldict = pickle.load(fin)
        # Make sure all needed calibration factors are in the dictionary
        for key in caldict_default:
            if not key in caldict:
                module_logger.info('Adding calibration value ' +
                                   str(key) + ' to dictionary.'
                )
                caldict[key] = caldict_default[key]
        fin.close()
    except IOError:
        module_logger.warning(
            'Failed to open calibration file...using defaults'
        )
        caldict = caldict_default
    return caldict

# get_cgr() 
#
# Returns a serial object for the cgr scope, or an error
# message if the connection fails.
#
# Inputs:
#     None
#
# Returns: 
#     cgr: Serial communication object corresponding to the CGR-101
#          USB oscilloscope.
def get_cgr():
    # The comports() function returns an iterable that yields tuples of
    # three strings:
    #
    # 1. Port name as it can be passed to serial.Serial
    # 2. Description in human readable form
    # 3. Sort of hardware ID -- may contain VID:PID of USB-serial adapters.
    portset = set(comports()) # Use set to prevent repeats
    # Add undetectable serial ports here
    portset.add(('/dev/ttyS0', 'ttyS0', 'n/a'))
    portset.add(('/dev/ttyS9', 'ttyS9', 'n/a'))
    portset.add(('/dev/ttyS3', 'ttyS3', 'n/a'))
    portlist = list(portset) # set objects do not support indexing

    for serport in portlist:
        rawstr = ''
        try:
            cgr = serial.Serial()
            cgr.baudrate = 230400
            cgr.timeout = 0.1 # Set timeout to 100ms
            cgr.port = serport[0]
            cgr.open()
            # If the port can be configured, it might be a CGR.  Check
            # to make sure.
            retnum = cgr.write("i\r\n") # Request the identity string
            rawstr = cgr.read(10) # Read a small number of bytes
            cgr.close()
            if rawstr.count('Syscomp') == 1:
                module_logger.info('Connecting to CGR-101 at ' +
                                    str(serport[0]))
                return cgr
            else:
                module_logger.info('Could not open ' + serport[0])
                portset.remove(serport)
                if serport == portlist[-1]: # This is the last port
                    module_logger.error('Did not find any CGR-101 units')
                    sys.exit()
        # Catch exceptions caused by problems opening a filesystem node as
        # a serial port, and by problems caused by the node not existing.
        except (serial.serialutil.SerialException, OSError):
            module_logger.info('Could not open ' + serport[0])
            portset.remove(serport)
            if serport == portlist[-1]: # This is the last port
                module_logger.error('Did not find any CGR-101 units')
                sys.exit()
        # This exception should never get handled.  It's just for debugging.
        except Exception as ex:
            template = "An exception of type {0} occured. Arguments:\n{1!r}"
            message = template.format(type(ex).__name__, ex.args)
            print message
            sys.exit()




def flush_cgr(handle):
    readstr = 'junk'
    while (len(readstr) > 0):
        readstr = handle.read(100)
        module_logger.info('Flushed ' + str(len(readstr)) + ' characters')


# sendcmd(handle,command)
#    
# Send an ascii command string to the CGR scope
def sendcmd(handle,cmd):
    handle.write(cmd + cmdterm)
    module_logger.debug('Sent command ' + cmd)
    time.sleep(0.1) # Don't know if there's a command buffer




# get_samplebits(Requested sample rate)
#
# Given a sample rate in Hz, returns the closest possible hardware
# sample rate setting.  This setting goes in bits 0:3 of the control
# register.
#
# The sample rate is given by (20Ms/s)/2**N, where N is the 4-bit
# value returned by this function.
#
# Returns:
#  [value for control register, actual sample rate]
def get_samplebits(fsamp_req):
    baserate = 20e6 # Maximum sample rate
    ratelist = []
    for nval in range(2**4):
        ratelist.append( (baserate / ( 2**nval )) )
    fsamp_act = min(ratelist, key=lambda x:abs(x - fsamp_req))
    setval = ratelist.index(fsamp_act)
    return [setval,fsamp_act]

# askcgr(handle, command)
#
# Send a command to the unit and check for a response.
def askcgr(handle,cmd):
    sendcmd(handle,cmd)
    try:
        retstr = handle.readline()
        return(retstr)
    except:
        return('No reply')

# get_state(handle)
#
# Returns the state string from the unit.  The string may be:
# Returned string     Corresponding state
# ---------------------------------------
# State 1             Idle
# State 2             Initializing capture
# State 3             Wait for trigger signal to reset
# State 4             Armed, waiting for capture
# State 5             Capturing
# State 6             Done
def get_state(handle):
    handle.open()
    retstr = askcgr(handle,'S S')
    print(retstr)
    if (retstr == "No reply"):
        print('getstat: no response')
    handle.close() 
    return retstr


# get_timelist(sample rate)
#
# Returns the list of sample times.  Remember that the CGR-101 takes
# 2048 samples, but this is a total for both channels.  Each channel
# will have 1024 samples.  The sample rate calculation is based on
# these 1024 samples -- not 2048.
def get_timelist(fsamp):
    timelist = []
    for samplenum in range(1024):
        timelist.append( samplenum * (1.0/fsamp) )
    return timelist


# get_eeprom_offlist(handle)
# 
# Returns the offsets set in eeprom.  The offsets are in signed counts.
#
# [Channel A high range offset, Channel A low range offset,
#  Channel B high range offset, Channel B low range offset]
def get_eeprom_offlist(handle):
    handle.open()
    sendcmd(handle,'S O')
    retdata = handle.read(10)
    handle.close()
    hexdata = binascii.hexlify(retdata)[2:]
    print(hexdata)
    cha_hioff = int(hexdata[0:2],16)
    cha_looff = int(hexdata[2:4],16)
    chb_hioff = int(hexdata[4:6],16)
    chb_looff = int(hexdata[6:8],16)
    # Unsigned decimal list
    udeclist = [cha_hioff, cha_looff, chb_hioff, chb_looff]
    declist = []
    for unsigned in udeclist:
        if (unsigned > 127):
            signed = unsigned - 256
        else:
            signed = unsigned
        declist.append(signed)
    return declist



# set_trig_samples(handle,trigdict)
#
# Sets the number of samples to take after a trigger.  The unit always
# takes 1024 samples.  Setting the post-trigger samples to a value
# less than 1024 means that samples before the trigger will be saved
# instead.
#
# Arguments: 
#   handle -- serial object representing the CGR-101
#   trigdict -- see get_trig_dict function
def set_trig_samples(handle,trigdict):
    handle.open()
    totsamp = 1024
    if (trigdict['trigpts'] <= totsamp):
        setval_h = int((trigdict['trigpts']%(2**16))/(2**8))
        setval_l = int((trigdict['trigpts']%(2**8)))
    else:
        setval_h = int((500%(2**16))/(2**8))
        setval_l = int((500%(2**8)))
    sendcmd(handle,('S C ' + str(setval_h) + ' ' + str(setval_l)))
    handle.close()
    
# set_ctrl_reg( handle, fsamp, trigdict )
#
# Sets the CGR-101's control register.
#
# Arguments:
#  handle -- serial object representing the CGR-101
#  fsamp_req -- requested sample rate in Hz.  The actual rate will be
#               determined using those allowed for the unit.
#  trigdict -- see get_trig_dict function
#
# Returns: 
#   The new control register value
def set_ctrl_reg(handle,fsamp_req,trigdict):
    reg_value = 0
    [reg_value,fsamp_act] = get_samplebits(fsamp_req) # Set sample rate
    # Configure the trigger source
    if trigdict['trigsrc'] == 0: # Trigger on channel A
        reg_value += (0 << 4)
    elif trigdict['trigsrc'] == 1: # Trigger on channel B
        reg_value += (1 << 4)
    elif trigdict['trigsrc'] == 2: # Trigger on external input
        reg_value += (1 << 6)
    # Configure the trigger polarity
    if trigdict['trigpol'] == 0: # Rising edge
        reg_value += (0 << 5)
    elif trigdict['trigpol'] == 1: # Falling edge
        reg_value += (1 << 5)
    handle.open()
    sendcmd(handle,('S R ' + str(reg_value)))
    handle.close()
    return [reg_value,fsamp_act]

# set_hw_gain( handle, gainlist)
#
# Sets the CGR-101's hardware gain.  I don't think there's actually a
# switched voltage divider at the inputs.  Rather, I think this switch
# just applies an extra gain factor to measurements.  This is useful
# to accomodate things like scope probes.
#
# Arguments:
#  handle -- serial object representing the CGR-101
#  gainlist -- [cha_gain, chb_gain]
#
#  ...where the gain values are:
#  cha_gain -- Set the gain for channel A
#              0: Set 1x gain
#              1: Set 10x gain (for use with a 10x probe)
#  chb_gain -- Set the gain for channel B
#              0: Set 1x gain
#              1: Set 10x gain (for use with a 10x probe)
#
# Returns the gainlist: [cha_gain, chb_gain]
def set_hw_gain(handle,gainlist):
    handle.open()
    if gainlist[0] == 0: # Set channel A gain to 1x
        sendcmd(handle,('S P A'))
    elif gainlist[0] == 1: # Set channel A gain to 10x
        sendcmd(handle,('S P a'))
    if gainlist[1] == 0: # Set channel B gain to 1x
        sendcmd(handle,('S P B'))
    elif gainlist[1] == 1: # Set channel B gain to 10x
        sendcmd(handle,('S P b'))
    handle.close()
    return gainlist

# get_trig_dict( trigsrc, triglev, trigpol, trigpts )
#
# Make a dictionary of trigger settings.
#
# Arguments:
#  trigsrc -- Trigger source
#             0: Channel A
#             1: Channel B
#             2: External
#             3: Internal
#  triglev -- Trigger voltage (floating point volts)
#  trigpol -- Trigger slope
#             0: Rising
#             1: Falling
#  trigpts -- Points to acquire after trigger (0 --> 1024)
def get_trig_dict( trigsrc, triglev, trigpol, trigpts ):
    trigdict = {}
    trigdict['trigsrc'] = trigsrc
    trigdict['triglev'] = triglev
    trigdict['trigpol'] = trigpol
    trigdict['trigpts'] = trigpts
    return trigdict



# set_trig_level( handle, caldict, gainlist, trigdict)
#
# Sets the trigger voltage.
#
# Arguments:
#  handle -- serial object representing the CGR-101
#  caldict -- dictionary of slope and offset values
#  gainlist -- [cha_gain, chb_gain]
#  trigdict -- see get_trig_dict function
def set_trig_level(handle, caldict, gainlist, trigdict):
    handle.open()
    if (gainlist[0] == 0 and trigdict['trigsrc'] == 0): 
        # Channel A gain is 1x
        trigcts = (511 - caldict['chA_1x_offset'] - 
                   float(trigdict['triglev'])/caldict['chA_1x_slope'])
    elif (gainlist[0] == 1 and trigdict['trigsrc'] == 0): 
        # Channel A gain is 10x
        trigcts = (511 - caldict['chA_10x_offset'] - 
                   float(trigdict['triglev'])/caldict['chA_10x_slope'])
    elif (gainlist[1] == 0 and trigdict['trigsrc'] == 1): 
        # Channel B gain is 1x
        trigcts = (511 - caldict['chB_1x_offset'] - 
                   float(trigdict['triglev'])/caldict['chB_1x_slope'])
    elif (gainlist[1] == 1 and trigdict['trigsrc'] == 1): 
        # Channel B gain is 10x
        trigcts = (511 - caldict['chB_10x_offset'] - 
                   float(trigdict['triglev'])/caldict['chB_10x_slope'])
    else:
        trigcts = 511 # 0V
    trigcts_l = int(trigcts%(2**8))
    trigcts_h = int((trigcts%(2**16))/(2**8))
    sendcmd(handle,('S T ' + str(trigcts_h) + ' ' + str(trigcts_l)))
    handle.close()



# get_uncal_triggered_data(handle, trigdict)
#
# Arguments:
#  handle -- serial object representing the CGR-101
#  trigdict -- dictionary of trigger settings
# 
# Returns 
#  Uncalibrated integer data and the trigger position: 
#  [ A channel data, B channel data]
def get_uncal_triggered_data(handle, trigdict):
    handle.open()
    sendcmd(handle,'S G') # Start the capture
    sys.stdout.write('Waiting for ' + 
                     '{:0.1f}'.format(trigdict['triglev']) +
                     'V trigger at ')
    if trigdict['trigsrc'] == 0:
        print('input A...')
    elif trigdict['trigsrc'] == 1:
        print('input B...')
    elif trigdict['trigsrc'] == 2:
        print('external input...')
    retstr = ''
    # The unit will reply with 3 bytes when it's done capturing data:
    # "A", high byte of last capture location, low byte
    # Wait on those three bytes.
    while (len(retstr) < 3):
        retstr = handle.read(10)
    lastpoint = int(binascii.hexlify(retstr)[2:],16)
    module_logger.debug('Capture ended at address ' + str(lastpoint))
    sendcmd(handle,'S B') # Query the data
    retdata = handle.read(5000) # Read until timeout
    hexdata = binascii.hexlify(retdata)[2:]
    module_logger.debug('Got ' + str(len(hexdata)/2) + ' bytes')
    handle.close()
    bothdata = [] # Alternating data from both channels
    adecdata = [] # A channel data
    bdecdata = [] # B channel data 
    # Data returned from the unit has alternating words of channel A
    # and channel B data.  Each word is 16 bits (four hex characters)
    for samplenum in range(2048):
        sampleval = int(hexdata[(samplenum*4):(samplenum*4 + 4)],16)
        bothdata.append(sampleval)
    adecdata = collections.deque(bothdata[0::2])
    adecdata.rotate(1024-lastpoint)
    bdecdata = collections.deque(bothdata[1::2])
    bdecdata.rotate(1024-lastpoint)
    return [list(adecdata),list(bdecdata)]


# reset( handle )
# Perform a hardware reset
def reset(handle):
    handle.open()
    sendcmd(handle,('S D 1' )) # Force the reset
    sendcmd(handle,('S D 0' )) # Return to normal
    handle.close()


# force_trigger( handle, ctrl_reg )
#
# Force a trigger.  Set bit 6 of the control register to configure
# triggering via the external input, then send a debug code to force
# the trigger.
#
# Arguments:
#  handle -- serial object representing the CGR-101
#  ctrl_reg -- value of the control register
def force_trigger(handle, ctrl_reg):
    old_reg = ctrl_reg
    new_reg = ctrl_reg | (1 << 6)
    handle.open()
    sendcmd(handle,'S G') # Start the capture
    sendcmd(handle,('S R ' + str(new_reg))) # Ready for forced trigger
    module_logger.info('Forcing trigger')
    sendcmd(handle,('S D 5')) # Force the trigger
    sendcmd(handle,('S D 4')) # Return the trigger to normal mode
    # Put the control register back the way it was
    sendcmd(handle,('S R ' + str(old_reg)))
    handle.close()
    

# get_uncal_forced_data(handle, ctrl_reg)
#
# Arguments:
#  handle -- serial object representing the CGR-101
#  ctrl_reg -- value of the control register
#            
# Returns uncalibrated integer data from the unit.  Returns two lists
# of data:
# [ A channel data, B channel data]
def get_uncal_forced_data(handle,ctrl_reg):
    force_trigger(handle, ctrl_reg)
    handle.open()
    sendcmd(handle,'S B') # Query the data
    retdata = handle.read(5000)
    hexdata = binascii.hexlify(retdata)[2:]
    module_logger.debug('Got ' + str(len(hexdata)/2) + ' bytes')
    handle.close()
    # There is no last capture location for forced triggers. Setting
    # lastpoint to zero doesn't rotate the data.
    lastpoint = 0
    bothdata = [] # Alternating data from both channels
    adecdata = [] # A channel data
    bdecdata = [] # B channel data 
    # Data returned from the unit has alternating words of channel A
    # and channel B data.  Each word is 16 bits (four hex characters)
    for samplenum in range(2048):
        sampleval = int(hexdata[(samplenum*4):(samplenum*4 + 4)],16)
        bothdata.append(sampleval)
    adecdata = collections.deque(bothdata[0::2])
    adecdata.rotate(1024-lastpoint)
    bdecdata = collections.deque(bothdata[1::2])
    bdecdata.rotate(1024-lastpoint)
    return [list(adecdata),list(bdecdata)]


# get_cal_data(caldict,gainlist,rawdata)
#
# Convert raw data points to voltages.  Return the list of
# voltages. The raw data list contains samples from both channels.
#
# Inputs:
#     caldict: A dictionary of (calibration factor name) : values
#     gainlist: List of gain settings -- [chA_gain, chB_gain]
#     rawdata: 2D list of data downloaded from the CGR-101.
#              [Channel A data, Channel B data]
#
# Returns:
#     2D list of calibrated data in Volt units:  
#     [Channel A data, Channel B data]
#              
def get_cal_data(caldict,gainlist,rawdata):
    if gainlist[0] == 0:
        # Channel A has 1x gain
        # Check for an outdated slope calibration
        if ((caldict['chA_1x_slope_caldate'] == 'none') or
            ((caldict['chA_1x_slope_caldate'] - 
              datetime.now()).days >= 365)):
            module_logger.warning('Channel A 1x slope is out of date')
        chA_slope = caldict['chA_1x_slope']
        # Check for an outdated offset calibration
        if ((caldict['chA_1x_offset_caldate'] == 'none') or
            ((caldict['chA_1x_offset_caldate'] - 
              datetime.now()).days >= 365)):
            module_logger.warning('Channel A 1x offset is out of date')
        chA_offset = caldict['chA_1x_offset']
    elif gainlist[0] == 1:
        # Channel A has 10x gain
        # Check for an outdated slope calibration
        if ((caldict['chA_10x_slope_caldate'] == 'none') or
            ((caldict['chA_10x_slope_caldate'] - 
              datetime.now()).days >= 365)):
            module_logger.warning('Channel A 10x slope is out of date')
        chA_slope = caldict['chA_10x_slope']
        # Check for an outdated offset calibration
        if ((caldict['chA_10x_offset_caldate'] == 'none') or
            ((caldict['chA_10x_offset_caldate'] - 
              datetime.now()).days >= 365)):
            module_logger.warning('Channel A 10x offset is out of date')
        chA_offset = caldict['chA_10x_offset']
    if gainlist[1] == 0:
        # Channel B has 1x gain
        # Check for an outdated slope calibration
        if ((caldict['chB_1x_slope_caldate'] == 'none') or
            ((caldict['chB_1x_slope_caldate'] - 
              datetime.now()).days >= 365)):
            module_logger.warning('Channel B 1x slope is out of date')
        chB_slope = caldict['chB_1x_slope']
        # Check for an outdated offset calibration
        if ((caldict['chB_1x_offset_caldate'] == 'none') or
            ((caldict['chB_1x_offset_caldate'] - 
              datetime.now()).days >= 365)):
            module_logger.warning('Channel B 1x offset is out of date')
        chB_offset = caldict['chB_1x_offset']
    elif gainlist[1] == 1:
        # Channel B has 10x gain
        # Check for an outdated slope calibration
        if ((caldict['chB_10x_slope_caldate'] == 'none') or
            ((caldict['chB_10x_slope_caldate'] - 
              datetime.now()).days >= 365)):
            module_logger.warning('Channel B 10x slope is out of date')
        chB_slope = caldict['chB_10x_slope']
        # Check for an outdated offset calibration
        if ((caldict['chB_10x_offset_caldate'] == 'none') or
            ((caldict['chB_10x_offset_caldate'] - 
              datetime.now()).days >= 365)):
            module_logger.warning('Channel B 10x offset is out of date')
        chB_offset = caldict['chB_10x_offset']
    # Process channel A data
    cha_voltdata = []
    for sample in rawdata[0]:
        cha_voltdata.append((511 - (sample + chA_offset))*chA_slope)
    # Process channel B data
    chb_voltdata = []
    for sample in rawdata[1]:
        chb_voltdata.append((511 - (sample + chB_offset))*chB_slope)
    return [cha_voltdata,chb_voltdata]
