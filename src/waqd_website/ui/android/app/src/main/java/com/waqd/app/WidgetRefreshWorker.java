package com.waqd.app;

import android.Manifest;
import android.content.Context;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.location.Location;
import android.util.Log;

import androidx.annotation.NonNull;
import androidx.core.content.ContextCompat;
import androidx.work.Worker;
import androidx.work.WorkerParameters;

import com.google.android.gms.location.CurrentLocationRequest;
import com.google.android.gms.location.FusedLocationProviderClient;
import com.google.android.gms.location.LocationCallback;
import com.google.android.gms.location.LocationRequest;
import com.google.android.gms.location.LocationResult;
import com.google.android.gms.location.LocationServices;
import com.google.android.gms.location.Priority;

import org.json.JSONArray;
import org.json.JSONObject;

import java.net.URLEncoder;
import java.net.UnknownHostException;
import java.net.URL;
import java.util.Locale;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.Executor;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicReference;

public class WidgetRefreshWorker extends Worker {

    private static final String TAG = "WidgetRefreshWorker";
    private static final int GPS_TIMEOUT_SECONDS = 60;
    private static final int BALANCED_TIMEOUT_SECONDS = 30;
    private String lastLocationFailure = "No current location fix was returned.";

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
        } finally {
            // Clear the spinner for success, failure, and retry. A retry will be
            // scheduled by WorkManager and the next attempt can show it again.
            String currentWorkId = prefs.getString(WeatherWidgetProvider.PREF_REFRESH_WORK_ID, null);
            if (getId().toString().equals(currentWorkId)) {
                prefs.edit()
                        .putBoolean(WeatherWidgetProvider.PREF_REFRESHING, false)
                    .remove(WidgetContract.PREF_REFRESH_STARTED)
                        .remove(WeatherWidgetProvider.PREF_REFRESH_WORK_ID)
                        .apply();
                WeatherWidgetProvider.updateAllWidgets(appContext);
            }
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
        lastLocationFailure = "No current location fix was returned.";
        SharedPreferences prefs = context.getSharedPreferences(WidgetContract.PREFS_NAME, Context.MODE_PRIVATE);
        String widgetKey = prefs.getString(WidgetContract.PREF_WIDGET_KEY, null);
        String baseUrl = prefs.getString(WidgetContract.PREF_BASE_URL, null);

        if (widgetKey == null || widgetKey.isEmpty()) {
            throw new RefreshException("No widget key stored (waqd.widget.key). Open the app while logged in so the key gets saved.", false, "no_key");
        }
        if (baseUrl == null || baseUrl.isEmpty()) {
            throw new RefreshException("No base URL stored (waqd.background.apiBaseUrl). Open the app once to persist it.", false, "no_base_url");
        }
        Log.d(TAG, "Widget refresh base URL: " + baseUrl);

        // Fetch the saved locations and build the cycle: [GPS] + saved locations.
        JSONArray savedLocations = new JSONArray();
        try {
            savedLocations = fetchSavedLocations(baseUrl, widgetKey);
        } catch (UnknownHostException e) {
            throw dnsFailure(baseUrl, e);
        } catch (RefreshException e) {
            throw e;
        } catch (Exception e) {
            throw new RefreshException(
                    "Saved locations request failed: " + e.getMessage(),
                    true,
                    "network");
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
                throw new RefreshException(lastLocationFailure, true, "no_gps");
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
            body = WidgetContract.httpGet(context, apiUrl, widgetKey);
        } catch (UnknownHostException e) {
            throw dnsFailure(baseUrl, e);
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
        // These are the coordinates currently displayed by the widget, not
        // necessarily GPS coordinates: when the user selected a saved location,
        // the forecast deep link must open that same location.
        prefs.edit().putString(WidgetContract.PREF_LAST_GPS_COORDS, lat + "," + lon).apply();
        prefs.edit().putString(WidgetContract.PREF_LAST_GPS_NAME, apiPayload.getString("locationName")).apply();
        String resolvedName = apiPayload.optString("locationName", "?");
        Log.d(TAG, "Widget data updated successfully: " + resolvedName + " at " + lat + "," + lon);

        // The worker's finally block redraws all widgets without scheduling a
        // second worker. Broadcasting APPWIDGET_UPDATE here would make the
        // provider's stale-data check enqueue another job while this one is
        // still running, potentially replacing the current work.
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
            String body = WidgetContract.httpGet(getApplicationContext(), url, widgetKey);
            return new JSONObject(body).getJSONArray("locations");
        } catch (WidgetContract.HttpException e) {
            throw new RefreshException("Locations API returned HTTP " + e.statusCode, false, "http");
        }
    }

    private double[] tryGetCoordinates(Context context) throws RefreshException {
        lastLocationFailure = "No current location fix was returned.";
        boolean hasFine = ContextCompat.checkSelfPermission(context, Manifest.permission.ACCESS_FINE_LOCATION)
                == PackageManager.PERMISSION_GRANTED;
        boolean hasCoarse = ContextCompat.checkSelfPermission(context, Manifest.permission.ACCESS_COARSE_LOCATION)
                == PackageManager.PERMISSION_GRANTED;
        if (!hasFine && !hasCoarse) {
            throw new RefreshException("No location permission granted. Grant 'Allow all the time' in app settings.", false, "no_permission");
        }
        boolean hasBackground = ContextCompat.checkSelfPermission(context, Manifest.permission.ACCESS_BACKGROUND_LOCATION)
                == PackageManager.PERMISSION_GRANTED;
        if (!hasBackground) {
            throw new RefreshException("The widget needs 'Allow all the time' location access to refresh in the background.", false, "no_permission");
        }

        // Always request a current fix. Never use getLastKnownLocation() here:
        // the widget can remain visible for hours while the phone is idle, and a
        // successful refresh with an old cached position is worse than a retry.
        Location fresh = tryGetFreshLocation(context, Priority.PRIORITY_HIGH_ACCURACY,
                GPS_TIMEOUT_SECONDS);
        if (fresh != null) {
            return new double[]{fresh.getLatitude(), fresh.getLongitude()};
        }

        // A fresh balanced-power request is a useful fallback indoors, but is
        // still not allowed to return an old cached fix.
        Location networkFix = tryGetFreshLocation(context, Priority.PRIORITY_BALANCED_POWER_ACCURACY,
            BALANCED_TIMEOUT_SECONDS);
        if (networkFix != null) {
            Log.d(TAG, "Using fresh balanced-power location: " + networkFix.getLatitude() + ", " + networkFix.getLongitude());
            return new double[]{networkFix.getLatitude(), networkFix.getLongitude()};
        }

        // A failed fresh fix is not proof that permission is missing. Permission
        // failures are reported only by the explicit checks above; otherwise this
        // is a temporary location/provider failure and should be retried.
        lastLocationFailure = "No current location fix was returned. " + lastLocationFailure
            + " Check that Location is enabled and try again.";
        Log.w(TAG, lastLocationFailure);
        return null;
    }

    private RefreshException dnsFailure(String baseUrl, UnknownHostException error) {
        String host = baseUrl;
        try {
            host = new URL(baseUrl).getHost();
        } catch (Exception ignored) {
        }
        String detail = error.getMessage();
        String suffix = detail == null || detail.isEmpty() ? "" : " (" + detail + ")";
        return new RefreshException(
                "DNS lookup failed for " + host + suffix + ". Check the device network or Private DNS settings.",
                true,
                "dns");
    }

    private Location tryGetFreshLocation(Context context, int priority, int timeoutSeconds) {
        FusedLocationProviderClient client = LocationServices.getFusedLocationProviderClient(context);
        LocationRequest request = new LocationRequest.Builder(priority, 5_000L)
                .setMinUpdateIntervalMillis(2_000L)
                .setMaxUpdateDelayMillis(5_000L)
                .build();
        CountDownLatch latch = new CountDownLatch(1);
        AtomicReference<Location> result = new AtomicReference<>();
        AtomicReference<String> failure = new AtomicReference<>();
        LocationCallback callback = new LocationCallback() {
            @Override
            public void onLocationResult(LocationResult locationResult) {
                Location latest = locationResult.getLastLocation();
                if (latest != null && isFresh(latest, timeoutSeconds)) {
                    result.set(latest);
                    latch.countDown();
                }
            }
        };

        try {
            client.requestLocationUpdates(request, callback, android.os.Looper.getMainLooper());
            if (!latch.await(timeoutSeconds, TimeUnit.SECONDS)) {
                failure.set("Location update session timed out after " + timeoutSeconds + " seconds.");
                lastLocationFailure = "Location provider timed out after " + timeoutSeconds + " seconds.";
                Log.w(TAG, "Fused location timed out after " + timeoutSeconds + "s");
                return null;
            }
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            return null;
        } catch (SecurityException e) {
            failure.set("Location permission rejected: " + e.getMessage());
            Log.w(TAG, failure.get());
            return null;
        } catch (Exception e) {
            failure.set("Location update request failed: " + e.getMessage());
            Log.w(TAG, failure.get());
            return null;
        } finally {
            client.removeLocationUpdates(callback);
        }

        Location location = result.get();
        if (location == null) {
            lastLocationFailure = failure.get() == null
                    ? "Location provider returned no current fix."
                    : failure.get();
            Log.w(TAG, lastLocationFailure);
            return null;
        }

        long ageMs = System.currentTimeMillis() - location.getTime();
        Log.d(TAG, "Fresh fused location obtained: " + location.getLatitude() + ", "
                + location.getLongitude() + " (age " + (ageMs / 1000) + "s)");
        return location;
    }

    private boolean isFresh(Location location, int timeoutSeconds) {
        return System.currentTimeMillis() - location.getTime() <= timeoutSeconds * 1000L;
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
