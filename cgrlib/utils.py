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
import os # For diagnosing exceptions
import collections # For rotatable lists
import shutil # For copying files
import termios # For catching termios exceptions

import ConfigParser # For writing and reading the config file
from configobj import ConfigObj # For writing and reading config file


utilnum = 47

# create logger
module_logger = logging.getLogger('root.utils')
module_logger.setLevel(logging.DEBUG)

# comports() returns a list of comports available in the system
from serial.tools.list_ports import comports 


cmdterm = '\r\n' # Terminates each command

def int8_to_dec(signed):
    """Return a signed decimal number given a signed 8-bit integer

    Arguments:
      signed -- Signed 8-bit integer (0-255)
    
    """
    if (signed > 127):
        decimal = signed - 256
    else:
        decimal = signed
    return decimal
    

def write_cal(handle, calfile, caldict):
    """Write calibration constants to a file and to the eeprom.

    See the caldict_default definition for the list of dictionary
    entries.  If the specified calfile exists, it will be saved as
    calfile_old and a new calfile will be written.

    Arguments:
      handle -- Serial object for the CGR-101
      calfile -- Filename for saving calibration constants.
      caldict -- A dictionary of (calibration factor names) : values

    """
    try:
        with open(calfile):
            # If this succeeds, the file already exists.  See if
            # anything has changed.
            caldict_old = load_cal(handle, calfile)
            calchanged = False
            for key in caldict:
                if (caldict[key] != caldict_old[key]):
                    calchanged = True
                    module_logger.debug('Cal factor ' + key + ' has changed')
                    module_logger.debug(str(caldict_old[key]) + ' --> ' +
                                        str(caldict[key]))
            if calchanged:
                # The calibration has changed.  Back up the old
                # calibration file and write a new one.
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
        # The calfile doesn't exist, so write one.
        module_logger.info('Writing calibration to ' + calfile)
        with open(calfile,'w') as fout:
            pickle.dump(caldict,fout)
            fout.close()
    # Write eeprom values
    set_eeprom_offlist(
        handle,
        [caldict['chA_10x_eeprom'],caldict['chA_1x_eeprom'],
         caldict['chB_10x_eeprom'],caldict['chB_1x_eeprom']]
    )
                       
        


"""Specify a default calibration dictionary.  

This dictionary definition is also where all the calibration factors
are defined.  If you want to add another factor, this is the place to
do it.

eeprom values are offsets to be stored in eeprom.  Values are scaled
from their file-based values by the eeprom_scaler factor.  If you
change this factor, you must remove the pickled calibration file and
recalibrate.

"""
caldict_default = {
    'eeprom_scaler': 5.0,
    'chA_1x_offset': 0,
    'chA_1x_eeprom': 0,
    'chA_1x_slope': 0.0445,
    'chA_10x_offset': 0,
    'chA_10x_eeprom':0,
    'chA_10x_slope': 0.0445,
    'chB_1x_offset': 0,
    'chB_1x_eeprom': 0,
    'chB_1x_slope': 0.0445,
    'chB_10x_offset': 0,
    'chB_10x_eeprom': 0,
    'chB_10x_slope': 0.0445,
}

def load_cal(handle, calfile):
    """Load and return calibration constant dictionary.

    If the calibration file exists, use the coefficients in it.  If it
    doesn't, load calibration offsets from the CGR unit.  Use these
    values in the caldict_default dictionary.

    Arguments:
      handle -- Serial object for the CGR-101
      calfile -- Filename for calibration constants saved in Python's
                 pickle format.

    """
    try:
        # Try loading the calibration file
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
        # We didn't find the calibration file.  Load constants from eeprom.
        module_logger.warning(
            'Failed to open calibration file...using defaults'
        )
        eeprom_list = get_eeprom_offlist(handle)
        caldict = caldict_default
        # Fill in offsets from eeprom values
        caldict['chA_10x_offset'] = int8_to_dec(
            eeprom_list[0]/caldict['eeprom_scaler']
        )
        caldict['chA_1x_offset'] = int8_to_dec(
            eeprom_list[1]/caldict['eeprom_scaler']
        )
        caldict['chB_10x_offset'] = int8_to_dec(
            eeprom_list[2]/caldict['eeprom_scaler']
        )
        caldict['chB_1x_offset'] = int8_to_dec(
            eeprom_list[3]/caldict['eeprom_scaler']
        )
    return caldict


def get_cgr(config):
    """ Return a serial object for the cgr scope

    Arguments:
      config -- Configuration object read from configuration file.
    """
    # The comports() function returns an iterable that yields tuples of
    # three strings:
    #
    # 1. Port name as it can be passed to serial.Serial
    # 2. Description in human readable form
    # 3. Sort of hardware ID -- may contain VID:PID of USB-serial adapters.
    portset = set(comports()) # Use set to prevent repeats
    # Add undetectable serial ports here
    portset.add(('/dev/ttyS0', 'ttyS0', 'n/a'))
    portset.add(('/dev/ttyS1', 'ttyS1', 'n/a'))
    portset.add(('/dev/ttyS2', 'ttyS2', 'n/a'))
    portset.add(('/dev/ttyS3', 'ttyS3', 'n/a'))
    portset.add(('/dev/ttyS4', 'ttyS4', 'n/a'))
    portset.add(('/dev/ttyS5', 'ttyS5', 'n/a'))
    portset.add(('/dev/ttyS6', 'ttyS6', 'n/a'))
    portset.add(('/dev/ttyS7', 'ttyS7', 'n/a'))
    portset.add(('/dev/ttyS8', 'ttyS8', 'n/a'))
    portset.add(('/dev/ttyS9', 'ttyS9', 'n/a'))
    
    # Add the port specified in the configuration to the front of the
    # list.  We have to convert the set object to a list because set
    # objects do not support indexing.
    portlist = [(config['Connection']['port'],'','')] + list(portset)

    for serport in portlist:
        rawstr = ''
        try:
            cgr = serial.Serial()
            cgr.baudrate = 230400
            cgr.timeout = 0.1 # Set timeout to 100ms
            cgr.port = serport[0]
            module_logger.debug('Trying to connect to CGR-101 at ' + serport[0])
            cgr.open()
            # If the port can be configured, it might be a CGR.  Check
            # to make sure.
            retnum = cgr.write("i\r\n") # Request the identity string
            rawstr = cgr.read(10) # Read a small number of bytes
            cgr.close()
            if rawstr.count('Syscomp') == 1:
                # Success!  We found a CGR-101 unit!
                module_logger.info('Connecting to CGR-101 at ' +
                                    str(serport[0]))
                # Write the successful connection port to the configuration
                config['Connection']['port'] = str(serport[0])
                config.write()
                return cgr
            else:
                module_logger.info('Could not open ' + serport[0])
                if serport == portlist[-1]: # This is the last port
                    module_logger.error(
                        'Did not find any CGR-101 units.  Exiting.'
                    )
                    sys.exit()
        # Catch exceptions caused by problems opening a filesystem node as
        # a serial port, by problems caused by the node not existing, and
        # general tty problems.
        except (serial.serialutil.SerialException, 
                OSError, termios.error):
            module_logger.debug('Could not open ' + serport[0])
            if serport == portlist[-1]: # This is the last port
                module_logger.error(
                    'Did not find any CGR-101 units.  Exiting.'
                )
                sys.exit()
        # This exception should never get handled.  It's just for debugging.
        except Exception as ex:
            template = "An exception of type: {0} occured. Arguments:\n{1!r}"
            message = template.format((type(ex).__module__ + '.' + 
                                       type(ex).__name__), ex.args)
            module_logger.error(message)
            sys.exit()


def flush_cgr(handle):
    readstr = 'junk'
    while (len(readstr) > 0):
        readstr = handle.read(100)
        module_logger.info('Flushed ' + str(len(readstr)) + ' characters')


def sendcmd(handle,cmd):
    """ Send an ascii command string to the CGR scope.

    Arguments:
      handle -- Serial object for the CGR scope
      cmd -- Command string

    """
    handle.write(cmd + cmdterm)
    module_logger.debug('Sent command ' + cmd)
    time.sleep(0.1) # Can't run at full speed.


def get_samplebits(fsamp_req):
    """Returns a valid sample rate setting.

    Given a sample rate in Hz, returns the closest possible hardware
    sample rate setting.  This setting goes in bits 0:3 of the control
    register.

    The sample rate is given by (20Ms/s)/2**N, where N is the 4-bit
    value returned by this function.

    Arguments:
      fsamp_req -- The requested sample rate in Hz.
    
    """
    baserate = 20e6 # Maximum sample rate
    ratelist = []
    for nval in range(2**4):
        ratelist.append( (baserate / ( 2**nval )) )
    fsamp_act = min(ratelist, key=lambda x:abs(x - fsamp_req))
    setval = ratelist.index(fsamp_act)
    return [setval,fsamp_act]


def askcgr(handle,cmd):
    """Send an ascii command to the CGR scope and return its reply.

    Arguments:
      handle -- Serial object for the CGR scope
      cmd -- Command string

    """
    sendcmd(handle,cmd)
    try:
        retstr = handle.readline()
        return(retstr)
    except:
        return('No reply')


def get_state(handle):
    """ Return the CGR's state string

    Returned string     Corresponding state
    ---------------------------------------
    State 1             Idle
    State 2             Initializing capture
    State 3             Wait for trigger signal to reset
    State 4             Armed, waiting for capture
    State 5             Capturing
    State 6             Done

    Arguments:
      handle -- Serial object for the CGR scope
    """
    handle.open()
    retstr = askcgr(handle,'S S')
    print(retstr)
    if (retstr == "No reply"):
        print('getstat: no response')
    handle.close() 
    return retstr


def get_timelist(fsamp):
    """Return a list of sample times

    Arguments:
      fsamp -- Sample rate in Hz

    Remember that the CGR-101 takes 2048 samples, but this is a total
    for both channels.  Each channel will have 1024 samples.  The
    sample rate calculation is based on these 1024 samples -- not
    2048.

    """
    timelist = []
    for samplenum in range(1024):
        timelist.append( samplenum * (1.0/fsamp) )
    return timelist


def get_eeprom_offlist(handle):
    """Returns the offsets stored in the CGR's eeprom.  This will be a
    list of signed integers:

    [Channel A 10x range offset, Channel A 1x range offset,
     Channel B 10x range offset, Channel B 1x range offset]

    """
    handle.open()
    sendcmd(handle,'S O')
    retdata = handle.read(10)
    handle.close()
    hexdata = binascii.hexlify(retdata)[2:]
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


def set_eeprom_offlist(handle,offlist):
    """Sets offsets in the CGR's eeprom.
    
    Arguments:
      handle -- Serial object for the CGR-101
      offlist -- List of signed 8-bit integers:

    [Channel A 10x range offset, 
     Channel A 1x range offset, 
     Channel B 10x range offset, 
     Channel B 1x range offset]
  
    """
    unsigned_list = []
    for offset in offlist:
        if (offset < 0):
            unsigned_list.append(offset + 256)
        else:
            unsigned_list.append(offset)
    handle.open()
    module_logger.debug('Writing chA 10x offset of ' + str(unsigned_list[0]) +
                        ' to eeprom')
    module_logger.debug('Writing chA 1x offset of ' + str(unsigned_list[1]) +
                        ' to eeprom')
    module_logger.debug('Writing chB 10x offset of ' + str(unsigned_list[2]) +
                        ' to eeprom')
    module_logger.debug('Writing chB 1x offset of ' + str(unsigned_list[3]) +
                        ' to eeprom')
    sendcmd(handle,('S F ' + 
                    str(unsigned_list[0]) + ' ' +
                    str(unsigned_list[1]) + ' ' +
                    str(unsigned_list[2]) + ' ' +
                    str(unsigned_list[3]) + ' '
                )
    )
    handle.close()
                    
                                 
def set_trig_samples(handle,trigdict):
    """Set the number of samples to take after a trigger.  

    The unit always takes 1024 samples per channel.  Setting the
    post-trigger samples to a value less than 1024 means that samples
    before the trigger will also be stored.

    Arguments:
      handle -- Serial object for the CGR-101
      trigdict -- Dictionary of trigger settings.  See get_trig_dict for
                  more details. 

    """
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
    

def set_ctrl_reg(handle,fsamp_req,trigdict):
    """ Sets the CGR-101's conrol register.

    Arguments:
      handle -- Serial object for the CGR-101
      fsamp_req -- Requested sample rate in Hz.  The actual rate will
                   be determined using those allowed for the unit.
      trigdict -- Dictionary of trigger settings.  See get_trig_dict
                  for more details.

    """
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


def set_hw_gain(handle,gainlist):
    """Sets the CGR-101's hardware gain.

    Arguments:
      handle -- Serial object for the CGR-101.
      gainlist -- [Channel A gain, Channel B gain]

    ...where the gain values are:
      0: Set 1x gain
      1: Set 10x gain (for use with a 10x probe)
    
    """
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


def get_trig_dict( trigsrc, triglev, trigpol, trigpts ):
    """Return a dictionary of trigger settings.

    Arguments:
      trigsrc -- Trigger source
                 0: Channel A
                 1: Channel B
                 2: External
                 3: Internal
      triglev -- Trigger voltage (floating point volts)
      trigpol -- Trigger slope
                 0: Rising
                 1: Falling
      trigpts -- Points to acquire after trigger (0,1,2,...,1024)
    """
    trigdict = {}
    trigdict['trigsrc'] = trigsrc
    trigdict['triglev'] = triglev
    trigdict['trigpol'] = trigpol
    trigdict['trigpts'] = trigpts
    return trigdict


def set_trig_level(handle, caldict, gainlist, trigdict):
    """Sets the trigger voltage.

    Arguements:
      handle -- Serial object for the CGR-101
      caldict -- Dictionary of slope and offset values
      gainlist -- [Channel A gain, Channel B gain]
      trigdict -- Dictionary of trigger settings.  See get_trig_dict
                  for more details.
    """
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


def get_uncal_triggered_data(handle, trigdict):
    """Return uncalibrated integer data.

    If you just ask the CGR for data, you'll get its circular buffer
    with the last point acquired somewhere in the middle.  This
    function rotates the buffer data so that the last point acquired
    is the last point in the returned array.

    Returned data is:
      [ list of channel A integers, list of channel B integers ] 

    Arguments:
      handle -- Serial object for the CGR-101.
      trigdict -- Dictionary of trigger settings (see get_trig_dict
                  for more details.
    """
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


def reset(handle):
    """ Perform a hardware reset.
    """
    handle.open()
    sendcmd(handle,('S D 1' )) # Force the reset
    sendcmd(handle,('S D 0' )) # Return to normal
    handle.close()


def force_trigger(handle, ctrl_reg):
    """Force a trigger.

    This sets bit 6 of the control register to configure triggering
    via the external input, then sends a debug code to force the
    trigger.

    Arguments:
      handle -- Serial object for the CGR-101.
      ctrl_reg -- Value of the control register.

    """
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
    

def get_uncal_forced_data(handle,ctrl_reg):
    """ Returns uncalibrated data from the unit after a forced trigger.

    Returned data is:
      [ list of channel A integers, list of channel B integers ]

    Arguments:
      handle -- Serial object for the CGR-101.
      ctrl_reg -- Value of the control register.

    """
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

        
def get_cal_data(caldict,gainlist,rawdata):
    """Return calibrated voltages.

    Arguments:
      caldict -- Dictionary of calibration constants.  See 
                 caldict_default for the keys in this dictionary.
      gainlist -- List of gain settings: 
                 [Channel A gain, Channel B gain]
      rawdata -- List of uncalibrated data downloaded from CGR-101:
                 [Channel A data, Channel B data]
    """
    if gainlist[0] == 0:
        # Channel A has 1x gain
        chA_slope = caldict['chA_1x_slope']
        chA_offset = caldict['chA_1x_offset']
    elif gainlist[0] == 1:
        # Channel A has 10x gain
        chA_slope = caldict['chA_10x_slope']
        chA_offset = caldict['chA_10x_offset']
    if gainlist[1] == 0:
        # Channel B has 1x gain
        chB_slope = caldict['chB_1x_slope']
        chB_offset = caldict['chB_1x_offset']
    elif gainlist[1] == 1:
        # Channel B has 10x gain
        chB_slope = caldict['chB_10x_slope']
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
