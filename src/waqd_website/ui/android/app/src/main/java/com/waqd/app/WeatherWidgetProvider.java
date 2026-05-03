package com.waqd.app;

import android.app.PendingIntent;
import android.appwidget.AppWidgetManager;
import android.appwidget.AppWidgetProvider;
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
    private static final String BASE_URL = "http://192.168.178.57:8000"; // Match capacitor.config.ts

    @Override
    public void onUpdate(Context context, AppWidgetManager appWidgetManager, int[] appWidgetIds) {
        for (int appWidgetId : appWidgetIds) {
            updateAppWidget(context, appWidgetManager, appWidgetId);
        }
    }

    private static void updateAppWidget(final Context context, final AppWidgetManager appWidgetManager, final int appWidgetId) {
        // Read data from Capacitor preferences
        SharedPreferences prefs = context.getSharedPreferences("CapacitorStorage", Context.MODE_PRIVATE);
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

        final RemoteViews views = new RemoteViews(context.getPackageName(), R.layout.widget_layout);

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
        views.setTextViewText(R.id.widget_update_time, updateStr);

        // Click to open app
        Intent intent = new Intent(context, MainActivity.class);
        PendingIntent pendingIntent = PendingIntent.getActivity(context, 0, intent, PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
        views.setOnClickPendingIntent(R.id.widget_container, pendingIntent);

        // Fetch Icon Async (Option B)
        if (!iconName.isEmpty()) {
            final String finalIconUrl = BASE_URL + "/static/weather_icons/" + iconName + ".svg";
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

                        // Create grey-tinted bitmap (preserve alpha)
                        Bitmap tintedBitmap = Bitmap.createBitmap(bitmap.getWidth(), bitmap.getHeight(), Bitmap.Config.ARGB_8888);
                        Canvas tintedCanvas = new Canvas(tintedBitmap);
                        tintedCanvas.drawColor(Color.parseColor("#9f9f9f"));
                        Paint maskPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
                        maskPaint.setXfermode(new PorterDuffXfermode(PorterDuff.Mode.DST_IN));
                        tintedCanvas.drawBitmap(bitmap, 0, 0, maskPaint);
                        maskPaint.setXfermode(null);

                        final Bitmap finalBitmap = tintedBitmap;

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
}