package com.waqd.app;

import android.appwidget.AppWidgetManager;
import android.content.ComponentName;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.util.Log;
import com.getcapacitor.BridgeActivity;
import java.net.URLEncoder;

public class MainActivity extends BridgeActivity {
    private SharedPreferences.OnSharedPreferenceChangeListener prefListener;
    private String pendingNavigatePath = null;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        Intent launchIntent = getIntent();
        if (launchIntent != null && launchIntent.hasExtra("navigate_to")) {
            pendingNavigatePath = launchIntent.getStringExtra("navigate_to");
        }

        SharedPreferences prefs = getSharedPreferences("CapacitorStorage", Context.MODE_PRIVATE);
        prefListener = (sharedPreferences, key) -> {
            if ("widget_weather_data".equals(key)) {
                String val = sharedPreferences.getString(key, "");
                Log.d("WeatherWidget", "MainActivity: widget_weather_data changed! Content: " + val);

                Intent intent = new Intent(this, WeatherWidgetProvider.class);
                intent.setAction(AppWidgetManager.ACTION_APPWIDGET_UPDATE);
                int[] ids = AppWidgetManager.getInstance(getApplication()).getAppWidgetIds(new ComponentName(getApplication(), WeatherWidgetProvider.class));
                intent.putExtra(AppWidgetManager.EXTRA_APPWIDGET_IDS, ids);
                sendBroadcast(intent);
            }
        };
        prefs.registerOnSharedPreferenceChangeListener(prefListener);
    }

    @Override
    protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        setIntent(intent);
        if (intent != null && intent.hasExtra("navigate_to")) {
            String path = intent.getStringExtra("navigate_to");
            if (path != null) {
                new Handler(Looper.getMainLooper()).postDelayed(() -> dispatchNavigation(path), 300);
            }
        }
    }

    @Override
    public void onResume() {
        super.onResume();
        if (pendingNavigatePath != null) {
            final String path = pendingNavigatePath;
            pendingNavigatePath = null;
            new Handler(Looper.getMainLooper()).postDelayed(() -> dispatchNavigation(path), 500);
        }
    }

    private void dispatchNavigation(String path) {
        if (getBridge() == null || getBridge().getWebView() == null) return;

        SharedPreferences prefs = getSharedPreferences("CapacitorStorage", Context.MODE_PRIVATE);
        String gpsCoords = prefs.getString("waqd.widget.lastGpsCoords", null);
        if (gpsCoords != null && !gpsCoords.isEmpty()) {
            String[] parts = gpsCoords.split(",");
            if (parts.length == 2) {
                try {
                    String gpsName = prefs.getString("waqd.widget.lastGpsName", "GPS Location");
                    String encodedName = URLEncoder.encode(gpsName != null ? gpsName : "GPS Location", "UTF-8");
                    path += (path.contains("?") ? "&" : "?") + "gps_lat=" + parts[0] + "&gps_lon=" + parts[1] + "&gps_name=" + encodedName;
                } catch (Exception ignored) {}
            }
        }

        String escapedPath = path.replace("'", "\\'");
        String js = "window.__waqdNavigate && window.__waqdNavigate('" + escapedPath + "')";
        getBridge().getWebView().post(() ->
            getBridge().getWebView().evaluateJavascript(js, null)
        );
    }
}
