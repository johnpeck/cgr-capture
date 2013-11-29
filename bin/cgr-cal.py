# cgr_cal.py
#
# Automates slope and offset calibration

import time     # For making pauses
import os       # For basic file I/O
import ConfigParser # For reading and writing the configuration file
import sys # For sys.exit()

# -------------------- Configure argument parsing ---------------------
import argparse
parser = argparse.ArgumentParser(
   formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument("-o", "--outfile", help="output filename")
parser.add_argument("-r", "--rcfile" , default="cgr-cal.cfg",
                    help="Runtime configuration file")
args = parser.parse_args()
if args.outfile:
   print('Output file specified is ' + args.outfile)

# --------------- Done with configuring argument parsing --------------



#------------------------- Configure logging --------------------------
import logging
from colorlog import ColoredFormatter

# create logger
logger = logging.getLogger('root')
logger.setLevel(logging.DEBUG)

# create console handler (ch) and set level to debug
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)

# create file handler and set level to debug
fh = logging.FileHandler('cgrlog.log',mode='a',encoding=None,delay=False)
fh.setLevel(logging.DEBUG)

color_formatter = ColoredFormatter(
    '[ %(log_color)s%(levelname)-8s%(reset)s] %(message)s',
    datefmt=None,
    reset=True,
    log_colors={
        'DEBUG':    'cyan',
        'INFO':     'green',
        'WARNING':  'yellow',
        'ERROR':    'red',
        'CRITICAL': 'red',
    }
)

plain_formatter = logging.Formatter(
    '%(asctime)s - %(name)s - [ %(levelname)s ] - %(message)s',
    '%Y-%m-%d %H:%M:%S'
)

# Colored output goes to the console
ch.setFormatter(color_formatter)
logger.addHandler(ch)

# Plain output goes to the file
fh.setFormatter(plain_formatter)
logger.addHandler(fh)

# --------------- Done with logging configuration ---------------------

# Now that logging has been set up, bring in the utility functions.
# These will use the same logger as the root application.
from cgrlib import utils


# ------------------ Configure plotting with gnuplot ------------------

# For the Gnuplot module
from numpy import * # For gnuplot.py
import Gnuplot, Gnuplot.funcutils # For gnuplot.py

# Set the gnuplot executable
Gnuplot.GnuplotOpts.gnuplot_command = 'gnuplot'

# Use this option to turn off fifo if you get warnings like:
# line 0: warning: Skipping unreadable file "/tmp/tmpakexra.gnuplot/fifo"
Gnuplot.GnuplotOpts.prefer_fifo_data = 0

# Use temporary files instead of inline data
Gnuplot.GnuplotOpts.prefer_inline_data = 0

# Set the default terminal
Gnuplot.GnuplotOpts.default_term = 'x11'

# ------------------ Done with gnuplot configuration ------------------


cmdterm = '\r\n' # Terminates each command

# ------------- Configure runtime configuration file ------------------
from configobj import ConfigObj # For writing and reading config file
configfile = args.rcfile # The configuration file name

# ---------- Done with configuring runtime configuration --------------


# load_config(configuration file name)
#
# Open the configuration file (if it exists) and return the
# configuration object.  If the file doesn't exist, call the init
# function to create it.
# 
# This function could probably go in the library, since there's
# nothing unique about it.
def load_config(configFileName):
    try:
        logger.info('Reading configuration file ' + configFileName)   
        config = ConfigObj(configFileName,file_error=True)
        return config
    except IOError:
        logger.warning('Did not find configuration file ' +
                       configFileName)
        config = init_config(configFileName)
        return config


# init_config(configuration file name)
#
# Initialize the configuration file.  The file name should be
# specified by the user in the application code.  This function is
# unique to the application, so it's not really a library function.
def init_config(configFileName):
    config = ConfigObj()
    config.filename = configFileName
    config.initial_comment = [
        'Configuration file for cgr_cal.py',
        ' ']
    config.comments = {}
    config.inline_comments = {}
    #----------------------- Calibration section ----------------------
    config['Calibration'] = {}
    config['Calibration'].comments = {}
    config.comments['Calibration'] = ['Calibration configuration']
    config['Calibration']['calfile'] = 'cgrcal.pkl'
    config['Calibration'].comments['calfile'] = [
        "The calibration file in Python's pickle format"
        ]
    
   
    #-------------------------- Inputs section ------------------------
    config['Inputs'] = {}
    config['Inputs'].comments = {}
    config.comments['Inputs'] = [
        ' ',
        'Input configuration.  The unit is limited to measuring +/-25Vpp',
        'at its inputs with the 1x probe setting, and at the end of a 10x',
        'probe with the 10x probe setting.',
        ' ',
        'Calibration coefficients will only be measured for the',
        'configuration specified here -- if you want to calibrate to',
        'the ends of 10x probes, you have to attach probes and specify',
        'them below.'
    ]
    # Probe setting
    config['Inputs']['Aprobe'] = 0
    config['Inputs']['Bprobe'] = 0
    config['Inputs'].comments['Aprobe'] = [
        ' ',
        'Probe setting:',
        '0 -- 1x probe',
        '1 -- 10x probe'
    ]

    #------------------------- Acquire section ------------------------
    config['Acquire'] = {}
    config['Acquire'].comments = {}
    config.comments['Acquire'] = [
        ' ',
        'Acquisition configuration.'
    ]
    # Sample rate
    config['Acquire']['rate'] = 100000
    config['Acquire'].comments['rate'] = [
        ' ',
        'Sample rate (Hz)',
        'Minimum: 610.35',
        'Maximum: 20000000 (20Msps)',
        'Keep in mind that the cgr-101 has a fixed analog bandwidth of',
        '2MHz -- it does not move an anti-alias filter depending on the',
        'sample rate.'
    ]
    # Averages
    config['Acquire']['averages'] = 1
    config['Acquire'].comments['averages'] = [
        ' ',
        'Number of acquisitions to average'
    ]

    
    # Writing our configuration file
    logger.debug('Initializing configuration file ' + 
                 configFileName)
    config.write()
    return config





# get_offcal_data(caldict,gainlist,rawdata)
#
# Correct raw data for offset only.
def get_offcal_data(caldict, gainlist, rawdata):
    if gainlist[0] == 0: # Channel A has 1x gain
        chA_offset = caldict['chA_1x_offset']
    elif gainlist[0] == 1: # Channel A has 10x gain
        chA_offset = caldict['chA_10x_offset']
    if gainlist[1] == 0: # Channel B has 1x gain
        chB_offset = caldict['chB_1x_offset']
    elif gainlist[1] == 1: # Channel B has 10x gain
        chB_offset = caldict['chB_10x_offset']
    # Process channel A data
    cha_voltdata = []
    for sample in rawdata[0]:
        cha_voltdata.append(511 - (sample + chA_offset))
    # Process channel B data
    chb_voltdata = []
    for sample in rawdata[1]:
        chb_voltdata.append(511 - (sample + chB_offset))
    return [cha_voltdata,chb_voltdata]


# get_offsets(handle, ctrl_reg, gainlist, caldict, config)
#
# Walks you through the calibration of offsets using the current gain
# settings.
#
# Arguments:
#  handle -- serial object representing the CGR-101
#  ctrl_reg -- value of the control register
#  gainlist -- [cha_gain, chb_gain]
#  caldict -- Dictionary of all calibration values
#  config -- Configuration dictionary from rc file
#
# Calibrated data is calculated with:
# volts = (511 - (rawdata + offset)) * slopevalue
# ...so offsets are calculated with:
# offset = 511 - rawdata
#
# Returns the calibration factor dictionary with the relevant offset
# factors filled in.
def get_offsets(handle, ctrl_reg, gainlist, caldict, config):
    offset_list = []
    gainlist = utils.set_hw_gain(handle,gainlist)
    for capturenum in range(int(config['Acquire']['averages'])):
        tracedata = utils.get_uncal_forced_data(handle, ctrl_reg)
        logger.info('Acquiring trace ' + str(capturenum + 1) + 
                           ' of ' + str(config['Acquire']['averages']))
        if capturenum == 0:
            sumdata = tracedata
        else:
            sumdata = add(sumdata,tracedata)
        avgdata = divide(sumdata,float(capturenum +1))
    for channel in range(2):
        offset_list.append(511 - average(avgdata[channel]))
    if gainlist[0] == 0: # Channel A set for 1x gain
        logger.debug('Channel A offset set to ' + 
                            str(offset_list[0]) + ' counts.')
        caldict['chA_1x_offset'] = offset_list[0]
    elif gainlist[0] == 1: # Channel A set for 10x gain
        logger.debug('Channel A offset set to ' + 
                            str(offset_list[0]) + ' counts.')
        caldict['chA_10x_offset'] = offset_list[0] 
    if gainlist[1] == 0: # Channel B set for 1x gain
        logger.debug('Channel B offset set to ' + 
                            str(offset_list[1]) + ' counts.')
        caldict['chB_1x_offset'] = offset_list[1]
    elif gainlist[1] == 1: # Channel B set for 10x gain
        logger.debug('Channel B offset set to ' + 
                            str(offset_list[1]) + ' counts.')
        caldict['chB_10x_offset'] = offset_list[1]
    return caldict


# get_slopes(handle, ctrl_reg, gainlist, caldict, calvolt)
#
# Fills in slope values for whatever gain is set. 
#
# To calibrate using the 10x gain settings, you should really be using
# a 10x scope probe.
#
# Calibrated data is calculated with:
# volts = (511 - (rawdata + offset)) * slopevalue
# ...so slopes are calculated with:
# slope = calvolt/(offset corrected data)
#
# Arguments:
#  handle -- serial object representing the CGR-101
#  ctrl_reg -- value of the control register
#  gainlist -- [cha_gain, chb_gain]
#  caldict -- Dictionary of all calibration values
#  calvolt -- The voltage used during slope calibration
def get_slopes(handle, ctrl_reg, gainlist, caldict, calvolt):
    slope_list = []
    gainlist = cgrlib.set_hw_gain(handle,gainlist)
    rawdata = cgrlib.get_uncal_forced_data(handle,ctrl_reg)
    offcal_data = get_offcal_data(caldict,gainlist,rawdata)
    for channel in range(2):
        slope_list.append(calvolt/(average(offcal_data[channel])))
    if gainlist[0] == 0: # Channel A set for 1x gain
        caldict['chA_1x_slope'] = slope_list[0]
    elif gainlist[0] == 1: # Channel A set for 10x gain
        caldict['chA_10x_slope'] = slope_list[0] 
    if gainlist[1] == 0: # Channel B set for 1x gain
        caldict['chB_1x_slope'] = slope_list[1]
    elif gainlist[1] == 1: # Channel B set for 10x gain
        caldict['chB_10x_slope'] = slope_list[1]
    return caldict

# plotdata()
#
# Plot data from both channels.
def plotdata(timedata, voltdata, trigdict):
    # Set debug=1 to see gnuplot commands
    gplot = Gnuplot.Gnuplot(debug=0)
    gplot('set terminal x11')
    # titlestr = ('Trigger at sample ' +
    #             ' ({:0.3f} ms)'.format(1000 * timedata[1]))
    # gplot('set title "' + titlestr + '"')
    gplot('set style data lines')
    gplot('set key bottom left')
    gplot.xlabel('Time (s)')
    gplot.ylabel('Voltage (V)')
    gplot("set yrange [*:*]")
    gplot("set format x '%0.0s %c'")
    gplot('set pointsize 1') 
    gdata_cha_notime = Gnuplot.PlotItems.Data(
        voltdata[0],title='Channel A')
    gdata_cha = Gnuplot.PlotItems.Data(
        timedata,voltdata[0],title='Channel A')
    gdata_chb = Gnuplot.PlotItems.Data(
        timedata,voltdata[1],title='Channel B')
    gplot.plot(gdata_cha,gdata_chb) # Plot the data
    # Add the trigger crosshair
    if (trigdict['trigsrc'] < 3):
        trigtime = timedata[1024-trigdict['trigpts']]
        gplot('set arrow from ' + str(trigtime) + ',graph 0 to ' + 
              str(trigtime) + ',graph 1 nohead linetype 0')
        gplot('set arrow from graph 0,first ' + str(trigdict['triglev']) +
              ' to graph 1,first ' + str(trigdict['triglev']) + 
              ' nohead linetype 0')
        gplot('replot')
    savefilename = ('trig.eps')
    gplot('set terminal postscript eps color')
    gplot("set output '" + savefilename + "'")
    gplot('replot')
    gplot('set terminal x11')
    raw_input('* Press return to dismiss plot and exit...')    



# ------------------------- Main procedure ----------------------------
def main(): 
    logger.debug('Utility module number is ' + str(utils.utilnum))
    config = load_config(args.rcfile)
    caldict = utils.load_cal(config['Calibration']['calfile'])
    
    # Trigger is hard coded to internal (auto trigger) for the
    # calibration code.
    trigdict = utils.get_trig_dict(3,0,0,0) 

    cgr = utils.get_cgr()
    gainlist = utils.set_hw_gain(
        cgr, [int(config['Inputs']['Aprobe']),
              int(config['Inputs']['Bprobe'])
          ]
    )
    
    utils.set_trig_level(cgr, caldict, gainlist, trigdict)
    utils.set_trig_samples(cgr,trigdict)
    [ctrl_reg, fsamp_act] = utils.set_ctrl_reg(
        cgr, float(config['Acquire']['rate']), trigdict
    )
    if not (fsamp_act == float(config['Acquire']['rate'])):
        logger.warning(
            'Requested sample frequency ' + '{:0.3f} kHz '.format(
                float(config['Acquire']['rate'])/1000
            ) 
            + 'adjusted to ' + '{:0.3f} kHz '.format(
                float(fsamp_act)/1000
            )
        )
    
    # Start the offset calibration
    raw_input('* Remove all inputs and press return...')
    caldict = get_offsets(cgr, ctrl_reg, gainlist, caldict, config)

    # Start the slope calibration
    # raw_input('* Connect ' + '{:0.3f}'.format(calvolt) +
    #           'V calibration voltage and press return...')
    # caldict = get_slopes(cgr, ctrl_reg, gainlist, caldict, calvolt)

    # Test calibration
    raw_input('* Ready to test calibration...')
    for capturenum in range(int(config['Acquire']['averages'])):
        tracedata = utils.get_uncal_forced_data(cgr,ctrl_reg)
        logger.info('Acquiring trace ' + str(capturenum + 1) + ' of ' +
                    str(config['Acquire']['averages']))
        if capturenum == 0:
            sumdata = tracedata
        else:
            sumdata = add(sumdata,tracedata)
        avgdata = divide(sumdata,float(capturenum +1))

    # Get calibrated volts
    voltdata = utils.get_cal_data(
       caldict,gainlist,[avgdata[0],avgdata[1]]
        )
    timedata = utils.get_timelist(fsamp_act)
    plotdata(timedata, voltdata, trigdict)
    # Write the calibration data
    utils.write_cal(config['Calibration']['calfile'],caldict)


# Execute main() from command line
if __name__ == '__main__':
    main()
