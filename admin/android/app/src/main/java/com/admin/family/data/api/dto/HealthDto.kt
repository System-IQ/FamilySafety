package com.admin.family.data.api.dto

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class HealthCheckDto(val ok: Boolean, val error: String? = null)

@Serializable
data class HealthChecksDto(val database: HealthCheckDto)

@Serializable
data class HealthDto(
    val status: String,
    val environment: String,
    @SerialName("uptime_seconds") val uptimeSeconds: Double,
    val checks: HealthChecksDto,
)
