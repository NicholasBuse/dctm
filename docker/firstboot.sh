#!/bin/bash
#
# firstboot    Setup Documentum Content Server
#
# chkconfig: 2345 60 04
# description: Performs initial setup of Documentum Content Server
#
# processname: firstboot

### BEGIN INIT INFO
# Provides: sshd
# Required-Start: $local_fs $network $syslog $oracle-xe
# Required-Stop: $local_fs $syslog
# Should-Start: $syslog
# Should-Stop: $network $syslog
# Default-Start: 2 3 4 5
# Default-Stop: 0 1 6
# Short-Description: Setup Documentum Content Server
# Description:       Performs initial setup of Documentum Content Server
### END INIT INFO

# source function library
. /etc/rc.d/init.d/functions

# pull in sysconfig settings
[ -f /etc/sysconfig/firstboot ] && . /etc/sysconfig/firstboot

RETVAL=0
prog="firstboot"

runlevel=$(set -- $(runlevel); eval "echo \$$#" )

export_from_pid() {
  VARNAME=$1
  PID=$2
  while read -d $'\0' ENV; do 
    if [[ $ENV == $VARNAME=* ]]; then
      export "$ENV"
    fi
  done < /proc/$PID/environ
}

prompt() {
  PROMPT=$*
  while true; do
     read -p "$PROMPT" -t $READ_TIMEOUT REPLY
     STATUS=$?
     if [ "x$STATUS" != "x0" ]; then
       return $STATUS
     fi
     if [ "x$REPLY" != "x" ]; then
       break
     fi
  done
}

check_log() {
  LOG_FILE=$1
  if [ ! -r $LOG_FILE ]; then
    echo "Unable to locate log file, aboring"
    return 1
  fi

  manual=false
  egrep "^[[:space:]]{1,}at[[:space:]]{1,}[[:alpha:]]{1,}\..*\(.*\)$" $LOG_FILE >/dev/null 2>&1
  if [ "x$?" = "x0" ]; then
    manual=true
    (
      echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
      echo "!!     PLEASE ANALIZE LOG FILE      !!"
      echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
      cat $LOG_FILE
    ) | less -F -E
  fi

  while $manual; do
     read -p "Continue? (Y/N):" -t $READ_TIMEOUT yn
     STATUS=$?
     if [ "x$STATUS" != "x0" ]; then
       echo "Read timeout, aborting..."
       return 1
     fi
     case $yn in
       [Yy]* ) break;;
       [Nn]* ) echo "Aborting..."; return 1;;
           * ) echo "Please answer yes or no.";;
     esac
  done
}

check_mandatory_variable() {
  VARNAME=$1
  shift
  PROMPT=$*
  eval VARVALUE=\$$VARNAME
  if [ "x$VARVALUE" = "x" ]; then
     export_from_pid $VARNAME 1
     eval VARVALUE=\$$VARNAME
  fi

  if [ "x$VARVALUE" = "x" ]; then
    if [ "x$PROMPT" = "x" ]; then
      echo "Unable to get $VARNAME enviroment variable"
      return 1
    fi
    prompt $PROMPT
    if [ "x$?" != "x0" ]; then
      echo "Read timeout, exiting"
      return 1
    fi
    eval $VARNAME=$REPLY
  fi
}

check_password_variable() {
  VARNAME=$1
  eval VARVALUE=\$$VARNAME
  if [ "x$VARVALUE" = "x" ]; then
    echo "Generating $VARNAME"
    RND=`tr -cd '[:alnum:]' < /dev/urandom | fold -w12 | head -n1`
    eval $VARNAME=$RND
  fi
}

setup_oracle() {
  if [ -r /etc/sysconfig/oracle-xe ]; then
    echo "Oracle is already initialized"
    return 0
  fi
  
  echo "Initializing oracle database..."

  cat >> /tmp/oracle.rsp <<__EOF__
ORACLE_HTTP_PORT=8080
ORACLE_LISTENER_PORT=1521
ORACLE_PASSWORD=$DATABASE_ADMIN_PASSWORD
ORACLE_CONFIRM_PASSWORD=$DATABASE_ADMIN_PASSWORD
ORACLE_DBENABLE=y
__EOF__
  /etc/init.d/oracle-xe configure responseFile=/tmp/oracle.rsp > /tmp/oracle.rsp.log
  rm -f /tmp/oracle.rsp
  chkconfig --level 345 oracle-xe on
  cat >> ~/.documentum_credentials <<__EOF__
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!! Oracle sys/system password: $DATABASE_ADMIN_PASSWORD
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
__EOF__
}

setup_docbase() {
  if [ -r $DOCUMENTUM/dba/config/$REPOSITORY_NAME/server.ini ]; then
    echo "Docbase is already initialized"
    return 0
  fi

  echo "Initializing Documentum docbase..."

##
# BEGIN: Preventing some exceptions during setup
##
  REGISTRY_SECRET=`runuser $DOCUMENTUM_OWNER -l -c /bin/bash <<__EOF__ 
\\\$JAVA_HOME/bin/java com.documentum.fc.impl.util.RegistryPasswordUtils $REGISTRY_PASSWORD
__EOF__`

  sed -i -e '/^dfc.verify_registration/d' $DOCUMENTUM_SHARED/config/dfc.properties

  cat >> $DOCUMENTUM_SHARED/config/dfc.properties <<__EOF__
dfc.verify_registration=false
dfc.globalregistry.password=$REGISTRY_SECRET
dfc.globalregistry.repository=$REPOSITORY_NAME
dfc.globalregistry.username=$REGISTRY_USER
__EOF__
##
# END: Preventing some exceptions during setup
##

  cat >> /tmp/docbase.properties <<__EOF__
INSTALLER_UI=silent

# Licensing configuration
SERVER.CONFIGURATOR.LICENSING=false
# Licenses
#SERVER.AS_LICENSE=XXXXXXXXXXXX
#SERVER.TCS_LICENSE=XXXXXXXXXXXX
#SERVER.STA_LICENSE=XXXXXXXXXXXX
#SERVER.XHIVE_LICENSE=XXXXXXXXXXXX
#SERVER.CSSL_LICENSE=XXXXXXXXXXXX
#SERVER.RPS_LICENSE=XXXXXXXXXXXX
#SERVER.FRS_LICENSE=XXXXXXXXXXXX
#SERVER.RM_LICENSE=XXXXXXXXXXXX
#SERVER.PRM_LICENSE=XXXXXXXXXXXX

# Docbroker configration
SERVER.CONFIGURATOR.BROKER=true
SERVER.DOCBROKER_ACTION=CREATE
SERVER.DOCBROKER_PORT=$DOCBROKER_PORT
SERVER.DOCBROKER_NAME=$DOCBROKER_NAME
SERVER.DOCBROKER_CONNECT_MODE=native

# Docbase configuration
SERVER.CONFIGURATOR.REPOSITORY=true
SERVER.DOCBASE_ACTION=CREATE
SERVER.DOCBASE_NAME=$REPOSITORY_NAME
SERVER.DOCBASE_ID=$REPOSITORY_ID
SERVER.DOCBASE_DESCRIPTION=$REPOSITORY_NAME
SERVER.AUTH_DOMAIN=
SERVER.DOCBASE_SIZE=MEDIUM
SERVER.DOCBASE_STARTUP=AUTO

SERVER.DOCUMENTUM_SHARE=$DOCUMENTUM/share
SERVER.DOCUMENTUM_DATA=$DOCUMENTUM/data
SERVER.DOCUMENTUM_DATA_FOR_SAN_NAS=false

SERVER.DOCBASE_SERVICE_NAME=$SERVICE_NAME
SERVER.FQDN=$HOSTNAME
SERVER.CONNECT_MODE=native

SERVER.PROJECTED_DOCBROKER_HOST=$HOSTNAME
SERVER.PROJECTED_DOCBROKER_PORT=$DOCBROKER_PORT
SERVER.TEST_DOCBROKER=true

SERVER.USE_EXISTING_DATABASE_ACCOUNT=false
SERVER.DATABASE_CONNECTION=XE
SERVER.DOCBASE_OWNER_NAME=$REPOSITORY_NAME
SERVER.SECURE.DOCBASE_OWNER_PASSWORD=$REPOSITORY_DB_PASSWORD
SERVER.DATABASE_ADMIN_NAME=system
SERVER.SECURE.DATABASE_ADMIN_PASSWORD=$DATABASE_ADMIN_PASSWORD

SERVER.NOTIFICATIONS_EMAIL_ACCOUNT=$ADMIN_EMAIL
SERVER.SMTP_SERVER_NAME=$SMTP_SERVER

SERVER.GLOBAL_REGISTRY_SPECIFY_OPTION=USE_THIS_REPOSITORY
SERVER.BOF_REGISTRY_USER_LOGIN_NAME=$REGISTRY_USER
SERVER.SECURE.BOF_REGISTRY_USER_PASSWORD=$REGISTRY_PASSWORD

SERVER.ENABLE_XHIVE=false
SERVER.CONFIGURATOR.DISTRIBUTED_ENV=false
SERVER.ENABLE_RKM=false
START_METHOD_SERVER=false
MORE_DOCBASE=false
SERVER.CONGINUE.MORECOMPONENT=false
__EOF__

  chmod a+x $DM_HOME/install/{dm_launch_server_config_program.sh,Server_Configuration_Program.bin}
  chmod a-x $DM_HOME/bin/dm_agent_exec

  /sbin/runuser $DOCUMENTUM_OWNER -l -c /bin/bash <<__EOF__
cd \$DM_HOME/install
./dm_launch_server_config_program.sh -f /tmp/docbase.properties
__EOF__
  
  rm -f /tmp/docbase.properties

  cat >> ~/.documentum_credentials <<__EOF__
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!! Documentum database password: $REPOSITORY_DB_PASSWORD
!! Global registry password: $REGISTRY_PASSWORD
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
__EOF__

  check_log $DM_HOME/install/logs/install.log
  STATUS=$?
  if [ "x$STATUS" != "x0" ]; then
    return $STATUS
  fi

  chmod a+x $DM_HOME/bin/dm_agent_exec

  cat > /etc/sysconfig/documentum <<__EOF__
DOCUMENTUM=$DOCUMENTUM
DOCUMENTUM_OWNER=$DOCUMENTUM_OWNER
__EOF__

  chkconfig --add documentum
  chkconfig --level 345 documentum on

  service documentum stop
  service oracle-xe stop
}

perform_setup() {
  READ_TIMEOUT=60

  for VAR in DOCUMENTUM DOCUMENTUM_SHARED DM_HOME SERVICE_NAME DOCUMENTUM_OWNER; do
    check_mandatory_variable $VAR
    STATUS=$?
    if [ "x$STATUS" != "x0" ]; then
      return $STATUS
    fi
  done

  check_mandatory_variable REPOSITORY_NAME "Enter repositroy name: "
  STATUS=$?
  if [ "x$STATUS" != "x0" ]; then
     return $STATUS
  fi
  check_mandatory_variable REPOSITORY_ID "Enter repositroy id: "
  STATUS=$?
  if [ "x$STATUS" != "x0" ]; then
     return $STATUS
  fi

  check_password_variable DATABASE_ADMIN_PASSWORD
  check_password_variable REPOSITORY_DB_PASSWORD
  check_password_variable REGISTRY_PASSWORD

  DOCBROKER_NAME=${DOCBROKER_NAME:-Docbroker01}
  DOCBROKER_PORT=${DOCBROKER_PORT:-1489}
  HOSTNAME=`hostname`
  REGISTRY_USER=${REGISTRY_USER:-dm_bof_registry}
  SMTP_SERVER=${SMTP_SERVER:-127.0.0.1}
  ADMIN_EMAIL=${ADMIN_EMAIL}

  setup_oracle
  setup_docbase

  service oracle-xe start
  service documentum start
  chkconfig --level 0123456 firstboot off
  [ -f /etc/sysconfig/firstboot ] && rm -f /etc/sysconfig/firstboot
}



start() {
  echo -n $"Starting $prog: "
  perform_setup
  RETVAL=$?
  return $RETVAL
}

stop() {
  return 0
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
