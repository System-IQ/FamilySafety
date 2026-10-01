package com.admin.family.service

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.util.Log
import com.admin.family.FamilyAdminApp

/**
 * Restarts the embedded server after device reboot IF the user
 * had left it enabled (serverEnabled == true).
 */
class BootReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action != Intent.ACTION_BOOT_COMPLETED &&
            intent.action != Intent.ACTION_MY_PACKAGE_REPLACED) return

        val app = context.applicationContext as FamilyAdminApp
        if (app.preferences.serverEnabled) {
            Log.i(TAG, "Boot completed and serverEnabled=true → starting service")
            ServerService.start(context)
        } else {
            Log.i(TAG, "Boot completed but serverEnabled=false → skip")
        }
    }

    companion object { private const val TAG = "BootReceiver" }
}
