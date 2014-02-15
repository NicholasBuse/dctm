#!python
import argparse
import nagiosplugin
from nagiosplugin.state import Critical, Warn, Ok, Unknown
from docbaseclient import DocbaseClient
from docbrokerclient import DocbrokerClient


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
            result = modes[self.mode][0](self)
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
        return nagiosplugin.Metric('sessioncount', count['hot_list_size'])

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
        ''

    def checkTimeSkew(self):
        ''

    def checkQuery(self):
        ''

    def checkCountQuery(self):
        ''

    def checkWorkQueue(self):
        ''

    def checkServerWorkQueue(self):
        ''

    def checkFulltextQueue(self):
        ''

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


def getIndexes(session):
    query = "select index_name, a.object_name " \
            "from dm_fulltext_index i, dm_ftindex_agent_config a " \
            "where i.index_name=a.index_name " \
            "and a.force_inactive = false"
    return runQuery(session, query)


def runQuery(session, query):
    return ((lambda x: dict((attr, x[attr]) for attr in x))(e) for e in session.query(query))


modes = {
    'sessioncount': [CheckDocbase.checkSessions, True, "checks active session count"],
    'targets': [CheckDocbase.checkTargets, False, "checks whether server is registered on projection targets"],
    'indexagents': [CheckDocbase.checkIndexAgents, False, "checks index agent status"],
    'jobs': [CheckDocbase.checkJobs, False, "checks jobs scheduling"],
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
    for mode in modes.keys():
        if not modes[mode][1]:
            continue
        argp.add_argument("--" + mode + "-warning", metavar='RANGE', default='',
                          help='<warning range for ' + mode + ' check>')
        argp.add_argument("--" + mode + "-critical", metavar='RANGE', default='',
                          help='<critical range for ' + mode + ' check>')
    args = argp.parse_args()
    check = nagiosplugin.Check()
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