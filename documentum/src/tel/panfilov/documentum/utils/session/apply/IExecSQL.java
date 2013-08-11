package tel.panfilov.documentum.utils.session.apply;

/**
 * @author Andrey B. Panfilov <andrew@panfilov.tel>
 */
public interface IExecSQL extends IApplyCommand<Boolean> {

    IExecSQL setSQL(String sql);

}
