package tel.panfilov.documentum.utils.session.apply;

import com.documentum.fc.client.IDfSession;
import com.documentum.fc.client.IDfTypedObject;
import com.documentum.fc.common.DfException;
import tel.panfilov.documentum.utils.CoreUtils;

/**
 * @author Andrey B. Panfilov <andrew@panfilov.tel>
 */
class ExecSQL extends AbstractApplyCommand<Boolean> implements IExecSQL {

    public ExecSQL(IDfSession session) {
        super(session);
    }

    @Override
    protected String getCommand() {
        return "EXEC_SQL";
    }

    @Override
    public IExecSQL setSQL(String sql) {
        setString("QUERY", sql);
        return this;
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
