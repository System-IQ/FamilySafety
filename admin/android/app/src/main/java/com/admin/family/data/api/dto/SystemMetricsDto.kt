package com.admin.family.data.api.dto

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class CpuMetrics(
    @SerialName("load_1m") val load1m: Double = 0.0,
    @SerialName("load_5m") val load5m: Double = 0.0,
    @SerialName("load_15m") val load15m: Double = 0.0,
    val cores: Int = 1,
    val percent: Double = 0.0,
)

@Serializable
data class MemoryMetrics(
    @SerialName("total_mb") val totalMb: Double = 0.0,
    @SerialName("used_mb") val usedMb: Double = 0.0,
    @SerialName("free_mb") val freeMb: Double = 0.0,
    val percent: Double = 0.0,
)

@Serializable
data class BatteryMetrics(
    val percent: Int? = null,
    val charging: Boolean? = null,
    @SerialName("temperature_c") val temperatureC: Double? = null,
    @SerialName("age_seconds") val ageSeconds: Double? = null,
)

@Serializable
data class StorageMetrics(
    @SerialName("total_mb") val totalMb: Double = 0.0,
    @SerialName("used_mb") val usedMb: Double = 0.0,
    @SerialName("free_mb") val freeMb: Double = 0.0,
    val percent: Double = 0.0,
    val path: String = "",
)

@Serializable
data class ProcessMetrics(
    val pid: Int = 0,
    @SerialName("rss_mb") val rssMb: Double = 0.0,
    val threads: Int = 0,
    @SerialName("uptime_seconds") val uptimeSeconds: Double = 0.0,
)

@Serializable
data class NetworkMetrics(
    @SerialName("rx_rate_bps") val rxRateBps: Double = 0.0,
    @SerialName("tx_rate_bps") val txRateBps: Double = 0.0,
    @SerialName("rx_total_mb") val rxTotalMb: Double = 0.0,
    @SerialName("tx_total_mb") val txTotalMb: Double = 0.0,
    val hostname: String = "",
    val unavailable: Boolean = false,
)

@Serializable
data class DatabaseMetrics(
    @SerialName("size_mb") val sizeMb: Double = 0.0,
    val path: String = "",
)

@Serializable
data class RequestMetrics(
    val total: Long = 0,
    val errors: Long = 0,
)

@Serializable
data class SystemMetrics(
    val timestamp: String = "",
    val cpu: CpuMetrics = CpuMetrics(),
    val memory: MemoryMetrics = MemoryMetrics(),
    val battery: BatteryMetrics = BatteryMetrics(),
    val storage: StorageMetrics = StorageMetrics(),
    val process: ProcessMetrics = ProcessMetrics(),
    val network: NetworkMetrics = NetworkMetrics(),
    val database: DatabaseMetrics = DatabaseMetrics(),
    val requests: RequestMetrics = RequestMetrics(),
)
