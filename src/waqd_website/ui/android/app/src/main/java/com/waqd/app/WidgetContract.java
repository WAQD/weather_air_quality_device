package com.waqd.app;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;

/**
 * Single source of truth for the SharedPreferences-based contract between the
 * web UI (via Capacitor Preferences), MainActivity, WeatherWidgetProvider and
 * WidgetRefreshWorker. All keys live in the "CapacitorStorage" prefs file.
 */
public final class WidgetContract {

    private WidgetContract() {}

    public static final String PREFS_NAME = "CapacitorStorage";

    // Written by the web UI, read by native code.
    public static final String PREF_WIDGET_KEY = "waqd.widget.key";
    public static final String PREF_BASE_URL = "waqd.background.apiBaseUrl";
    public static final String PREF_LOCALE = "waqd.locale";

    // Shared between worker and provider.
    public static final String PREF_LAST_SUCCESS = "waqd.widget.lastSuccessTs";
    public static final String PREF_SELECTED_INDEX = "waqd.widget.selectedIndex";
    public static final String PREF_LOCATION_COUNT = "waqd.widget.locationCount";
    /** "gps" = GPS only (no arrows); "selectable" = arrows cycle GPS + saved locations. */
    public static final String PREF_LOCATION_MODE = "waqd.widget.locationMode";
    public static final String PREF_STATUS = "waqd.widget.lastStatus";
    public static final String PREF_UPDATE_HISTORY = "waqd.widget.updateHistory";
    public static final String PREF_WEATHER_DATA = "widget_weather_data";
    public static final String PREF_LAST_GPS_COORDS = "waqd.widget.lastGpsCoords";
    public static final String PREF_LAST_GPS_NAME = "waqd.widget.lastGpsName";

    /** Simple authenticated GET returning the response body; throws on non-200. */
    public static String httpGet(String url, String widgetKey) throws Exception {
        HttpURLConnection conn = (HttpURLConnection) new URL(url).openConnection();
        try {
            conn.setRequestMethod("GET");
            conn.setRequestProperty("Authorization", "WidgetToken " + widgetKey);
            conn.setConnectTimeout(10000);
            conn.setReadTimeout(10000);

            int code = conn.getResponseCode();
            if (code != 200) {
                throw new HttpException(code);
            }
            BufferedReader reader = new BufferedReader(new InputStreamReader(conn.getInputStream()));
            StringBuilder sb = new StringBuilder();
            String line;
            while ((line = reader.readLine()) != null) sb.append(line);
            reader.close();
            return sb.toString();
        } finally {
            conn.disconnect();
        }
    }

    /** HTTP error carrying the status code so callers can decide retryability. */
    public static class HttpException extends Exception {
        public final int statusCode;

        public HttpException(int statusCode) {
            super("HTTP " + statusCode);
            this.statusCode = statusCode;
        }
    }
}
