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

killdocumentum() {
  ps -fu ${DMUSER} | grep "./documentum -docbase_name ${DOCBASE}" | grep -v grep | awk '{print $2}' | xargs -n1 /usr/bin/kill -9
  ps -fu ${DMUSER} | grep "./dm_agent_exec -docbase_name ${DOCBASE}" | grep -v grep | awk '{print $2}' | xargs -n1 /usr/bin/kill -9
}

stopcontents() {
  for content in $DOCUMENTUM/dba/dm_shutdown_*; do
    DOCBASE=${content##*dm_shutdown_}

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
      echo "Server is running"
      $content
    else
      echo "Could not connect to server"
    fi

    killdocumentum >/dev/null 2>&1

  done

}

stopdocbrokers() {
  for docbrocker in $DOCUMENTUM/dba/dm_stop_*; do
    if [ -x $docbrocker ]; then
      echo "Stopping $docbrocker"
      $docbrocker
    else
      echo "Warning: $docbrocker not executable"
    fi
  done
}

stopjms() {
  ${DOCUMENTUM}/dba/stopdjms
}

DMUSER=${DMUSER:-`whoami`}
DMPASSWORD=${DMPASSWORD:-$DMUSER}
DOCUMENTUM=${DOCUMENTUM:-%DOCUMENTUM%}
DOCUMENTUM_SHARED=${DOCUMENTUM_SHARED:-%DOCUMENTUM_SHARED%}
DM_HOME=${DM_HOME:-%DM_HOME%}

export ORACLE_HOME=${ORACLE_HOME:-%ORACLE_HOME%}
export NLS_LANG=AMERICAN_AMERICA.AL32UTF8

export LC_ALL=en_US.utf8
export LANG=en_US.utf8


if [ ! -d $DM_HOME ]; then
  echo "Documentum home $DM_HOME not availiable"
  exit 1
fi

if [ -r $DM_HOME/bin/dm_set_server_env.sh ]; then
  echo "Applying server environment"
  . $DM_HOME/bin/dm_set_server_env.sh
fi

stopcontents

stopjms

stopdocbrokers

exit 0
