#!/bin/sh

DOCKER_IMAGE=documentum
DOCKER_TAG=71
DOCKER_URL=-

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
DOCUMENTUM=/u01/documentum/cs
DOCUMENTUM_SHARED=$DOCUMENTUM/shared
DM_HOME=$DOCUMENTUM/product/7.1
DOCUMENTUM_JMS_PORT=9080
DOCUMENTUM_SERVICE_NAME=dm_DOCUMENTUM
DOCUMENTUM_SERVICE_SECURE_NAME=dm_DOCUMENTUM_s
DOCUMENTUM_SERVICE_PORT=10000
DOCUMENTUM_SERVICE_SECURE_PORT=10001
# set passwords or use random
DOCUMENTUM_OWNER_PASSWORD=`tr -cd '[:alnum:]' < /dev/urandom | fold -w12 | head -n1`
DOCUMENTUM_JMS_PASSWORD=`tr -cd '[:alnum:]' < /dev/urandom | fold -w12 | head -n1`
ROOT_PASSWORD=`tr -cd '[:alnum:]' < /dev/urandom | fold -w12 | head -n1`

cleanup() {
  umount $TARGET/proc
  exit
}


check_log() {
  
  LOG_FILE=$1

  if [ ! -r $LOG_FILE ]; then
    echo "Unable to locate log file, aborting..."
    cleanup
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
     read -p "Continue installation? (Y/N):" yn
     case $yn in
       [Yy]* ) rm -rf $DISTRIB_DIR; break;;
       [Nn]* ) echo "Aborting..."; cleanup;;
           * ) echo "Please answer yes or no.";;
     esac
  done
}

process_template() {
  sed -i -e "s#%DOCUMENTUM%#$DOCUMENTUM#g" $TEMPLATE
  sed -i -e "s#%DOCUMENTUM_SHARED%#$DOCUMENTUM_SHARED#g" $TEMPLATE
  sed -i -e "s#%DM_HOME%#$DM_HOME#g" $TEMPLATE
  sed -i -e "s#%DOCUMENTUM_SERVICE_NAME%#$DOCUMENTUM_SERVICE_NAME#g" $TEMPLATE
  sed -i -e "s#%DOCUMENTUM_SERVICE_NAME_SECURE%#$DOCUMENTUM_SERVICE_NAME_SECURE#g" $TEMPLATE
  sed -i -e "s#%DOCUMENTUM_OWNER%#$DOCUMENTUM_OWNER#g" $TEMPLATE
  sed -i -e "s#%JAVA_HOME%#$JAVA_HOME#g" $TEMPLATE
  sed -i -e "s#%JBOSS_HOME%#$JBOSS_HOME#g" $TEMPLATE
  sed -i -e "s#%ORACLE_HOME%#/usr/lib/oracle/11.2/client64#g" $TEMPLATE
}


YUMDIR=$(mktemp -d --tmpdir $(basename $0).XXXXXX)
mkdir $YUMDIR/yum.repos.d

TARGET=$(mktemp -d --tmpdir $(basename $0).XXXXXX)
BUILD_DIR=$(mktemp -d --tmpdir $(basename $0).XXXXXX)

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


echo "Installing packages..."
yum -c $YUMDIR/yum.conf --installroot=$TARGET -y -q groupinstall \
  base core compat-libraries

yum -c $YUMDIR/yum.conf --installroot=$TARGET -y -q clean all

mknod -m 666 $TARGET/dev/tty0 c 4 0
mknod -m 600 $TARGET/dev/console c 5 1
mknod -m 600 $TARGET/dev/initctl p
mknod -m 666 $TARGET/dev/full c 1 7
chmod 666 $TARGET/dev/null
mknod -m 666 $TARGET/dev/ptmx c 5 2
mknod -m 666 $TARGET/dev/random c 1 8
mknod -m 666 $TARGET/dev/tty c 5 0
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
echo $ROOT_PASSWORD | passwd --stdin root
mkdir -p $DOCUMENTUM
mkdir -p $DOCUMENTUM_SHARED
__EOF__

export DOCUMENTUM_OWNER_HOME=`chroot $TARGET /bin/bash <<__EOF__
echo ~$DOCUMENTUM_OWNER
__EOF__`

export DOCUMENTUM_OWNER_UID=`chroot $TARGET /bin/bash <<__EOF__
stat -c %u $DOCUMENTUM_OWNER_HOME
__EOF__`


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

  mkdir -p $DISTRIB_DIR
  tar -x -C $DISTRIB_DIR -f $DOCUMENTUM_CS_ARCHIVE

  cat > $DISTRIB_DIR/silentinstall.properties <<__EOF__
INSTALLER_UI=silent
SERVER.DOCUMENTUM=$DOCUMENTUM
APPSERVER.SERVER_HTTP_PORT=$DOCUMENTUM_JMS_PORT
APPSERVER.SECURE.PASSWORD=$DOCUMENTUM_JMS_PASSWORD
__EOF__

  chown -R $DOCUMENTUM_OWNER_UID $DISTRIB_DIR

  chroot $TARGET /sbin/runuser $DOCUMENTUM_OWNER -l -c /bin/bash <<__EOF__
export PATH=/bin:/usr/bin
export DOCUMENTUM=$DOCUMENTUM
export DOCUMENTUM_SHARED=$DOCUMENTUM_SHARED
export DM_HOME=$DM_HOME
cd ${DISTRIB_DIR//$TARGET/}
chmod u+x serverSetup.bin
./serverSetup.bin -f silentinstall.properties
__EOF__

  check_log $DISTRIB_DIR/logs/install.log
  
fi

JAVA_BINARY=`ls -1d $TARGET/$DOCUMENTUM_SHARED/java*/*/bin/java 2>/dev/null | head -1`
JAVA_HOME=`dirname $JAVA_BINARY`
JAVA_HOME=`dirname $JAVA_HOME`
JAVA_HOME=${JAVA_HOME//$TARGET\//}

if [ "x$JAVA_HOME" = "x" ]; then
  echo "Unable locate JAVA_HOME"
  cleanup
fi


JBOSS_HOME=`ls -1d $TARGET/$DOCUMENTUM_SHARED/jboss* 2>/dev/null | head -1`
JBOSS_HOME=${JBOSS_HOME//$TARGET\//}
if [ "x$JBOSS_HOME" = "x" ]; then
  echo "Unable locate JBOSS"
  cleanup
fi


echo "Installing documentum patch..."

if [ "x$DOCUMENTUM_CS_PATCH" = "x" -o "x$DOCUMENTUM_CS_ARCHIVE" = "x" ]; then
  echo "Nothing to install"
else

  DISTRIB_DIR=$TARGET/$DOCUMENTUM/distr/cspatch

  mkdir -p $DISTRIB_DIR
  PATCH_FILE=`tar -x -z -v -C $DISTRIB_DIR -f $DOCUMENTUM_CS_PATCH | grep tar.gz`

  cat > $DISTRIB_DIR/silentinstall.properties <<__EOF__
INSTALLER_UI=silent
USER_SELECTED_PATCH_ZIP_FILE=$PATCH_FILE
__EOF__

  chown -R $DOCUMENTUM_OWNER_UID $DISTRIB_DIR

  chroot $TARGET /sbin/runuser $DOCUMENTUM_OWNER -l -c /bin/bash <<__EOF__
export PATH=/bin:/usr/bin
export DOCUMENTUM=$DOCUMENTUM
export DOCUMENTUM_SHARED=$DOCUMENTUM_SHARED
export DM_HOME=$DM_HOME
export JAVA_BINARY=$JAVA_HOME/bin/java
cd ${DISTRIB_DIR//$TARGET/}
chmod u+x patch.bin
./patch.bin LAX_VM \$JAVA_BINARY -f silentinstall.properties
__EOF__

  check_log $DISTRIB_DIR/logs/install.log

fi

echo "Installing process engine..."

if [ "x$DOCUMENTUM_PE_ARCHIVE" = "x" -o "x$DOCUMENTUM_CS_ARCHIVE" = "x" ]; then
  echo "Nothing to install"
else

  DISTRIB_DIR=$TARGET/$DOCUMENTUM/distr/pe

  mkdir -p $DISTRIB_DIR
  tar -x -C $DISTRIB_DIR -f $DOCUMENTUM_PE_ARCHIVE

  cat > $DISTRIB_DIR/silentinstall.properties <<__EOF__
INSTALLER_UI=silent
APPSERVER.SERVER_HTTP_PORT=$DOCUMENTUM_JMS_PORT
APPSERVER.SECURE.PASSWORD=$DOCUMENTUM_JMS_PASSWORD
__EOF__

  chown -R $DOCUMENTUM_OWNER_UID $DISTRIB_DIR

  chroot $TARGET /sbin/runuser $DOCUMENTUM_OWNER -l -c /bin/bash <<__EOF__
export JAVA_HOME=$JAVA_HOME
export PATH=/bin:/usr/bin:$JAVA_HOME/bin
export DOCUMENTUM=$DOCUMENTUM
export DOCUMENTUM_SHARED=$DOCUMENTUM_SHARED
export DM_HOME=$DM_HOME
cd ${DISTRIB_DIR//$TARGET/}
chmod u+x peSetup.bin
./peSetup.bin -f silentinstall.properties
__EOF__

  check_log $DISTRIB_DIR/logs/install.log

fi

echo "Postinstall steps..."

cat >> $TARGET/etc/ld.so.conf.d/oracle-instant-client-x86_64.conf <<__EOF__
/usr/lib/oracle/11.2/client64/lib
__EOF__


for file in /u01/app/oracle/product/11.2.0/xe/config/scripts/init.ora /u01/app/oracle/product/11.2.0/xe/config/scripts/initXETemp.ora; do
  sed -i -e 's/memory_target=/#memory_target=/' $TARGET/$file
  sed -i -e 's/sessions=.*/sessions=150\nprocesses=100/' $TARGET/$file
done

cat >> $TARGET/$DOCUMENTUM_OWNER_HOME/.bashrc <<__EOF__
# Documentum env
export DOCUMENTUM=$DOCUMENTUM
export DOCUMENTUM_SHARED=$DOCUMENTUM_SHARED
export DM_HOME=$DM_HOME

# Oracle env
export ORACLE_HOME=/usr/lib/oracle/11.2/client64
export NLS_LANG=american_america.al32utf8

# Java env
export JAVA_HOME=$JAVA_HOME
export CLASSPATH=\$DOCUMENTUM_SHARED/config:\$DOCUMENTUM_SHARED/dctm.jar:\$DM_HOME/dctm-server.jar:\$DOCUMENTUM_SHARED/dfc/log4j.jar

# Path
export PATH=/bin:/usr/bin:\$ORACLE_HOME/bin:\$DM_HOME/bin:\$DOCUMENTUM/dba

# Libraries
export LD_LIBRARY_PATH=\$DM_HOME/bin:\$JAVA_HOME/jre/lib/amd64:\$JAVA_HOME/jre/lib/amd64/server 
__EOF__

chown $DOCUMENTUM_OWNER_UID $TARGET/$DOCUMENTUM_OWNER_HOME/.bashrc

sed -i -e '/^dfc.docbroker.host/d' $TARGET/$DOCUMENTUM_SHARED/config/dfc.properties
sed -i -e '/^dfc.docbroker.port/d' $TARGET/$DOCUMENTUM_SHARED/config/dfc.properties

for script in jbosscontrol.sh startdjms.sh start_documentum.sh stopdjms.sh stop_documentum.sh tomcatcontrol.sh; do
  target=${script//\.sh/}
  cp $script $TARGET/$DOCUMENTUM/dba/$target
  TEMPLATE=$TARGET/$DOCUMENTUM/dba/$target
  process_template
  chmod a+x $TEMPLATE
  chown $DOCUMENTUM_OWNER_UID $TEMPLATE
done

for script in firstboot.sh documentum.sh; do
  target=${script//\.sh/}
  cp $script $TARGET/etc/init.d/$target
  TEMPLATE=$TARGET/etc/init.d/$target
  process_template
  chmod a+x $TEMPLATE
  chown root $TEMPLATE
done 

cat > $TARGET/etc/sysconfig/firstboot <<__EOF__
DOCUMENTUM=$DOCUMENTUM
DOCUMENTUM_SHARED=$DOCUMENTUM_SHARED
DM_HOME=$DM_HOME
DOCUMENTUM_OWNER=$DOCUMENTUM_OWNER
SERVICE_NAME=$DOCUMENTUM_SERVICE_NAME
__EOF__

chroot $TARGET /bin/bash <<__EOF__
export PATH=/bin:/sbin:/usr/bin:/usr/sbin

ldconfig

id -gn $DOCUMENTUM_OWNER | $DOCUMENTUM/dba/dm_root_task

ln -s /u01/app/oracle/product/11.2.0/xe/network /usr/lib/oracle/11.2/client64/

chkconfig | awk {'print \$1'} | xargs -I %service% chkconfig --level 0123456 %service% off

chkconfig --add firstboot

chkconfig --level 345 postfix on
chkconfig --level 345 rsyslog on
chkconfig --level 345 sshd on
chkconfig --level 345 firstboot on
__EOF__

umount $TARGET/proc

tar --numeric-owner -c -C $TARGET . | docker import $DOCKER_URL $DOCKER_IMAGE:$DOCKER_TAG

rm -rf $TARGET
rm -rf $YUMDIR

cat << __EOF__
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!! Image $DOCKER_IMAGE:$DOCKER_TAG is ready
!! Shell password for user root: $ROOT_PASSWORD
!! Shell password for user $DOCUMENTUM_OWNER: $DOCUMENTUM_OWNER_PASSWORD
!! JMS admin password: $DOCUMENTUM_JMS_PASSWORD
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
__EOF__

cat >  $BUILD_DIR/Dockerfile <<__EOF__
FROM $DOCKER_IMAGE:$DOCKER_TAG
MAINTAINER Andrey B. Panfilov <andrew@panfilov.tel>
ENTRYPOINT /sbin/init
__EOF__

docker build --force-rm -t $DOCKER_IMAGE:$DOCKER_TAG $BUILD_DIR

rm -rf $BUILD_DIR
