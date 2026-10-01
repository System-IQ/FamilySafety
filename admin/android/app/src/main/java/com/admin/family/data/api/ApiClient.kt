package com.admin.family.data.api

import com.admin.family.data.api.dto.DeviceDto
import com.admin.family.data.api.dto.DeviceListResponse
import com.admin.family.data.api.dto.HealthDto
import com.admin.family.data.api.dto.LoginRequest
import com.admin.family.data.api.dto.SystemMetrics
import com.admin.family.data.api.dto.TokenResponse
import com.admin.family.data.api.dto.UserPublic
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import kotlinx.serialization.json.Json
import okhttp3.Interceptor
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import java.util.concurrent.TimeUnit

class ApiClient(initialBaseUrl: String) {

    @Volatile
    private var currentBaseUrl: String = normalize(initialBaseUrl)

    @Volatile
    private var authToken: String? = null

    private val json = Json {
        ignoreUnknownKeys = true
        explicitNulls = false
    }

    private val authInterceptor = Interceptor { chain ->
        val original = chain.request()
        val token = authToken
        val request = if (token.isNullOrBlank()) {
            original
        } else {
            original.newBuilder()
                .header("Authorization", "Bearer $token")
                .build()
        }
        chain.proceed(request)
    }

    private val http: OkHttpClient = OkHttpClient.Builder()
        .connectTimeout(10, TimeUnit.SECONDS)
        .readTimeout(20, TimeUnit.SECONDS)
        .addInterceptor(authInterceptor)
        .build()

    private val fastHttp: OkHttpClient = OkHttpClient.Builder()
        .connectTimeout(2, TimeUnit.SECONDS)
        .readTimeout(3, TimeUnit.SECONDS)
        .addInterceptor(authInterceptor)
        .build()

    private val jsonMedia = "application/json; charset=utf-8".toMediaType()

    val baseUrl: String get() = currentBaseUrl

    fun updateBaseUrl(newBaseUrl: String) {
        currentBaseUrl = normalize(newBaseUrl)
    }

    fun setAuthToken(token: String?) {
        authToken = token
    }

    fun getAuthToken(): String? = authToken

    private fun url(path: String): String =
        currentBaseUrl.trimEnd('/') + "/" + path.trimStart('/')

    // ---------------- health ----------------

    suspend fun health(): HealthDto = withContext(Dispatchers.IO) {
        val req = Request.Builder().url(url("health")).get().build()
        fastHttp.newCall(req).execute().use { resp ->
            if (!resp.isSuccessful) error("HTTP ${resp.code}")
            val body = resp.body?.string() ?: error("empty body")
            json.decodeFromString(HealthDto.serializer(), body)
        }
    }

    // ---------------- auth ----------------

    suspend fun login(req: LoginRequest): TokenResponse = withContext(Dispatchers.IO) {
        val payload = json.encodeToString(LoginRequest.serializer(), req)
        val httpReq = Request.Builder()
            .url(url("auth/login"))
            .post(payload.toRequestBody(jsonMedia))
            .build()
        http.newCall(httpReq).execute().use { resp ->
            val body = resp.body?.string() ?: ""
            if (!resp.isSuccessful) {
                val msg = when (resp.code) {
                    401 -> "Invalid email or password"
                    422 -> "Malformed credentials"
                    else -> "HTTP ${resp.code}"
                }
                error(msg)
            }
            json.decodeFromString(TokenResponse.serializer(), body)
        }
    }

    suspend fun register(email: String, password: String, displayName: String): UserPublic =
        withContext(Dispatchers.IO) {
            val esc = { s: String -> s.replace("\\", "\\\\").replace("\"", "\\\"") }
            val payload = "{\"email\":\"${esc(email)}\"," +
                    "\"password\":\"${esc(password)}\"," +
                    "\"display_name\":\"${esc(displayName)}\"}"
            val httpReq = Request.Builder()
                .url(url("auth/register"))
                .post(payload.toRequestBody(jsonMedia))
                .build()
            http.newCall(httpReq).execute().use { resp ->
                val body = resp.body?.string() ?: ""
                if (!resp.isSuccessful) {
                    val msg = when (resp.code) {
                        409 -> "Email already registered"
                        422 -> "Invalid email or password"
                        else -> "HTTP ${resp.code}"
                    }
                    error(msg)
                }
                json.decodeFromString(UserPublic.serializer(), body)
            }
        }

    suspend fun me(): UserPublic = withContext(Dispatchers.IO) {
        val req = Request.Builder().url(url("auth/me")).get().build()
        http.newCall(req).execute().use { resp ->
            if (!resp.isSuccessful) error("HTTP ${resp.code}")
            val body = resp.body?.string() ?: error("empty body")
            json.decodeFromString(UserPublic.serializer(), body)
        }
    }

    // ---------------- devices ----------------

    suspend fun listDevices(): List<DeviceDto> = withContext(Dispatchers.IO) {
        val req = Request.Builder().url(url("devices")).get().build()
        http.newCall(req).execute().use { resp ->
            if (resp.code == 401) error("unauthorized")
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

    // ---------------- system metrics ----------------

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
