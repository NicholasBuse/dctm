package tel.panfilov.documentum.api.methods.job;

/**
 * @author Andrey B. Panfilov <andrew@panfilov.tel>
 */
public interface IJobTracer {

    void logMsg(String msg);

    void logWarn(String warnMsg);

    void logError(String msg);

    void writeBoldLine();

    void writeLine();

    void logError(Throwable throwable);

    void logInfo(String infoMsg);

    void logDebug(String debugMsg);

    boolean isDebug();

    boolean isInfo();

    boolean isWarn();

}
