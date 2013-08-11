package tel.panfilov.documentum.utils.session.apply;

import com.documentum.fc.common.DfException;

/**
 * @author Andrey B. Panfilov <andrew@panfilov.tel>
 */
public interface IApplyCommand<T> {

    int DISABLE_TIMEOUT = 1;

    int ENABLE_TIMEOUT = 2;

    int EXEC_SQL = 3;

    int INBOX_ITEM_APPEND = 4;

    T execute() throws DfException;

}
