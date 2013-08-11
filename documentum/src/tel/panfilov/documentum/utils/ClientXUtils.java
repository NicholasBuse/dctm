package tel.panfilov.documentum.utils;

import com.documentum.com.DfClientX;
import com.documentum.com.IDfClientX;
import com.documentum.fc.client.IDfClient;
import com.documentum.fc.client.IDfQuery;
import com.documentum.fc.client.IDfSession;
import com.documentum.fc.client.IDfSessionManager;
import com.documentum.fc.common.DfException;
import com.documentum.fc.common.IDfId;
import com.documentum.fc.common.IDfList;
import com.documentum.fc.common.IDfLoginInfo;

/**
 * @author Andrey B. Panfilov <andrew@panfilov.tel>
 */
public final class ClientXUtils {

    private ClientXUtils() {
        super();
    }

    public static IDfId getId(String objectId) {
        return new DfClientX().getId(objectId);
    }

    public static IDfClientX getClientX() throws DfException {
        return new DfClientX();
    }

    public static IDfClient getClient() throws DfException {
        return getClientX().getLocalClient();
    }

    public static IDfSessionManager getSessionManager() throws DfException {
        return getClient().newSessionManager();
    }

    public static IDfLoginInfo getLoginInfo() throws DfException {
        return new DfClientX().getLoginInfo();
    }

    public static IDfSessionManager newSessionManager(IDfSession session)
        throws DfException {
        IDfLoginInfo loginInfo = session.getLoginInfo();
        int timeout = session.getServerConfig().getInt(
                "max_login_ticket_timeout");
        loginInfo.setPassword(session.getLoginTicketEx(loginInfo.getUser(),
                "docbase", timeout, false, session.getDocbaseName()));
        IDfSessionManager sessionManager = getSessionManager();
        sessionManager.setIdentity(session.getDocbaseName(), loginInfo);
        return sessionManager;
    }

    public static IDfSessionManager getSessionManager(String docbase,
            String userName, String password) throws DfException {
        return getSessionManager(docbase, userName, password, null);
    }

    public static IDfSessionManager getSessionManager(String docbase,
            String userName, String password, String domain) throws DfException {
        IDfSessionManager sessionManager = getSessionManager();
        sessionManager.setIdentity(docbase,
                getLoginInfo(userName, password, domain));
        return sessionManager;
    }

    public static IDfLoginInfo getLoginInfo(String user, String password)
        throws DfException {
        return getLoginInfo(user, password, null);
    }

    public static IDfLoginInfo getLoginInfo(String user, String password,
            String domain) throws DfException {
        IDfLoginInfo loginInfo = getLoginInfo();
        loginInfo.setUser(user);
        loginInfo.setPassword(password);
        loginInfo.setDomain(domain);
        return loginInfo;
    }

    public static IDfQuery getQuery(String dql) throws DfException {
        IDfQuery query = new DfClientX().getQuery();
        query.setDQL(dql);
        return query;
    }

    public static IDfList getList() throws DfException {
        return new DfClientX().getList();
    }

}
