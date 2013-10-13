import java.lang.reflect.Constructor;
import java.util.concurrent.ConcurrentLinkedQueue;
import java.util.concurrent.atomic.AtomicLong;

import com.documentum.com.DfClientX;
import com.documentum.fc.client.IDfClient;
import com.documentum.fc.client.IDfSession;
import com.documentum.fc.client.IDfSessionManager;
import com.documentum.fc.common.DfException;
import com.documentum.fc.common.DfLoginInfo;

/**
 * @author Andrey B. Panfilov <andrew@panfilov.tel>
 */
public class SessionBenchmark implements Runnable {

    public static final int SLEEP_TIME = 5000;

    public static volatile AtomicLong counter = new AtomicLong(0);

    private final ISessionBenchmarkFactory _factory;

    private static final ConcurrentLinkedQueue<String> _tickets = new ConcurrentLinkedQueue<String>();

    public static final IDfClient _dfClient;

    static {
        try {
            _dfClient = new DfClientX().getLocalClient();
        } catch (DfException ex) {
            throw new RuntimeException(ex);
        }
    }

    public SessionBenchmark(ISessionBenchmarkFactory factory) {
        _factory = factory;
    }

    public static void main(String[] argv) throws Exception {
        String docbase = argv[0];
        String userName = argv[1];
        String password = argv[2];
        String factoryName = argv[3];

        Class<? extends ISessionBenchmarkFactory> factoryClass = Class.forName(
                factoryName).asSubclass(ISessionBenchmarkFactory.class);
        Constructor<? extends ISessionBenchmarkFactory> factoryConstructor = factoryClass
                .getConstructor(String.class, String.class, String.class);

        if (DynamicSessionManager3.class.isAssignableFrom(factoryClass)) {
            IDfSession session = _dfClient.newSession(docbase, new DfLoginInfo(
                    userName, password));

            for (int i = 1; i <= 50000; i++) {
                _tickets.add(session.getLoginTicketEx(null, "docbase",
                        3600 * 24, false, docbase));
                if (i % 1000 == 0) {
                    System.out.println("Generated " + i + " tickets");
                }
            }
        }

        for (int i = 0; i < 50; i++) {
            new Thread(new SessionBenchmark(factoryConstructor.newInstance(
                    docbase, userName, password))).start();
        }

        long prevValue = counter.get();
        for (int iteration = 1; iteration < 51; iteration++) {
            Thread.sleep(SLEEP_TIME);
            long curValue = counter.get();
            System.out.println("Sessions per second: "
                    + ((curValue - prevValue) * 1000 / SLEEP_TIME)
                    + ", queue size: " + _tickets.size() + ", iteration: "
                    + iteration);
            prevValue = curValue;
        }
        System.exit(0);
    }

    @Override
    public void run() {
        while (true) {
            IDfSession session = null;
            try {
                session = _factory.createSession();
                counter.incrementAndGet();
            } catch (Exception ex) {
                throw new RuntimeException(ex);
            } finally {
                if (session != null) {
                    try {
                        _factory.releaseSession(session);
                    } catch (DfException ex) {
                        throw new RuntimeException(ex);
                    }
                }
            }
        }
    }

    public interface ISessionBenchmarkFactory {

        IDfSession createSession() throws DfException;

        void releaseSession(IDfSession session) throws DfException;

    }

    public static class NoSessionManager implements ISessionBenchmarkFactory {
        private final String _docbase;

        private final String _userName;

        private final String _password;

        public NoSessionManager(String docbase, String username, String password)
            throws DfException {
            _docbase = docbase;
            _userName = username;
            _password = password;
        }

        @Override
        public IDfSession createSession() throws DfException {
            return _dfClient.newSession(_docbase, new DfLoginInfo(_userName,
                    _password));
        }

        @Override
        public void releaseSession(IDfSession session) throws DfException {
            session.disconnect();
        }
    }

    public static class StaticSessionManager implements
            ISessionBenchmarkFactory {

        private final String _docbase;

        private final String _userName;

        private final String _password;

        private final IDfSessionManager _sessionManager;

        public StaticSessionManager(String docbase, String username,
                String password) throws DfException {
            _docbase = docbase;
            _userName = username;
            _password = password;
            _sessionManager = new DfClientX().getLocalClient()
                    .newSessionManager();
            _sessionManager.setIdentity(_docbase, new DfLoginInfo(_userName,
                    _password));
        }

        @Override
        public IDfSession createSession() throws DfException {
            return _sessionManager.getSession(_docbase);
        }

        @Override
        public void releaseSession(IDfSession session) throws DfException {
            _sessionManager.release(session);
        }

    }

    public static class DynamicSessionManager1 implements
            ISessionBenchmarkFactory {

        protected final String _docbase;

        protected final String _userName;

        protected String _password;

        public DynamicSessionManager1(String docbase, String username,
                String password) throws DfException {
            _docbase = docbase;
            _userName = username;
            _password = password;
        }

        @Override
        public IDfSession createSession() throws DfException {
            IDfSessionManager sessionManager = _dfClient.newSessionManager();
            sessionManager.setIdentity(_docbase, new DfLoginInfo(_userName,
                    _password));
            return sessionManager.getSession(_docbase);
        }

        @Override
        public void releaseSession(IDfSession session) throws DfException {
            IDfSessionManager sessionManager = session.getSessionManager();
            sessionManager.release(session);
        }
    }

    public static class DynamicSessionManager2 extends DynamicSessionManager1 {

        public DynamicSessionManager2(String docbase, String username,
                String password) throws DfException {
            super(docbase, username, password);
        }

        @Override
        public void releaseSession(IDfSession session) throws DfException {
            IDfSessionManager sessionManager = session.getSessionManager();
            sessionManager.release(session);
            sessionManager.clearIdentity(_docbase);
        }
    }

    public static class DynamicSessionManager3 extends DynamicSessionManager1 {

        public DynamicSessionManager3(String docbase, String username,
                String password) throws DfException {
            super(docbase, username, password);
        }

        @Override
        public IDfSession createSession() throws DfException {
            IDfSessionManager sessionManager = _dfClient.newSessionManager();
            sessionManager.setIdentity(_docbase, new DfLoginInfo(_userName,
                    _password));
            IDfSession session = sessionManager.newSession(_docbase);
            _password = _tickets.poll();
            return session;
        }

        @Override
        public void releaseSession(IDfSession session) throws DfException {
            IDfSessionManager sessionManager = session.getSessionManager();
            sessionManager.release(session);
            sessionManager.clearIdentity(_docbase);
        }
    }

}
