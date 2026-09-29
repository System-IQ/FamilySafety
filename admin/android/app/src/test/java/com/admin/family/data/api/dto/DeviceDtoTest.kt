package com.admin.family.data.api.dto

import kotlinx.serialization.json.Json
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class DeviceDtoTest {

    private val json = Json { ignoreUnknownKeys = true }

    private val sample = """
    {
      "device_id": "dev_01H8XYZ",
      "device_name": "Ali's Phone",
      "platform": "android",
      "android_version": "14",
      "app_version": "1.0.0",
      "management_state": "managed",
      "connection_state": "online",
      "battery": {
        "level_percent": 78,
        "charging": false,
        "timestamp": "2026-09-29T10:00:00Z"
      },
      "last_seen": "2026-09-29T10:00:00Z",
      "location_capability": {
        "supported": true,
        "permission_state": "granted",
        "background_supported": true
      },
      "created_at": "2026-09-01T00:00:00Z",
      "updated_at": "2026-09-29T10:00:00Z"
    }
    """.trimIndent()

    @Test
    fun `deserializes device contract v1 correctly`() {
        val dto = json.decodeFromString(DeviceDto.serializer(), sample)
        assertEquals("dev_01H8XYZ", dto.deviceId)
        assertEquals("Ali's Phone", dto.deviceName)
        assertEquals("managed", dto.managementState)
        assertEquals(78, dto.battery.levelPercent)
        assertTrue(dto.locationCapability.supported)
    }

    @Test
    fun `round trip preserves fields`() {
        val dto = json.decodeFromString(DeviceDto.serializer(), sample)
        val encoded = json.encodeToString(DeviceDto.serializer(), dto)
        val again = json.decodeFromString(DeviceDto.serializer(), encoded)
        assertEquals(dto, again)
    }
}
