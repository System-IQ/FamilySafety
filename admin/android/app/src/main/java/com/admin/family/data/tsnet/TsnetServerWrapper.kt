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
 * Maps to Go:
 *   tsnetbridge.NewServer(stateDir, hostname, authKey) *Server
 *   (*Server).Start() error
 *   (*Server).Stop()
 *   (*Server).Status() string
 *   (*Server).IsRunning() bool
 *   (*Server).IP4() string
 *   (*Server).ListenAndProxy(port, target) error
 */
class TsnetServerWrapper(private val context: Context) {

    private var goServer: GoServer? = null

    @Volatile
    var lastError: String? = null
        private set

    fun isRunning(): Boolean = goServer?.isRunning() ?: false

    fun status(): String = goServer?.status() ?: "stopped"

    fun ip4(): String = goServer?.ip4() ?: ""

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
                Log.e("TsnetWrapper", "start failed", t)
                Result.failure(t)
            }
        }

    suspend fun listenAndProxy(port: Int, target: String): Result<Unit> =
        withContext(Dispatchers.IO) {
            try {
                goServer?.listenAndProxy(port, target)
                Result.success(Unit)
            } catch (t: Throwable) {
                lastError = t.message ?: "listen failed"
                Result.failure(t)
            }
        }

    fun stop() {
        try {
            goServer?.stop()
        } catch (t: Throwable) {
            Log.e("TsnetWrapper", "stop failed", t)
        }
    }
}
