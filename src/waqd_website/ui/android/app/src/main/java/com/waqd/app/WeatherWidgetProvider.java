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
import java.io.InputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Locale;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public class WeatherWidgetProvider extends AppWidgetProvider {

    private static final ExecutorService executor = Executors.newSingleThreadExecutor();
    private static final String BASE_URL = "https://waqd.de";
    private static final String ACTION_CLOCK_TICK = "com.waqd.app.CLOCK_TICK";

    @Override
    public void onUpdate(Context context, AppWidgetManager appWidgetManager, int[] appWidgetIds) {
        for (int appWidgetId : appWidgetIds) {
            updateAppWidget(context, appWidgetManager, appWidgetId);
        }
        scheduleClockTick(context);
    }

    @Override
    public void onEnabled(Context context) {
        super.onEnabled(context);
        scheduleClockTick(context);
    }

    @Override
    public void onDisabled(Context context) {
        super.onDisabled(context);
        cancelClockTick(context);
    }

    @Override
    public void onAppWidgetOptionsChanged(Context context, AppWidgetManager appWidgetManager, int appWidgetId, Bundle newOptions) {
        updateAppWidget(context, appWidgetManager, appWidgetId);
        super.onAppWidgetOptionsChanged(context, appWidgetManager, appWidgetId, newOptions);
    }

    @Override
    public void onReceive(Context context, Intent intent) {
        super.onReceive(context, intent);
        if (ACTION_CLOCK_TICK.equals(intent.getAction())) {
            AppWidgetManager mgr = AppWidgetManager.getInstance(context);
            int[] ids = mgr.getAppWidgetIds(new ComponentName(context, WeatherWidgetProvider.class));
            for (int id : ids) {
                updateAppWidget(context, mgr, id);
            }
            scheduleClockTick(context); // reschedule for next minute
        }
    }

    private static void scheduleClockTick(Context context) {
        AlarmManager alarmManager = (AlarmManager) context.getSystemService(Context.ALARM_SERVICE);
        if (alarmManager == null) return;
        Intent intent = new Intent(context, WeatherWidgetProvider.class);
        intent.setAction(ACTION_CLOCK_TICK);
        PendingIntent pi = PendingIntent.getBroadcast(context, 0, intent,
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
        // Fire at the top of the next minute - use set() which requires no special permission
        long now = System.currentTimeMillis();
        long nextMinute = now + (60_000L - (now % 60_000L));
        alarmManager.set(AlarmManager.RTC, nextMinute, pi);
    }

    private static void cancelClockTick(Context context) {
        AlarmManager alarmManager = (AlarmManager) context.getSystemService(Context.ALARM_SERVICE);
        if (alarmManager == null) return;
        Intent intent = new Intent(context, WeatherWidgetProvider.class);
        intent.setAction(ACTION_CLOCK_TICK);
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

        // Update Clock panels
        SimpleDateFormat hourFormat = new SimpleDateFormat("HH", Locale.getDefault());
        SimpleDateFormat minuteFormat = new SimpleDateFormat("mm", Locale.getDefault());
        String hour = hourFormat.format(new Date());
        String minute = minuteFormat.format(new Date());
        
        views.setTextViewText(R.id.widget_clock_hour, hour);
        views.setTextViewText(R.id.widget_clock_minute, minute);

        // Update Weather data
        views.setTextViewText(R.id.widget_temp, tempStr);
        views.setTextViewText(R.id.widget_location, locationStr);
        views.setTextViewText(R.id.widget_condition, conditionStr);
        views.setTextViewText(R.id.widget_daily_temp, dailyTempStr);

        // Click to open app
        Intent intent = new Intent(context, MainActivity.class);
        PendingIntent pendingIntent = PendingIntent.getActivity(context, 0, intent, PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
        views.setOnClickPendingIntent(R.id.widget_container, pendingIntent);

        // Fetch Icon Async (Option B)
        if (!iconName.isEmpty()) {
            final String mappedIconName = getGoogleIconName(iconName);
            final String finalIconUrl = BASE_URL + "/static/weather_icons/google/v0/light/" + mappedIconName + ".svg";
            executor.execute(() -> {
                try {
                    URL url = new URL(finalIconUrl);
                    HttpURLConnection connection = (HttpURLConnection) url.openConnection();
                    connection.setDoInput(true);
                    connection.connect();
                    InputStream input = connection.getInputStream();
                    
                    SVG svg = SVG.getFromInputStream(input);
                    if (svg != null) {
                        // Create a bitmap to render the SVG into
                        // Using 192px for a sharp result on widget
                        float width = (svg.getDocumentWidth() != -1) ? svg.getDocumentWidth() : 192f;
                        float height = (svg.getDocumentHeight() != -1) ? svg.getDocumentHeight() : 192f;
                        
                        final Bitmap bitmap = Bitmap.createBitmap((int) width, (int) height, Bitmap.Config.ARGB_8888);
                        Canvas canvas = new Canvas(bitmap);
                        
                        // Render SVG onto bitmap
                        svg.renderToCanvas(canvas);

                        final Bitmap finalBitmap = bitmap;

                        new Handler(Looper.getMainLooper()).post(() -> {
                            views.setImageViewBitmap(R.id.widget_icon, finalBitmap);
                            appWidgetManager.updateAppWidget(appWidgetId, views);
                        });
                    }
                } catch (Exception e) {
                    e.printStackTrace();
                }
            });
        }

        appWidgetManager.updateAppWidget(appWidgetId, views);
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