#!/bin/sh

export DOCUMENTUM=${DOCUMENTUM:-%DOCUMENTUM%}

${DOCUMENTUM}/dba/jbosscontrol -r %JBOSS_HOME% -c DctmServer_MethodServer KILL
