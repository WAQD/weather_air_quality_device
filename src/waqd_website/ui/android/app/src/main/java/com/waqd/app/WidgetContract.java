package com.waqd.app;

import android.content.Context;
import android.net.ConnectivityManager;
import android.net.Network;
import android.net.NetworkCapabilities;
import android.net.NetworkRequest;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;
import java.net.UnknownHostException;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicReference;

/**
 * Single source of truth for the SharedPreferences-based contract between the
 * web UI (via Capacitor Preferences), MainActivity, WeatherWidgetProvider and
 * WidgetRefreshWorker. All keys live in the "CapacitorStorage" prefs file.
 */
public final class WidgetContract {

    private static final int HTTP_ATTEMPTS = 3;
    private static final long RETRY_DELAY_MS = 750L;
    private static final int NETWORK_WAIT_SECONDS = 15;

    private WidgetContract() {}

    public static final String PREFS_NAME = "CapacitorStorage";

    // Written by the web UI, read by native code.
    public static final String PREF_WIDGET_KEY = "waqd.widget.key";
    public static final String PREF_BASE_URL = "waqd.background.apiBaseUrl";
    public static final String PREF_LOCALE = "waqd.locale";
    public static final String PREF_WIDGET_STYLE = "waqd.website.widgetStyle";
    public static final String PREF_WIDGET_TEMPERATURE_MODE = "waqd.website.widgetTemperatureMode";
    public static final String PREF_REFRESH_STARTED = "waqd.widget.refreshStarted";

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
        HttpURLConnection conn = openConnection(context, url);
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

    public static HttpURLConnection openConnection(Context context, String url) throws Exception {
        Network activeNetwork = awaitValidatedNetwork(context);
        return (HttpURLConnection) activeNetwork.openConnection(new URL(url));
    }

    /**
     * Gets a network that Android currently considers usable for internet traffic.
     * getActiveNetwork() is only a snapshot and can be null during idle/network
     * handover even while connectivity is about to become available.
     */
    private static Network awaitValidatedNetwork(Context context) throws IOException {
        ConnectivityManager connectivityManager =
                (ConnectivityManager) context.getSystemService(Context.CONNECTIVITY_SERVICE);
        if (connectivityManager == null) {
            throw new IOException("Connectivity service unavailable");
        }

        Network active = connectivityManager.getActiveNetwork();
        if (isValidatedInternet(connectivityManager, active)) {
            return active;
        }

        CountDownLatch latch = new CountDownLatch(1);
        AtomicReference<Network> result = new AtomicReference<>();
        NetworkRequest request = new NetworkRequest.Builder()
                .addCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET)
                .addCapability(NetworkCapabilities.NET_CAPABILITY_VALIDATED)
                .build();
        ConnectivityManager.NetworkCallback callback = new ConnectivityManager.NetworkCallback() {
            @Override
            public void onAvailable(Network network) {
                if (isValidatedInternet(connectivityManager, network)) {
                    result.set(network);
                    latch.countDown();
                }
            }
        };

        try {
            connectivityManager.registerNetworkCallback(request, callback);
            if (!latch.await(NETWORK_WAIT_SECONDS, TimeUnit.SECONDS)) {
                throw new IOException("No validated network became available within "
                        + NETWORK_WAIT_SECONDS + " seconds");
            }
            Network network = result.get();
            if (network == null) {
                throw new IOException("No validated network available");
            }
            return network;
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new IOException("Interrupted while waiting for a validated network", e);
        } finally {
            try {
                connectivityManager.unregisterNetworkCallback(callback);
            } catch (Exception ignored) {
            }
        }
    }

    private static boolean isValidatedInternet(ConnectivityManager connectivityManager, Network network) {
        if (network == null) return false;
        NetworkCapabilities capabilities = connectivityManager.getNetworkCapabilities(network);
        return capabilities != null
                && capabilities.hasCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET)
                && capabilities.hasCapability(NetworkCapabilities.NET_CAPABILITY_VALIDATED);
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
