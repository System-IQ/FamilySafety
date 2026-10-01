package com.admin.family.tsnet

import android.content.Context
import android.util.Log
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import tsnetbridge.Server as GoServer
import tsnetbridge.Tsnetbridge

/**
 * Kotlin wrapper around the tsnet-bridge AAR (gomobile).
 *
 * Supports MULTIPLE independent profiles (e.g. kids, wife).
 *
 * gomobile method names (verified from classes.jar):
 *   Tsnetbridge.newServer(instance, stateDir, hostname, authKey) : Server
 *   Server.start()          (throws on error)
 *   Server.stop()
 *   Server.status()         : String
 *   Server.isRunning()      : Boolean
 *   Server.iP4()            : String
 *   Server.tailnetHostname(): String
 *   Server.logFilePath()    : String
 *   Server.proxyPort()      : Int
 *   Server.listenAndProxy(long, String)
 */
class TsnetBridge(private val context: Context) {

    private val servers = mutableMapOf<String, GoServer>()

    @Volatile
    var lastError: String? = null
        private set

    private fun ensureServer(profile: TsnetProfile): GoServer {
        servers[profile.id]?.let { return it }
        val stateDir = context.filesDir.resolve("tsnet/${profile.id}").absolutePath
        val s = Tsnetbridge.newServer(
            profile.id,
            stateDir,
            profile.hostname,
            profile.authKey,
        )
        servers[profile.id] = s
        return s
    }

    suspend fun start(profile: TsnetProfile): Result<String> = withContext(Dispatchers.IO) {
        try {
            val srv = ensureServer(profile)
            srv.start()
            val ip = srv.iP4()
            lastError = null
            Result.success(ip)
        } catch (t: Throwable) {
            lastError = t.message ?: "start failed"
            Log.e(TAG, "start(${profile.id}) failed", t)
            Result.failure(t)
        }
    }

    suspend fun stop(profileId: String): Result<Unit> = withContext(Dispatchers.IO) {
        try {
            servers[profileId]?.stop()
            Result.success(Unit)
        } catch (t: Throwable) {
            lastError = t.message ?: "stop failed"
            Result.failure(t)
        }
    }

    suspend fun listenAndProxy(
        profileId: String,
        port: Int,
        target: String,
    ): Result<Unit> = withContext(Dispatchers.IO) {
        try {
            servers[profileId]?.listenAndProxy(port.toLong(), target)
            Result.success(Unit)
        } catch (t: Throwable) {
            lastError = t.message ?: "proxy failed"
            Result.failure(t)
        }
    }

    fun isRunning(profileId: String): Boolean =
        try { servers[profileId]?.isRunning() ?: false } catch (_: Throwable) { false }

    fun ip(profileId: String): String =
        try { servers[profileId]?.iP4() ?: "" } catch (_: Throwable) { "" }

    fun status(profileId: String): String =
        try { servers[profileId]?.status() ?: "idle" } catch (_: Throwable) { "error" }

    fun stopAll() {
        servers.values.forEach { runCatching { it.stop() } }
        servers.clear()
    }

    companion object { private const val TAG = "TsnetBridge" }
}
