#!/bin/sh

CONTAINER=$1
TIMEOUT=${2:-300}
WAIT_INTERVAL=10

if [ "x$CONTAINER" = "x" ]; then
  echo "Specify container id"
  exit 1
fi

INIT_PID=`docker inspect --format "{{ .State.Pid }}" $CONTAINER`
STATUS=$?

if [ "x$STATUS" != "x0" ]; then
  echo "Unable to inspect container $CONTAINER"
  exit $STATUS
fi

if [ "x$INIT_PID" = "x0" ]; then
  echo "Container $CONTAINER is stopped"
  exit
fi

nsenter -t $INIT_PID -m -u -i -n -p /bin/bash >/dev/null 2>&1 <<__EOF__
export PATH=/bin:/sbin:/usr/bin:/usr/sbin
shutdown -h now
__EOF__

let total_wait=0
while [ "x$INIT_PID" != "x0" ] && [ $total_wait -lt $TIMEOUT ]; do
  sleep $WAIT_INTERVAL
  let "total_wait=$total_wait+$WAIT_INTERVAL"
  ps -o pid --no-headers --ppid $INIT_PID >/dev/null 2>&1
  STATUS=$?
  if [ "x$STATUS" != "x0" ]; then
    break
  fi
done

docker stop $CONTAINER
