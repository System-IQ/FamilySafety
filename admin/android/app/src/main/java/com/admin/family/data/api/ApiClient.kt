package com.admin.family.data.api

import com.admin.family.data.api.dto.DeviceDto
import com.admin.family.data.api.dto.DeviceListResponse
import com.admin.family.data.api.dto.HealthDto
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import kotlinx.serialization.json.Json
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import java.util.concurrent.TimeUnit

class ApiClient(baseUrl: String) {

    private val root = baseUrl.trimEnd('/') + "/"
    private val json = Json {
        ignoreUnknownKeys = true
        explicitNulls = false
    }

    private val http = OkHttpClient.Builder()
        .connectTimeout(10, TimeUnit.SECONDS)
        .readTimeout(20, TimeUnit.SECONDS)
        .build()

    private val jsonMedia = "application/json; charset=utf-8".toMediaType()

    suspend fun health(): HealthDto = withContext(Dispatchers.IO) {
        val req = Request.Builder().url(root + "health").get().build()
        http.newCall(req).execute().use { resp ->
            if (!resp.isSuccessful) error("HTTP ${resp.code}")
            val body = resp.body?.string() ?: error("empty body")
            json.decodeFromString(HealthDto.serializer(), body)
        }
    }

    suspend fun listDevices(): List<DeviceDto> = withContext(Dispatchers.IO) {
        val req = Request.Builder().url(root + "devices").get().build()
        http.newCall(req).execute().use { resp ->
            if (!resp.isSuccessful) error("HTTP ${resp.code}")
            val body = resp.body?.string() ?: error("empty body")
            json.decodeFromString(DeviceListResponse.serializer(), body).devices
        }
    }

    suspend fun upsertDevice(device: DeviceDto): DeviceDto = withContext(Dispatchers.IO) {
        val payload = json.encodeToString(DeviceDto.serializer(), device)
        val req = Request.Builder()
            .url(root + "devices")
            .post(payload.toRequestBody(jsonMedia))
            .build()
        http.newCall(req).execute().use { resp ->
            if (!resp.isSuccessful) error("HTTP ${resp.code}")
            val body = resp.body?.string() ?: error("empty body")
            json.decodeFromString(DeviceDto.serializer(), body)
        }
    }
}
