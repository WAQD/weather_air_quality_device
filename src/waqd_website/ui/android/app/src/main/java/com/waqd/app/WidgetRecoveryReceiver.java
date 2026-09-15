package com.waqd.app;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;

/**
 * Restores widget scheduling after Android or an OEM has recreated the app.
 * This receiver deliberately does no network or location work on the broadcast
 * thread; it only asks WorkManager to restore its existing periodic request.
 */
public final class WidgetRecoveryReceiver extends BroadcastReceiver {

    @Override
    public void onReceive(Context context, Intent intent) {
        String action = intent == null ? null : intent.getAction();
        if (Intent.ACTION_BOOT_COMPLETED.equals(action)
                || Intent.ACTION_MY_PACKAGE_REPLACED.equals(action)
                || Intent.ACTION_USER_PRESENT.equals(action)) {
            WeatherWidgetProvider.schedulePeriodicWork(context.getApplicationContext());
        }
    }
}