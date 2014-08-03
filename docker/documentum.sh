#!/bin/bash
#
# documentum	Start up the Documentum Content Server
#
# chkconfig: 2345 81 05
# description: Documentum is a ECM platform
#              This service starts up the Documentum Content Server
#
# processname: documentum

### BEGIN INIT INFO
# Provides: sshd
# Required-Start: $local_fs $network $syslog $oracle-xe
# Required-Stop: $local_fs $syslog
# Should-Start: $syslog
# Should-Stop: $network $syslog
# Default-Start: 2 3 4 5
# Default-Stop: 0 1 6
# Short-Description: Start up the Documentum Content Server
# Description:       Documentum is a ECM platform
#		     This service starts up the Documentum Content Server
### END INIT INFO

# source function library
. /etc/rc.d/init.d/functions

# pull in sysconfig settings
[ -f /etc/sysconfig/documentum ] && . /etc/sysconfig/documentum

RETVAL=0
prog="documentum"
lockfile=/var/lock/subsys/$prog

runlevel=$(set -- $(runlevel); eval "echo \$$#" )


check() {
  if [ "x$DOCUMENTUM" = "x" ]; then
    failure
    echo
    echo "Documentum home is not speficied"
    exit 5
  fi

  if [ ! -d $DOCUMENTUM ]; then
    failure
    echo
    echo "Documentum home $DOCUMENTUM does not exist"
    exit 5
  fi

  if [ "x$DOCUMENTUM_OWNER" = "x" ]; then
    failure
    echo
    echo "Documentum installation owner is not specified"
    exit 5
  fi
}

start() {
  echo -n $"Starting $prog: "
  check
  message=`/sbin/runuser $DOCUMENTUM_OWNER -l -c $DOCUMENTUM/dba/start_documentum 2>&1` && success || failure
  RETVAL=$?
  echo
  if [ $RETVAL -eq 0 ]; then
    touch $lockfile
  else
    echo $message
  fi
  return $RETVAL
}

stop() {
  echo -n $"Stopping $prog: "
  check
  message=`/sbin/runuser $DOCUMENTUM_OWNER -l -c $DOCUMENTUM/dba/stop_documentum 2>&1` && success || failure
  RETVAL=$?
  echo
  if [ $RETVAL -eq 0 ]; then
    rm -f $lockfile
  else
    echo $message
  fi
  return $RETVAL
}

restart() {
  stop
  start
}

case "$1" in
  start)
    start
    ;;
  stop)
    stop
    ;;
  restart)
    restart
    ;;
  *)
    echo $"Usage: $0 {start|stop|restart}"
    RETVAL=2
esac

exit $RETVAL
