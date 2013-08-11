package tel.panfilov.documentum.utils.session.apply;

import com.documentum.fc.client.IDfSession;
import com.documentum.fc.client.IDfTypedObject;
import com.documentum.fc.common.DfException;
import com.documentum.fc.common.DfId;
import com.documentum.fc.common.IDfId;
import com.documentum.fc.common.IDfTime;

class InboxItemAppend extends AbstractApplyCommandWithObject<IDfId> implements
        IInboxItemAppend {

    public InboxItemAppend(IDfSession session, IDfId objectId) {
        super(session, objectId);
    }

    @Override
    protected String getCommand() {
        return "InboxItemAppend";
    }

    @Override
    public IInboxItemAppend setPriority(int priority) {
        setInt("priority", priority);
        return this;
    }

    @Override
    public IInboxItemAppend setUserName(String userName) {
        setString("list_id", userName);
        return this;
    }

    @Override
    public IInboxItemAppend setEvent(String event) {
        setString("event", event);
        return this;
    }

    @Override
    public IInboxItemAppend setSendMail(boolean sendMail) {
        setBoolean("sendmail", sendMail);
        return this;
    }

    @Override
    public IInboxItemAppend setAliasSet(String aliasSet) {
        setString("sessionaliasset", aliasSet);
        return this;
    }

    @Override
    public IInboxItemAppend setMessage(String message) {
        setString("message", message);
        return this;
    }

    @Override
    public IInboxItemAppend setDueDate(IDfTime dueDate) {
        setTime("due_date", dueDate);
        return this;
    }

    @Override
    public IDfId execute() throws DfException {
        IDfTypedObject object = applyForOjbect();
        if (object != null) {
            object.getId("result");
        }
        return DfId.DF_NULLID;
    }

}
