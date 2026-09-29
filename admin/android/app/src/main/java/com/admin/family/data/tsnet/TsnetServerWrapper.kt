package com.admin.family.data.tsnet

import android.content.Context
import android.util.Log
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import tsnetbridge.Server as GoServer
import tsnetbridge.Tsnetbridge

/**
 * Kotlin wrapper around the gomobile-generated tsnet API.
 *
 * ACTUAL gomobile method names (verified from classes.jar via JVM reflection):
 *   tsnetbridge.Tsnetbridge.newServer(stateDir, hostname, authKey) : Server
 *   Server.start()                   - throws on error
 *   Server.stop()
 *   Server.status()                  : String
 *   Server.isRunning()               : Boolean
 *   Server.iP4()                     : String  (NOTE: capital P!)
 *   Server.listenAndProxy(long, String) - Go int -> Java long
 */
class TsnetServerWrapper(private val context: Context) {

    private var goServer: GoServer? = null

    @Volatile
    var lastError: String? = null
        private set

    fun isRunning(): Boolean = try {
        goServer?.isRunning() ?: false
    } catch (t: Throwable) {
        Log.e(TAG, "isRunning failed", t)
        false
    }

    fun status(): String = try {
        goServer?.status() ?: "stopped"
    } catch (t: Throwable) {
        Log.e(TAG, "status failed", t)
        "error: ${t.message}"
    }

    fun ip4(): String = try {
        // NOTE: gomobile exports "iP4" (capital P)
        goServer?.iP4() ?: ""
    } catch (t: Throwable) {
        Log.e(TAG, "iP4 failed", t)
        ""
    }

    suspend fun start(authKey: String, hostname: String = "admin-phone"): Result<Unit> =
        withContext(Dispatchers.IO) {
            try {
                if (goServer == null) {
                    val stateDir = context.filesDir.resolve("tsnet").absolutePath
                    goServer = Tsnetbridge.newServer(stateDir, hostname, authKey)
                }
                goServer!!.start()
                lastError = null
                Result.success(Unit)
            } catch (t: Throwable) {
                lastError = t.message ?: "unknown error"
                Log.e(TAG, "start failed", t)
                Result.failure(t)
            }
        }

    suspend fun listenAndProxy(port: Int, target: String): Result<Unit> =
        withContext(Dispatchers.IO) {
            try {
                // gomobile widens Go int -> Java long
                goServer?.listenAndProxy(port.toLong(), target)
                Result.success(Unit)
            } catch (t: Throwable) {
                lastError = t.message ?: "listen failed"
                Log.e(TAG, "listenAndProxy failed", t)
                Result.failure(t)
            }
        }

    fun stop() {
        try {
            goServer?.stop()
        } catch (t: Throwable) {
            Log.e(TAG, "stop failed", t)
        }
    }

    companion object {
        private const val TAG = "TsnetWrapper"
    }
}
