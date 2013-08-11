package tel.panfilov.documentum.utils.session.apply;

import com.documentum.fc.common.DfException;

/**
 * @author Andrey B. Panfilov <andrew@panfilov.tel>
 */
public interface IEnableTimeout extends IApplyCommand<Boolean> {

    Boolean execute() throws DfException;

}
