package com.waqd.app;

import android.Manifest;
import android.appwidget.AppWidgetManager;
import android.content.ComponentName;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.location.Location;
import android.location.LocationManager;
import android.os.CancellationSignal;
import android.util.Log;

import androidx.annotation.NonNull;
import androidx.core.content.ContextCompat;
import androidx.work.Worker;
import androidx.work.WorkerParameters;

import org.json.JSONArray;
import org.json.JSONObject;

import java.net.URLEncoder;
import java.util.Locale;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicReference;

public class WidgetRefreshWorker extends Worker {

    private static final String TAG = "WidgetRefreshWorker";
    private static final int GPS_TIMEOUT_SECONDS = 30;

    public WidgetRefreshWorker(@NonNull Context context, @NonNull WorkerParameters params) {
        super(context, params);
    }

    @NonNull
    @Override
    public Result doWork() {
        Context appContext = getApplicationContext();
        SharedPreferences prefs = appContext.getSharedPreferences(WidgetContract.PREFS_NAME, Context.MODE_PRIVATE);

        try {
            doRefresh(appContext);
            long now = System.currentTimeMillis();
            logStatus(prefs, true, "ok", "Weather updated");
            prefs.edit().putLong(WeatherWidgetProvider.PREF_LAST_SUCCESS, now).apply();
            logUpdateHistory(prefs, now);
            return Result.success();
        } catch (RefreshException e) {
            logStatus(prefs, false, e.code, e.getMessage());
            Log.e(TAG, "Refresh failed: " + e.getMessage(), e);
            return e.retryable ? Result.retry() : Result.failure();
        } catch (Exception e) {
            logStatus(prefs, false, "error", e.getMessage());
            Log.e(TAG, "Unexpected error: " + e.getMessage(), e);
            return Result.retry();
        }
    }

    /** Structured status consumed by the web UI to render guided, actionable messages. */
    private void logStatus(SharedPreferences prefs, boolean ok, String code, String message) {
        try {
            JSONObject entry = new JSONObject();
            entry.put("ts", System.currentTimeMillis());
            entry.put("ok", ok);
            entry.put("code", code == null ? "error" : code);
            entry.put("message", message == null ? "" : message);
            prefs.edit().putString(WidgetContract.PREF_STATUS, entry.toString()).apply();
        } catch (Exception ignored) {}
    }

    /** Keeps a rolling list of the last 3 successful update timestamps (newest first). */
    private void logUpdateHistory(SharedPreferences prefs, long ts) {
        try {
            JSONArray history = new JSONArray();
            history.put(ts);
            String existing = prefs.getString(WidgetContract.PREF_UPDATE_HISTORY, null);
            if (existing != null && !existing.isEmpty()) {
                JSONArray old = new JSONArray(existing);
                for (int i = 0; i < old.length() && history.length() < 3; i++) {
                    history.put(old.getLong(i));
                }
            }
            prefs.edit().putString(WidgetContract.PREF_UPDATE_HISTORY, history.toString()).apply();
        } catch (Exception ignored) {}
    }

    private void doRefresh(Context context) throws Exception {
        SharedPreferences prefs = context.getSharedPreferences(WidgetContract.PREFS_NAME, Context.MODE_PRIVATE);
        String widgetKey = prefs.getString(WidgetContract.PREF_WIDGET_KEY, null);
        String baseUrl = prefs.getString(WidgetContract.PREF_BASE_URL, null);

        if (widgetKey == null || widgetKey.isEmpty()) {
            throw new RefreshException("No widget key stored (waqd.widget.key). Open the app while logged in so the key gets saved.", false, "no_key");
        }
        if (baseUrl == null || baseUrl.isEmpty()) {
            throw new RefreshException("No base URL stored (waqd.background.apiBaseUrl). Open the app once to persist it.", false, "no_base_url");
        }

        // Fetch the saved locations and build the cycle: [GPS] + saved locations.
        JSONArray savedLocations = new JSONArray();
        try {
            savedLocations = fetchSavedLocations(baseUrl, widgetKey);
        } catch (Exception e) {
            Log.w(TAG, "Failed to fetch saved locations, defaulting to GPS only: " + e.getMessage());
        }

        int total = 1 + savedLocations.length();
        boolean arrowsEnabled = !"gps".equals(prefs.getString(WeatherWidgetProvider.PREF_LOCATION_MODE, "selectable"));
        int index = arrowsEnabled ? prefs.getInt(WeatherWidgetProvider.PREF_SELECTED_INDEX, 0) : 0;
        if (index < 0 || index >= total) {
            index = 0;
        }
        prefs.edit().putInt(WeatherWidgetProvider.PREF_SELECTED_INDEX, index).apply();
        prefs.edit().putInt(WeatherWidgetProvider.PREF_LOCATION_COUNT, total).apply();

        double lat;
        double lon;
        String locationName = null;
        if (index == 0) {
            double[] coords = tryGetCoordinates(context);
            if (coords == null) {
                throw new RefreshException("No GPS location available (fresh or cached). Turn on GPS.", true, "no_gps");
            }
            lat = coords[0];
            lon = coords[1];
        } else {
            JSONObject loc = savedLocations.getJSONObject(index - 1);
            lat = loc.getDouble("latitude");
            lon = loc.getDouble("longitude");
            locationName = loc.optString("name", null);
        }

        Log.d(TAG, "Fetching weather for " + lat + ", " + lon + (locationName != null ? " (" + locationName + ")" : ""));

        String apiUrl = baseUrl + "/api/public/widget/weather?latitude=" + lat + "&longitude=" + lon
                + "&lang=" + resolveLocale(prefs);
        if (locationName != null && !locationName.isEmpty()) {
            apiUrl += "&name=" + URLEncoder.encode(locationName, "UTF-8");
        }

        String body;
        try {
            body = WidgetContract.httpGet(apiUrl, widgetKey);
        } catch (WidgetContract.HttpException e) {
            boolean retryable = e.statusCode >= 500 || e.statusCode == 429;
            throw new RefreshException("Widget API returned HTTP " + e.statusCode, retryable, "http");
        }

        JSONObject apiPayload = new JSONObject(body);
        JSONObject widgetData = new JSONObject();
        widgetData.put("temp", apiPayload.getDouble("temp"));
        widgetData.put("locationName", apiPayload.getString("locationName"));
        widgetData.put("main", apiPayload.getString("main"));
        widgetData.put("icon", apiPayload.getString("icon"));
        widgetData.put("temp_min", apiPayload.getDouble("temp_min"));
        widgetData.put("temp_max", apiPayload.getDouble("temp_max"));
        widgetData.put("updateTime", apiPayload.getLong("updateTime"));
        widgetData.put("widget_style", apiPayload.getString("widget_style"));
        widgetData.put("forecast_3_days", apiPayload.getJSONArray("forecast_3_days"));

        prefs.edit().putString(WidgetContract.PREF_WEATHER_DATA, widgetData.toString()).apply();
        prefs.edit().putString(WidgetContract.PREF_LAST_GPS_COORDS, lat + "," + lon).apply();
        prefs.edit().putString(WidgetContract.PREF_LAST_GPS_NAME, apiPayload.getString("locationName")).apply();
        String resolvedName = apiPayload.optString("locationName", "?");
        Log.d(TAG, "Widget data updated successfully: " + resolvedName + " at " + lat + "," + lon);

        Intent updateIntent = new Intent(context, WeatherWidgetProvider.class);
        updateIntent.setAction(AppWidgetManager.ACTION_APPWIDGET_UPDATE);
        ComponentName provider = new ComponentName(context, WeatherWidgetProvider.class);
        int[] ids = AppWidgetManager.getInstance(context).getAppWidgetIds(provider);
        updateIntent.putExtra(AppWidgetManager.EXTRA_APPWIDGET_IDS, ids);
        context.sendBroadcast(updateIntent);
        Log.d(TAG, "Widget update broadcast sent for " + ids.length + " instances");
    }

    private static String resolveLocale(SharedPreferences prefs) {
        String locale = prefs.getString(WidgetContract.PREF_LOCALE, null);
        if (locale == null || locale.isEmpty()) {
            locale = Locale.getDefault().getLanguage();
        }
        if ("de".equals(locale) || "hu".equals(locale)) {
            return locale;
        }
        return "en";
    }

    /** Fetches the user's saved locations as a JSON array of {name, latitude, longitude}. */
    private JSONArray fetchSavedLocations(String baseUrl, String widgetKey) throws Exception {
        String url = baseUrl + "/api/public/widget/locations";
        try {
            String body = WidgetContract.httpGet(url, widgetKey);
            return new JSONObject(body).getJSONArray("locations");
        } catch (WidgetContract.HttpException e) {
            throw new RefreshException("Locations API returned HTTP " + e.statusCode, false, "http");
        }
    }

    private double[] tryGetCoordinates(Context context) throws RefreshException {
        LocationManager lm = (LocationManager) context.getSystemService(Context.LOCATION_SERVICE);
        if (lm == null) {
            throw new RefreshException("LocationManager unavailable", false);
        }

        boolean hasFine = ContextCompat.checkSelfPermission(context, Manifest.permission.ACCESS_FINE_LOCATION)
                == PackageManager.PERMISSION_GRANTED;
        boolean hasCoarse = ContextCompat.checkSelfPermission(context, Manifest.permission.ACCESS_COARSE_LOCATION)
                == PackageManager.PERMISSION_GRANTED;
        if (!hasFine && !hasCoarse) {
            throw new RefreshException("No location permission granted. Grant 'Allow all the time' in app settings.", false, "no_permission");
        }

        // 1. Cached location first (instant) — avoids blocking the render on a fresh fix
        Location cached = tryGetCachedLocation(lm, LocationManager.FUSED_PROVIDER);
        if (cached != null) {
            long ageMs = System.currentTimeMillis() - cached.getTime();
            Log.d(TAG, "Using fused cached location: " + cached.getLatitude() + ", " + cached.getLongitude() + " (age " + (ageMs / 1000) + "s)");
            return new double[]{cached.getLatitude(), cached.getLongitude()};
        }

        // 2. Fresh GPS fix (30s timeout) — only when nothing cached
        Location fresh = tryGetFreshLocation(lm, LocationManager.FUSED_PROVIDER, GPS_TIMEOUT_SECONDS);
        if (fresh != null) {
            return new double[]{fresh.getLatitude(), fresh.getLongitude()};
        }

        // 3. Quick network-based approximate fix (10s timeout) — cell/WiFi, works indoors
        Location networkFix = tryGetFreshLocation(lm, LocationManager.NETWORK_PROVIDER, 10);
        if (networkFix != null) {
            Log.d(TAG, "Using network provider location: " + networkFix.getLatitude() + ", " + networkFix.getLongitude());
            return new double[]{networkFix.getLatitude(), networkFix.getLongitude()};
        }

        // If we could not get a fix and the app lacks background location access, that is
        // almost certainly why — foreground-only permission can't be used while the worker
        // runs in the background. Point the user at the correct fix ("Allow all the time").
        boolean hasBackground = ContextCompat.checkSelfPermission(context, Manifest.permission.ACCESS_BACKGROUND_LOCATION)
                == PackageManager.PERMISSION_GRANTED;
        if (!hasBackground) {
            throw new RefreshException(
                    "The widget needs 'Allow all the time' location access to refresh in the background.",
                    false, "no_permission");
        }

        Log.w(TAG, "No location available (GPS timeout, no cached, no network). Will retry.");
        return null;
    }

    private Location tryGetFreshLocation(LocationManager lm, String provider, int timeoutSeconds) throws RefreshException {
        final CountDownLatch latch = new CountDownLatch(1);
        final AtomicReference<Location> resultRef = new AtomicReference<>();
        final CancellationSignal cancelSignal = new CancellationSignal();

        new Thread(() -> {
            try { Thread.sleep(timeoutSeconds * 1000L); } catch (InterruptedException ignored) {}
            cancelSignal.cancel();
            latch.countDown();
        }).start();

        try {
            lm.getCurrentLocation(provider, cancelSignal, Runnable::run,
                location -> {
                    if (location != null) resultRef.set(location);
                    latch.countDown();
                });
        } catch (Exception e) {
            cancelSignal.cancel();
            Log.w(TAG, "LocationManager.getCurrentLocation(" + provider + ") failed: " + e.getMessage());
            return null;
        }

        try {
            boolean gotResult = latch.await(timeoutSeconds + 2, TimeUnit.SECONDS);
            cancelSignal.cancel();

            if (!gotResult || resultRef.get() == null) {
                Log.w(TAG, "No " + provider + " fix within " + timeoutSeconds + "s");
                return null;
            }

            Location loc = resultRef.get();
            long ageMs = System.currentTimeMillis() - loc.getTime();
            if (ageMs > timeoutSeconds * 1000L) {
                Log.w(TAG, provider + " fix too old (" + (ageMs / 1000) + "s > " + timeoutSeconds + "s)");
                return null;
            }
            Log.d(TAG, provider + " fix obtained: " + loc.getLatitude() + ", " + loc.getLongitude() + " (age " + (ageMs / 1000) + "s)");
            return loc;
        } catch (InterruptedException e) {
            cancelSignal.cancel();
            Thread.currentThread().interrupt();
            Log.w(TAG, provider + " acquisition interrupted");
            return null;
        }
    }

    private Location tryGetCachedLocation(LocationManager lm, String provider) {
        try {
            Location cached = lm.getLastKnownLocation(provider);
            if (cached != null) {
                long ageMs = System.currentTimeMillis() - cached.getTime();
                // Accept cached location up to 6 hours old
                if (ageMs < 6 * 3600 * 1000L) {
                    return cached;
                }
                Log.d(TAG, "Cached " + provider + " location too old (" + (ageMs / 1000) + "s > 6h)");
            }
        } catch (Exception e) {
            Log.w(TAG, "Failed to get cached " + provider + " location: " + e.getMessage());
        }
        return null;
    }

    private static final class RefreshException extends RuntimeException {
        final boolean retryable;
        final String code;

        RefreshException(String message, boolean retryable) {
            this(message, retryable, "error");
        }

        RefreshException(String message, boolean retryable, String code) {
            super(message);
            this.retryable = retryable;
            this.code = code;
        }
    }
}
