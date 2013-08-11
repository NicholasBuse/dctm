package tel.panfilov.documentum.utils.session.apply;

import com.documentum.fc.client.IDfCollection;
import com.documentum.fc.client.IDfSession;
import com.documentum.fc.client.IDfTypedObject;
import com.documentum.fc.common.DfException;
import com.documentum.fc.common.DfId;
import com.documentum.fc.common.DfList;
import com.documentum.fc.common.DfProperties;
import com.documentum.fc.common.DfUtil;
import com.documentum.fc.common.IDfId;
import com.documentum.fc.common.IDfList;
import com.documentum.fc.common.IDfProperties;
import com.documentum.fc.common.IDfTime;
import com.documentum.fc.common.IDfValue;

import tel.panfilov.documentum.utils.query.QueryHelper;

/**
 * @author Andrey B. Panfilov <andrew@panfilov.tel>
 */
abstract class AbstractApplyCommand<T> {

    private final IDfProperties _properties;

    private final IDfSession _session;

    private String _objectId = DfId.DF_NULLID_STR;

    protected AbstractApplyCommand(IDfSession session) {
        _session = session;
        _properties = new DfProperties();
    }

    protected abstract String getCommand();

    protected final IDfTypedObject applyForOjbect() throws DfException {
        IDfCollection collection = null;
        try {
            collection = applyForCollection();
            if (collection != null && collection.next()) {
                return collection.getTypedObject();
            }
            return null;
        } finally {
            QueryHelper.close(collection);
        }
    }

    protected final IDfCollection applyForCollection() throws DfException {
        IDfList types = null;
        IDfList values = null;
        IDfList args = null;
        if (_properties != null) {
            args = _properties.getProperties();

            if (args.getCount() > 0) {
                types = new DfList();
                values = new DfList();
            }

            for (int i = 0; i < args.getCount(); i++) {
                String arg = args.getString(i);
                int dataType = _properties.getPropertyType(arg);
                switch (dataType) {
                case IDfProperties.DF_STRING:
                    values.appendString(_properties.getString(arg));
                    types.appendString("S");
                    break;

                case IDfProperties.DF_BOOLEAN:
                    values.appendString(DfUtil.toString(_properties
                            .getBoolean(arg)));
                    types.append("B");
                    break;

                case IDfProperties.DF_DOUBLE:
                    values.appendString(DfUtil.toString(_properties
                            .getDouble(arg)));
                    types.appendString("D");
                    break;

                case IDfProperties.DF_ID:
                    values.appendString(DfUtil.toString(_properties.getId(arg)));
                    types.appendString("S");
                    break;

                case IDfProperties.DF_INTEGER:
                    values.appendString(DfUtil.toString(_properties.getInt(arg)));
                    types.appendString("I");
                    break;

                case IDfProperties.DF_TIME:
                    values.appendString(DfUtil.toString(_properties
                            .getTime(arg)));
                    types.appendString("T");
                    break;

                default:
                    break;
                }
            }
        }

        return _session.apply(_objectId, getCommand(), args, types, values);
    }

    protected final void setObjectId(IDfId objId) {
        if (objId != null) {
            _objectId = objId.getId();
        }
    }

    public String getString(String propertyName) throws DfException {
        return _properties.getString(propertyName);
    }

    public boolean getBoolean(String propertyName) throws DfException {
        return _properties.getBoolean(propertyName);
    }

    public double getDouble(String propertyName) throws DfException {
        return _properties.getDouble(propertyName);
    }

    public IDfId getId(String propertyName) throws DfException {
        return _properties.getId(propertyName);
    }

    public int getInt(String propertyName) throws DfException {
        return _properties.getInt(propertyName);
    }

    public IDfList getList(String propertyName) throws DfException {
        return _properties.getList(propertyName);
    }

    public IDfTime getTime(String propertyName) throws DfException {
        return _properties.getTime(propertyName);
    }

    public IDfValue getValue(String propertyName) throws DfException {
        return _properties.getValue(propertyName);
    }

    public void setString(String propertyName, String propertyValue) {
        _properties.putString(propertyName, propertyValue);
    }

    public void setBoolean(String propertyName, boolean propertyValue) {
        _properties.putBoolean(propertyName, propertyValue);
    }

    public void setDouble(String propertyName, double propertyValue) {
        _properties.putDouble(propertyName, propertyValue);
    }

    public void setId(String propertyName, IDfId propertyValue) {
        _properties.putId(propertyName, propertyValue);
    }

    public void setInt(String propertyName, int propertyValue) {
        _properties.putInt(propertyName, propertyValue);
    }

    public void setList(String propertyName, IDfList propertyValue) {
        _properties.putList(propertyName, propertyValue);
    }

    public void setTime(String propertyName, IDfTime propertyValue) {
        _properties.putTime(propertyName, propertyValue);
    }

    public void setValue(String propertyName, IDfValue propertyValue) {
        _properties.putValue(propertyName, propertyValue);
    }

}
