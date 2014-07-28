#!/bin/sh

set -x

YUM_URL=http://public-yum.oracle.com/repo/OracleLinux/OL6/5/base/x86_64/

RPM_PACKAGES=(
oracle-instantclient11.2-basic-11.2.0.4.0-1.x86_64.rpm
oracle-instantclient11.2-devel-11.2.0.4.0-1.x86_64.rpm
oracle-instantclient11.2-sqlplus-11.2.0.4.0-1.x86_64.rpm
oracle-xe-11.2.0-1.0.x86_64.rpm
)

DOCUMENTUM_CS_ARCHIVE=Content_Server_7.1_linux64_oracle.tar
DOCUMENTUM_CS_PATCH=CS_7.1.0060.0200_linux_ora_P06.tar.gz
DOCUMENTUM_PE_ARCHIVE=Process_Engine_linux.tar

DOCUMENTUM_OWNER=dmadmin
DOCUMENTUM_OWNER_PASSWORD=dmadmin
DOCUMENTUM=/u01/documentum/cs
DOCUMENTUM_SHARED=/u01/documentum/cs/shared
DM_HOME=/u01/documentum/cs/product/7.1
DOCUMENTUM_JMS_PORT=9080
DOCUMENTUM_JMS_PASSWORD=Welcome1
DOCUMENTUM_SERVICE_NAME=dm_DOCUMENTUM
DOCUMENTUM_SERVICE_SECURE_NAME=dm_DOCUMENTUM_s
DOCUMENTUM_SERVICE_PORT=10000
DOCUMENTUM_SERVICE_SECURE_PORT=10001

export TMPDIR=/u01/tmp

if [ ! -d $TMPDIR ]; then
  unset TMPDIR
fi

check_log() {
  if [ ! -r $LOG_FILE ]; then
    echo "Unable to locate log file, aborting..."
    cleanup
  fi

  manual=false
  egrep "at .*(.*)$" $LOG_FILE
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
     read yn -p "Continue installation? (Y/N):"
     case $yn in
       [Yy]* ) rm -rf $DISTRIB_DIR; break;;
       [Nn]* ) echo "Aborting..."; cleanup;;
           * ) echo "Please answer yes or no.";;
     esac
  done
}

cleanup() {
  umount $TARGET/proc
  exit
}

YUMDIR=$(mktemp -d --tmpdir $(basename $0).XXXXXX)
mkdir $YUMDIR/yum.repos.d

TARGET=$(mktemp -d --tmpdir $(basename $0).XXXXXX)

cat > $YUMDIR/yum.conf <<__EOF__
[main]
cachedir=/var/cache/yum/$basearch/$releasever
keepcache=0
debuglevel=2
logfile=/var/log/yum.log
exactarch=1
obsoletes=1
gpgcheck=1
plugins=1
installonly_limit=3
reposdir=$YUMDIR/yum.repos.d
__EOF__

cat > $YUMDIR/yum.repos.d/public-yum-ol6.repo <<__EOF__
[oel]
name=Oracle Linux
baseurl=$YUM_URL
gpgcheck=0
enabled=1
__EOF__


yum -c $YUMDIR/yum.conf --installroot=$TARGET -y groupinstall \
  base core compat-libraries
#  additional-devel base core debugging development compat-libraries

yum -c $YUMDIR/yum.conf --installroot=$TARGET -y clean all


mknod -m 600 $TARGET/dev/console c 5 1
mknod -m 600 $TARGET/dev/initctl p
mknod -m 666 $TARGET/dev/full c 1 7
mknod -m 666 $TARGET/dev/null c 1 3
chmod 666 $TARGET/dev/null
mknod -m 666 $TARGET/dev/ptmx c 5 2
mknod -m 666 $TARGET/dev/random c 1 8
mknod -m 666 $TARGET/dev/tty c 5 0
mknod -m 666 $TARGET/dev/tty0 c 4 0
mknod -m 666 $TARGET/dev/urandom c 1 9
mknod -m 666 $TARGET/dev/zero c 1 5

cat > $TARGET/etc/sysconfig/network <<__EOF__
NETWORKING=yes
HOSTNAME=localhost.localdomain
__EOF__

grep ^nameserver /etc/resolv.conf > $TARGET/etc/resolv.conf

mkdir $TARGET/distr

for package in ${RPM_PACKAGES[@]:0}; do
  cp $package $TARGET/distr
done

mount -t proc none $TARGET/proc
ln -s /proc/self/mounts $TARGET/etc/mtab

echo "Fixing rpm database"
chroot $TARGET /bin/bash <<__EOF__
export PATH=/bin:/sbin:/usr/bin:/usr/sbin
rpmdb --rebuilddb
__EOF__

echo "Installing extra rpms..."
chroot $TARGET /bin/bash <<__EOF__
export PATH=/bin:/sbin:/usr/bin:/usr/sbin
find /distr -name "*.rpm" | xargs rpm -ivh
rm -rf /distr
__EOF__

echo "Creating documentum user and directories..."
chroot $TARGET /bin/bash <<__EOF__
export PATH=/bin:/sbin:/usr/bin:/usr/sbin
useradd $DOCUMENTUM_OWNER
echo $DOCUMENTUM_OWNER_PASSWORD | passwd --stdin $DOCUMENTUM_OWNER
mkdir -p $DOCUMENTUM
mkdir -p $DOCUMENTUM_SHARED
__EOF__

DOCUMENTUM_OWNER_UID=`stat -c %u $TARGET/home/$DOCUMENTUM_OWNER`
chown -R $DOCUMENTUM_OWNER_UID $TARGET/$DOCUMENTUM
chown -R $DOCUMENTUM_OWNER_UID $TARGET/$DOCUMENTUM_SHARED

cat >> $TARGET/etc/services <<__EOF__

$DOCUMENTUM_SERVICE_NAME    $DOCUMENTUM_SERVICE_PORT/tcp
$DOCUMENTUM_SERVICE_SECURE_NAME    $DOCUMENTUM_SERVICE_SECURE_PORT/tcp
__EOF__

echo "Installing documentum software..."

if [ "x$DOCUMENTUM_CS_ARCHIVE" = "x" ]; then
  echo "Nothing to install"
else

  DISTRIB_DIR=$TARGET/$DOCUMENTUM/distr/cs
  LOG_FILE=$DISTRIB_DIR/logs/install.log

  mkdir -p $DISTRIB_DIR
  tar -x -C $DISTRIB_DIR -f $DOCUMENTUM_CS_ARCHIVE

  cat > $DISTRIB_DIR/silentinstall.properties <<__EOF__
INSTALLER_UI=silent
##default documentum home directory
SERVER.DOCUMENTUM=$DOCUMENTUM
##app server port
APPSERVER.SERVER_HTTP_PORT=$DOCUMENTUM_JMS_PORT
##app server password
APPSERVER.SECURE.PASSWORD=$DOCUMENTUM_JMS_PASSWORD
##enable cas as default
SERVER.CAS_LICENSE=LDSOPEJPWDQ
__EOF__

  chown -R $DOCUMENTUM_OWNER_UID $DISTRIB_DIR

  chroot $TARGET /usr/bin/sudo -u $DOCUMENTUM_OWNER /bin/bash <<__EOF__
export PATH=/bin:/usr/bin
export DOCUMENTUM=$DOCUMENTUM
export DOCUMENTUM_SHARED=$DOCUMENTUM_SHARED
export DM_HOME=$DM_HOME
cd ${DISTRIB_DIR//$TARGET/}
chmod u+x serverSetup.bin
./serverSetup.bin -f silentinstall.properties
__EOF__

  check_log
  
fi

JAVA_BINARY=`ls -1d $TARGET/$DOCUMENTUM_SHARED/java*/*/bin/java 2>/dev/null | head -1`
JAVA_HOME=`dirname $JAVA_BINARY`
JAVA_HOME=`dirname $JAVA_HOME`
export JAVA_HOME=${JAVA_HOME//$TARGET\//}

if [ "x$JAVA_HOME" = "x" ]; then
  echo "Unable locate JAVA_HOME"
  cleanup
fi

echo "Installing documentum patch..."

if [ "x$DOCUMENTUM_CS_PATCH" = "x" -o "x$DOCUMENTUM_CS_ARCHIVE" = "x" ]; then
  echo "Nothing to install"
else

  DISTRIB_DIR=$TARGET/$DOCUMENTUM/distr/cspatch
  LOG_FILE=$DISTRIB_DIR/logs/install.log

  mkdir -p $DISTRIB_DIR
  PATCH_FILE=`tar -x -z -v -C $DISTRIB_DIR -f $DOCUMENTUM_CS_PATCH | grep tar.gz`

  cat > $DISTRIB_DIR/silentinstall.properties <<__EOF__
INSTALLER_UI=silent
USER_SELECTED_PATCH_ZIP_FILE=$PATCH_FILE
__EOF__

  chown -R $DOCUMENTUM_OWNER_UID $DISTRIB_DIR

  chroot $TARGET /usr/bin/sudo -u $DOCUMENTUM_OWNER /bin/bash <<__EOF__
export PATH=/bin:/usr/bin
export DOCUMENTUM=$DOCUMENTUM
export DOCUMENTUM_SHARED=$DOCUMENTUM_SHARED
export DM_HOME=$DM_HOME
export JAVA_BINARY=$JAVA_HOME/bin/java
cd ${DISTRIB_DIR//$TARGET/}
chmod u+x patch.bin
./patch.bin LAX_VM \$JAVA_BINARY -f silentinstall.properties
__EOF__

  check_log

fi

echo "Installing process engine..."

if [ "x$DOCUMENTUM_PE_ARCHIVE" = "x" -o "x$DOCUMENTUM_CS_ARCHIVE" = "x" ]; then
  echo "Nothing to install"
else

  DISTRIB_DIR=$TARGET/$DOCUMENTUM/distr/pe
  LOG_FILE=$DISTRIB_DIR/logs/install.log

  mkdir -p $DISTRIB_DIR
  tar -x -C $DISTRIB_DIR -f $DOCUMENTUM_PE_ARCHIVE

  cat > $DISTRIB_DIR/silentinstall.properties <<__EOF__
INSTALLER_UI=silent
##app server port
APPSERVER.SERVER_HTTP_PORT=$DOCUMENTUM_JMS_PORT
##app server password
APPSERVER.SECURE.PASSWORD=$DOCUMENTUM_JMS_PASSWORD
__EOF__

  chown -R $DOCUMENTUM_OWNER_UID $DISTRIB_DIR

  chroot $TARGET /usr/bin/sudo -u $DOCUMENTUM_OWNER /bin/bash <<__EOF__
export JAVA_HOME=$JAVA_HOME
export PATH=/bin:/usr/bin:$JAVA_HOME/bin
export DOCUMENTUM=$DOCUMENTUM
export DOCUMENTUM_SHARED=$DOCUMENTUM_SHARED
export DM_HOME=$DM_HOME
cd ${DISTRIB_DIR//$TARGET/}
chmod u+x peSetup.bin
./peSetup.bin -f silentinstall.properties
__EOF__

  check_log

fi

echo "Postinstall steps..."

chroot $TARGET /bin/bash <<__EOF__
export PATH=/bin:/sbin:/usr/bin:/usr/sbin

cat >> /etc/ld.so.conf.d/oracle-instant-client-x86_64.conf <<___EOF___
/usr/lib/oracle/11.2/client64/lib
___EOF___

ldconfig

id -gn dmadmin | $DOCUMENTUM/dba/dm_root_task

sed -i -e 's/memory_target=/#memory_target=/' /u01/app/oracle/product/11.2.0/xe/config/scripts/init.ora
sed -i -e 's/memory_target=/#memory_target=/' /u01/app/oracle/product/11.2.0/xe/config/scripts/initXETemp.ora

ln -s /u01/app/oracle/product/11.2.0/xe/network /usr/lib/oracle/11.2/client64/

cat >> ~$DOCUMENTUM_OWNER/.bashrc <<___EOF___

# Documentum env
export DOCUMENTUM=$DOCUMENTUM
export DOCUMENTUM_SHARED=$DOCUMENTUM_SHARED
export DM_HOME=$DM_HOME

# Oracle env
export ORACLE_HOME=/usr/lib/oracle/11.2/client64
export NLS_LANG=american_america.al32utf8

# Java env
export JAVA_HOME=$JAVA_HOME
export CLASSPATH=\\\$DOCUMENTUM_SHARED/config:\\\$DOCUMENTUM_SHARED/dctm.jar:\\\$DM_HOME/dctm-server.jar:\\\$DOCUMENTUM_SHARED/dfc/log4j.jar

# Path
export PATH=/bin:/usr/bin:\\\$ORACLE_HOME/bin:\\\$DM_HOME/bin:\\\$DOCUMENTUM/dba

___EOF___

chown $DOCUMENTUM_OWNER ~$DOCUMENTUM_OWNER/.bashrc

__EOF__

cleanup

