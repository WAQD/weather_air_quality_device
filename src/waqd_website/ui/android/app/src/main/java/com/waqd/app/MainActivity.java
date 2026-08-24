package com.waqd.app;

import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import com.getcapacitor.BridgeActivity;
import java.net.URLEncoder;

public class MainActivity extends BridgeActivity {
    private String pendingNavigatePath = null;
    private SharedPreferences.OnSharedPreferenceChangeListener prefListener;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        // Must register plugins BEFORE super.onCreate(): the Capacitor bridge
        // initializes there and ignores plugins registered afterwards.
        registerPlugin(LocationPermissionPlugin.class);
        super.onCreate(savedInstanceState);

        Intent launchIntent = getIntent();
        if (launchIntent != null && launchIntent.hasExtra("navigate_to")) {
            pendingNavigatePath = launchIntent.getStringExtra("navigate_to");
        }

        // Refresh the widget right away when the app language changes (so it re-fetches
        // in the new locale immediately), or when login/first-setup keys become available.
        // Also update widget UI layout immediately when style or location mode settings change.
        SharedPreferences prefs = getSharedPreferences(WidgetContract.PREFS_NAME, Context.MODE_PRIVATE);
        prefListener = (sharedPreferences, key) -> {
            if (WidgetContract.PREF_LOCALE.equals(key)
                    || WidgetContract.PREF_WIDGET_KEY.equals(key)
                    || WidgetContract.PREF_BASE_URL.equals(key)) {
                WeatherWidgetProvider.refreshNow(this);
            } else if (WidgetContract.PREF_LOCATION_MODE.equals(key)
                    || "waqd.website.widgetStyle".equals(key)) {
                WeatherWidgetProvider.updateAllWidgets(this);
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
        // Re-render the widget right away: if the user just granted the location
        // permission in system settings, this clears the warning banner immediately.
        WeatherWidgetProvider.updateAllWidgets(this);
        // Then re-fetch weather (bypassing the rate limit) so a stale error status
        // like "no_permission" is replaced with an up-to-date success status.
        WeatherWidgetProvider.refreshNow(this);
        // Notify the web UI directly so it re-checks the permission state and the
        // widget status (the Capacitor 'appStateChange' event alone proved unreliable).
        // Guard against the WebView/JS runtime not being ready yet (cold start).
        if (getBridge() != null && getBridge().getWebView() != null) {
            android.util.Log.d("WAQD", "onResume: triggering waqdAppResume JS event");
            getBridge().getWebView().post(() ->
                getBridge().triggerJSEvent("waqdAppResume", "window"));
        } else {
            android.util.Log.w("WAQD", "onResume: bridge/webview not ready, skipping JS event");
        }
        if (pendingNavigatePath != null) {
            final String path = pendingNavigatePath;
            pendingNavigatePath = null;
            new Handler(Looper.getMainLooper()).postDelayed(() -> dispatchNavigation(path), 500);
        }
    }

    private void dispatchNavigation(String path) {
        if (getBridge() == null || getBridge().getWebView() == null) return;

        SharedPreferences prefs = getSharedPreferences(WidgetContract.PREFS_NAME, Context.MODE_PRIVATE);
        String gpsCoords = prefs.getString(WidgetContract.PREF_LAST_GPS_COORDS, null);
        if (gpsCoords != null && !gpsCoords.isEmpty()) {
            String[] parts = gpsCoords.split(",");
            if (parts.length == 2) {
                try {
                    String gpsName = prefs.getString(WidgetContract.PREF_LAST_GPS_NAME, "GPS Location");
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
