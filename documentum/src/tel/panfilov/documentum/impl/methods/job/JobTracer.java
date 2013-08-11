package tel.panfilov.documentum.impl.methods.job;

import java.io.ByteArrayOutputStream;
import java.io.PrintStream;
import java.io.PrintWriter;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Date;
import java.util.List;

import com.documentum.fc.common.DfException;
import com.documentum.fc.common.DfLogger;
import com.documentum.fc.common.IDfId;
import com.documentum.server.impl.method.report.IReportWriter;
import com.documentum.server.impl.method.report.ReportFactory;

import tel.panfilov.documentum.api.methods.job.IJobTracer;

/**
 * @author Andrey B. Panfilov <andrew@panfilov.tel>
 */
public final class JobTracer implements IJobTracer {

    public static final String E_REPORT_WRITER_CREATE_FAILURE = "Failed to create Report Writer";

    public static final int TRACE_LEVEL_WARN = 0;
    public static final int TRACE_LEVEL_INFO = 4;
    public static final int TRACE_LEVEL_DEBUG = 9;

    public static final int BUFFER_SIZE = 1024;

    public static final SimpleDateFormat LOG_DATE_FORMAT = new SimpleDateFormat(
            "yyyy-MM-dd HH:mm:ss:S z");

    private List<String> _traceStore = new ArrayList<String>();

    private IReportWriter _reportWriter;

    private int _traceLevel = TRACE_LEVEL_WARN;

    private final Object _logger;

    public JobTracer(Object logger) {
        super();
        _logger = logger;
    }

    public void setTraceLevel(int traceLevel) {
        if (traceLevel > TRACE_LEVEL_DEBUG - 1) {
            _traceLevel = TRACE_LEVEL_DEBUG;
        } else if ((traceLevel >= TRACE_LEVEL_INFO)
                && (traceLevel <= TRACE_LEVEL_DEBUG - 1)) {
            _traceLevel = TRACE_LEVEL_INFO;
        } else if ((traceLevel >= TRACE_LEVEL_WARN)
                && (traceLevel <= TRACE_LEVEL_INFO - 1)) {
            _traceLevel = TRACE_LEVEL_WARN;
        }
    }

    public int getTraceLevel() {
        return _traceLevel;
    }

    public void createReportWriter(String repositoryName,
            String repositoryOwnerName, String domainName, IDfId jobId,
            PrintWriter printWriter) throws DfException {
        ReportFactory reportFactory = new ReportFactory();
        try {
            _reportWriter = reportFactory.getReport(repositoryName,
                    repositoryOwnerName, domainName, TRACE_LEVEL_WARN, jobId,
                    printWriter);
            if (_reportWriter == null) {
                throw new DfException(E_REPORT_WRITER_CREATE_FAILURE);
            }
            processTraceStore();
        } catch (Exception ex) {
            throw new DfException(E_REPORT_WRITER_CREATE_FAILURE, ex);
        }
    }

    private void processTraceStore() {
        if (_traceStore == null) {
            return;
        }
        if (_reportWriter == null) {
            for (String msg : _traceStore) {
                System.out.println(msg);
                System.out.flush();
            }
        } else {
            for (String msg : _traceStore) {
                _reportWriter.emitLineToReport(msg);
            }
        }
        _traceStore = null;
    }

    public void close(boolean closeFlag) throws DfException {
        try {
            if (_reportWriter == null) {
                if (_traceStore != null) {
                    processTraceStore();
                }
            } else {
                _reportWriter.closeOut(closeFlag);
                _reportWriter.close();
            }
        } catch (Exception anyEx) {
            throw new DfException(anyEx);
        }
    }

    public void logDebug(String debugMsg) {
        if (isDebug()) {
            writeOutput("DEBUG: " + debugMsg);
            DfLogger.debug(_logger, debugMsg, null, null);
        }
    }

    public void logInfo(String infoMsg) {
        if (isInfo()) {
            writeOutput("INFO: " + infoMsg);
            DfLogger.info(_logger, infoMsg, null, null);
        }
    }

    public boolean isWarn() {
        return getTraceLevel() >= TRACE_LEVEL_WARN;
    }

    public void logWarn(String warnMsg) {
        if (isWarn()) {
            writeOutput("WARNING: " + warnMsg);
            DfLogger.warn(_logger, warnMsg, null, null);
        }
    }

    public void logMsg(String msg) {
        writeOutput(msg);
    }

    public void logError(Throwable throwable) {
        writeOutput("ERROR: " + exceptionStackTraceToString(throwable));
        String message = throwable.getMessage();
        if (message == null) {
            message = "";
        }
        DfLogger.error(_logger, message, null, throwable);
    }

    public void logError(String msg) {
        writeOutput("ERROR: " + msg);
        DfLogger.error(_logger, msg, null, null);
    }

    public boolean isDebug() {
        return getTraceLevel() >= TRACE_LEVEL_DEBUG;
    }

    public boolean isInfo() {
        return getTraceLevel() >= TRACE_LEVEL_INFO;
    }

    private void writeOutput(String msg) {
        String message;
        synchronized (LOG_DATE_FORMAT) {
            message = LOG_DATE_FORMAT.format(new Date()) + " ["
                    + Thread.currentThread().getName() + "]: " + msg;
        }
        if (_reportWriter == null) {
            if (_traceStore == null) {
                System.out.println(message);
                System.out.flush();
            } else {
                _traceStore.add(message);
            }
        } else {
            _reportWriter.emitLineToReport(message);
        }
    }

    private String exceptionStackTraceToString(Throwable throwable) {
        ByteArrayOutputStream byteArrayOutputStream = new ByteArrayOutputStream(
                BUFFER_SIZE);
        PrintStream printStream = new PrintStream(byteArrayOutputStream);

        throwable.printStackTrace(printStream);

        return byteArrayOutputStream.toString();
    }

    public void writeLine() {
        writeOutput("---------------------------------------------------------------------------------");
    }

    public void writeBoldLine() {
        writeOutput("*********************************************************************************");
    }

}
