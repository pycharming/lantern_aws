#!/bin/bash

VERSION={{ version }}
HERE=$(readlink -f $(dirname $0))

# Maven is too chatty for syslog.
LOGFILE=$HERE/build-installers.log

source $HERE/env-vars.txt

# Make sure we find install4jc; processes spawned by cron jobs have narrow
# PATHs...
PATH=$PATH:/usr/local/bin

echo "Building Windows installer..." >> $LOGFILE
cd $HERE/windows-x86-repo
cp $HERE/lantern_getexceptional.txt . 2> /dev/null
./winInstall.bash $VERSION false  >> $LOGFILE 2>&1

echo "Building OS X installer..." >> $LOGFILE
cd $HERE/osx-repo
cp $HERE/lantern_getexceptional.txt . 2> /dev/null
./osxInstall.bash $VERSION false >> $LOGFILE 2>&1

echo "Building Debian/Ubuntu (32bit) installer..." >> $LOGFILE
cd $HERE/linux-x86-repo
cp $HERE/lantern_getexceptional.txt . 2> /dev/null
./debInstall32Bit.bash $VERSION false >> $LOGFILE 2>&1
mv lantern-${VERSION}-32-bit.deb lantern-${VERSION}-32bit.deb

echo "Building Debian/Ubuntu (64bit) installer..." >> $LOGFILE
cd $HERE/linux-amd64-repo
cp $HERE/lantern_getexceptional.txt . 2> /dev/null
./debInstall64Bit.bash $VERSION false >> $LOGFILE 2>&1
mv lantern-${VERSION}-64-bit.deb lantern-${VERSION}-64bit.deb

echo "Installers built." >> $LOGFILE
