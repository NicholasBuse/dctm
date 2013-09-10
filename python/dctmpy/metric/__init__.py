#  Copyright (c) 2013 Andrey B. Panfilov <andrew@panfilov.tel>
#
#  See main module for license.
#
from dctmpy import *
from dctmpy.docbase import Docbase
from dctmpy.docbroker import Docbroker


JOB_ATTRIBUTES = ['object_name', 'is_inactive', 'a_last_invocation',
                  'a_last_completion', 'a_last_return_code', 'a_current_status',
                  'a_status', 'a_special_app', 'run_mode', 'run_interval',
                  'expiration_date', 'max_iterations', 'a_iterations',
                  'a_next_invocation', 'start_date', 'a_current_status']

JOB_QUERY = "SELECT " + ", ".join(JOB_ATTRIBUTES) + " FROM dm_job WHERE 1=1 "

JOB_ACTIVE_CONDITION = " AND ((a_last_invocation IS NOT NULLDATE and a_last_completion IS NULLDATE) OR a_special_app = 'agentexec')" \
                       " AND (i_is_reference = 0 OR i_is_reference is NULL)" \
                       " AND (i_is_replica = 0 OR i_is_replica is NULL)"


def checkRegistration(docbroker, docbasename, servername=None, checkall=True):
    docbasemap = docbroker.getDocbaseMap()
    if not docbasename in docbasemap['r_docbase_name']:
        raise CheckError("docbase %s is not registered on %s" % (docbasename, parseAddr(docbasemap['i_host_addr'])))
    servermap = docbroker.getServerMap(docbasename)
    if servername is not None and not servername in servermap['r_server_name']:
        raise CheckError(
            "%s.%s is not registered on %s" % (docbasename, servername, parseAddr(servermap['i_host_addr'])))
    elif not checkall:
        return "docbase %s is registered on %s" % (docbasename, parseAddr(docbasemap['i_host_addr']))
    message = ""
    success = True
    for (srv, status, docbaseid, connaddr) in zip(servermap['r_server_name'], servermap['r_last_status'],
                                                  servermap['i_docbase_id'],
                                                  servermap['i_server_connection_address']):
        if servername is not None and not srv == servername:
            continue
        if status != "Open":
            message += "%s.%s has status %s on %s, " % (
                docbasename, srv, status, parseAddr(servermap['i_host_addr']))
            success = False
        else:
            chunks = connaddr.split(" ")
            host = chunks[4]
            port = int(chunks[2], 16)
            try:
                Docbase(host=host, port=port, docbaseid=docbaseid).disconnect()
                message += "%s.%s has status %s on %s, " % (
                    docbasename, srv, status, parseAddr(servermap['i_host_addr']))
            except Exception, e:
                message += "%s.%s has status %s on %s, but error occurred during connection %s, " % (
                    docbasename, srv, status, parseAddr(servermap['i_host_addr']), str(e))
                success = False
    if success:
        return message[:-2]
    raise CheckError(message[:-2])


def checkJobs(session, jobs=None):
    message = ""
    critical = False
    warning = False
    for job in getJobs(session, jobs):
        try:
            message += "%s, " % checkJobStatus(**job)
        except CheckWarning, w:
            message += "%s, " % str(w)
            warning |= True
        except CheckError, e:
            message += "%s, " % str(e)
            critical |= True
        except Exception, e:
            message += "%s, " % str(e)
            critical |= True

    if critical:
        raise CheckError(message[:-2])
    if warning:
        raise CheckWarning(message[:-2])
    return message


def getJobs(session, jobs=None, condition=""):
    query = JOB_QUERY + condition
    if not isEmpty(jobs):
        query += " AND object_name IN ('" + "','".join(jobs) + "')"
    return runQuery(session, query)


def getRunningJobs(session):
    return getJobs(session, JOB_ACTIVE_CONDITION)


def checkActiveSessions(session, warn=0, crit=0, warnpct=0, critpct=0):
    info = session.COUNT_SESSIONS()
    concurrent = info['concurrent_sessions']
    hot = info['hot_list_size']
    if crit != 0 and hot > crit:
        raise CheckError("Session count %d exceeds critical threshold %d" % (hot, crit))
    if warn != 0 and hot > warn:
        raise CheckWarning("Session count %d exceeds warning threshold %d" % (hot, crit))
    if critpct != 0 and 100.0 * hot / concurrent > critpct:
        raise CheckError("Session count %d/%d exceeds critical threshold %02.2f" % (hot, concurrent, critpct))
    if warnpct != 0 and 100.0 * hot / concurrent > warnpct:
        raise CheckWarning("Session count %d/%d exceeds warning threshold %02.2f" % (hot, concurrent, warnpct))
    return concurrent


def checkProjectionTargets(session):
    servername = session.serverconfig['object_name']
    docbasename = session.docbaseconfig['object_name']
    message = "server %s.%s: " % (docbasename, servername)
    success = True
    for (host, port) in getServerTargets(session):
        try:
            docbroker = Docbroker(host=host, port=port)
            servermap = docbroker.getServerMap(docbasename)
            if not servername in servermap['r_server_name']:
                message += "not registered on %s, " % (parseAddr(servermap['i_host_addr']))
                success &= False
            else:
                for (srv, status) in zip(servermap['r_server_name'], servermap['r_last_status']):
                    if srv == servername and status != "Open":
                        raise CheckError("status is %s on %s" % (status, parseAddr(servermap['i_host_addr'])))
                message += "registered on %s, " % (parseAddr(servermap['i_host_addr']))
        except Exception, e:
            message += "%s, " % str(e)
            success &= False
    if success:
        return message[:-2]
    else:
        raise CheckError(message[:-2])


def checkJobStatus(**job):
    jobname = job['object_name']
    if job['start_date'] is None or job['start_date'] <= 0:
        raise CheckError("Job %s has undefined start_date" % jobname)
    if job['a_next_invocation'] is None or job['a_next_invocation'] <= 0:
        raise CheckError("Job %s has undefined next_invocation_date" % jobname)
    if job['expiration_date'] is not None and job['expiration_date'] < job['start_date']:
        raise CheckError("Job %s has expiration_date less then start_date" % jobname)
    if job['max_iterations'] < 0:
        raise CheckError("Job %s has invalid max_iterations value: %d" % (jobname, job['max_iterations']))
    if job['run_mode'] == 0 and job['run_interval'] == 0 and job['max_iterations'] != 1:
        raise CheckError("Job %s has invalid max_iterations value for run_mode=0 and run_interval=0" % jobname)
    if (job['run_mode'] == 1 or job['run_mode'] == 2 or job['run_mode'] == 3 or job['run_mode'] == 4) and (
                job['run_interval'] < 1 or job['run_interval'] > 32767):
        raise CheckError(
            "Job %s has invalid run_interval value, expected [1, 32767], got %d" % (jobname, job['run_interval']))
    if job['run_mode'] == 7 and (job['run_interval'] < -7 or job['run_interval'] > 7 or job['run_interval'] == 0):
        raise CheckError(
            "Job %s has invalid run_interval value, expected [-7,7], got %d)" % (jobname, job['run_interval']))
    if job['run_mode'] == 8 and (job['run_interval'] < -28 or job['run_interval'] > 28 or job['run_interval'] == 0):
        raise CheckError(
            "Job %s has invalid run_interval value, expected [-28,0) U (0,28], got %d)" % (
                jobname, job['run_interval']))
    if job['run_mode'] == 9 and (job['run_interval'] < -365 or job['run_interval'] > 365 or job['run_interval'] == 0):
        raise CheckError(
            "Job %s has invalid run_interval value, expected [-365,0) U (0,365], got %d)" % (
                jobname, job['run_interval']))
    if job['is_inactive']:
        raise CheckError("Job %s is inactive" % jobname)
    if job['expiration_date'] is not None and time.time() > job['expiration_date']:
        raise CheckError("Job %s is expired" % jobname)
    if 0 < job['max_iterations'] < job['a_iterations']:
        raise CheckError("Job %s max iterations exceeded" % jobname)
    if job['a_last_invocation'] is None:
        raise CheckWarning("Job %s has been never executed" % jobname)
    if job['a_last_return_code'] != 0:
        raise CheckError("Job %s has status: %s" % (jobname, job['a_current_status']))
    if re.search('agentexec', job['a_special_app']) is not None or (
                job['a_last_invocation'] is not None and job['a_last_completion'] is None):
        return "Job %s is running for %s" % (jobname, prettyInterval(job['a_last_invocation']))
    timegap = time.time() - job['a_last_completion']
    interval = prettyInterval(job['a_last_completion'])
    intervals = {
        1: 60,
        2: 60 * 60,
        3: 24 * 60 * 60,
        4: 7 * 24 * 60 * 60
    }
    if job['run_mode'] == 1 or job['run_mode'] == 2 or job['run_mode'] == 3 or job['run_mode'] == 4:
        if timegap > 2 * intervals[job['run_mode']] * job['run_interval']:
            raise CheckError("Job %s last run - %s ago" % (jobname, interval))
        elif timegap > intervals[job['run_mode']] * job['run_interval']:
            raise CheckWarning("Job %s last run - %s ago" % (jobname, interval))
        else:
            return "Job %s last run - %s ago" % (jobname, interval)
    else:
        raise CheckError("Scheduling type for job %s is not currently supported" % jobname)


def getFailedTasks(session, offset=7):
    query = "SELECT que.task_name, que.name" \
            " FROM dmi_queue_item que, dmi_workitem wi, dmi_package pkg" \
            " WHERE que.date_sent > date(now) - %d " \
            " AND que.event = 'dm_changedactivityinstancestate'" \
            " AND que.item_id LIKE '4%%'" \
            " AND que.MESSAGE LIKE 'Activity instance, %%, of workflow, %%, failed.'" \
            " AND que.item_id = wi.r_object_id" \
            " AND wi.r_workflow_id = pkg.r_workflow_id" \
            " AND wi.r_act_seqno = pkg.r_act_seqno" \
            " AND que.delete_flag = 0" % offset
    return runQuery(session, query)


def runQuery(session, query):
    return ((lambda x: dict((attr, x[attr]) for attr in x))(e) for e in session.query(query))


def getServerTargets(session):
    for target in session.LIST_TARGETS():
        return zip(target['projection_targets'], target['projection_ports'])


def prettyInterval(timestamp):
    now = time.time()
    if now >= timestamp:
        secs = (now - timestamp) % 60
        mins = (int((now - timestamp) / 60)) % 60
        hours = (int((now - timestamp) / 3600))
        if hours < 24:
            return "%02d:%02d:%02d" % (hours, mins, secs)
        else:
            days = int(hours / 24)
            hours -= days * 24
            return "%d days %02d:%02d:%02d" % (days, hours, mins, secs)
    return "future"


class CheckError(RuntimeError):
    def __init__(self, *args, **kwargs):
        super(CheckError, self).__init__(*args, **kwargs)


class CheckWarning(RuntimeWarning):
    def __init__(self, *args, **kwargs):
        super(CheckWarning, self).__init__(*args, **kwargs)
