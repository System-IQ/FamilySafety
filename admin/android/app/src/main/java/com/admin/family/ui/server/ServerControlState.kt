package com.admin.family.ui.server

sealed interface ServerState {
    data object Stopped : ServerState
    data object Starting : ServerState
    data class Running(val tailnetIp: String) : ServerState
    data class Failed(val message: String) : ServerState
}

data class ServerControlUiState(
    val state: ServerState = ServerState.Stopped,
    val authKeySaved: Boolean = false,
    val authKeyInput: String = "",
    val hostname: String = "admin-phone",
    val proxyPort: Int = 8000,
    val proxyTarget: String = "http://127.0.0.1:8001",
)
