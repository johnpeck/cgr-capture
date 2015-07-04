#!/usr/bin/env python

# cgr_gen.py
#
# Waveform generation with the cgr-101 USB oscilloscope

import time     # For making pauses
import os       # For basic file I/O
import ConfigParser # For reading and writing the configuration file
import sys # For sys.exit()
from math import sin # For generating sine waves
from math import pi

# --------------------- Configure argument parsing --------------------
import argparse
parser = argparse.ArgumentParser(
   formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument("-r", "--rcfile" , default="cgr-gen.cfg",
                    help="Runtime configuration file"
)
parser.add_argument("-w", "--waveform", default="sine",
                    help="Waveform.  Known values are: sine"
)
parser.add_argument("-f", "--frequency", default=100,
                    help="Output frequency"
)
parser.add_argument("-a", "--amplitude", default=0.1,
                    help="Output amplitude (Vp)"
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

cmdterm = '\r\n' # Terminates each command


# ------------- Configure runtime configuration file ------------------
from configobj import ConfigObj # For writing and reading config file


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
        'Configuration file for cgr_gen.py',
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
    #----------------------- Waveform section -------------------------
    config['Waveform'] = {}
    config['Waveform'].comments = {}
    config.comments['Waveform'] = [
        ' ',
        '------------------- Waveform configuration -------------------'
    ]
    config['Waveform']['shape'] = 'sine'
    config['Waveform'].comments['shape'] = [
        ' ',
        'Manually set the output waveform shape here.  Shapes set at the'
        'command line will be given priority.  This configuration will'
        'be overwritten by the most recent shape.  This saves download'
        'time when changing frequency or amplitude but not shape.'
    ]



    # Writing our configuration file
    logger.debug('Initializing configuration file ' +
                 configFileName)
    config.write()
    return config

# ---------- Done with configuring runtime configuration --------------

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


# ------------------------- Main procedure ----------------------------
def main():
    logger.debug('Utility module number is ' + str(utils.utilnum))
    config = load_config(args.rcfile)
    global ch,fh # Need to modify console and file logger handlers
                 # with the config file, from inside main().  They
                 # thus must be made global.
    (ch,fh) = init_logger(config,ch,fh)
    cgr = utils.get_cgr(config)
    actfreq = utils.set_sine_frequency(cgr, float(args.frequency)) # Return the actual frequency
    logger.debug('Requested ' + '{:0.2f}'.format(float(args.frequency)) + ' Hz, set ' +
                 '{:0.2f}'.format(actfreq) + ' Hz')
    if args.waveform == 'sine':
        logger.debug('Configuring sine wave output')
        if not (config['Waveform']['shape'] == 'sine'):
            for samplenum in range(256):
                sampleval = int(round(127 + 127*sin(samplenum * 2*pi/255)))
                utils.set_arb_value(cgr, samplenum, sampleval)
            cgr.open()
            utils.sendcmd(cgr,'W P')
            cgr.close()   
            config['Waveform']['shape'] = 'sine'
            config.write()
    if args.waveform == 'square':
        logger.debug('Configuring square wave output')
        if not (config['Waveform']['shape'] == 'square'):
            # Set the output to 0 while we load and activate the waveform
            utils.set_output_amplitude(cgr, 0)
            for samplenum in range(256):
                if samplenum < 128:
                    sampleval = 0
                else:
                    sampleval = 255
                utils.set_arb_value(cgr, samplenum, sampleval)
            cgr.open()
            utils.sendcmd(cgr,'W P')
            cgr.close()
            config['Waveform']['shape'] = 'square'
            config.write()
    actamp = utils.set_output_amplitude(cgr, float(args.amplitude))
    logger.debug('Requested ' + '{:0.2f}'.format(float(args.amplitude)) + ' Vp, set ' +
                 '{:0.2f}'.format(actamp) + ' Vp')



# Execute main() from command line
if __name__ == '__main__':
    main()
