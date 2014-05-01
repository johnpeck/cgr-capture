#!/bin/bash
# Name: submod.sh
#
# Checks out the correct versions of submodules
#
# Usage: submod.sh
set -e # bash should exit the script if any statement returns a non-true 
       # return value
# The path to the howto's doctools module
HOWTO_DOCTOOLS=./cgrlib/docs/howto/doctools


# --------------------- Done with configuration -------------------------
SCRIPTDIR=$(pwd -P)

# Check out a version of doctools for the howto
cd $SCRIPTDIR
if [ -d "$HOWTO_DOCTOOLS" ]; then
    # The directory already exists
    cd $HOWTO_DOCTOOLS;git pull
else
    # git clone git@github.com:johnpeck/doctools.git $HOWTO_DOCTOOLS 
    git clone https://github.com/johnpeck/doctools.git $HOWTO_DOCTOOLS
fi
