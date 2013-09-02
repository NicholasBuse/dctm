package tel.panfilov.documentum.impl.methods.job;

/**
 * @author: Andrey B. Panfilov <andrew@panfilov.tel>
 */

import java.io.PrintWriter;
import java.text.MessageFormat;
import java.util.Map;

import com.documentum.fc.client.IDfModule;
import com.documentum.fc.client.IDfSession;
import com.documentum.fc.client.IDfSessionManager;
import com.documentum.fc.client.IDfSysObject;
import com.documentum.fc.common.DfException;
import com.documentum.fc.common.DfLogger;
import com.documentum.fc.methodserver.DfMethodArgumentManager;
import com.documentum.fc.methodserver.IDfMethod;

import tel.panfilov.documentum.api.methods.job.IJobTracer;
import tel.panfilov.documentum.utils.ClientXUtils;
import tel.panfilov.documentum.utils.CoreUtils;
import tel.panfilov.documentum.utils.session.apply.ApplyCommand;

/**
 * @author Andrey B. Panfilov <andrew@panfilov.tel>
 */
public abstract class AbstractJobMethod implements IDfMethod, IDfModule,
        IJobTracer {

    public static final String JOBARG_METHOD_TRACE_LEVEL = "method_trace_level";
    public static final String JOBARG_REPOSITORY_NAME = "docbase_name";
    public static final String JOBARG_USER_NAME = "user_name";
    public static final String JOBARG_PASSWORD = "password";
    public static final String JOBARG_DOMAIN = "domain";
    public static final String JOBARG_JOB_ID = "job_id";

    public static final String JOBARG_SINGLE_EXECUTION = "single_execution";
    public static final String JOBARG_USE_TRANSACTION = "use_transaction";

    public static final int DEFAULT_VALUE_METHOD_TRACE_LEVEL = 4;

    public static final boolean DEFAULT_VALUE_SINGLE_EXECUTION = false;
    public static final boolean DEFAULT_VALUE_USE_TRANSACTION = false;

    public static final String DEFAULT_VALUE_DOMAIN = null;
    public static final String DEFAULT_VALUE_PASSWORD = "";

    public static final String DMLS_JOB_ARG_VALUE_INVALID = "Job Argument \"{0}\" has invalid Value \"{1}\".";

    public static final int RETURN_SUCCESS = 0;
    public static final int RETURN_FAILURE = -1;

    private DfMethodArgumentManager _methodArgsManager;

    private String _jobId;

    private boolean _singleExecution;

    private boolean _useTransaction;

    private JobTracer _jobTracer;

    protected AbstractJobMethod() {
        super();
        setJobTracer(new JobTracer(this));
    }

    public final int execute(Map jobArguments, PrintWriter printWriter)
        throws Exception {
        int result = RETURN_FAILURE;
        IDfSession session = null;
        try {
            writeHeader();
            session = initJob(jobArguments, printWriter);
            result = doJob(session);
        } catch (Exception ex) {
            logError(ex);
            throw new DfException(ex);
        } catch (Error err) {
            logError(err);
            throw err;
        } finally {
            try {
                writeFooter(result);
                closeTracer(result == RETURN_SUCCESS);
            } finally {
                if (session != null) {
                    IDfSessionManager sessionManager = session
                            .getSessionManager();
                    if (sessionManager == null) {
                        session.disconnect();
                    } else {
                        sessionManager.release(session);
                        sessionManager.clearIdentities();
                    }
                }
                closeTracer(result == RETURN_SUCCESS);
            }
        }
        return result;
    }

    private void writeHeader() {
        writeLine();
        logMsg("Job " + getJobName() + " started");
        writeLine();
    }

    private void writeFooter(int result) {
        writeLine();
        logMsg("Job " + getJobName() + " finished, result: " + result);
        writeLine();
    }

    private void createLockObject(IDfSession session) throws DfException {
        IDfSysObject lockObject = getLockObj(session);
        if (lockObject == null) {
            lockObject = (IDfSysObject) session.newObject("dm_folder");
            lockObject.setObjectName(getJobId());
            lockObject.save();
            lockObject.fetch(null);
            if (lockObject.getObjectName().startsWith("dm_fix_me")) {
                lockObject.destroy();
                throw new DfException("Unable to create lock object");
            }
        }
    }

    private IDfSysObject getLockObj(IDfSession session) throws DfException {
        String lockObjectName = getJobId();
        return (IDfSysObject) session
                .getObjectByQualification("dm_folder where object_name='"
                        + lockObjectName + "'");
    }

    private int doJob(IDfSession session) throws DfException {
        if (isSingleExecution()) {
            createLockObject(session);
        }
        doPrepare(session);
        if (isSingleExecution() || isUseTransaction()) {
            return executeInTransaction(session);
        } else {
            return doExecute(session);
        }
    }

    private IDfSession initJob(Map jobArguments, PrintWriter printWriter)
        throws DfException {

        setMethodArgsManager(new DfMethodArgumentManager(jobArguments));

        String userName = extractUserName();
        String password = extractUserPassword();
        String docbaseName = extractRepositoryName();
        String domain = extractUserDomain();
        setJobId(extractJobId());

        getJobTracer().setTraceLevel(extractMethodTraceLevel());
        getJobTracer().createReportWriter(docbaseName, userName, domain,
                ClientXUtils.getId(getJobId()), printWriter);

        setSingleExecution(extractSingleExecution());
        setUseTransaction(extractUseTransaction());

        try {
            IDfSessionManager sessionManager = ClientXUtils.getSessionManager(
                    docbaseName, userName, password, domain);
            return sessionManager.newSession(docbaseName);
        } catch (DfException df) {
            throw new DfException("Session Creation Failed", df);
        }
    }

    protected abstract String getJobName();

    protected abstract int doExecute(IDfSession session) throws DfException;

    protected abstract void doPrepare(IDfSession session) throws DfException;

    private int executeInTransaction(IDfSession session) throws DfException {
        IDfSessionManager txSessionManager = ClientXUtils
                .newSessionManager(session);
        IDfSession txSession = null;
        try {
            txSessionManager.beginTransaction();
            txSession = txSessionManager.newSession(session.getDocbaseName());
            if (isSingleExecution()) {
                if (!isUseTransaction()) {
                    ApplyCommand.disableTimeout(txSession);
                }
                IDfSysObject lockObj = getLockObj(txSession);
                logDebug("Acquiring lock: " + lockObj.getObjectId().getId());
                lockObj.lock();
                logDebug("Acquired lock: " + lockObj.getObjectId().getId());
            }
            int result;
            if (isUseTransaction()) {
                logDebug("Executing in transaction");
                result = doExecute(txSession);
            } else {
                logDebug("Executing not in transaction");
                result = doExecute(session);
            }
            logDebug("Committing...");
            txSessionManager.commitTransaction();
            return result;
        } finally {
            try {
                if (txSessionManager.isTransactionActive()) {
                    logDebug("Transaction is active, aborting");
                    txSessionManager.abortTransaction();
                }
            } finally {
                if (txSession != null) {
                    try {
                        if (!isUseTransaction()) {
                            ApplyCommand.enableTimeout(txSession);
                        }
                    } finally {
                        txSessionManager.release(txSession);
                    }
                }
                txSessionManager.clearIdentities();
            }
        }
    }

    private int extractMethodTraceLevel() throws DfException {
        if (!getMethodArgsManager().isArgumentProvided(
                JOBARG_METHOD_TRACE_LEVEL)) {
            return DEFAULT_VALUE_METHOD_TRACE_LEVEL;
        }
        int methodTraceLevel = extractArgIntValue(JOBARG_METHOD_TRACE_LEVEL);

        if ((methodTraceLevel < 0) || (methodTraceLevel > 10)) {
            throw new DfException(
                    "\"Method Trace Level\" is out of range. Valid Range is 0 - 10");
        }

        return methodTraceLevel;
    }

    private boolean extractSingleExecution() throws DfException {
        if (!getMethodArgsManager().isArgumentProvided(JOBARG_SINGLE_EXECUTION)) {
            return DEFAULT_VALUE_SINGLE_EXECUTION;
        }
        return extractArgBoolValue(JOBARG_SINGLE_EXECUTION);
    }

    private boolean extractUseTransaction() throws DfException {
        if (!getMethodArgsManager().isArgumentProvided(JOBARG_USE_TRANSACTION)) {
            return DEFAULT_VALUE_USE_TRANSACTION;
        }
        return extractArgBoolValue(JOBARG_USE_TRANSACTION);
    }

    private String extractJobId() throws DfException {
        if (getMethodArgsManager().isArgumentProvided(JOBARG_JOB_ID)) {
            return extractArgStringValue(JOBARG_JOB_ID);
        }
        throw new DfException(
                "Mandatory Job Argument \"Job ID\" <job_id> is missing"
                        + "\nPlease enable \"Pass Standard Arguments\" option in Job Object\n"
                        + "When running from Command Prompt provide \"job_id\".");
    }

    private String extractRepositoryName() throws DfException {
        if (getMethodArgsManager().isArgumentProvided(JOBARG_REPOSITORY_NAME)) {
            String repositoryName = extractArgStringValue(JOBARG_REPOSITORY_NAME);
            int index = repositoryName.indexOf('.');
            if (index > 0) {
                repositoryName = repositoryName.substring(0, index);
            }
            return repositoryName;
        }
        throw new DfException(
                "Mandatory Job Argument \"Repository Name\" <docbase_name> is missing"
                        + "\nPlease enable \"Pass Standard Arguments\" option in Job Object\n"
                        + "When running from Command Prompt provide \"docbase_name\".");
    }

    private String extractUserName() throws DfException {
        if (getMethodArgsManager().isArgumentProvided(JOBARG_USER_NAME)) {
            return extractArgStringValue(JOBARG_USER_NAME);
        }
        throw new DfException(
                "Mandatory Job Argument \"Repository Owner Name\" <user_name> is missing"
                        + "\nPlease enable \"Pass Standard Arguments\" option in Job Object\n"
                        + "When running from Command Prompt provide \"user_name\".");
    }

    private String extractUserPassword() throws DfException {
        if (getMethodArgsManager().isArgumentProvided(JOBARG_PASSWORD)) {
            return extractArgStringValue(JOBARG_PASSWORD);
        } else {
            return DEFAULT_VALUE_PASSWORD;
        }
    }

    private String extractUserDomain() throws DfException {
        if (getMethodArgsManager().isArgumentProvided(JOBARG_DOMAIN)) {
            return extractArgStringValue(JOBARG_DOMAIN);
        } else {
            return DEFAULT_VALUE_DOMAIN;
        }
    }

    protected String extractArgStringValue(String propertyName)
        throws DfException {
        String extractedVal = getMethodArgsManager().getString(propertyName);
        if (CoreUtils.isNotEmpty(extractedVal)) {
            return extractedVal;
        }
        throw new DfException(MessageFormat.format(DMLS_JOB_ARG_VALUE_INVALID,
                propertyName, extractedVal));
    }

    protected Integer extractArgIntValue(String propertyName)
        throws DfException {
        String stringValue = extractArgStringValue(propertyName);
        try {
            return Integer.parseInt(stringValue);
        } catch (NumberFormatException numEx) {
            throw new DfException(numEx);
        }
    }

    protected Boolean extractArgBoolValue(String propertyName)
        throws DfException {
        String stringValue = extractArgStringValue(propertyName);
        Boolean boolVal;
        if ("true".equalsIgnoreCase(stringValue)
                || "t".equalsIgnoreCase(stringValue)) {
            boolVal = Boolean.TRUE;
        } else if ("false".equalsIgnoreCase(stringValue)
                || "f".equalsIgnoreCase(stringValue)) {
            boolVal = Boolean.FALSE;
        } else {
            throw new DfException(MessageFormat.format(
                    DMLS_JOB_ARG_VALUE_INVALID, propertyName, stringValue));
        }
        return boolVal;
    }

    protected final DfMethodArgumentManager getMethodArgsManager() {
        return _methodArgsManager;
    }

    private void setMethodArgsManager(DfMethodArgumentManager methodArgsManager) {
        _methodArgsManager = methodArgsManager;
    }

    protected final String getJobId() {
        return _jobId;
    }

    private void setJobId(String jobId) {
        _jobId = jobId;
    }

    private JobTracer getJobTracer() {
        return _jobTracer;
    }

    private void setJobTracer(JobTracer jobTracer) {
        _jobTracer = jobTracer;
    }

    private boolean isSingleExecution() {
        return _singleExecution;
    }

    private void setSingleExecution(boolean singleExecution) {
        _singleExecution = singleExecution;
    }

    private boolean isUseTransaction() {
        return _useTransaction;
    }

    private void setUseTransaction(boolean useTransaction) {
        _useTransaction = useTransaction;
    }

    private void closeTracer(boolean flag) {
        try {
            getJobTracer().close(flag);
        } catch (Exception ex) {
            getJobTracer().logError(ex);
        }
    }

    public final void logMsg(String msg) {
        getJobTracer().logMsg(msg);
    }

    public final void logWarn(String warnMsg) {
        getJobTracer().logWarn(warnMsg);
    }

    public final void logError(String msg) {
        getJobTracer().logError(msg);
        DfLogger.error(this, msg, null, null);
    }

    public final void writeBoldLine() {
        getJobTracer().writeBoldLine();
    }

    public final void writeLine() {
        getJobTracer().writeLine();
    }

    public final void logError(Throwable throwable) {
        getJobTracer().logError(throwable);
        String message = throwable.getMessage();
        if (message == null) {
            message = "";
        }
        DfLogger.error(this, message, null, throwable);
    }

    public final void logInfo(String infoMsg) {
        getJobTracer().logInfo(infoMsg);
    }

    public final void logDebug(String debugMsg) {
        getJobTracer().logDebug(debugMsg);
    }

    public boolean isDebug() {
        return getJobTracer().isDebug();
    }

    @Override
    public boolean isInfo() {
        return getJobTracer().isInfo();
    }

    @Override
    public boolean isWarn() {
        return getJobTracer().isWarn();
    }

}

