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
    public static final String PREF_LAST_SUCCESS = WidgetContract.PREF_LAST_SUCCESS;
    /** Persisted selected location index and total count for the location switcher. */
    public static final String PREF_SELECTED_INDEX = WidgetContract.PREF_SELECTED_INDEX;
    public static final String PREF_LOCATION_COUNT = WidgetContract.PREF_LOCATION_COUNT;
    /** "gps" = GPS only (no arrows); "selectable" = arrows cycle GPS + saved locations. */
    public static final String PREF_LOCATION_MODE = WidgetContract.PREF_LOCATION_MODE;
    private static final String ACTION_LOCATION_PREV = "com.waqd.app.action.LOCATION_PREV";
    private static final String ACTION_LOCATION_NEXT = "com.waqd.app.action.LOCATION_NEXT";
    /** Widgets at least this tall (dp) get the large (forecast) layout. */
    private static final int LAYOUT_LARGE_MIN_HEIGHT_DP = 220;

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
        SharedPreferences prefs = context.getSharedPreferences(WidgetContract.PREFS_NAME, Context.MODE_PRIVATE);
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
        SharedPreferences prefs = context.getSharedPreferences(WidgetContract.PREFS_NAME, Context.MODE_PRIVATE);
        long lastSuccess = prefs.getLong(PREF_LAST_SUCCESS, 0);
        if (System.currentTimeMillis() - lastSuccess > 5 * 60_000L) {
            enqueueImmediateRefresh(context);
        }
    }

    /** Refresh immediately, bypassing the rate limit. Use for explicit user actions (e.g. language change). */
    public static void refreshNow(Context context) {
        enqueueImmediateRefresh(context);
    }

    /** Updates the RemoteViews of all placed widgets immediately with current local preferences without a network call. */
    public static void updateAllWidgets(Context context) {
        AppWidgetManager appWidgetManager = AppWidgetManager.getInstance(context);
        ComponentName provider = new ComponentName(context, WeatherWidgetProvider.class);
        int[] appWidgetIds = appWidgetManager.getAppWidgetIds(provider);
        for (int appWidgetId : appWidgetIds) {
            updateAppWidget(context, appWidgetManager, appWidgetId);
        }
    }

    /**
     * Returns a short warning to display on the widget, or null when everything is fine.
     * Prefers the background-location check (the silent-failure case) over the last error status.
     */
    private static String getWidgetWarning(Context context, SharedPreferences prefs) {
        boolean bgGranted = ContextCompat.checkSelfPermission(context, Manifest.permission.ACCESS_BACKGROUND_LOCATION)
                == PackageManager.PERMISSION_GRANTED;
        if (!bgGranted) {
            return context.getString(R.string.widget_warn_no_permission);
        }

        String statusRaw = prefs.getString(WidgetContract.PREF_STATUS, null);
        if (statusRaw == null) return null;
        try {
            JSONObject status = new JSONObject(statusRaw);
            if (status.optBoolean("ok", false)) return null;
            switch (status.optString("code", "error")) {
                case "no_permission":
                    // Unreachable in practice: bgGranted is checked above, so a stored
                    // no_permission status is stale and should not warn.
                    return null;
                case "no_gps":
                    return context.getString(R.string.widget_warn_no_gps);
                case "no_key":
                case "no_base_url":
                    return context.getString(R.string.widget_warn_no_key);
                case "http":
                    return context.getString(R.string.widget_warn_http);
                default:
                    return context.getString(R.string.widget_warn_generic);
            }
        } catch (Exception e) {
            return null;
        }
    }

    private static void updateAppWidget(final Context context, final AppWidgetManager appWidgetManager, final int appWidgetId) {
        SharedPreferences prefs = context.getSharedPreferences(WidgetContract.PREFS_NAME, Context.MODE_PRIVATE);

        WidgetData data = parseWidgetData(prefs);

        // If the stored weather is stale, kick off a refresh (rate-limited internally)
        requestImmediateRefresh(context);

        Bundle options = appWidgetManager.getAppWidgetOptions(appWidgetId);
        int maxHeight = options.getInt(AppWidgetManager.OPTION_APPWIDGET_MAX_HEIGHT, 0);
        boolean isLargeLayout = maxHeight >= LAYOUT_LARGE_MIN_HEIGHT_DP;
        int layoutId = isLargeLayout ? R.layout.widget_layout_large : R.layout.widget_layout;

        final RemoteViews views = new RemoteViews(context.getPackageName(), layoutId);
        bindTexts(views, data);
        bindTapTargets(context, views);
        bindLocationSwitcher(context, views, prefs);
        bindWarningBanner(context, views, prefs);

        if (isLargeLayout) {
            bindForecastSection(context, views, data);
        }

        loadIconsAsync(context, appWidgetManager, appWidgetId, views, layoutId, data);
    }

    /** Parses the cached widget weather JSON; missing fields fall back to placeholders. */
    private static WidgetData parseWidgetData(SharedPreferences prefs) {
        WidgetData data = new WidgetData();
        try {
            JSONObject json = new JSONObject(prefs.getString(WidgetContract.PREF_WEATHER_DATA, "{}"));
            if (json.has("temp")) {
                data.tempStr = Math.round(json.getDouble("temp")) + "°";
            }
            if (json.has("locationName")) {
                data.locationStr = json.getString("locationName");
            }
            if (json.has("main")) {
                data.conditionStr = json.getString("main");
            }
            if (json.has("icon")) {
                data.iconName = json.getString("icon");
            }
            if (json.has("temp_min") && json.has("temp_max")) {
                data.dailyTempStr = Math.round(json.getDouble("temp_max")) + "° / " + Math.round(json.getDouble("temp_min")) + "°";
            }
            if (json.has("widget_style")) {
                data.widgetStyle = json.getString("widget_style");
            }
            if (json.has("forecast_3_days")) {
                data.forecastArr = json.getJSONArray("forecast_3_days");
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
        return data;
    }

    private static void bindTexts(RemoteViews views, WidgetData data) {
        views.setTextViewText(R.id.widget_temp, data.tempStr);
        views.setTextViewText(R.id.widget_location, data.locationStr);
        views.setTextViewText(R.id.widget_condition, data.conditionStr);
        views.setTextViewText(R.id.widget_daily_temp, data.dailyTempStr);
    }

    /** Tap targets: main area opens the app's weather page, clock icon opens the clock app. */
    private static void bindTapTargets(Context context, RemoteViews views) {
        Intent intent = new Intent(context, MainActivity.class);
        intent.putExtra("navigate_to", "/rest/weather?day=0");
        intent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_SINGLE_TOP);
        PendingIntent pendingIntent = PendingIntent.getActivity(context, 0, intent, PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
        views.setOnClickPendingIntent(R.id.widget_container, pendingIntent);

        Intent clockIntent = new Intent(android.provider.AlarmClock.ACTION_SHOW_ALARMS);
        clockIntent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
        PendingIntent clockPendingIntent = PendingIntent.getActivity(context, 1, clockIntent, PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
        views.setOnClickPendingIntent(R.id.clock_section, clockPendingIntent);
    }

    /** Location switcher arrows and GPS label. */
    private static void bindLocationSwitcher(Context context, RemoteViews views, SharedPreferences prefs) {
        int locationCount = prefs.getInt(PREF_LOCATION_COUNT, 1);
        boolean arrowsEnabled = !"gps".equals(prefs.getString(PREF_LOCATION_MODE, "selectable"));
        int arrowsVisible = (arrowsEnabled && locationCount > 1) ? android.view.View.VISIBLE : android.view.View.GONE;
        views.setViewVisibility(R.id.widget_prev, arrowsVisible);
        views.setViewVisibility(R.id.widget_next, arrowsVisible);

        // GPS label: shown when the selected location is the device GPS (index 0).
        int selectedIndex = prefs.getInt(PREF_SELECTED_INDEX, 0);
        if (selectedIndex == 0) {
            views.setTextViewText(R.id.widget_gps_label, "GPS");
            views.setViewVisibility(R.id.widget_gps_label, android.view.View.VISIBLE);
        } else {
            views.setViewVisibility(R.id.widget_gps_label, android.view.View.GONE);
        }

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
    }

    /**
     * Warning banner: shown on the widget itself when background refresh can't work,
     * so the user sees the problem without opening the app. Tapping it opens the app
     * home page, where the fix (e.g. "Allow all the time") lives.
     */
    private static void bindWarningBanner(Context context, RemoteViews views, SharedPreferences prefs) {
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
    }

    /** Forecast cells on the large layout (only when style is "forecast" and data is present). */
    private static void bindForecastSection(Context context, RemoteViews views, WidgetData data) {
        if (!"forecast".equals(data.widgetStyle) || data.forecastArr == null || data.forecastArr.length() < 3) {
            views.setViewVisibility(R.id.forecast_section, android.view.View.GONE);
            return;
        }
        views.setViewVisibility(R.id.forecast_section, android.view.View.VISIBLE);
        try {
            for (int i = 0; i < 3; i++) {
                JSONObject dayObj = data.forecastArr.getJSONObject(i);
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
    }

    /**
     * Downloads (or loads from cache) the main and forecast icons off the main thread,
     * then applies them to the RemoteViews and pushes the update.
     */
    private static void loadIconsAsync(final Context context, final AppWidgetManager appWidgetManager,
                                       final int appWidgetId, final RemoteViews views, final int layoutId,
                                       final WidgetData data) {
        if (data.iconName.isEmpty()) {
            appWidgetManager.updateAppWidget(appWidgetId, views);
            return;
        }
        executor.execute(() -> {
            try {
                Bitmap mainBitmap = fetchIcon(context, getGoogleIconName(data.iconName));

                Bitmap[] forecastBitmaps = new Bitmap[3];
                boolean showForecast = layoutId == R.layout.widget_layout_large
                        && "forecast".equals(data.widgetStyle)
                        && data.forecastArr != null && data.forecastArr.length() >= 3;
                if (showForecast) {
                    for (int i = 0; i < 3; i++) {
                        String fIconName = data.forecastArr.getJSONObject(i).getString("icon");
                        forecastBitmaps[i] = fetchIcon(context, getGoogleIconName(fIconName));
                    }
                }

                new Handler(Looper.getMainLooper()).post(() -> {
                    if (mainBitmap != null) {
                        views.setImageViewBitmap(R.id.widget_icon, mainBitmap);
                    }
                    if (showForecast) {
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
    }

    /** Mutable holder for the parsed widget weather data. */
    private static final class WidgetData {
        String tempStr = "--°";
        String locationStr = "Waiting…";
        String conditionStr = "---";
        String dailyTempStr = "--° / --°";
        String iconName = "";
        String widgetStyle = "simple";
        JSONArray forecastArr = null;
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
