package com.admin.family.data.tsnet

import android.content.Context
import android.util.Log
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import tsnetbridge.Server as GoServer
import tsnetbridge.Tsnetbridge

/**
 * Thread-safe Kotlin wrapper around the gomobile-generated tsnet API.
 *
 * Responsibilities:
 * - Own exactly one Go tsnet server instance.
 * - Prevent concurrent start/stop operations.
 * - Start the tsnet server before exposing it as running.
 * - Start the proxy only after the server is running.
 * - Never report success when an operation actually failed.
 */
class TsnetServerWrapper(
    private val context: Context,
) {

    private val lock = Any()

    private var goServer: GoServer? = null
    private var proxyStarted = false

    @Volatile
    var lastError: String? = null
        private set

    fun isRunning(): Boolean = synchronized(lock) {
        try {
            goServer?.isRunning() ?: false
        } catch (t: Throwable) {
            Log.e(TAG, "isRunning failed", t)
            false
        }
    }

    fun status(): String = synchronized(lock) {
        try {
            goServer?.status() ?: "stopped"
        } catch (t: Throwable) {
            Log.e(TAG, "status failed", t)
            "error: ${t.message}"
        }
    }

    fun ip4(): String = synchronized(lock) {
        try {
            // NOTE: gomobile exports "iP4" (capital P)
            goServer?.iP4() ?: ""
        } catch (t: Throwable) {
            Log.e(TAG, "iP4 failed", t)
            ""
        }
    }

    suspend fun start(
        authKey: String,
        hostname: String = "admin-phone",
    ): Result<Unit> = withContext(Dispatchers.IO) {

        synchronized(lock) {
            try {
                val existing = goServer

                if (existing != null) {
                    if (existing.isRunning()) {
                        lastError = null
                        return@withContext Result.success(Unit)
                    }

                    // Do not reuse an old stopped Go server instance.
                    goServer = null
                    proxyStarted = false
                }

                val stateDir = context.filesDir
                    .resolve("tsnet")
                    .absolutePath

                val server = Tsnetbridge.newServer(
                    stateDir,
                    hostname,
                    authKey,
                )

                goServer = server

                server.start()

                if (!server.isRunning()) {
                    throw IllegalStateException(
                        "tsnet server did not enter running state"
                    )
                }

                lastError = null
                Result.success(Unit)

            } catch (t: Throwable) {
                lastError = t.message ?: "unknown error"

                Log.e(TAG, "start failed", t)

                try {
                    goServer?.stop()
                } catch (cleanupError: Throwable) {
                    Log.e(TAG, "start cleanup failed", cleanupError)
                }

                goServer = null
                proxyStarted = false

                Result.failure(t)
            }
        }
    }

    suspend fun listenAndProxy(
        port: Int,
        target: String,
    ): Result<Unit> = withContext(Dispatchers.IO) {

        synchronized(lock) {
            try {
                val server = goServer
                    ?: return@withContext Result.failure(
                        IllegalStateException("tsnet server is not initialized")
                    )

                if (!server.isRunning()) {
                    return@withContext Result.failure(
                        IllegalStateException("tsnet server is not running")
                    )
                }

                if (proxyStarted) {
                    return@withContext Result.success(Unit)
                }

                // gomobile widens Go int -> Java long.
                server.listenAndProxy(
                    port.toLong(),
                    target,
                )

                proxyStarted = true
                lastError = null

                Result.success(Unit)

            } catch (t: Throwable) {
                lastError = t.message ?: "listen failed"

                Log.e(TAG, "listenAndProxy failed", t)

                Result.failure(t)
            }
        }
    }

    fun stop() {
        synchronized(lock) {
            try {
                goServer?.stop()
            } catch (t: Throwable) {
                Log.e(TAG, "stop failed", t)
            } finally {
                goServer = null
                proxyStarted = false
            }
        }
    }

    companion object {
        private const val TAG = "TsnetWrapper"
    }
}
