package com.admin.family.ui.controlroom

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.admin.family.data.repository.DeviceRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import java.net.SocketTimeoutException
import java.net.UnknownHostException

class ControlRoomViewModel(
    private val repo: DeviceRepository,
) : ViewModel() {

    private val _state = MutableStateFlow<ControlRoomState>(ControlRoomState.Loading)
    val state: StateFlow<ControlRoomState> = _state.asStateFlow()

    init { refresh() }

    fun refresh() {
        _state.value = ControlRoomState.Loading
        viewModelScope.launch {
            try {
                val health = repo.loadHealth()
                val devices = repo.loadDevices()
                _state.value = ControlRoomState.Ready(health, devices)
            } catch (t: Throwable) {
                _state.value = when {
                    t.message?.contains("unauthorized", ignoreCase = true) == true ||
                            t.message?.contains("401") == true -> ControlRoomState.Unauthorized

                    t is SocketTimeoutException ->
                        ControlRoomState.Failed("Server not responding (timeout)")

                    t is UnknownHostException ->
                        ControlRoomState.Failed("Server unreachable")

                    t.message?.contains("HTTP 502") == true ->
                        ControlRoomState.Failed("Server gateway error")

                    else -> ControlRoomState.Failed(t.message ?: "Connection failed")
                }
            }
        }
    }
}

class ControlRoomViewModelFactory(
    private val repo: DeviceRepository,
) : ViewModelProvider.Factory {
    @Suppress("UNCHECKED_CAST")
    override fun <T : ViewModel> create(modelClass: Class<T>): T =
        ControlRoomViewModel(repo) as T
}
