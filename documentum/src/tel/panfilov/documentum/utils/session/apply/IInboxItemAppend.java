package tel.panfilov.documentum.utils.session.apply;

import com.documentum.fc.common.IDfId;
import com.documentum.fc.common.IDfTime;

/**
 * @author Andrey B. Panfilov <andrew@panfilov.tel>
 */
public interface IInboxItemAppend extends IApplyCommand<IDfId> {

    IInboxItemAppend setUserName(String userName);

    IInboxItemAppend setPriority(int priority);

    IInboxItemAppend setEvent(String event);

    IInboxItemAppend setMessage(String message);

    IInboxItemAppend setDueDate(IDfTime dueDate);

    IInboxItemAppend setAliasSet(String aliasSet);

    IInboxItemAppend setSendMail(boolean sendMail);

}
