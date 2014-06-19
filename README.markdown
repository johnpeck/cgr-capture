# cgrlib #

cgrlib provides functions for taking data with the CGR-101 USB
oscilloscope from
[Syscomp Electronic Design](http://www.syscompdesign.com).

## Installation ##

### For Windows with Cygwin ###

1. Download the Cygwin installer

    Download the appropriate version of setup.exe from
    [cygwin.com](http://cygwin.com/).  I like to copy it to my Windows
    desktop so I can easily run it again when I need to add packages.

2. Run the installer, selecting `install from internet`

    I like to install the root directory to C:\cygwin for all users.
    I also like to store package information to C:\cygstore, but this
    doesn't really matter.  After selecting file locations, you can
    use the [Cygwin mirrors](https://cygwin.com/mirrors.html) site to
    choose a mirror near you.

3. Install the default packages, plus the following:

    1. `gnuplot`
    2. `python` (2.7 branch)
    3. `python-numpy`

        This along with lapack and liblapack-devel really should be
        pulled in with cgrlib's installation script, but there are
        some problems with dependencies that make this hard right now.

    4. `lapack`
    5. `liblapack-devel`
    6. `xorg-server`

        We need to set up the X server to display waveforms with
        gnuplot.

    7. `xinit`
    8. `xorg-docs`

4. Start the `Cygwin Terminal`

    This creates your home directory and some useful configuration
    files.

5. Create a .startxwinrc file

    This is what you can use to start various X applications when the
    server starts.  If you, like me, don't want to start any, a simple
    `touch .startxwinrc` from your home directory will suffice.

6. Edit your `.bashrc` file to set your DISPLAY variable

    `echo 'export DISPLAY=:0' >> ~/.bashrc` will keep `gnuplot` from
    complaining that it can't open the display.  You'll need to
    restart your shell or re-read the rc file after adding the line.
    I like just typing `bash` to do this.

7. Install pip

    1. Download `get-pip.py` from
       [pip](http://pip.readthedocs.org/en/latest/installing.html).  I
       like to save it to `C:\cygwin\usr\`.
	2. Run the installer with `python get-pip.py`.

8. Repair numpy

    I copied these instructions from
    [centilemma.com](http://centilemma.com/windows/cygwin.html).
    There's a lot of good information there.
	* `cp /usr/lib/lapack/cygblas-0.dll /usr/bin`
	* `cp /usr/lib/lapack/cyglapack-0.dll /usr/bin`

9. Install `gnuplot-py`

    This should be handled by `setup.py`, but I don't know how to
    specify allowing external and unverified packages.
	* `pip install --allow-external gnuplot-py --allow-unverified
      gnuplot-py gnuplot-py`

10.  Finally, install `cgrlib`

    * `pip install cgrlib`

11. Start X using `startxwin`

12. Try capturing a waveform with the `cgr-capture` command.



