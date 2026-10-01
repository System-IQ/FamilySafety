package com.admin.family.ui.server

import com.admin.family.data.api.ControlStatus

sealed interface ServerInfoPhase {
    data object Idle : ServerInfoPhase
    data object Starting : ServerInfoPhase
    data object Stopping : ServerInfoPhase
    data class Error(val message: String) : ServerInfoPhase
}

data class ServerInfoUiState(
    val phase: ServerInfoPhase = ServerInfoPhase.Idle,
    val status: ControlStatus? = null,
    val tokenSaved: Boolean = false,
    val tokenInput: String = "",
    val agentReachable: Boolean = false,
    val lastMessage: String? = null,
) {
    val isBusy: Boolean
        get() = phase is ServerInfoPhase.Starting || phase is ServerInfoPhase.Stopping
}
