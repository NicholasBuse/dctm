package tel.panfilov.documentum.utils;

/**
 * @author Andrey B. Panfilov <andrew@panfilov.tel>
 */
public final class CoreUtils {

    private CoreUtils() {
        super();
    }

    public static boolean isNotEmpty(String str) {
        return !isEmpty(str);
    }

    public static boolean isEmpty(String str) {
        return str == null || str.length() == 0;
    }

    public static boolean asBoolean(String booleanStr) {
        return "T".equalsIgnoreCase(booleanStr)
                || "TRUE".equalsIgnoreCase(booleanStr)
                || "1".equalsIgnoreCase(booleanStr)
                || "1.0".equalsIgnoreCase(booleanStr);
    }

}
