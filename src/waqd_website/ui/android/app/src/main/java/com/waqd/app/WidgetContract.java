package com.waqd.app;

import android.content.Context;
import android.net.ConnectivityManager;
import android.net.Network;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;
import java.net.UnknownHostException;

/**
 * Single source of truth for the SharedPreferences-based contract between the
 * web UI (via Capacitor Preferences), MainActivity, WeatherWidgetProvider and
 * WidgetRefreshWorker. All keys live in the "CapacitorStorage" prefs file.
 */
public final class WidgetContract {

    private static final int HTTP_ATTEMPTS = 3;
    private static final long RETRY_DELAY_MS = 750L;

    private WidgetContract() {}

    public static final String PREFS_NAME = "CapacitorStorage";

    // Written by the web UI, read by native code.
    public static final String PREF_WIDGET_KEY = "waqd.widget.key";
    public static final String PREF_BASE_URL = "waqd.background.apiBaseUrl";
    public static final String PREF_LOCALE = "waqd.locale";
    public static final String PREF_WIDGET_STYLE = "waqd.website.widgetStyle";

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
    public static String httpGet(Context context, String url, String widgetKey) throws Exception {
        UnknownHostException lastDnsFailure = null;
        for (int attempt = 1; attempt <= HTTP_ATTEMPTS; attempt++) {
            try {
                return httpGetOnce(context, url, widgetKey);
            } catch (UnknownHostException e) {
                lastDnsFailure = e;
                if (attempt == HTTP_ATTEMPTS) throw e;
                try {
                    Thread.sleep(RETRY_DELAY_MS * attempt);
                } catch (InterruptedException interrupted) {
                    Thread.currentThread().interrupt();
                    throw e;
                }
            }
        }
        throw lastDnsFailure;
    }

    private static String httpGetOnce(Context context, String url, String widgetKey) throws Exception {
        ConnectivityManager connectivityManager =
                (ConnectivityManager) context.getSystemService(Context.CONNECTIVITY_SERVICE);
        Network activeNetwork = connectivityManager == null
                ? null
                : connectivityManager.getActiveNetwork();
        if (activeNetwork == null) {
            throw new UnknownHostException("No active network");
        }

        HttpURLConnection conn =
                (HttpURLConnection) activeNetwork.openConnection(new URL(url));
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
