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

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicReference;

public class WidgetRefreshWorker extends Worker {

    private static final String TAG = "WidgetRefreshWorker";
    private static final String PREF_WIDGET_KEY = "waqd.widget.key";
    private static final String PREF_BASE_URL = "waqd.background.apiBaseUrl";
    private static final String PREF_DEBUG = "waqd.widget.lastDebug";
    private static final int GPS_TIMEOUT_SECONDS = 15;

    public WidgetRefreshWorker(@NonNull Context context, @NonNull WorkerParameters params) {
        super(context, params);
    }

    @NonNull
    @Override
    public Result doWork() {
        Context appContext = getApplicationContext();

        try {
            doRefresh(appContext);
            logDebug(appContext.getSharedPreferences("CapacitorStorage", Context.MODE_PRIVATE),
                    "Widget refresh OK at " + System.currentTimeMillis());
            return Result.success();
        } catch (RefreshException e) {
            logDebug(appContext.getSharedPreferences("CapacitorStorage", Context.MODE_PRIVATE),
                    "Refresh failed: " + e.getMessage());
            Log.e(TAG, "Refresh failed: " + e.getMessage(), e);
            return e.retryable ? Result.retry() : Result.failure();
        } catch (Exception e) {
            logDebug(appContext.getSharedPreferences("CapacitorStorage", Context.MODE_PRIVATE),
                    "Refresh failed: " + e.getMessage());
            Log.e(TAG, "Unexpected error: " + e.getMessage(), e);
            return Result.retry();
        }
    }

    private void logDebug(SharedPreferences prefs, String message) {
        try {
            JSONObject entry = new JSONObject();
            entry.put("ts", System.currentTimeMillis());
            entry.put("msg", message);
            prefs.edit().putString(PREF_DEBUG, entry.toString()).apply();
        } catch (Exception ignored) {}
    }

    private void doRefresh(Context context) throws Exception {
        SharedPreferences prefs = context.getSharedPreferences("CapacitorStorage", Context.MODE_PRIVATE);
        String widgetKey = prefs.getString(PREF_WIDGET_KEY, null);
        String baseUrl = prefs.getString(PREF_BASE_URL, null);

        if (widgetKey == null || widgetKey.isEmpty()) {
            throw new RefreshException("No widget key stored (waqd.widget.key). Open the app while logged in so the key gets saved.", false);
        }
        if (baseUrl == null || baseUrl.isEmpty()) {
            throw new RefreshException("No base URL stored (waqd.background.apiBaseUrl). Open the app once to persist it.", false);
        }

        Location location = getCurrentLocation(context);
        if (location == null) {
            throw new RefreshException("No GPS location available. Grant location permission (Allow all the time) and turn on GPS.", true);
        }

        double lat = location.getLatitude();
        double lon = location.getLongitude();
        Log.d(TAG, "Fetching weather for " + lat + ", " + lon);

        String apiUrl = baseUrl + "/api/public/widget/weather?latitude=" + lat + "&longitude=" + lon;
        URL url = new URL(apiUrl);
        HttpURLConnection conn = (HttpURLConnection) url.openConnection();
        conn.setRequestMethod("GET");
        conn.setRequestProperty("Authorization", "WidgetToken " + widgetKey);
        conn.setConnectTimeout(10000);
        conn.setReadTimeout(10000);

        int code = conn.getResponseCode();
        if (code != 200) {
            String errorBody = "";
            try {
                BufferedReader errReader = new BufferedReader(new InputStreamReader(conn.getErrorStream()));
                StringBuilder errSb = new StringBuilder();
                String line;
                while ((line = errReader.readLine()) != null) errSb.append(line);
                errReader.close();
                errorBody = errSb.toString();
            } catch (Exception ignored) {}
            conn.disconnect();
            boolean retryable = code >= 500 || code == 429;
            throw new RefreshException("Widget API returned HTTP " + code + (errorBody.isEmpty() ? "" : " :: " + errorBody), retryable);
        }

        BufferedReader reader = new BufferedReader(new InputStreamReader(conn.getInputStream()));
        StringBuilder sb = new StringBuilder();
        String line;
        while ((line = reader.readLine()) != null) {
            sb.append(line);
        }
        reader.close();
        String body = sb.toString();
        conn.disconnect();

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

        prefs.edit().putString("widget_weather_data", widgetData.toString()).apply();
        prefs.edit().putString("waqd.widget.lastGpsCoords", lat + "," + lon).apply();
        prefs.edit().putString("waqd.widget.lastGpsName", apiPayload.getString("locationName")).apply();
        String resolvedName = apiPayload.optString("locationName", "?");
        Log.d(TAG, "Widget data updated successfully: " + resolvedName + " at " + lat + "," + lon);
        logDebug(prefs, "OK: " + resolvedName + " (" + lat + "," + lon + "), temp " + widgetData.optInt("temp") + "° at " + System.currentTimeMillis());

        Intent updateIntent = new Intent(context, WeatherWidgetProvider.class);
        updateIntent.setAction(AppWidgetManager.ACTION_APPWIDGET_UPDATE);
        ComponentName provider = new ComponentName(context, WeatherWidgetProvider.class);
        int[] ids = AppWidgetManager.getInstance(context).getAppWidgetIds(provider);
        updateIntent.putExtra(AppWidgetManager.EXTRA_APPWIDGET_IDS, ids);
        context.sendBroadcast(updateIntent);
        Log.d(TAG, "Widget update broadcast sent for " + ids.length + " instances");
    }

    private Location getCurrentLocation(Context context) throws RefreshException {
        LocationManager lm = (LocationManager) context.getSystemService(Context.LOCATION_SERVICE);
        if (lm == null) {
            throw new RefreshException("LocationManager unavailable", false);
        }

        boolean hasFine = ContextCompat.checkSelfPermission(context, Manifest.permission.ACCESS_FINE_LOCATION)
                == PackageManager.PERMISSION_GRANTED;
        boolean hasCoarse = ContextCompat.checkSelfPermission(context, Manifest.permission.ACCESS_COARSE_LOCATION)
                == PackageManager.PERMISSION_GRANTED;
        if (!hasFine && !hasCoarse) {
            throw new RefreshException("No location permission granted. Grant 'Allow all the time' in app settings.", false);
        }

        final CountDownLatch latch = new CountDownLatch(1);
        final AtomicReference<Location> resultRef = new AtomicReference<>();
        final CancellationSignal cancelSignal = new CancellationSignal();

        // Timeout thread: cancel after GPS_TIMEOUT_SECONDS
        new Thread(() -> {
            try { Thread.sleep(GPS_TIMEOUT_SECONDS * 1000L); } catch (InterruptedException ignored) {}
            cancelSignal.cancel();
            latch.countDown();
        }).start();

        try {
            lm.getCurrentLocation(LocationManager.FUSED_PROVIDER, cancelSignal, Runnable::run,
                location -> {
                    if (location != null) resultRef.set(location);
                    latch.countDown();
                });
        } catch (Exception e) {
            cancelSignal.cancel();
            throw new RefreshException("LocationManager.getCurrentLocation failed: " + e.getMessage(), true);
        }

        try {
            boolean gotResult = latch.await(GPS_TIMEOUT_SECONDS + 2, TimeUnit.SECONDS);
            cancelSignal.cancel();

            if (!gotResult || resultRef.get() == null) {
                throw new RefreshException("No fresh GPS fix within " + GPS_TIMEOUT_SECONDS + "s. Turn on location/GPS and try again.", true);
            }

            Location loc = resultRef.get();
            long ageMs = System.currentTimeMillis() - loc.getTime();
            if (ageMs > GPS_TIMEOUT_SECONDS * 1000L) {
                throw new RefreshException("GPS fix too old (" + (ageMs / 1000) + "s > " + GPS_TIMEOUT_SECONDS + "s). Turn on location/GPS and try again.", true);
            }
            Log.d(TAG, "GPS fix obtained: " + loc.getLatitude() + ", " + loc.getLongitude() + " (age " + (ageMs / 1000) + "s)");
            return loc;
        } catch (InterruptedException e) {
            cancelSignal.cancel();
            Thread.currentThread().interrupt();
            throw new RefreshException("GPS acquisition interrupted", true);
        }
    }

    private static final class RefreshException extends RuntimeException {
        final boolean retryable;

        RefreshException(String message, boolean retryable) {
            super(message);
            this.retryable = retryable;
        }
    }
}
