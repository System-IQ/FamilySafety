package com.admin.family.data.repository

import com.admin.family.data.api.ApiClient
import com.admin.family.data.api.dto.DeviceDto
import com.admin.family.data.api.dto.HealthDto

class DeviceRepository(private val api: ApiClient) {

    suspend fun loadHealth(): HealthDto = api.health()
    suspend fun loadDevices(): List<DeviceDto> = api.listDevices()
    suspend fun upsert(device: DeviceDto): DeviceDto = api.upsertDevice(device)
}
