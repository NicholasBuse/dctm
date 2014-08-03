#!/bin/sh

dmlogin() {
  idql ${DOCBASE} -U${DMUSER} -P${DMPASSWORD} <<__EOF__ 2>&1
quit
__EOF__
}

WaitForServer() {
  WAIT_INTERVAL=${1:-10}
  MAX_WAIT=${2:-120}
  CONNECTCMD="dmlogin"
  CONNECTRESPONSE=
  CONNECTED=
  let total_wait=0
  echo Attempting to connect to server.
  while [ "x$CONNECTED" != "x0" ] && [ $total_wait -lt $MAX_WAIT ]; do
    sleep $WAIT_INTERVAL
    let "total_wait=$total_wait+$WAIT_INTERVAL"
    CONNECTRESPONSE=`$CONNECTCMD`
    echo $CONNECTRESPONSE | grep DM_SESSION_I_SESSION_START >/dev/null 2>&1
    CONNECTED=$?
  done

  if [ "x$CONNECTED" = "x0" ]; then
    SERVERSTATE="RUNNING"
    echo Connected to server!
  else
    SERVERSTATE="SHUTDOWN"
    echo Could not connect to server
  fi
}

startdocbrokers() {
  for docbroker in $DOCUMENTUM/dba/dm_launch_*; do
    if [ -x $docbroker ] && [ -O $docbroker ]; then
      echo "Starting $docbroker"
      $docbroker
    else
      echo "Warning: $docbroker not executable"
    fi
  done
}

startcontents() {

  for l in `locale | sed -e 's/=.*//'`; do
    unset $l
  done

  export LANG=C

  for content in $DOCUMENTUM/dba/dm_start_*; do
    DOCBASE=${content##*dm_start_}

    if [[ $DOCBASE == *.bak ]]; then
       continue
    fi

    if [ ! -r $DOCUMENTUM/dba/config/$DOCBASE/server.ini ]; then
       echo "$DOCUMENTUM/dba/config/$DOCBASE/server.ini doesn't exist, skipping..."
       continue
    fi

    SERVERSTATE="" # reset result of Wait function
    WaitForServer 5 5

    if [ "$SERVERSTATE" == "RUNNING" ]; then
      echo "Server is already running"
    else
      if [ -x $content ] && [ -O $content ]; then
        $content
        SERVERSTATE="" # reset result of Wait function
        WaitForServer 10 1200
        if [ "$SERVERSTATE" == "RUNNING" ]; then
          echo "Server is running"
        fi
      else
        echo "Warning: $content not executable"
      fi
    fi
  done
}

startjms() {
  ${DOCUMENTUM}/dba/startdjms
}

DMUSER=${DMUSER:-`whoami`}
DMPASSWORD=${DMPASSWORD:-$DMUSER}
DOCUMENTUM=${DOCUMENTUM:-%DOCUMENTUM%}
DOCUMENTUM_SHARED=${DOCUMENTUM_SHARED:-%DOCUMENTUM_SHARED%}
DM_HOME=${DM_HOME:-%DM_HOME%}

export ORACLE_HOME=${ORACLE_HOME:-%ORACLE_HOME%}
export NLS_LANG=AMERICAN_AMERICA.AL32UTF8

export LANG=en_US.UTF-8
export LC_ALL=en_US.UTF-8

export DEVRANDOM=/dev/urandom

if [ ! -d $DM_HOME ]; then
  echo "Documentum home $DM_HOME not availiable"
  exit 1
fi

if [ -r $DM_HOME/bin/dm_set_server_env.sh ]; then
  echo "Applying server environment"
  . $DM_HOME/bin/dm_set_server_env.sh
fi

startdocbrokers

#startcontents function changes locale parameters, so run it in subshell
(startcontents)

startjms

exit 0
