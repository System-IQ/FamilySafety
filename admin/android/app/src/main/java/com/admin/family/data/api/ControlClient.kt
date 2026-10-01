package com.admin.family.data.api

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import java.util.concurrent.TimeUnit

@Serializable
data class ControlStatus(
    val running: Boolean = false,
    val backend: Boolean = false,
    @SerialName("tailscale_ip") val tailscaleIp: String = "",
)

@Serializable
data class ControlActionResponse(
    val ok: Boolean = false,
    val action: String = "",
    @SerialName("duration_ms") val durationMs: Long = 0L,
    @SerialName("output_tail") val outputTail: String = "",
    val status: ControlStatus = ControlStatus(),
    val error: String? = null,
)

/**
 * Talks to the local fs-control agent on 127.0.0.1:9999 (running in Termux).
 *
 * Endpoints:
 *   GET  /control/ping    (no auth)   -> {"pong": true}
 *   GET  /control/status  (Bearer)    -> ControlStatus
 *   POST /control/start   (Bearer)    -> ControlActionResponse
 *   POST /control/stop    (Bearer)    -> ControlActionResponse
 */
class ControlClient(
    private val baseUrl: String = "http://127.0.0.1:9999",
) {
    private val json = Json {
        ignoreUnknownKeys = true
        explicitNulls = false
    }

    private val http = OkHttpClient.Builder()
        .connectTimeout(5, TimeUnit.SECONDS)
        .readTimeout(120, TimeUnit.SECONDS)
        .writeTimeout(10, TimeUnit.SECONDS)
        .build()

    private val jsonMedia = "application/json; charset=utf-8".toMediaType()

    @Volatile
    var token: String? = null

    private fun build(path: String, method: String = "GET"): Request {
        val b = Request.Builder().url("${baseUrl.trimEnd('/')}$path")
        token?.takeIf { it.isNotBlank() }?.let { b.header("Authorization", "Bearer $it") }
        return when (method) {
            "POST" -> b.post("".toRequestBody(jsonMedia)).build()
            else -> b.get().build()
        }
    }

    suspend fun ping(): Boolean = withContext(Dispatchers.IO) {
        try {
            http.newCall(build("/control/ping")).execute().use { it.isSuccessful }
        } catch (_: Throwable) { false }
    }

    suspend fun status(): ControlStatus = withContext(Dispatchers.IO) {
        http.newCall(build("/control/status")).execute().use { resp ->
            val body = resp.body?.string() ?: ""
            when (resp.code) {
                200 -> json.decodeFromString(ControlStatus.serializer(), body)
                401 -> error("Control token rejected")
                else -> error("HTTP ${resp.code}")
            }
        }
    }

    suspend fun start(): ControlActionResponse = withContext(Dispatchers.IO) {
        http.newCall(build("/control/start", "POST")).execute().use { resp ->
            val body = resp.body?.string() ?: ""
            when (resp.code) {
                200 -> json.decodeFromString(ControlActionResponse.serializer(), body)
                401 -> error("Control token rejected")
                409 -> error("Another operation in progress")
                500 -> runCatching {
                    json.decodeFromString(ControlActionResponse.serializer(), body)
                }.getOrElse { error("Server failed to start") }
                else -> error("HTTP ${resp.code}")
            }
        }
    }

    suspend fun stop(): ControlActionResponse = withContext(Dispatchers.IO) {
        http.newCall(build("/control/stop", "POST")).execute().use { resp ->
            val body = resp.body?.string() ?: ""
            when (resp.code) {
                200 -> json.decodeFromString(ControlActionResponse.serializer(), body)
                401 -> error("Control token rejected")
                409 -> error("Another operation in progress")
                500 -> runCatching {
                    json.decodeFromString(ControlActionResponse.serializer(), body)
                }.getOrElse { error("Server failed to stop") }
                else -> error("HTTP ${resp.code}")
            }
        }
    }
}
