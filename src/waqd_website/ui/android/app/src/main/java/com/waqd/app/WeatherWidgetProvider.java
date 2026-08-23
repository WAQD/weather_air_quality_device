package com.waqd.app;

import android.Manifest;
import android.app.PendingIntent;
import android.appwidget.AppWidgetManager;
import android.appwidget.AppWidgetProvider;
import android.content.ComponentName;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.graphics.Canvas;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.widget.RemoteViews;
import com.caverock.androidsvg.SVG;
import org.json.JSONObject;
import org.json.JSONArray;
import java.io.InputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;
import java.io.File;
import java.io.FileOutputStream;

import androidx.core.content.ContextCompat;
import androidx.work.BackoffPolicy;
import androidx.work.ExistingPeriodicWorkPolicy;
import androidx.work.ExistingWorkPolicy;
import androidx.work.OneTimeWorkRequest;
import androidx.work.PeriodicWorkRequest;
import androidx.work.WorkManager;

public class WeatherWidgetProvider extends AppWidgetProvider {

    private static final ExecutorService executor = Executors.newSingleThreadExecutor();
    private static final String BASE_URL = BuildConfig.WAQD_BASE_URL;
    private static final String PERIODIC_WORK_NAME = "waqd_widget_periodic";
    /** Epoch millis of the last successful widget refresh (written by WidgetRefreshWorker). */
    public static final String PREF_LAST_SUCCESS = "waqd.widget.lastSuccessTs";
    /** Persisted selected location index and total count for the location switcher. */
    public static final String PREF_SELECTED_INDEX = "waqd.widget.selectedIndex";
    public static final String PREF_LOCATION_COUNT = "waqd.widget.locationCount";
    private static final String ACTION_LOCATION_PREV = "com.waqd.app.action.LOCATION_PREV";
    private static final String ACTION_LOCATION_NEXT = "com.waqd.app.action.LOCATION_NEXT";

    @Override
    public void onUpdate(Context context, AppWidgetManager appWidgetManager, int[] appWidgetIds) {
        for (int appWidgetId : appWidgetIds) {
            updateAppWidget(context, appWidgetManager, appWidgetId);
        }
    }

    @Override
    public void onEnabled(Context context) {
        super.onEnabled(context);
        schedulePeriodicWork(context);
        enqueueImmediateRefresh(context);
    }

    @Override
    public void onDisabled(Context context) {
        super.onDisabled(context);
        WorkManager.getInstance(context).cancelUniqueWork(PERIODIC_WORK_NAME);
    }

    @Override
    public void onAppWidgetOptionsChanged(Context context, AppWidgetManager appWidgetManager, int appWidgetId, Bundle newOptions) {
        updateAppWidget(context, appWidgetManager, appWidgetId);
        super.onAppWidgetOptionsChanged(context, appWidgetManager, appWidgetId, newOptions);
    }

    @Override
    public void onReceive(Context context, Intent intent) {
        super.onReceive(context, intent);
        String action = intent.getAction();
        if (ACTION_LOCATION_PREV.equals(action)) {
            changeLocation(context, true);
        } else if (ACTION_LOCATION_NEXT.equals(action)) {
            changeLocation(context, false);
        }
    }

    /** Steps the selected location index (prev/next, wrapping) and triggers a refresh. */
    private void changeLocation(Context context, boolean prev) {
        SharedPreferences prefs = context.getSharedPreferences("CapacitorStorage", Context.MODE_PRIVATE);
        int count = prefs.getInt(PREF_LOCATION_COUNT, 1);
        if (count <= 1) return;
        int index = prefs.getInt(PREF_SELECTED_INDEX, 0);
        index = prev ? (index - 1 + count) % count : (index + 1) % count;
        prefs.edit().putInt(PREF_SELECTED_INDEX, index).apply();
        refreshNow(context);
    }

    private static void schedulePeriodicWork(Context context) {
        PeriodicWorkRequest periodic = new PeriodicWorkRequest.Builder(
                WidgetRefreshWorker.class, 15, TimeUnit.MINUTES)
                .setBackoffCriteria(BackoffPolicy.LINEAR, 2, TimeUnit.MINUTES)
                .build();
        WorkManager.getInstance(context)
                .enqueueUniquePeriodicWork(PERIODIC_WORK_NAME, ExistingPeriodicWorkPolicy.KEEP, periodic);
    }

    private static void enqueueImmediateRefresh(Context context) {
        OneTimeWorkRequest request = new OneTimeWorkRequest.Builder(WidgetRefreshWorker.class)
                .setBackoffCriteria(BackoffPolicy.LINEAR, 2, TimeUnit.MINUTES)
                .build();
        WorkManager.getInstance(context)
                .enqueueUniqueWork("waqd_widget_immediate", ExistingWorkPolicy.REPLACE, request);
    }

    /** Refresh the widget now, but never more often than every 5 minutes per success. */
    public static void requestImmediateRefresh(Context context) {
        SharedPreferences prefs = context.getSharedPreferences("CapacitorStorage", Context.MODE_PRIVATE);
        long lastSuccess = prefs.getLong(PREF_LAST_SUCCESS, 0);
        if (System.currentTimeMillis() - lastSuccess > 5 * 60_000L) {
            enqueueImmediateRefresh(context);
        }
    }

    /** Refresh immediately, bypassing the rate limit. Use for explicit user actions (e.g. language change). */
    public static void refreshNow(Context context) {
        enqueueImmediateRefresh(context);
    }

    /**
     * Returns a short warning to display on the widget, or null when everything is fine.
     * Prefers the background-location check (the silent-failure case) over the last error status.
     */
    private static String getWidgetWarning(Context context, SharedPreferences prefs) {
        boolean bgGranted = ContextCompat.checkSelfPermission(context, Manifest.permission.ACCESS_BACKGROUND_LOCATION)
                == PackageManager.PERMISSION_GRANTED;
        if (!bgGranted) {
            return "Allow location \u201cAll the time\u201d \u2014 tap to fix";
        }

        String statusRaw = prefs.getString("waqd.widget.lastStatus", null);
        if (statusRaw == null) return null;
        try {
            JSONObject status = new JSONObject(statusRaw);
            if (status.optBoolean("ok", false)) return null;
            switch (status.optString("code", "error")) {
                case "no_permission":
                    return "Allow location \u201cAll the time\u201d \u2014 tap to fix";
                case "no_gps":
                    return "Turn on location \u2014 tap to fix";
                case "no_key":
                case "no_base_url":
                    return "Log in to set up the widget";
                case "http":
                    return "Update failed \u2014 will retry";
                default:
                    return "Couldn't update \u2014 tap for details";
            }
        } catch (Exception e) {
            return null;
        }
    }

    private static void updateAppWidget(final Context context, final AppWidgetManager appWidgetManager, final int appWidgetId) {
        SharedPreferences prefs = context.getSharedPreferences("CapacitorStorage", Context.MODE_PRIVATE);

        String weatherDataRaw = prefs.getString("widget_weather_data", "{}");

        String tempStr = "--°";
        String locationStr = "Waiting...";
        String conditionStr = "---";
        String dailyTempStr = "--° / --°";
        String iconName = "";
        String widgetStyle = "simple";
        JSONArray forecastDataArr = null;

        try {
            JSONObject data = new JSONObject(weatherDataRaw);
            if (data.has("temp")) {
                tempStr = Math.round(data.getDouble("temp")) + "°";
            }
            if (data.has("locationName")) {
                locationStr = data.getString("locationName");
            }
            if (data.has("main")) {
                conditionStr = data.getString("main");
            }
            if (data.has("icon")) {
                iconName = data.getString("icon");
            }
            if (data.has("temp_min") && data.has("temp_max")) {
                dailyTempStr = Math.round(data.getDouble("temp_max")) + "° / " + Math.round(data.getDouble("temp_min")) + "°";
            }
            if (data.has("widget_style")) {
                widgetStyle = data.getString("widget_style");
            }
            if (data.has("forecast_3_days")) {
                forecastDataArr = data.getJSONArray("forecast_3_days");
            }
        } catch (Exception e) {
            e.printStackTrace();
        }

        // If the stored weather is stale, kick off a refresh (rate-limited internally)
        requestImmediateRefresh(context);

        Bundle options = appWidgetManager.getAppWidgetOptions(appWidgetId);
        int maxHeight = options.getInt(AppWidgetManager.OPTION_APPWIDGET_MAX_HEIGHT, 0);

        int layoutId = maxHeight >= 220 ? R.layout.widget_layout_large : R.layout.widget_layout;

        final RemoteViews views = new RemoteViews(context.getPackageName(), layoutId);

        views.setTextViewText(R.id.widget_temp, tempStr);
        views.setTextViewText(R.id.widget_location, locationStr);
        views.setTextViewText(R.id.widget_condition, conditionStr);
        views.setTextViewText(R.id.widget_daily_temp, dailyTempStr);

        // Tap: open app + enqueue immediate weather refresh
        Intent intent = new Intent(context, MainActivity.class);
        intent.putExtra("navigate_to", "/rest/weather?day=0");
        intent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_SINGLE_TOP);
        PendingIntent pendingIntent = PendingIntent.getActivity(context, 0, intent, PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
        views.setOnClickPendingIntent(R.id.widget_container, pendingIntent);

        // Tap clock icon: open clock app
        Intent clockIntent = new Intent(android.provider.AlarmClock.ACTION_SHOW_ALARMS);
        clockIntent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
        PendingIntent clockPendingIntent = PendingIntent.getActivity(context, 1, clockIntent, PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
        views.setOnClickPendingIntent(R.id.clock_section, clockPendingIntent);

        // Location switcher arrows (left = prev, right = next); hidden when there is
        // only the GPS location (no saved locations to switch to).
        int locationCount = prefs.getInt(PREF_LOCATION_COUNT, 1);
        int arrowsVisible = locationCount > 1 ? android.view.View.VISIBLE : android.view.View.GONE;
        views.setViewVisibility(R.id.widget_prev, arrowsVisible);
        views.setViewVisibility(R.id.widget_next, arrowsVisible);

        Intent prevIntent = new Intent(context, WeatherWidgetProvider.class);
        prevIntent.setAction(ACTION_LOCATION_PREV);
        PendingIntent prevPending = PendingIntent.getBroadcast(context, 3, prevIntent,
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
        views.setOnClickPendingIntent(R.id.widget_prev, prevPending);

        Intent nextIntent = new Intent(context, WeatherWidgetProvider.class);
        nextIntent.setAction(ACTION_LOCATION_NEXT);
        PendingIntent nextPending = PendingIntent.getBroadcast(context, 4, nextIntent,
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
        views.setOnClickPendingIntent(R.id.widget_next, nextPending);

        // Warning banner: shown on the widget itself when background refresh can't work,
        // so the user sees the problem without opening the app. Tapping it opens the app
        // home page, where the fix (e.g. "Allow all the time") lives.
        String warning = getWidgetWarning(context, prefs);
        if (warning != null) {
            views.setTextViewText(R.id.widget_warning, "\u26A0 " + warning);
            views.setViewVisibility(R.id.widget_warning, android.view.View.VISIBLE);

            Intent warnIntent = new Intent(context, MainActivity.class);
            warnIntent.putExtra("navigate_to", "/home");
            warnIntent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_SINGLE_TOP);
            PendingIntent warnPendingIntent = PendingIntent.getActivity(context, 2, warnIntent,
                    PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
            views.setOnClickPendingIntent(R.id.widget_warning, warnPendingIntent);
        } else {
            views.setViewVisibility(R.id.widget_warning, android.view.View.GONE);
        }

        if (layoutId == R.layout.widget_layout_large) {
            if ("forecast".equals(widgetStyle) && forecastDataArr != null && forecastDataArr.length() >= 3) {
                views.setViewVisibility(R.id.forecast_section, android.view.View.VISIBLE);
                try {
                    for (int i = 0; i < 3; i++) {
                        JSONObject dayObj = forecastDataArr.getJSONObject(i);
                        String fDay = dayObj.getString("day");
                        String fTempMin = String.valueOf(dayObj.getInt("temp_min"));
                        String fTempMax = String.valueOf(dayObj.getInt("temp_max"));
                        String fTempStr = fTempMax + "°\n" + fTempMin + "°";

                        int dayId = context.getResources().getIdentifier("forecast_day_" + (i+1), "id", context.getPackageName());
                        int tempId = context.getResources().getIdentifier("forecast_temp_" + (i+1), "id", context.getPackageName());
                        int cellId = context.getResources().getIdentifier("forecast_cell_" + (i+1), "id", context.getPackageName());

                        views.setTextViewText(dayId, fDay);
                        views.setTextViewText(tempId, fTempStr);

                        int appDayIndex = i + 1;
                        Intent dayIntent = new Intent(context, MainActivity.class);
                        dayIntent.putExtra("navigate_to", "/rest/weather?day=" + appDayIndex);
                        dayIntent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_SINGLE_TOP);
                        PendingIntent dayPendingIntent = PendingIntent.getActivity(context, 10 + i, dayIntent,
                                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
                        if (cellId != 0) {
                            views.setOnClickPendingIntent(cellId, dayPendingIntent);
                        }
                    }
                } catch (Exception e) {
                    e.printStackTrace();
                }
            } else {
                views.setViewVisibility(R.id.forecast_section, android.view.View.GONE);
            }
        }

        final JSONArray finalForecastData = forecastDataArr;
        final String finalWidgetStyle = widgetStyle;
        if (!iconName.isEmpty()) {
            final String mappedIconName = getGoogleIconName(iconName);
            executor.execute(() -> {
                try {
                    Bitmap mainBitmap = fetchIcon(context, mappedIconName);

                    Bitmap[] forecastBitmaps = new Bitmap[3];
                    if (layoutId == R.layout.widget_layout_large && "forecast".equals(finalWidgetStyle) && finalForecastData != null && finalForecastData.length() >= 3) {
                        for (int i = 0; i < 3; i++) {
                            String fIconName = finalForecastData.getJSONObject(i).getString("icon");
                            forecastBitmaps[i] = fetchIcon(context, getGoogleIconName(fIconName));
                        }
                    }

                    new Handler(Looper.getMainLooper()).post(() -> {
                        if (mainBitmap != null) {
                            views.setImageViewBitmap(R.id.widget_icon, mainBitmap);
                        }
                        if (layoutId == R.layout.widget_layout_large && "forecast".equals(finalWidgetStyle)) {
                            for (int i = 0; i < 3; i++) {
                                if (forecastBitmaps[i] != null) {
                                    int iconId = context.getResources().getIdentifier("forecast_icon_" + (i+1), "id", context.getPackageName());
                                    views.setImageViewBitmap(iconId, forecastBitmaps[i]);
                                }
                            }
                        }
                        appWidgetManager.updateAppWidget(appWidgetId, views);
                    });
                } catch (Exception e) {
                    e.printStackTrace();
                }
            });
        } else {
            appWidgetManager.updateAppWidget(appWidgetId, views);
        }
    }

    private static Bitmap fetchIcon(Context context, String mappedIconName) throws Exception {
        String cacheKey = "icon_" + mappedIconName + ".png";
        File cacheFile = new File(context.getCacheDir(), cacheKey);
        Bitmap bitmap = null;

        if (cacheFile.exists()) {
            bitmap = BitmapFactory.decodeFile(cacheFile.getAbsolutePath());
        }

        if (bitmap == null) {
            String finalIconUrl = BASE_URL + "/static/weather_icons/google/v0/light/" + mappedIconName + ".svg";
            URL url = new URL(finalIconUrl);
            HttpURLConnection connection = (HttpURLConnection) url.openConnection();
            connection.setConnectTimeout(5000);
            connection.setReadTimeout(5000);
            connection.setDoInput(true);
            connection.connect();
            InputStream input = connection.getInputStream();

            SVG svg = SVG.getFromInputStream(input);
            if (svg != null) {
                float width = (svg.getDocumentWidth() != -1) ? svg.getDocumentWidth() : 192f;
                float height = (svg.getDocumentHeight() != -1) ? svg.getDocumentHeight() : 192f;

                bitmap = Bitmap.createBitmap((int) width, (int) height, Bitmap.Config.ARGB_8888);
                Canvas canvas = new Canvas(bitmap);
                svg.renderToCanvas(canvas);

                try (FileOutputStream out = new FileOutputStream(cacheFile)) {
                    bitmap.compress(Bitmap.CompressFormat.PNG, 100, out);
                }
            }
            input.close();
        }
        return bitmap;
    }

    private static String getGoogleIconName(String iconName) {
        if (iconName == null) return "not_available";

        switch (iconName) {
            case "wi-day-sunny": return "clear_day";
            case "wi-night-clear": return "clear_night";
            case "wi-day-sunny-overcast": return "partly_cloudy_day";
            case "wi-night-alt-partly-cloudy": return "partly_cloudy_night";
            case "wi-day-cloudy": return "mostly_cloudy_day";
            case "wi-night-alt-cloudy": return "mostly_cloudy_night";
            case "wi-cloudy": return "cloudy";
            case "wi-day-fog": case "wi-night-fog": case "wi-fog": return "haze_fog_dust_smoke";
            case "wi-day-sprinkle": case "wi-night-alt-sprinkle": return "drizzle";
            case "wi-day-sleet": case "wi-night-alt-sleet": case "wi-day-hail": case "wi-night-alt-hail": case "wi-night-alt-snow-thunderstorm": return "sleet_hail";
            case "wi-day-rain-mix": case "wi-night-alt-rain-mix": return "mixed_rain_hail_sleet";
            case "wi-day-rain": case "wi-night-alt-rain": return "heavy_rain";
            case "wi-day-snow": case "wi-night-alt-snow": return "heavy_snow";
            case "wi-day-showers": return "scattered_showers_day";
            case "wi-night-alt-showers": return "scattered_showers_night";
            case "wi-day-thunderstorm": return "isolated_scattered_tstorms_day";
            case "wi-night-alt-thunderstorm": return "isolated_scattered_tstorms_night";
            case "wi-day-lightning": case "wi-night-alt-lightning": return "isolated_tstorms";
            case "wi-smoke": case "wi-dust": return "haze_fog_dust_smoke";
            case "wi-tornado": case "wi-hurricane": return "tropical_storm_hurricane";
            case "wi-snowflake-cold": return "very_cold";
            case "wi-hot": return "very_hot";
            case "wi-strong-wind": case "wi-windy": case "wi-day-windy": return "windy_breezy";
            default:
                if (iconName.contains("thunderstorm")) return "strong_tstorms";
                if (iconName.contains("snow")) return "snow_showers_snow";
                if (iconName.contains("rain")) return "showers_rain";
                if (iconName.contains("cloud")) return "cloudy";
                return "not_available";
        }
    }
}
