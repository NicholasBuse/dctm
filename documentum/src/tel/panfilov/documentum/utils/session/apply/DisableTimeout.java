package tel.panfilov.documentum.utils.session.apply;

import com.documentum.fc.client.IDfSession;
import com.documentum.fc.client.IDfTypedObject;
import com.documentum.fc.common.DfException;

import tel.panfilov.documentum.utils.CoreUtils;

class DisableTimeout extends AbstractApplyCommand<Boolean> implements
        IDisableTimeout {

    public DisableTimeout(IDfSession session) {
        super(session);
    }

    @Override
    protected String getCommand() {
        return "DISABLE_TIMEOUT";
    }

    @Override
    public Boolean execute() throws DfException {
        IDfTypedObject object = applyForOjbect();
        if (object != null) {
            return CoreUtils.asBoolean(object.getString("result"));
        }
        return false;
    }

}
