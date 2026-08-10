package com.waqd.app;

import android.app.PendingIntent;
import android.appwidget.AppWidgetManager;
import android.appwidget.AppWidgetProvider;
import android.content.ComponentName;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
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
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Locale;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;
import java.io.File;
import java.io.FileOutputStream;

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

    private static void updateAppWidget(final Context context, final AppWidgetManager appWidgetManager, final int appWidgetId) {
        SharedPreferences prefs = context.getSharedPreferences("CapacitorStorage", Context.MODE_PRIVATE);
        if (!prefs.contains("widget_weather_data")) {
            prefs = context.getSharedPreferences(context.getPackageName() + "_preferences", Context.MODE_PRIVATE);
        }

        String weatherDataRaw = prefs.getString("widget_weather_data", "{}");

        String tempStr = "--°";
        String locationStr = "Waiting...";
        String conditionStr = "---";
        String dailyTempStr = "--° / --°";
        String iconName = "";
        String widgetStyle = "simple";
        JSONArray forecastDataArr = null;
        long updateTime = 0;

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
            if (data.has("updateTime")) {
                updateTime = data.getLong("updateTime");
            }
        } catch (Exception e) {
            e.printStackTrace();
        }

        // If weather data is stale (> 1 hour old), trigger a refresh on background thread
        final long finalUpdateTime = updateTime;
        if (finalUpdateTime > 0 && (System.currentTimeMillis() - finalUpdateTime) > 3600_000L) {
            executor.execute(() -> {
                try {
                    // Double-check staleness after delay to avoid race with in-progress refresh
                    Thread.sleep(100);
                    enqueueImmediateRefresh(context);
                } catch (Exception ignored) {}
            });
        }

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
