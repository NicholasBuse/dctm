package tel.panfilov.documentum.utils.session.apply;

import com.documentum.fc.client.IDfSession;
import com.documentum.fc.common.DfException;
import com.documentum.fc.common.DfId;
import com.documentum.fc.common.IDfId;
import com.documentum.fc.common.IDfTime;

import tel.panfilov.documentum.utils.ClientXUtils;

/**
 * @author Andrey B. Panfilov <andrew@panfilov.tel>
 */
public final class ApplyCommand {

    private ApplyCommand() {
        super();
    }

    public static IApplyCommand getCommand(int command, IDfSession session)
        throws DfException {
        return getCommand(command, session, DfId.DF_NULLID);
    }

    public static IApplyCommand getCommand(int command, IDfSession session,
            IDfId objectId) throws DfException {
        switch (command) {
        case IApplyCommand.DISABLE_TIMEOUT:
            return new DisableTimeout(session);
        case IApplyCommand.ENABLE_TIMEOUT:
            return new EnableTimeout(session);
        case IApplyCommand.EXEC_SQL:
            return new ExecSQL(session);
        case IApplyCommand.INBOX_ITEM_APPEND:
            return new InboxItemAppend(session, objectId);
        default:
            throw new IllegalArgumentException("Unknown command: " + command);
        }
    }

    public static boolean disableTimeout(IDfSession session) throws DfException {
        return ((IDisableTimeout) getCommand(IApplyCommand.DISABLE_TIMEOUT,
                session)).execute();
    }

    public static boolean enableTimeout(IDfSession session) throws DfException {
        return ((IEnableTimeout) getCommand(IApplyCommand.ENABLE_TIMEOUT,
                session)).execute();
    }

    public static boolean execSQL(IDfSession session, String sql)
        throws DfException {
        return ((IExecSQL) getCommand(IApplyCommand.EXEC_SQL, session)).setSQL(
                sql).execute();
    }

    public static IDfId inboxItemAppend(IDfSession sesssion, String objectId,
            String userName, int priority, String event, boolean sendMail,
            String message, IDfTime dueDate, String sessionAliasSet)
        throws DfException {
        return ((IInboxItemAppend) getCommand(IApplyCommand.INBOX_ITEM_APPEND,
                sesssion, ClientXUtils.getId(objectId))).setUserName(userName)
                .setPriority(priority).setEvent(event).setSendMail(sendMail)
                .setMessage(message).setDueDate(dueDate)
                .setAliasSet(sessionAliasSet).execute();
    }

}
