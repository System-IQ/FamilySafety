package com.admin.family.data.api

import com.admin.family.data.api.dto.DeviceDto
import com.admin.family.data.api.dto.DeviceListResponse
import com.admin.family.data.api.dto.HealthDto
import com.admin.family.data.api.dto.SystemMetrics
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import kotlinx.serialization.json.Json
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import java.util.concurrent.TimeUnit

/**
 * API client with a MUTABLE base URL.
 *
 * `baseUrl` is read at request time — so a Settings change takes effect
 * immediately without recreating the client.
 *
 * The OkHttpClient itself is reused (connection pool + timeouts preserved).
 */
class ApiClient(initialBaseUrl: String) {

    @Volatile
    private var currentBaseUrl: String = normalize(initialBaseUrl)

    private val json = Json {
        ignoreUnknownKeys = true
        explicitNulls = false
    }

    private val http: OkHttpClient = OkHttpClient.Builder()
        .connectTimeout(10, TimeUnit.SECONDS)
        .readTimeout(20, TimeUnit.SECONDS)
        .build()

    // Fast client for dashboard polling — fails quickly if server is down
    private val fastHttp: OkHttpClient = OkHttpClient.Builder()
        .connectTimeout(2, TimeUnit.SECONDS)
        .readTimeout(3, TimeUnit.SECONDS)
        .build()

    private val jsonMedia = "application/json; charset=utf-8".toMediaType()

    val baseUrl: String
        get() = currentBaseUrl

    /**
     * Change the base URL. Safe to call from any thread.
     * A change takes effect on the next request.
     */
    fun updateBaseUrl(newBaseUrl: String) {
        currentBaseUrl = normalize(newBaseUrl)
    }

    private fun url(path: String): String =
        currentBaseUrl.trimEnd('/') + "/" + path.trimStart('/')

    // ---------------- endpoints ----------------

    suspend fun health(): HealthDto = withContext(Dispatchers.IO) {
        val req = Request.Builder().url(url("health")).get().build()
        http.newCall(req).execute().use { resp ->
            if (!resp.isSuccessful) error("HTTP ${resp.code}")
            val body = resp.body?.string() ?: error("empty body")
            json.decodeFromString(HealthDto.serializer(), body)
        }
    }

    suspend fun listDevices(): List<DeviceDto> = withContext(Dispatchers.IO) {
        val req = Request.Builder().url(url("devices")).get().build()
        http.newCall(req).execute().use { resp ->
            if (!resp.isSuccessful) error("HTTP ${resp.code}")
            val body = resp.body?.string() ?: error("empty body")
            json.decodeFromString(DeviceListResponse.serializer(), body).devices
        }
    }

    suspend fun upsertDevice(device: DeviceDto): DeviceDto = withContext(Dispatchers.IO) {
        val payload = json.encodeToString(DeviceDto.serializer(), device)
        val req = Request.Builder()
            .url(url("devices"))
            .post(payload.toRequestBody(jsonMedia))
            .build()
        http.newCall(req).execute().use { resp ->
            if (!resp.isSuccessful) error("HTTP ${resp.code}")
            val body = resp.body?.string() ?: error("empty body")
            json.decodeFromString(DeviceDto.serializer(), body)
        }
    }

    suspend fun systemMetrics(): SystemMetrics = withContext(Dispatchers.IO) {
        val req = Request.Builder().url(url("metrics")).get().build()
        fastHttp.newCall(req).execute().use { resp ->
            if (!resp.isSuccessful) error("HTTP ${resp.code}")
            val body = resp.body?.string() ?: error("empty body")
            json.decodeFromString(SystemMetrics.serializer(), body)
        }
    }

    companion object {
        fun normalize(raw: String): String {
            val trimmed = raw.trim()
            require(trimmed.isNotEmpty()) { "baseUrl must not be empty" }
            val lower = trimmed.lowercase()
            require(lower.startsWith("http://") || lower.startsWith("https://")) {
                "baseUrl must start with http:// or https://"
            }
            return if (trimmed.endsWith("/")) trimmed else "$trimmed/"
        }
    }
}
