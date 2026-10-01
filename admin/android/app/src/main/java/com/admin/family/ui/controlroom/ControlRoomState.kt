package com.admin.family.ui.controlroom

import com.admin.family.data.api.dto.DeviceDto
import com.admin.family.data.api.dto.HealthDto

sealed interface ControlRoomState {
    data object Loading : ControlRoomState
    data object Unauthorized : ControlRoomState
    data class Ready(
        val health: HealthDto,
        val devices: List<DeviceDto>,
    ) : ControlRoomState
    data class Failed(val message: String) : ControlRoomState
}
