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
import android.util.Log;
import com.getcapacitor.BridgeActivity;

public class MainActivity extends BridgeActivity {
    private SharedPreferences.OnSharedPreferenceChangeListener prefListener;
    private BroadcastReceiver gpsRefreshReceiver;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

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
