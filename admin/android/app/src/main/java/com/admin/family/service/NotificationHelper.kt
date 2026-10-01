package com.admin.family.service

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.os.Build
import androidx.core.app.NotificationCompat
import com.admin.family.MainActivity
import com.admin.family.R

/**
 * Centralized notification channel + builder for the embedded server.
 *
 * Channel importance is LOW so the notification is silent but always visible.
 * The notification is ongoing (no dismiss by swipe) while the server runs.
 */
object NotificationHelper {

    const val CHANNEL_ID = "familysafety_server"
    const val CHANNEL_NAME = "FamilySafety Server"
    const val NOTIFICATION_ID = 1001

    fun createChannel(context: Context) {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) return
        val mgr = context.getSystemService(NotificationManager::class.java) ?: return
        if (mgr.getNotificationChannel(CHANNEL_ID) != null) return

        val channel = NotificationChannel(
            CHANNEL_ID,
            CHANNEL_NAME,
            NotificationManager.IMPORTANCE_LOW,
        ).apply {
            description = "Shows while the embedded FamilySafety server is running"
            setShowBadge(false)
            enableVibration(false)
            enableLights(false)
        }
        mgr.createNotificationChannel(channel)
    }

    fun buildServerNotification(
        context: Context,
        title: String,
        body: String,
        showStop: Boolean,
    ): Notification {
        createChannel(context)

        val openIntent = PendingIntent.getActivity(
            context,
            0,
            Intent(context, MainActivity::class.java).apply {
                flags = Intent.FLAG_ACTIVITY_SINGLE_TOP or Intent.FLAG_ACTIVITY_CLEAR_TOP
            },
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT,
        )

        val builder = NotificationCompat.Builder(context, CHANNEL_ID)
            .setSmallIcon(android.R.drawable.stat_sys_upload_done)
            .setContentTitle(title)
            .setContentText(body)
            .setOngoing(true)
            .setOnlyAlertOnce(true)
            .setContentIntent(openIntent)
            .setCategory(NotificationCompat.CATEGORY_SERVICE)
            .setPriority(NotificationCompat.PRIORITY_LOW)
            .setForegroundServiceBehavior(NotificationCompat.FOREGROUND_SERVICE_IMMEDIATE)

        if (showStop) {
            val stopIntent = PendingIntent.getService(
                context,
                1,
                Intent(context, ServerService::class.java).setAction(ServerService.ACTION_STOP),
                PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT,
            )
            builder.addAction(
                android.R.drawable.ic_menu_close_clear_cancel,
                "Stop server",
                stopIntent,
            )
        }

        return builder.build()
    }
}
