package com.admin.family.data.api.dto

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class BatteryDto(
    @SerialName("level_percent") val levelPercent: Int,
    val charging: Boolean,
    val timestamp: String,
)

@Serializable
data class LocationCapabilityDto(
    val supported: Boolean,
    @SerialName("permission_state") val permissionState: String,
    @SerialName("background_supported") val backgroundSupported: Boolean,
)

@Serializable
data class DeviceDto(
    @SerialName("device_id") val deviceId: String,
    @SerialName("device_name") val deviceName: String,
    val platform: String,
    @SerialName("android_version") val androidVersion: String,
    @SerialName("app_version") val appVersion: String,
    @SerialName("management_state") val managementState: String,
    @SerialName("connection_state") val connectionState: String,
    val battery: BatteryDto,
    @SerialName("last_seen") val lastSeen: String,
    @SerialName("location_capability") val locationCapability: LocationCapabilityDto,
    @SerialName("created_at") val createdAt: String,
    @SerialName("updated_at") val updatedAt: String,
)

@Serializable
data class DeviceListResponse(val devices: List<DeviceDto>)
