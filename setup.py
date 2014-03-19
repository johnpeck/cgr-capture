#!/usr/bin/env python
from setuptools import setup

entry_points = {
    'console_scripts': [
        'cgr-capture = cgrlib.tools.cgr_capture:main',
        'cgr-cal = cgrlib.tools.cgr_cal:main'
    ]
}


setup(
    name = 'cgrlib',
    packages = ['cgrlib','cgrlib.tools','cgrlib.test'],
    version = '0.1.0',
    license='LICENSE.txt',
    description = 'Capture waveforms with the CGR-101 USB oscilloscope',
    author = 'John Peck',
    author_email = 'john@johnpeck.info',
    url = 'https://github.com/johnpeck/cgr-capture',
    install_requires=[
        "numpy >= 1.7.1",
        "configobj >= 4.7.2",
        "gnuplot-py >= 1.8",
        "colorlog >= 2.0.0"
    ],
    zip_safe = True,
    entry_points = entry_points,
    keywords = ['testing', 'logging', 'example'] # arbitrary keywords
)
