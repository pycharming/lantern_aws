#!/bin/bash

HERE=$(readlink -f $(dirname $0))

# Maven is too chatty for syslog.
LOGFILE=$HERE/build-installers.log

source $HERE/secure/env-vars.txt

# Make sure we find install4jc.
PATH=$PATH:/usr/local/bin

cd $HERE/repo
cp $HERE/secure/lantern_getexceptional.txt . 2> /dev/null

echo "Building Windows installer..." >> $LOGFILE
./winInstall.bash latest false  >> $LOGFILE 2>&1

echo "Building OS X installer..." >> $LOGFILE
./osxInstall.bash latest false >> $LOGFILE 2>&1

echo "Building Debian/Ubuntu (32bit) installer..." >> $LOGFILE
./debInstall32Bit.bash latest false >> $LOGFILE 2>&1

echo "Building Debian/Ubuntu (64bit) installer..." >> $LOGFILE
./debInstall64Bit.bash latest false >> $LOGFILE 2>&1

echo "Installers built." >> $LOGFILE
