#!/bin/bash

VERSION=0.20.2
HERE=$(dirname $0)
# Maven is too chatty for syslog.
LOGFILE=$HERE/build-installers.log

source $HERE/env-vars.txt
SERVER_HOST=$(cat $HERE/host)
SERVER_PORT=$(cat $HERE/public-proxy-port)

# Make sure we find install4jc; processes spawned by cron jobs have narrow
# PATHs...
PATH=$PATH:/usr/local/bin

mv $HERE/lantern_getexceptional.txt . 2> /dev/null


echo "Installing dependencies..." > $LOGFILE

./installDeps.bash >> $LOGFILE 2>&1

echo "Building Windows installer..." >> $LOGFILE
./winInstall.bash $VERSION false  >> $LOGFILE 2>&1
echo "Building OS X installer..." >> $LOGFILE
./osxInstall.bash $VERSION  >> $LOGFILE 2>&1
echo "Building Debian/Ubuntu (32bit) installer..." >> $LOGFILE
./debInstall32Bit.bash $VERSION  >> $LOGFILE 2>&1
echo "Building Debian/Ubuntu (64bit) installer..." >> $LOGFILE
./debInstall64Bit.bash $VERSION  >> $LOGFILE 2>&1

# XXX: rename the installers and move them to the directory from which we'll
# serve them.

touch $HERE/.installers-built;
