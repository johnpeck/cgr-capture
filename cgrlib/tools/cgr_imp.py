#!/usr/bin/env python

# cgr_imp.py
#
# Impedance measurement with the cgr-101 USB oscilloscope

import time     # For making pauses
import os       # For basic file I/O
import ConfigParser # For reading and writing the configuration file
import sys # For sys.exit()
from math import sin # For generating sine waves
from math import pi
# from scipy.optimize import minimize # For calculating phase shift

# --------------------- Configure argument parsing --------------------
import argparse
parser = argparse.ArgumentParser(
   formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument("-r", "--rcfile" , default="cgr-imp.cfg",
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
fh = logging.FileHandler('cgrimp.log',mode='a',encoding=None,delay=False)
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
        'Configuration file for cgr-imp',
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
    config['Connection']['port'] = '/dev/ttyUSB0'
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

    #--------------------- Frequency sweep section --------------------
    config['Sweep'] = {}
    config['Sweep'].comments = {}
    config.comments['Sweep'] = [
        ' ',
        '-------------- Frequency sweep configuration -----------------'
    ]
    config['Sweep']['start'] = 100
    config['Sweep'].comments['start'] = [
        'Starting frequency (Hz)'
    ]
    config['Sweep']['stop'] = 1000
    config['Sweep'].comments['stop'] = [
        'Last frequency in the sweep (Hz)'
    ]
    config['Sweep']['points'] = 10
    config['Sweep'].comments['points'] = [
        'Number of points in the sweep'
    ]
    config['Sweep']['cycles'] = 10
    config['Sweep'].comments['cycles'] = [
        'Number of sine wave cycles to acquire for each frequency step'
    ]
    config['Sweep']['amplitude'] = 0.1
    config['Sweep'].comments['amplitude'] = [
        'Amplitude of the driving frequency (Volts peak)'
    ]

    #------------------ Impedance calculation section -----------------
    config['Impedance'] = {}
    config['Impedance'].comments = {}
    config.comments['Impedance'] = [
        ' ',
        '------------- Impedance calculation configuration ------------'
    ]
    config['Impedance']['resistor'] = 100
    config['Impedance'].comments['resistor'] = [
        'Reference resistor -- current is voltage divided by this value'
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

def get_sweep_list(config):
    """ Returns the frequencies in the sweep

    Arguments:
      config -- The configuration file object
    """
    freqlist = []
    points = int(config['Sweep']['points'])
    startfreq = float(config['Sweep']['start'])
    stopfreq = float(config['Sweep']['stop'])
    for freqnum in range(points):
        if freqnum == 0:
            freqlist.append(startfreq)
        else:
            freqlist.append(startfreq +
                            freqnum * (stopfreq - startfreq)/(points-1)
            )
    return freqlist
        
def set_sample_rate(handle, config, drive_frequency, trigger_dictionary):
    """Returns the sample rate set to acquire multiple periods of the drive frequency

    We need to send the trigger dictionary along with the drive
    frequency because the two settings share the same register.

    Arguments:
      handle -- Serial object for the CGR scope
      config -- The configuration file object
      drive_frequency -- The drive frequency (Hz)
      trigger_dictionary -- Trigger settings

    """
    capture_points = 1024 # Points acquired after a trigger
    seconds_needed = int(config['Sweep']['cycles'])/drive_frequency
    target_rate = capture_points/seconds_needed
    [control_register_value, actual_samplerate] = utils.set_ctrl_reg(
        handle, target_rate, trigger_dictionary
    )
    return actual_samplerate

def get_volts_rms(voltdata):
    """Returns the calculated Vrms for both channels

    Arguments:
      voltdata -- 1024 x 2 list of voltage samples
    """
    offsets = []
    offsets.append(mean(voltdata[0]))
    offsets.append(mean(voltdata[1]))
    sum = [0,0]
    for point in range(len(voltdata[0])):
        sum[0] += (voltdata[0][point] - offsets[0])**2
        sum[1] += (voltdata[1][point] - offsets[1])**2
    vrms = [sqrt(sum[0]/1024),sqrt(sum[1]/1024)]
    return(vrms[0],vrms[1])

def get_sine_vectors(frequency,timedata,voltdata):
    """Returns the amplitudes for both channels using a homodyne technique

    Amplitude values are peak volts (Vp)

    Arguments:
      frequency -- the frequency to lock in on
      timedata -- List of sample times
      voltdata -- 1024 x 2 list of voltage samples
    """
    offsets = []
    offsets.append(mean(voltdata[0]))
    offsets.append(mean(voltdata[1]))
    refsin = []
    refcos = []
    for time in timedata:
        refsin.append(sin(2*pi*frequency*time))
        refcos.append(cos(2*pi*frequency*time))
    sineprod = []
    cosprod = []
    for channelnum in range(2):
        sineprod.append(multiply(voltdata[channelnum]-offsets[channelnum],refsin))
        cosprod.append(multiply(voltdata[channelnum]-offsets[channelnum],refcos))
    inphase_amplitudes = [mean(sineprod[0]), mean(sineprod[1])]
    quadrature_amplitudes = [mean(cosprod[0]), mean(cosprod[1])]
    amplitudes = []
    phases = []
    for channelnum in range(2):
        amplitudes.append(2*sqrt(inphase_amplitudes[channelnum]**2 +
                                 quadrature_amplitudes[channelnum]**2)
        )
        # Use arctan2 to allow angle to run from 0 --> 2pi
        phases.append(arctan2(quadrature_amplitudes[channelnum],
                              inphase_amplitudes[channelnum])
        )        
    return [amplitudes, phases]


def get_z_vector(frequency, timedata, voltdata, resistor):
    """Returns the magnitude and phase of the measured impedance

    Arguments:
      frequency -- The frequency to lock in on
      timedata -- List of sample times
      voltdata -- 1024 x 2 list of voltage samples
      resistor -- Reference resistor value (ohms)
    """
    [amplitudes, phases] = get_sine_vectors(frequency, timedata, voltdata)
    ratio_mag = amplitudes[0]/amplitudes[1]
    ratio_phi = phases[0] - phases[1]
    impedance = [resistor * (ratio_mag + 1),ratio_phi]
    return impedance

def sinediff(phaseshift, frequency, timedata, voltdata):
    """Returns the difference between calculated sine and input data

    Arguments:
      phaseshift -- Offset to apply to the calculated sine (radians)
      frequency -- Frequency for the calculated sine (Hz)
      timedata -- List of sample times
      voltdata -- List of voltages at sample times
    """
    offset_volts = mean(voltdata)
    refdata = []
    for time in timedata:
        refdata.append(sin(2*pi*frequency*time + phaseshift))
    diff = 0
    for data, ref in zip(voltdata, refdata):
        diff += ((data - offset_volts) - ref)**2
    return diff
        
    
        
    
def wave_plot_init():
    """ Returns the configured gnuplot plot object for raw waveforms.
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

def plot_wave_data(plotobj, timedata, voltdata, trigdict, frequency, amplitudes, phases):
    """Plot data from both channels along with the fit result.

    Arguments:
      plotobj -- The gnuplot plot object
      timedata -- List of sample times
      voltdata -- 1024 x 2 list of voltage samples
      trigdict -- Trigger parameter dictionary
      frequency -- The frequency of the synthesized fit
      amplitudes -- The measured amplitudes
      phases -- The measured phase shifts
    """
    fitdata = [[],[]]
    for time in timedata:
        fitdata[0].append(amplitudes[0]*sin(2*pi*frequency*time +phases[0]) +
                          mean(voltdata[0])
        )
        fitdata[1].append(amplitudes[1]*sin(2*pi*frequency*time + phases[1]) +
                          mean(voltdata[1])
        )
    plotitem_cha_raw = Gnuplot.PlotItems.Data(
        timedata,voltdata[0],title='Channel A raw')
    plotitem_chb_raw = Gnuplot.PlotItems.Data(
        timedata,voltdata[1],title='Channel B raw')
    plotitem_cha_recovered = Gnuplot.PlotItems.Data(
        timedata,fitdata[0],title='Channel A recovered')
    plotitem_chb_recovered = Gnuplot.PlotItems.Data(
        timedata,fitdata[1],title='Channel B recovered')
    plotobj.plot(plotitem_cha_raw,plotitem_chb_raw,
                 plotitem_cha_recovered, plotitem_chb_recovered)
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


# ------------------------- Main procedure ----------------------------
def main():
    logger.debug('Utility module number is ' + str(utils.utilnum))
    config = load_config(args.rcfile)
    global ch,fh # Need to modify console and file logger handlers
                 # with the config file, from inside main().  They
                 # thus must be made global.
    (ch,fh) = init_logger(config,ch,fh)
    cgr = utils.get_cgr(config)
    caldict = utils.load_cal(cgr, config['Calibration']['calfile'])
    eeprom_list = utils.get_eeprom_offlist(cgr)
    # Configure the trigger:
    #   Trigger on channel A
    #   Trigger at 0.05 V
    #   Trigger on the rising edge
    #   Capture 512 points after trigger
    trigdict = utils.get_trig_dict(0,0.05,0,512)
    # Configure the inputs for 1x gain (no probe)
    gainlist = utils.set_hw_gain(cgr,[0,0])
    utils.set_trig_level(cgr, caldict, gainlist, trigdict)
    utils.set_trig_samples(cgr,trigdict)
    waveplot = wave_plot_init()
    freqlist = get_sweep_list(config)
    for progfreq in freqlist:
        # The actual frequency will be determined by the hardware
        actfreq = utils.set_sine_frequency(cgr, float(progfreq))
        logger.debug('Requested ' + '{:0.2f}'.format(float(progfreq)) +
                     ' Hz, set ' + '{:0.2f}'.format(actfreq) + ' Hz')
        if (progfreq == freqlist[0]):
            # Only set amplitude once
            actamp = utils.set_output_amplitude(cgr, float(config['Sweep']['amplitude']))
            logger.debug('Requested ' + '{:0.2f}'.format(float(config['Sweep']['amplitude'])) +
                         ' Vp, set ' + '{:0.2f}'.format(actamp) + ' Vp')
        actrate = set_sample_rate(cgr, config, actfreq, trigdict)
        logger.debug('Sample rate set to ' + '{:0.2f}'.format(actrate) +
                     ' Hz, for an acquisition time of ' + '{:0.2f}'.format(1024/actrate * 1000) +
                     ' milliseconds'
                     )
        for capturenum in range(1):
            if trigdict['trigsrc'] == 3:
                # Internal trigger
                tracedata = utils.get_uncal_forced_data(cgr,ctrl_reg)
            elif trigdict['trigsrc'] < 3:
                # Trigger on a voltage present at some input
                tracedata = utils.get_uncal_triggered_data(cgr,trigdict)
            logger.info('Acquiring trace ' + str(capturenum + 1) + ' of ' +
                        str(0)
            )
            if capturenum == 0:
                sumdata = tracedata
            else:
                sumdata = add(sumdata,tracedata)
            avgdata = divide(sumdata,float(capturenum +1))
            # Apply calibration
            voltdata = utils.get_cal_data(
                caldict,gainlist,[avgdata[0],avgdata[1]]
            )
            timedata = utils.get_timelist(actrate)
        

        
        [amplitudes, phases] = get_sine_vectors(actfreq, timedata, voltdata)
        logger.debug('Channel A amplitude is ' + '{:0.3f}'.format(amplitudes[0]) +
                     ' Vp'
        )
        logger.debug('Channel B amplitude is ' + '{:0.3f}'.format(amplitudes[1]) +
                     ' Vp'
        )     
        logger.debug('Channel A phase shift is ' + '{:0.3f}'.format(phases[0] * 180/pi) +
                     ' degrees'
        )
        logger.debug('Channel B phase shift is ' + '{:0.3f}'.format(phases[1] * 180/pi) +
                     ' degrees'
        )      
        logger.debug('Channel A lockin amplitude is ' + '{:0.3f}'.format(amplitudes[0]) +
                     ' Vp'
        )
        logger.debug('Channel B lockin amplitude is ' + '{:0.3f}'.format(amplitudes[1]) +
                     ' Vp'
        )
        plot_wave_data(waveplot, timedata, voltdata, trigdict, actfreq, amplitudes, phases)
        [zmag,zphase] = get_z_vector(actfreq, timedata, voltdata,
                                     float(config['Impedance']['resistor'])
        )
        logger.debug('Impedance magnitude is ' + '{:0.3f}'.format(zmag) +
                     ' Ohms'
        )
        logger.debug('Impedance angle is ' + '{:0.3f}'.format(zphase * 180/pi) +
                     ' degrees'
        )
    # Set amplitude to zero to end the sweep
    utils.set_output_amplitude(cgr, 0)
    raw_input('Press any key to close plot and exit...')



# Execute main() from command line
if __name__ == '__main__':
    main()
