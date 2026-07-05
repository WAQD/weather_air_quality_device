package com.waqd.app;

import android.appwidget.AppWidgetManager;
import android.content.BroadcastReceiver;
import android.content.ComponentName;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.content.SharedPreferences;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.util.Log;
import com.getcapacitor.BridgeActivity;

public class MainActivity extends BridgeActivity {
    private SharedPreferences.OnSharedPreferenceChangeListener prefListener;
    private BroadcastReceiver gpsRefreshReceiver;
    private String pendingNavigatePath = null;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        // Store any deep-link navigation from widget tap (cold start)
        Intent launchIntent = getIntent();
        if (launchIntent != null && launchIntent.hasExtra("navigate_to")) {
            pendingNavigatePath = launchIntent.getStringExtra("navigate_to");
        }

        SharedPreferences prefs = getSharedPreferences("CapacitorStorage", Context.MODE_PRIVATE);
        prefListener = (sharedPreferences, key) -> {
            if ("widget_weather_data".equals(key)) {
                String val = sharedPreferences.getString(key, "");
                Log.d("WeatherWidget", "MainActivity: widget_weather_data changed! Content: " + val);

                // Force update the widget instantly when Vue updates Capacitor preferences
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
                // App already running — dispatch after a short delay to ensure WebView is ready
                new Handler(Looper.getMainLooper()).postDelayed(() -> dispatchNavigation(path), 300);
            }
        }
    }

    @Override
    public void onResume() {
        super.onResume();
        // Cold start: navigate after WebView has had time to load
        if (pendingNavigatePath != null) {
            final String path = pendingNavigatePath;
            pendingNavigatePath = null;
            new Handler(Looper.getMainLooper()).postDelayed(() -> dispatchNavigation(path), 500);
        }
    }

    private void dispatchNavigation(String path) {
        if (getBridge() == null || getBridge().getWebView() == null) return;
        String escapedPath = path.replace("'", "\\'");
        // __waqdNavigate is set immediately in main.ts (even before initI18n finishes)
        // as a queuing stub, so it is always available. No sessionStorage fallback needed.
        String js = "window.__waqdNavigate && window.__waqdNavigate('" + escapedPath + "')";
        getBridge().getWebView().post(() ->
            getBridge().getWebView().evaluateJavascript(js, null)
        );
    }

    @Override
    public void onStart() {
        super.onStart();
        gpsRefreshReceiver = new BroadcastReceiver() {
            @Override
            public void onReceive(Context context, Intent intent) {
                Log.d("WeatherWidget", "MainActivity: GPS widget refresh received, dispatching to Vue");
                if (getBridge() != null && getBridge().getWebView() != null) {
                    getBridge().getWebView().post(() ->
                        getBridge().getWebView().evaluateJavascript(
                            "window.dispatchEvent(new CustomEvent('waqd-widget-gps-refresh'))", null
                        )
                    );
                }
            }
        };
        IntentFilter filter = new IntentFilter("com.waqd.app.GPS_WIDGET_REFRESH");
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            registerReceiver(gpsRefreshReceiver, filter, Context.RECEIVER_NOT_EXPORTED);
        } else {
            registerReceiver(gpsRefreshReceiver, filter);
        }
    }

    @Override
    public void onStop() {
        super.onStop();
        if (gpsRefreshReceiver != null) {
            unregisterReceiver(gpsRefreshReceiver);
            gpsRefreshReceiver = null;
        }
    }
}
