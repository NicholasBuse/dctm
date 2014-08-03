#!/bin/sh

export JAVA_HOME=%JAVA_HOME%
export DOCUMENTUM=${DOCUMENTUM:-%DOCUMENTUM%}
export DOCUMENTUM_SHARED=${DOCUMENTUM_SHARED:-%DOCUMENTUM_SHARED%}
export USER_MEM_ARGS="-Xms128m -Xmx1g -XX:MaxPermSize=512m -XX:PermSize=256m -Xss256k"
export JAVA_OPTS="-XX:+DisableExplicitGC -XX:+HeapDumpOnOutOfMemoryError"
export JAVA_OPTS="-verbose:gc $JAVA_OPTS"

${DOCUMENTUM}/dba/jbosscontrol -r %JBOSS_HOME% -c DctmServer_MethodServer -b 0.0.0.0 START
