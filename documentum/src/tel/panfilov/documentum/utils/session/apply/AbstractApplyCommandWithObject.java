package tel.panfilov.documentum.utils.session.apply;

import com.documentum.fc.client.IDfSession;
import com.documentum.fc.common.IDfId;

abstract class AbstractApplyCommandWithObject<T> extends
        AbstractApplyCommand<T> {

    protected AbstractApplyCommandWithObject(IDfSession session, IDfId objectId) {
        super(session);
        setObjectId(objectId);
    }

}
