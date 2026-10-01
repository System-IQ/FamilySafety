package com.admin.family.service

import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.ServiceInfo
import android.os.Build
import android.os.IBinder
import android.util.Log
import androidx.core.app.ServiceCompat
import com.admin.family.FamilyAdminApp
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

/**
 * Foreground service that keeps the embedded FastAPI backend and
 * the Tailscale (tsnet) bridge alive while the app is in the background.
 *
 * Lifecycle:
 *   START  → startForeground(notification "Starting…")
 *          → PythonServer.configure() (already done by app)
 *          → PythonServer.startBackendBlocking() on IO thread
 *          → startForeground(notification "Running")
 *          → periodically updates notification with uptime
 *   STOP   → PythonServer.stopBackendBlocking()
 *          → stopForeground() + stopSelf()
 */
class ServerService : Service() {

    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    private var tickerJob: Job? = null
    private var startedAt: Long = 0L
    @Volatile private var running = false

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        when (intent?.action) {
            ACTION_STOP -> {
                Log.i(TAG, "ACTION_STOP received")
                stopServer()
                return START_NOT_STICKY
            }
            ACTION_START -> {
                Log.i(TAG, "ACTION_START received")
                startServer()
                return START_STICKY
            }
            else -> {
                // Restart from system (START_STICKY) — check persisted preference
                val app = application as FamilyAdminApp
                if (app.preferences.serverEnabled) {
                    Log.i(TAG, "Service restarted by system; resuming server")
                    startServer()
                } else {
                    Log.i(TAG, "Service restarted but serverEnabled=false → stopping")
                    stopSelf()
                }
                return START_STICKY
            }
        }
    }

    private fun startServer() {
        if (running) {
            Log.i(TAG, "Already running")
            return
        }

        // 1) Promote to foreground immediately (must be within 5s of startForegroundService)
        val initial = NotificationHelper.buildServerNotification(
            this,
            title = "FamilySafety Server",
            body = "Starting embedded backend…",
            showStop = false,
        )
        ServiceCompat.startForeground(
            this,
            NotificationHelper.NOTIFICATION_ID,
            initial,
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.UPSIDE_DOWN_CAKE)
                ServiceInfo.FOREGROUND_SERVICE_TYPE_SPECIAL_USE
            else 0,
        )

        running = true
        startedAt = System.currentTimeMillis()

        // 2) Persist preference (idempotent)
        val app = application as FamilyAdminApp
        app.preferences.serverEnabled = true

        // 3) Start uvicorn on IO thread
        scope.launch {
            try {
                val result = app.startEmbeddedServer()
                Log.i(TAG, "startEmbeddedServer -> $result")
            } catch (t: Throwable) {
                Log.e(TAG, "startEmbeddedServer failed", t)
            }
        }

        // 4) Ticker: update notification with uptime + readiness
        tickerJob?.cancel()
        tickerJob = scope.launch {
            while (running) {
                delay(15_000L)
                if (!running) break
                val ready = app.isBackendReadyBlocking(1.0)
                val uptime = formatUptime(System.currentTimeMillis() - startedAt)
                val body = if (ready)
                    "Running · uptime $uptime · tap to open"
                else
                    "Starting backend… ($uptime)"

                val n = NotificationHelper.buildServerNotification(
                    this@ServerService,
                    title = "FamilySafety Server",
                    body = body,
                    showStop = true,
                )
                ServiceCompat.startForeground(
                    this@ServerService,
                    NotificationHelper.NOTIFICATION_ID,
                    n,
                    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.UPSIDE_DOWN_CAKE)
                        ServiceInfo.FOREGROUND_SERVICE_TYPE_SPECIAL_USE
                    else 0,
                )
            }
        }
    }

    private fun stopServer() {
        val app = application as FamilyAdminApp
        app.preferences.serverEnabled = false
        scope.launch {
            try {
                val r = app.stopEmbeddedServer()
                Log.i(TAG, "stopEmbeddedServer -> $r")
            } catch (t: Throwable) {
                Log.e(TAG, "stopEmbeddedServer failed", t)
            }
        }
        running = false
        tickerJob?.cancel()
        ServiceCompat.stopForeground(this, ServiceCompat.STOP_FOREGROUND_REMOVE)
        stopSelf()
    }

    override fun onDestroy() {
        running = false
        tickerJob?.cancel()
        scope.cancel()
        super.onDestroy()
    }

    private fun formatUptime(ms: Long): String {
        val s = ms / 1000
        val h = s / 3600
        val m = (s % 3600) / 60
        return when {
            h > 0 -> "${h}h ${m}m"
            m > 0 -> "${m}m"
            else -> "${s}s"
        }
    }

    companion object {
        private const val TAG = "ServerService"
        const val ACTION_START = "com.admin.family.action.START_SERVER"
        const val ACTION_STOP = "com.admin.family.action.STOP_SERVER"

        fun start(context: Context) {
            val i = Intent(context, ServerService::class.java).setAction(ACTION_START)
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                context.startForegroundService(i)
            } else {
                context.startService(i)
            }
        }

        fun stop(context: Context) {
            val i = Intent(context, ServerService::class.java).setAction(ACTION_STOP)
            context.startService(i)
        }
    }
}
