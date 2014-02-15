#!python
import argparse
import re
import nagiosplugin
from nagiosplugin.state import Critical, Warn, Ok, Unknown
from dctmpy.docbaseclient import DocbaseClient
from dctmpy.docbrokerclient import DocbrokerClient

JOB_ATTRIBUTES = ['object_name', 'is_inactive', 'a_last_invocation',
                  'a_last_completion', 'a_last_return_code', 'a_current_status',
                  'a_status', 'a_special_app', 'run_mode', 'run_interval',
                  'expiration_date', 'max_iterations', 'a_iterations',
                  'a_next_invocation', 'start_date', 'a_current_status']

JOB_QUERY = "SELECT " + ", ".join(JOB_ATTRIBUTES) + " FROM dm_job WHERE 1=1 "

JOB_ACTIVE_CONDITION = " AND ((a_last_invocation IS NOT NULLDATE and a_last_completion IS NULLDATE) OR a_special_app = 'agentexec')" \
                       " AND (i_is_reference = 0 OR i_is_reference is NULL)" \
                       " AND (i_is_replica = 0 OR i_is_replica is NULL)"

JOB_INTERVALS = {
    1: 60,
    2: 60 * 60,
    3: 24 * 60 * 60,
    4: 7 * 24 * 60 * 60
}


class CheckDocbase(nagiosplugin.Resource):
    def __init__(self, args, results):
        self.args = args
        self.results = results
        self.session = None

    def probe(self):
        yield nagiosplugin.Metric("null", 0, "null")
        try:
            self.checkLogin()
            if not self.session:
                return
            if self.mode == 'login':
                return
            for result in modes[self.mode][0](self):
                if result:
                    yield result
        finally:
            try:
                if self.session:
                    self.session.disconnect()
            except Exception, e:
                pass

    def checkSessions(self):
        try:
            count = self.session.COUNT_SESSIONS()
        except Exception, e:
            self.addResult(Critical, "Unable to retrieve session count: " + str(e))
            return
        return nagiosplugin.Metric('sessioncount', count['hot_list_size'], min=0, context='sessioncount')

    def checkTargets(self):
        targets = []
        servername = self.session.serverconfig['object_name']
        docbaseame = self.session.docbaseconfig['object_name']
        try:
            for target in self.session.LIST_TARGETS():
                targets.extend(zip(target['projection_targets'], target['projection_ports']))
        except Exception, e:
            message = "Unable to retrieve targets: %s" % str(e)
            self.addResult(Critical, message)
            return
        for (docbrokerhost, docbrokerport) in targets:
            docbroker = DocbrokerClient(host=docbrokerhost, port=docbrokerport)
            try:
                docbasemap = docbroker.getDocbaseMap()
            except Exception, e:
                message = "Unable to retrieve docbasemap from docbroker %s:%d: %s" % (
                    docbrokerhost, docbrokerport, str(e))
                self.addResult(Critical, message)
                continue
            if not docbaseame in docbasemap['r_docbase_name']:
                message = "docbase %s is not registered on %s:%d" % (docbaseame, docbrokerhost, docbrokerport)
                self.addResult(Critical, message)
                continue
            try:
                servermap = docbroker.getServerMap(docbaseame)
            except Exception, e:
                message = "Unable to retrieve servermap from docbroker %s:%d: %s" % (
                    docbrokerhost, docbrokerport, str(e))
                self.addResult(Critical, message)
                continue
            if servername is not None and not servername in servermap['r_server_name']:
                message = "server %s.%s is not registered on %s:%d" % (
                    docbaseame, servername, docbrokerhost, docbrokerport)
                self.addResult(Critical, message)
                continue
            tmpmap = zip(servermap['r_server_name'], servermap['r_last_status'],
                         servermap['i_docbase_id'],
                         servermap['i_server_connection_address'])
            for (srv, status, docbaseid, connaddr) in tmpmap:
                if servername is not None and not srv == servername:
                    continue
                if status != "Open":
                    message = "%s.%s has status %s on %s:%d, " % (
                        docbaseame, servername, status, docbrokerhost, docbrokerport)
                    self.addResult(Critical, message)
                    continue
                chunks = connaddr.split(" ")
                host = chunks[5]
                port = int(chunks[2], 16)
                session = None
                try:
                    session = DocbaseClient(host=host, port=port, docbaseid=docbaseid)
                    message = "%s.%s has status %s on %s:%d" % (
                        docbaseame, servername, status, docbrokerhost, docbrokerport)
                    self.addResult(Ok, message)
                except Exception, e:
                    message = "%s.%s has status %s on %s:%d, but error occurred during connection to %s" % (
                        docbaseame, servername, status, docbrokerhost, docbrokerport, str(e))
                    self.addResult(Critical, message)
                    continue
                if session is not None:
                    try:
                        session.disconnect()
                    except Exception, e:
                        pass

    def checkIndexAgents(self):
        count = 0
        for index in getIndexes(self.session):
            count += 1
            result = self.session.FTINDEX_AGENT_ADMIN(
                index['index_name'], index['object_name']
            )
            status = result['status'][0]
            if status == 0:
                message = "Indexagent %s/%s is up and running" % (index['index_name'], index['object_name'])
                self.addResult(Ok, message)
            elif status == 100:
                message = "Indexagent %s/%s is stopped" % (index['index_name'], index['object_name'])
                self.addResult(Warn, message)
            elif status == 200:
                message = "A problem with indexagent %s/%s" % (index['index_name'], index['object_name'])
                self.addResult(Critical, message)
            else:
                message = "Indexagent %s/%s has unknown status" % (index['index_name'], index['object_name'])
                self.addResult(Unknown, message)
        if count == 0:
            self.addResult(Warn, "No indexagents configured")

    def checkJobs(self):
        jobstocheck = None
        if not isEmpty(self.jobs):
            if isinstance(self.jobs, list):
                jobstocheck = list(self.jobs)
            elif isinstance(self.jobs, str):
                jobstocheck = re.split(",\s*", self.jobs)
            else:
                raise RuntimeError("Wrong jobs argument")
        now = self.session.TIME()
        for job in getJobs(self.session, jobstocheck):
            name = job['object_name']
            if jobstocheck is not None and name in jobstocheck:
                jobstocheck.remove(name)
            start = job['start_date']
            nextinvocation = job['a_next_invocation']
            expire = job['expiration_date']
            maxiterations = job['max_iterations']
            mode = job['run_mode']
            interval = job['run_interval']
            inactive = job['is_inactive']
            iterations = job['a_iterations']
            lastinvocation = job['a_last_invocation']
            lastcompletion = job['a_last_completion']
            lastreturncode = job['a_last_return_code']
            currentstatus = job['a_current_status']
            specialapp = job['a_special_app']
            if start is None or start <= 0:
                message = "%s has undefined start_date" % name
                self.addResult(Critical, message)
                continue
            if nextinvocation is None or nextinvocation <= 0:
                message = "%s has undefined next_invocation_date" % name
                self.addResult(Critical, message)
                continue
            if expire is not None and expire < start:
                message = "%s has expiration_date less then start_date" % name
                self.addResult(Critical, message)
                continue
            if maxiterations < 0:
                message = "%s has invalid max_iterations value: %d" % (name, maxiterations)
                self.addResult(Critical, message)
                continue
            if mode == 0 and interval == 0 and maxiterations != 1:
                message = "%s has invalid max_iterations value for run_mode=0 and run_interval=0" % name
                self.addResult(Critical, message)
                continue
            if mode in [1, 2, 3, 4] and (interval < 1 or interval > 32767):
                message = "%s has invalid run_interval value, expected [1, 32767], got %d" % (
                    name, interval)
                self.addResult(Critical, message)
                continue
            if mode == 7 and (interval < -7 or interval > 7 or interval == 0):
                message = "%s has invalid run_interval value, expected [-7,7], got %d" % (
                    name, interval)
                self.addResult(Critical, message)
                continue
            if mode == 8 and (interval < -28 or interval > 28 or interval == 0):
                message = "%s has invalid run_interval value, expected [-28,0) U (0,28], got %d" % (
                    name, interval)
                self.addResult(Critical, message)
                continue
            if mode == 9 and (interval < -365 or interval > 365 or interval == 0):
                message = "%s has invalid run_interval value, expected [-365,0) U (0,365], got %d" % (
                    name, interval)
                self.addResult(Critical, message)
                continue
            if inactive:
                message = "%s is inactive" % name
                self.addResult(Critical, message)
                continue
            if expire is not None and now > expire:
                message = "%s is expired" % name
                self.addResult(Critical, message)
                continue
            if 0 < maxiterations < iterations:
                message = "%s max iterations exceeded" % name
                self.addResult(Critical, message)
                continue
            if lastinvocation is None:
                message = "%s has been never executed" % name
                self.addResult(Warn, message)
                continue
            if lastreturncode != 0:
                message = "%s has status: %s" % (name, currentstatus)
                self.addResult(Critical, message)
                continue
            if re.search('agentexec', specialapp) is not None or (
                        lastinvocation is not None and lastcompletion is None):
                message = "%s is running for %s" % (name, prettyInterval(now - lastinvocation))
                self.addResult(Ok, message)
                continue

            timegap = now - lastcompletion

            if mode in [1, 2, 3, 4]:
                message = "%s last run - %s ago" % (name, prettyInterval(timegap))
                if timegap > 2 * JOB_INTERVALS[mode] * interval:
                    self.addResult(Critical, message)
                    continue
                elif timegap > JOB_INTERVALS[mode] * interval:
                    self.addResult(Warn, message)
                    continue
                else:
                    self.addResult(Ok, message)
                    continue
            else:
                message = "Scheduling type for job %s is not currently supported" % name
                self.addResult(Critical, message)
                continue
        if not isEmpty(jobstocheck):
            message = ""
            for job in jobstocheck:
                message += "%s not found, " % job
            self.addResult(Critical, message)


    def checkTimeSkew(self):
        ''

    def checkQuery(self):
        ''

    def checkCountQuery(self):
        ''

    def checkWorkQueue(self):
        query = "SELECT count(r_object_id) AS work_queue_size FROM dmi_workitem " \
                "WHERE r_runtime_state IN (0, 1) " \
                "AND r_auto_method_id > '0000000000000000' " \
                "AND a_wq_name is NULLSTRING"
        collection = None
        try:
            collection = self.session.query(query)
            result = collection.nextRecord()
            return nagiosplugin.Metric('workqueue', result['work_queue_size'], min=0, context='workqueue')
        except Exception, e:
            message = "Unable to execute query: %s" % str(e)
            self.addResult(Critical, message)
        finally:
            try:
                if collection is not None:
                    collection.close()
            except Exception, e:
                pass

    def checkServerWorkQueue(self):
        serverid = self.session.serverconfig['r_object_id']
        servername = self.session.serverconfig['object_name']
        query = "SELECT count(r_object_id) AS work_queue_size FROM dmi_workitem " \
                "WHERE r_runtime_state IN (0, 1) " \
                "AND r_auto_method_id > '0000000000000000' " \
                "AND a_wq_name ='" + serverid + "'"
        collection = None
        try:
            collection = self.session.query(query)
            result = collection.nextRecord()
            return nagiosplugin.Metric(servername, result['work_queue_size'], min=0, context='serverworkqueue')
        except Exception, e:
            message = "Unable to execute query: %s" % str(e)
            self.addResult(Critical, message)
        finally:
            try:
                if collection is not None:
                    collection.close()
            except Exception, e:
                pass

    def checkFulltextQueue(self):
        users = []
        for u in self.session.query("select distinct queue_user from dm_ftindex_agent_config"):
            users.append(u['queue_user'])
        if isEmpty(users):
            self.addResult(Warn, "No fulltext")
            return
        for username in users:
            query = "SELECT count(r_object_id) AS queue_size FROM dmi_queue_item WHERE name='" \
                    + username + "'AND task_state not in ('failed','warning')"
            collection = None
            try:
                collection = self.session.query(query)
                result = collection.nextRecord()
                yield nagiosplugin.Metric(username, result['queue_size'], min=0, context='indexqueue')
            except Exception, e:
                message = "Unable to execute query: %s" % str(e)
                self.addResult(Critical, message)
                continue
            finally:
                try:
                    if collection is not None:
                        collection.close()
                except Exception, e:
                    pass

    def checkFailedTasks(self):
        ''

    def checkLogin(self):
        try:
            session = DocbaseClient(host=self.host, port=self.port, docbaseid=self.docbaseid)
        except Exception, e:
            message = "Unable to connect to docbase: %s" % str(e)
            self.addResult(Critical, message)
            return
        if self.username and self.password:
            try:
                session.authenticate(self.username, self.secret)
            except Exception, e:
                message = "Unable to authenticate: %s" % str(e)
                self.addResult(Critical, message)
                return
            self.session = session
        else:
            if not self.password:
                if self.mode != 'login':
                    self.addResult(Warn, "No password provided")
                else:
                    self.addResult(Critical, "No password provided")
            else:
                if self.mode != 'login':
                    self.addResult(Warn, "No username provided")
                else:
                    self.addResult(Critical, "No username provided")

    def addResult(self, state, message):
        self.results.add(nagiosplugin.Result(state, message))

    def __getattr__(self, name):
        if hasattr(self.args, name):
            return getattr(self.args, name)
        else:
            return AttributeError


class CheckSummary(nagiosplugin.Summary):
    def verbose(self, results):
        return ''

    def ok(self, results):
        return self.format(results)

    def problem(self, results):
        return self.format(results)

    def format(self, results):
        message = ""
        for state in [Ok, Unknown, Warn, Critical]:
            hint = ", ".join(str(result) for result in results if result.state == state and not isEmpty(result.hint))
            message = ", ".join(x for x in [hint, message] if not isEmpty(x))
        return message


def isEmpty(value):
    if value is None:
        return True
    if isinstance(value, str):
        if len(value) == 0:
            return True
        elif value.isspace():
            return True
        else:
            return False
    if isinstance(value, list):
        if len(value) == 0:
            return True
        else:
            return False
    if isinstance(value, dict):
        if len(value) == 0:
            return True
        else:
            return False
    return False


def getIndexes(session):
    query = "select index_name, a.object_name " \
            "from dm_fulltext_index i, dm_ftindex_agent_config a " \
            "where i.index_name=a.index_name " \
            "and a.force_inactive = false"
    return runQuery(session, query)


def runQuery(session, query):
    return ((lambda x: dict((attr, x[attr]) for attr in x))(e) for e in session.query(query))


def getJobs(session, jobs=None, condition=""):
    query = JOB_QUERY + condition
    if jobs is not None:
        query += " AND object_name IN ('" + "','".join(jobs) + "')"
    return runQuery(session, query)


def getRunningJobs(session):
    return getJobs(session, JOB_ACTIVE_CONDITION)


def prettyInterval(delta):
    if delta >= 0:
        secs = (delta) % 60
        mins = (int((delta) / 60)) % 60
        hours = (int((delta) / 3600))
        if hours < 24:
            return "%02d:%02d:%02d" % (hours, mins, secs)
        else:
            days = int(hours / 24)
            hours -= days * 24
            return "%d days %02d:%02d:%02d" % (days, hours, mins, secs)
    return "future"


modes = {
    'sessioncount': [CheckDocbase.checkSessions, True, "checks active session count"],
    'targets': [CheckDocbase.checkTargets, False, "checks whether server is registered on projection targets"],
    'indexagents': [CheckDocbase.checkIndexAgents, False, "checks index agent status"],
    'checkjobs': [CheckDocbase.checkJobs, False, "checks jobs scheduling"],
    'timeskew': [CheckDocbase.checkTimeSkew, True, "checks time skew between nagios host and documentum"],
    'query': [CheckDocbase.checkQuery, True, "checks results returned by query"],
    'countquery': [CheckDocbase.checkCountQuery, True, "checks results returned by query"],
    'workqueue': [CheckDocbase.checkWorkQueue, True, "checks workqueue size"],
    'serverworkqueue': [CheckDocbase.checkServerWorkQueue, True, "checks server workqueue size"],
    'indexqueue': [CheckDocbase.checkFulltextQueue, True, "checks index agent queue size"],
    'failedtasks': [CheckDocbase.checkFailedTasks, True, "checks failed tasks"],
    'login': [CheckDocbase.checkLogin, False, "checks login"],
}


@nagiosplugin.guarded
def main():
    argp = argparse.ArgumentParser(description=__doc__)
    argp.add_argument('-H', '--host', required=True, metavar='hostname', help='server hostname')
    argp.add_argument('-p', '--port', required=True, metavar='port', type=int, help='server port')
    argp.add_argument('-i', '--docbaseid', required=True, metavar='docbaseid', type=int, help='docbase identifier')
    argp.add_argument('-u', '--username', metavar='username', help='username')
    argp.add_argument('-s', '--secret', metavar='password', help='password')
    argp.add_argument('-t', '--timeout', metavar='timeout', default=60, type=int, help='check timeout')
    argp.add_argument('-m', '--mode', required=True, metavar='mode',
                      help="check to use, any of: " + "; ".join(x + " - " + modes[x][2] for x in modes.keys()))
    argp.add_argument('-j', '--jobs', metavar='jobs', default='', help='jobs to check')
    for mode in modes.keys():
        if not modes[mode][1]:
            continue
        argp.add_argument("--" + mode + "-warning", metavar='RANGE', default='',
                          help='<warning range for ' + mode + ' check>')
        argp.add_argument("--" + mode + "-critical", metavar='RANGE', default='',
                          help='<critical range for ' + mode + ' check>')
    args = argp.parse_args()
    check = nagiosplugin.Check(CheckSummary())
    check.name = args.mode
    check.add(CheckDocbase(args, check.results))
    for mode in modes.keys():
        if not modes[mode][1]:
            continue
        check.add(
            nagiosplugin.ScalarContext(mode, getattr(args, mode + "_warning"), getattr(args, mode + "_critical")))
    check.main(timeout=args.timeout)


if __name__ == '__main__':
    main()