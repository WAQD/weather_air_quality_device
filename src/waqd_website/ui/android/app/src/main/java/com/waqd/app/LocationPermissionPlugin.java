package com.waqd.app;

import android.Manifest;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.net.Uri;
import android.provider.Settings;

import androidx.core.content.ContextCompat;

import com.getcapacitor.JSObject;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;

/**
 * Native helper for the weather widget's background-location requirement.
 *
 * Detects ACCESS_BACKGROUND_LOCATION ("Allow all the time") and opens the app
 * details screen so the user can enable it (on Android 11+ it can no longer be
 * granted via a runtime dialog).
 */
@CapacitorPlugin(name = "LocationPermission")
public class LocationPermissionPlugin extends Plugin {

    @PluginMethod
    public void isBackgroundGranted(PluginCall call) {
        boolean granted = ContextCompat.checkSelfPermission(
                getContext(), Manifest.permission.ACCESS_BACKGROUND_LOCATION)
                == PackageManager.PERMISSION_GRANTED;
        JSObject ret = new JSObject();
        ret.put("granted", granted);
        call.resolve(ret);
    }

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
