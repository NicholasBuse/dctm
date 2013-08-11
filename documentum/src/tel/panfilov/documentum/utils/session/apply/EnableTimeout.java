package tel.panfilov.documentum.utils.session.apply;

import com.documentum.fc.client.IDfSession;
import com.documentum.fc.client.IDfTypedObject;
import com.documentum.fc.common.DfException;
import tel.panfilov.documentum.utils.CoreUtils;

/**
 * @author  Andrey B. Panfilov <andrew@panfilov.tel>
 */
class EnableTimeout extends AbstractApplyCommand<Boolean> implements
        IEnableTimeout {

    public EnableTimeout(IDfSession session) {
        super(session);
    }

    @Override
    protected String getCommand() {
        return "ENABLE_TIMEOUT";
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
