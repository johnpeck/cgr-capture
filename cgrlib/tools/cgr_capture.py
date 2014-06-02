#!/usr/bin/env python

# cgr_capture.py
#
# Captures one buffer of data from the cgr-101 USB scope

import time     # For making pauses
import os       # For basic file I/O
import ConfigParser # For reading and writing the configuration file
import sys # For sys.exit()
from itertools import izip


# --------------------- Configure argument parsing --------------------
import argparse
parser = argparse.ArgumentParser(
   formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument("-o", "--outfile", help="output filename",
                    default="last_capture.dat"
)
parser.add_argument("-r", "--rcfile" , default="cgr-capture.cfg",
                    help="Runtime configuration file"
)
args = parser.parse_args()

#---------------- Done with configuring argument parsing --------------



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




def init_config(configFileName):
    """ Initialize the configuration file and return config object.

    Arguments:
      configFileName -- Configuration file name
    """
    config = ConfigObj()
    config.filename = configFileName
    config.initial_comment = [
        'Configuration file for cgr_capture.py',
        ' ']
    config.comments = {}
    config.inline_comments = {}
    #------------------------ Connection section ----------------------
    config['Connection'] = {}
    config['Connection'].comments = {}
    config.comments['Connection'] = [
        ' ',
        '------------------ Connection configuration ------------------'
    ]
    config['Connection']['port'] = '/dev/ttyS0'
    config['Connection'].comments['port'] = [
        ' ',
        'Manually set the connection port here.  This will be overwritten',
        'by the most recent successful connection.  The software will try',
        'to connect using the configuration port first, then it will move',
        'on to automatically detected ports and some hardcoded values.'
    ]
    #------------------------- Logging section ------------------------
    config['Logging'] = {}
    config['Logging'].comments = {}
    config.comments['Logging'] = [
        ' ',
        '------------------- Logging configuration --------------------'
    ]
    config['Logging']['termlevel'] = 'debug'
    config['Logging'].comments['termlevel'] = [
        ' ',
        'Set the logging level for the terminal.  Levels:',
        'debug, info, warning, error, critical'
        ]
    config['Logging']['filelevel'] = 'debug'
    config['Logging'].comments['filelevel'] = [
        ' ',
        'Set the logging level for the logfile.  Levels:',
        'debug, info, warning, error, critical'
        ]
    
    #----------------------- Calibration section ----------------------
    config['Calibration'] = {}
    config['Calibration'].comments = {}
    config.comments['Calibration'] = [
        ' ',
        '----------------- Calibration configuration ------------------'
    ]
    config['Calibration']['calfile'] = 'cgrcal.pkl'
    config['Calibration'].comments['calfile'] = [
        "The calibration file in Python's pickle format"
        ]


    #------------------------- Trigger section ------------------------
    config['Trigger'] = {}
    config['Trigger'].comments = {}
    config.comments['Trigger'] = [
        ' ',
        '----------------- Trigger configuration ----------------------'
    ]
    config['Trigger']['level'] = 1.025
    # config.inline_comments['Trigger'] = 'Inline comment about trigger section'
    config['Trigger'].comments['level'] = ['The trigger level (Volts)']

    # Trigger source
    config['Trigger']['source'] = 3
    config['Trigger'].comments['source'] = [
        ' ',
        'Trigger source settings:',
        '0 -- channel A',
        '1 -- channel B',
        '2 -- external',
        '3 -- internal (Triggers generated regardless of any level)'
    ]

    # Trigger polarity
    config['Trigger']['polarity'] = 0
    config['Trigger'].comments['polarity'] = [
        ' ',
        'Trigger polarity settings:',
        '0 -- Rising edge',
        '1 -- Falling edge'
    ]

    # Points to acquire after trigger
    config['Trigger']['points'] = 512
    config['Trigger'].comments['points'] = [
        ' ',
        'Points to acqure after trigger',
        'The unit always acquires 1024 points from each channel.  This',
        'number sets the number of points to acquire after a trigger.',
        'So a value of 100 would mean that 924 points are acquired before',
        'the trigger, and 100 are acquired after.',
        'Range: 0, 1, 2, ... , 1024'
    ]

    #-------------------------- Inputs section ------------------------
    config['Inputs'] = {}
    config['Inputs'].comments = {}
    config.comments['Inputs'] = [
        ' ',
        '-------------------- Input configuration ---------------------',  
        'The unit is limited to measuring +/-25Vpp at its inputs with',
        'the 1x probe setting, and at the end of a 10x probe with the',
        '10x probe setting.'
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
        '----------------- Acquisition configuration ------------------'
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

def init_logger(config,conhandler,filehandler):
    """ Returns the configured console and file logging handlers

    Arguments:
      config -- The configuration file object
      conhandler -- The console logging handler
      filehandler -- The file logging handler
    """
    if config['Logging']['termlevel'] == 'debug':
        conhandler.setLevel(logging.DEBUG)
    elif config['Logging']['termlevel'] == 'info':
        conhandler.setLevel(logging.INFO)
    elif config['Logging']['termlevel'] == 'warning':
        conhandler.setLevel(logging.WARNING)
    return (conhandler,filehandler)

def plotinit():
    """ Returns the configured gnuplot plot object.
    """
    # Set debug=1 to see gnuplot commands during execution.
    plotobj = Gnuplot.Gnuplot(debug=0)
    plotobj('set terminal x11') # Send a gnuplot command
    plotobj('set style data lines')
    plotobj('set key bottom left')
    plotobj.xlabel('Time (s)')
    plotobj.ylabel('Voltage (V)')
    plotobj("set autoscale y")
    plotobj("set format x '%0.0s %c'")
    plotobj('set pointsize 1')
    return plotobj


def plotdata(plotobj, timedata, voltdata, trigdict):
    """Plot data from both channels.

    Arguments:
      plotobj -- The gnuplot plot object
      timedata -- List of sample times
      voltdata -- 1024 x 2 list of voltage samples
      trigdict -- Trigger parameter dictionary
    """
    gdata_cha_notime = Gnuplot.PlotItems.Data(
        voltdata[0],title='Channel A')
    gdata_cha = Gnuplot.PlotItems.Data(
        timedata,voltdata[0],title='Channel A')
    gdata_chb = Gnuplot.PlotItems.Data(
        timedata,voltdata[1],title='Channel B')
    plotobj.plot(gdata_cha,gdata_chb) # Plot the data
    # Freeze the axis limits after the initial autoscale.
    plotobj('unset autoscale y')
    plotobj('set yrange [GPVAL_Y_MIN:GPVAL_Y_MAX]')
    # Add the trigger crosshair
    if (trigdict['trigsrc'] < 3):
        trigtime = timedata[1024-trigdict['trigpts']]
        plotobj('set arrow from ' + str(trigtime) + ',graph 0 to ' +
                str(trigtime) + ',graph 1 nohead linetype 0')
        plotobj('set arrow from graph 0,first ' + str(trigdict['triglev']) +
                ' to graph 1,first ' + str(trigdict['triglev']) +
                ' nohead linetype 0')
        plotobj('replot')
    savefilename = ('trig.eps')
    plotobj('set terminal postscript eps color')
    plotobj("set output '" + savefilename + "'")
    plotobj('replot')
    plotobj('set terminal x11')


def savedata(config, timedata, voltdata):
    """ Write data to a file.

    Arguments:
      config -- The configuration object created from the configuration
                file.
      timedata -- List of sample times.
      voltdata -- List of voltage samples:
                  voltdata[0] -- Samples from channel A
                  voltdata[1] -- Samples from channel B
    """
    # Open output file
    with open(args.outfile, 'w') as outfile:
        logger.info('Writing data to ' + args.outfile)
        outfile.write('# Created by cgr-capture' + '\n')
        outfile.write('{:<20}'.format('# Time (s)'))
        outfile.write('{:<20}'.format('Channel A (V)'))
        outfile.write('{:<20}'.format('Channel B (V)') + '\n')
        for timepoint, avolt, bvolt in zip(timedata, voltdata[0], voltdata[1]):
            # Write the time coordinate
            outfile.write('{:<20.5e}'.format(timepoint))
            # Write the A datapoint
            outfile.write('{:<20.5e}'.format(avolt))
            # Write the B datapoint
            outfile.write('{:<20.5e}'.format(bvolt) + '\n')



# ------------------------- Main procedure ----------------------------
def main():
    logger.debug('Utility module number is ' + str(utils.utilnum))
    config = load_config(args.rcfile)
    global ch,fh # Need to modify console and file logger handlers
                 # with the config file, from inside main().  They
                 # thus must be made global.
    (ch,fh) = init_logger(config,ch,fh)
    trigdict = utils.get_trig_dict( int(config['Trigger']['source']),
                                     float(config['Trigger']['level']),
                                     int(config['Trigger']['polarity']),
                                     int(config['Trigger']['points'])
    )
    cgr = utils.get_cgr(config)
    caldict = utils.load_cal(cgr, config['Calibration']['calfile'])
    eeprom_list = utils.get_eeprom_offlist(cgr)
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

    # Wait for trigger, then return uncalibrated data
    gplot = plotinit() # Create plot object
    for capturenum in range(int(config['Acquire']['averages'])):
        if trigdict['trigsrc'] == 3:
            # Internal trigger
            tracedata = utils.get_uncal_forced_data(cgr,ctrl_reg)
        elif trigdict['trigsrc'] < 3:
            # Trigger on a voltage present at some input
            tracedata = utils.get_uncal_triggered_data(cgr,trigdict)
        logger.info('Acquiring trace ' + str(capturenum + 1) + ' of ' +
                    str(config['Acquire']['averages']))
        if capturenum == 0:
            sumdata = tracedata
        else:
            sumdata = add(sumdata,tracedata)
        avgdata = divide(sumdata,float(capturenum +1))
        # Apply calibration
        voltdata = utils.get_cal_data(
            caldict,gainlist,[avgdata[0],avgdata[1]]
        )
        timedata = utils.get_timelist(fsamp_act)
        logger.debug(
            'Plotting average of ' + str(capturenum + 1) + ' traces.'
        )
        plotdata(gplot, timedata, voltdata, trigdict)



    savedata(config, timedata, voltdata)
    raw_input('Press any key to close plot and exit...')


# Execute main() from command line
if __name__ == '__main__':
    main()
