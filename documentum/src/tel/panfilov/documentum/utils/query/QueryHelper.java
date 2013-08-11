package tel.panfilov.documentum.utils.query;

import com.documentum.fc.client.IDfCollection;
import com.documentum.fc.common.DfException;
import com.documentum.fc.common.DfLogger;

/**
 * @author Andrey B. Panfilov <andrew@panfilov.tel>
 */
public final class QueryHelper {

    private QueryHelper() {
        super();
    }

    public static void close(IDfCollection coll) {
        try {
            if (coll != null
                    && coll.getState() != IDfCollection.DF_CLOSED_STATE) {
                coll.close();
            }
        } catch (DfException ex) {
            DfLogger.error(QueryHelper.class, "Exception in close()", null, ex);
        }
    }

}
