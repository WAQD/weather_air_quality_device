package com.waqd.app;

import android.app.AlarmManager;
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
import android.graphics.Color;
import android.graphics.Paint;
import android.graphics.PorterDuff;
import android.graphics.PorterDuffXfermode;
import android.graphics.PorterDuffColorFilter;
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
import java.io.File;
import java.io.FileOutputStream;

public class WeatherWidgetProvider extends AppWidgetProvider {

    private static final ExecutorService executor = Executors.newSingleThreadExecutor();
    private static final String BASE_URL = "https://waqd.de";
    private static final String ACTION_WEATHER_UPDATE = "com.waqd.app.WEATHER_UPDATE";

    @Override
    public void onUpdate(Context context, AppWidgetManager appWidgetManager, int[] appWidgetIds) {
        android.util.Log.d("WeatherWidget", "onUpdate called for " + appWidgetIds.length + " widgets");
        for (int appWidgetId : appWidgetIds) {
            updateAppWidget(context, appWidgetManager, appWidgetId);
        }
        scheduleWeatherUpdate(context);
    }

    @Override
    public void onEnabled(Context context) {
        super.onEnabled(context);
        android.util.Log.d("WeatherWidget", "onEnabled - Widget added to home screen");
        scheduleWeatherUpdate(context);
    }

    @Override
    public void onDisabled(Context context) {
        super.onDisabled(context);
        android.util.Log.d("WeatherWidget", "onDisabled - Last widget removed from home screen");
        cancelWeatherUpdate(context);
    }

    @Override
    public void onAppWidgetOptionsChanged(Context context, AppWidgetManager appWidgetManager, int appWidgetId, Bundle newOptions) {
        updateAppWidget(context, appWidgetManager, appWidgetId);
        super.onAppWidgetOptionsChanged(context, appWidgetManager, appWidgetId, newOptions);
    }

    private static final String ACTION_GPS_WIDGET_REFRESH = "com.waqd.app.GPS_WIDGET_REFRESH";
    private static final String PREF_LOCATION_MODE_KEY = "waqd.website.locationMode";

    @Override
    public void onReceive(Context context, Intent intent) {
        super.onReceive(context, intent);
        String action = intent.getAction();
        android.util.Log.d("WeatherWidget", "onReceive called with action: " + action);
        
        if (ACTION_WEATHER_UPDATE.equals(action)) {
            android.util.Log.d("WeatherWidget", "Periodic update triggered");
            AppWidgetManager mgr = AppWidgetManager.getInstance(context);
            int[] ids = mgr.getAppWidgetIds(new ComponentName(context, WeatherWidgetProvider.class));
            android.util.Log.d("WeatherWidget", "Found " + ids.length + " widget instances");
            
            // If in GPS mode, trigger background GPS refresh before updating widget
            triggerGpsRefreshIfNeeded(context);
            
            // Update all widget instances
            for (int id : ids) {
                updateAppWidget(context, mgr, id);
            }
            
            // Reschedule next alarm (interval depends on GPS/Home mode)
            scheduleWeatherUpdate(context);
        }
    }

    /**
     * Triggers a GPS weather refresh when GPS mode is active.
     * Called every 30 minutes by the periodic alarm (ACTION_WEATHER_UPDATE).
     *
     * Strategy (layered):
     *  1. If the app is in the foreground, the existing broadcast reaches MainActivity
     *     which dispatches the JS event to the running Vue app — fast path.
     *  2. If the app is backgrounded or killed, dispatch the @capacitor/background-runner
     *     task which runs the GPS fetch in a V8 isolate via WorkManager.
     *
     * Both paths write to CapacitorStorage "widget_weather_data", so the
     * widget update (called immediately after this) will show the fresh data.
     */
    private static void triggerGpsRefreshIfNeeded(Context context) {
        SharedPreferences prefs = context.getSharedPreferences("CapacitorStorage", Context.MODE_PRIVATE);
        String locationMode = prefs.getString(PREF_LOCATION_MODE_KEY, "home");
        android.util.Log.d("WeatherWidget", "Checking location mode: " + locationMode);
        if (!"gps".equals(locationMode)) {
            android.util.Log.d("WeatherWidget", "Not in GPS mode, using cached Home data");
            return;
        }

        android.util.Log.d("WeatherWidget", "GPS mode active — triggering background GPS refresh");

        // Path 1: broadcast to foreground app (fast; no-op if app is not running)
        Intent gpsIntent = new Intent(ACTION_GPS_WIDGET_REFRESH);
        gpsIntent.setPackage(context.getPackageName());
        context.sendBroadcast(gpsIntent);
        android.util.Log.d("WeatherWidget", "Foreground broadcast sent");

        // Path 2: background runner via WorkManager (works when app is killed)
        dispatchBackgroundRunnerTask(context);
    }

    /**
     * Enqueues a one-shot WorkManager job that executes the 'gpsWeatherRefresh'
     * event in the @capacitor/background-runner V8 isolate.
     * The runner reads GPS coords, fetches weather, and writes to CapacitorStorage.
     */
    private static void dispatchBackgroundRunnerTask(Context context) {
        try {
            androidx.work.Data inputData = new androidx.work.Data.Builder()
                .putString("event", "gpsWeatherRefresh")
                .putString("label", "com.waqd.app.background")
                .putString("src", "background-runner.js")
                .build();

            androidx.work.OneTimeWorkRequest workRequest =
                new androidx.work.OneTimeWorkRequest.Builder(
                    io.ionic.backgroundrunner.plugin.RunnerWorker.class)
                .setInputData(inputData)
                .build();

            androidx.work.WorkManager.getInstance(context).enqueue(workRequest);
            android.util.Log.d("WeatherWidget", "BackgroundRunner WorkManager task enqueued");
        } catch (Exception e) {
            android.util.Log.e("WeatherWidget", "Failed to dispatch BackgroundRunner task: " + e.getMessage());
        }
    }

    private static void scheduleWeatherUpdate(Context context) {
        AlarmManager alarmManager = (AlarmManager) context.getSystemService(Context.ALARM_SERVICE);
        if (alarmManager == null) return;
        
        // Check if GPS mode is active to determine update frequency
        SharedPreferences prefs = context.getSharedPreferences("CapacitorStorage", Context.MODE_PRIVATE);
        String locationMode = prefs.getString(PREF_LOCATION_MODE_KEY, "home");
        
        // GPS mode: 5 minute interval for fresh location data
        // Home mode: 30 minute interval (weather doesn't change that fast)
        long intervalMillis = "gps".equals(locationMode) ? 5 * 60 * 1000L : 30 * 60 * 1000L;
        
        Intent intent = new Intent(context, WeatherWidgetProvider.class);
        intent.setAction(ACTION_WEATHER_UPDATE);
        PendingIntent pi = PendingIntent.getBroadcast(context, 0, intent,
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
        
        // Use setAndAllowWhileIdle for background updates even in Doze mode
        long triggerAtMillis = System.currentTimeMillis() + intervalMillis;
        alarmManager.setAndAllowWhileIdle(AlarmManager.RTC, triggerAtMillis, pi);
        
        android.util.Log.d("WeatherWidget", "Scheduled next update in " + (intervalMillis / 60000) + " minutes (mode: " + locationMode + ")");
    }

    private static void cancelWeatherUpdate(Context context) {
        AlarmManager alarmManager = (AlarmManager) context.getSystemService(Context.ALARM_SERVICE);
        if (alarmManager == null) return;
        Intent intent = new Intent(context, WeatherWidgetProvider.class);
        intent.setAction(ACTION_WEATHER_UPDATE);
        PendingIntent pi = PendingIntent.getBroadcast(context, 0, intent,
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
        alarmManager.cancel(pi);
    }
    
    private static void updateAppWidget(final Context context, final AppWidgetManager appWidgetManager, final int appWidgetId) {
        // Read data from Capacitor preferences
        SharedPreferences prefs = context.getSharedPreferences("CapacitorStorage", Context.MODE_PRIVATE);
        
        // Fallback for APK builds where storage name might differ
        if (!prefs.contains("widget_weather_data")) {
            prefs = context.getSharedPreferences(context.getPackageName() + "_preferences", Context.MODE_PRIVATE);
        }

        String weatherDataRaw = prefs.getString("widget_weather_data", "{}");
        android.util.Log.d("WeatherWidget", "Raw data from prefs: " + weatherDataRaw);

        String tempStr = "--°";
        String locationStr = "Waiting...";
        String conditionStr = "---";
        String dailyTempStr = "--° / --°";
        String updateStr = "Updated: --:--";
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
            if (data.has("updateTime")) {
                long timeMs = data.getLong("updateTime");
                SimpleDateFormat sdf = new SimpleDateFormat("HH:mm", Locale.getDefault());
                updateStr = "Updated: " + sdf.format(new Date(timeMs));
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

        Bundle options = appWidgetManager.getAppWidgetOptions(appWidgetId);
        int maxHeight = options.getInt(AppWidgetManager.OPTION_APPWIDGET_MAX_HEIGHT, 0);

        // Portrait height (maxHeight):
        // 5x2 is ~183dp
        // 5x3 is ~280dp
        // Threshold set to 220dp to cleanly split the difference
        int layoutId = maxHeight >= 220 ? R.layout.widget_layout_large : R.layout.widget_layout;
        
        final RemoteViews views = new RemoteViews(context.getPackageName(), layoutId);

        // Update Weather data
        views.setTextViewText(R.id.widget_temp, tempStr);
        views.setTextViewText(R.id.widget_location, locationStr);
        views.setTextViewText(R.id.widget_condition, conditionStr);
        views.setTextViewText(R.id.widget_daily_temp, dailyTempStr);

        // Click to open weather page in app (scrolled to forecast)
        Intent intent = new Intent(context, MainActivity.class);
        intent.putExtra("navigate_to", "/rest/weather?day=0");
        intent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_SINGLE_TOP);
        PendingIntent pendingIntent = PendingIntent.getActivity(context, 0, intent, PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
        views.setOnClickPendingIntent(R.id.widget_container, pendingIntent);

        // Click to open clock app
        Intent clockIntent = new Intent(android.provider.AlarmClock.ACTION_SHOW_ALARMS);
        clockIntent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
        PendingIntent clockPendingIntent = PendingIntent.getActivity(context, 1, clockIntent, PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
        views.setOnClickPendingIntent(R.id.clock_section, clockPendingIntent);

        // Show/Hide forecast section
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

                        // forecast days in widget = tomorrow onwards (index 1, 2, 3 in app forecast)
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

        // Fetch Icons Async with Caching
        final JSONArray finalForecastData = forecastDataArr;
        final String finalWidgetStyle = widgetStyle;
        if (!iconName.isEmpty()) {
            final String mappedIconName = getGoogleIconName(iconName);
            executor.execute(() -> {
                try {
                    Bitmap mainBitmap = fetchIcon(context, mappedIconName);
                    
                    // Fetch forecast bitmaps
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

                // Cache the bitmap as PNG
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