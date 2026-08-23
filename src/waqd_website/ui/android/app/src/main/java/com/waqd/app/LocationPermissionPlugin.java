package com.waqd.app;

import android.content.Intent;
import android.net.Uri;
import android.provider.Settings;

import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;

/**
 * Native helper for the weather widget's background-location requirement.
 *
 * Opens the app details screen so the user can enable "Allow all the time"
 * location access (on Android 11+ it can no longer be granted via a runtime
 * dialog).
 */
@CapacitorPlugin(name = "LocationPermission")
public class LocationPermissionPlugin extends Plugin {

    @PluginMethod
    public void openAppDetails(PluginCall call) {
        Intent intent = new Intent(
                Settings.ACTION_APPLICATION_DETAILS_SETTINGS,
                Uri.parse("package:" + getContext().getPackageName()));
        intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
        getContext().startActivity(intent);
        call.resolve();
    }
}
