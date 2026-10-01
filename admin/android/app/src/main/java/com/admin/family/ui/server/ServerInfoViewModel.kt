package com.admin.family.ui.server

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.admin.family.data.api.ControlClient
import com.admin.family.data.auth.ControlTokenStore
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

class ServerInfoViewModel(
    private val client: ControlClient,
    private val tokenStore: ControlTokenStore,
) : ViewModel() {

    private val _ui = MutableStateFlow(
        ServerInfoUiState(
            tokenSaved = tokenStore.isConfigured(),
        )
    )
    val ui: StateFlow<ServerInfoUiState> = _ui.asStateFlow()

    init {
        client.token = tokenStore.token
        refresh()
    }

    fun onTokenInputChanged(v: String) = _ui.update {
        it.copy(tokenInput = v.trim(), lastMessage = null)
    }

    fun saveToken() {
        val t = _ui.value.tokenInput
        if (t.isBlank()) return
        tokenStore.token = t
        client.token = t
        _ui.update {
            it.copy(tokenSaved = true, tokenInput = "", lastMessage = "Token saved")
        }
        refresh()
    }

    fun clearToken() {
        tokenStore.clear()
        client.token = null
        _ui.update {
            it.copy(tokenSaved = false, agentReachable = false, status = null, lastMessage = "Token cleared")
        }
    }

    fun refresh() {
        viewModelScope.launch {
            try {
                val reachable = client.ping()
                if (!reachable) {
                    _ui.update {
                        it.copy(
                            agentReachable = false,
                            status = null,
                            lastMessage = "Control agent unreachable (is Termux running?)",
                        )
                    }
                    return@launch
                }
                _ui.update { it.copy(agentReachable = true) }

                if (!tokenStore.isConfigured()) {
                    _ui.update { it.copy(lastMessage = "Enter the fs-control token to continue") }
                    return@launch
                }
                try {
                    val s = client.status()
                    _ui.update { it.copy(status = s, lastMessage = null) }
                } catch (t: Throwable) {
                    _ui.update { it.copy(lastMessage = t.message ?: "Cannot read status") }
                }
            } catch (t: Throwable) {
                _ui.update {
                    it.copy(agentReachable = false, lastMessage = t.message ?: "Unreachable")
                }
            }
        }
    }

    fun startServer() {
        if (!tokenStore.isConfigured()) {
            _ui.update { it.copy(lastMessage = "Save the token first") }
            return
        }
        _ui.update { it.copy(phase = ServerInfoPhase.Starting, lastMessage = "Starting…") }
        viewModelScope.launch {
            try {
                val r = client.start()
                _ui.update {
                    it.copy(
                        phase = ServerInfoPhase.Idle,
                        status = r.status,
                        lastMessage = if (r.ok) "Started in ${r.durationMs} ms" else "Start failed",
                    )
                }
            } catch (t: Throwable) {
                _ui.update {
                    it.copy(
                        phase = ServerInfoPhase.Error(t.message ?: "Start failed"),
                        lastMessage = t.message ?: "Start failed",
                    )
                }
            }
        }
    }

    fun stopServer() {
        if (!tokenStore.isConfigured()) {
            _ui.update { it.copy(lastMessage = "Save the token first") }
            return
        }
        _ui.update { it.copy(phase = ServerInfoPhase.Stopping, lastMessage = "Stopping…") }
        viewModelScope.launch {
            try {
                val r = client.stop()
                _ui.update {
                    it.copy(
                        phase = ServerInfoPhase.Idle,
                        status = r.status,
                        lastMessage = if (r.ok) "Stopped in ${r.durationMs} ms" else "Stop failed",
                    )
                }
            } catch (t: Throwable) {
                _ui.update {
                    it.copy(
                        phase = ServerInfoPhase.Error(t.message ?: "Stop failed"),
                        lastMessage = t.message ?: "Stop failed",
                    )
                }
            }
        }
    }
}

class ServerInfoViewModelFactory(
    private val client: ControlClient,
    private val tokenStore: ControlTokenStore,
) : ViewModelProvider.Factory {
    @Suppress("UNCHECKED_CAST")
    override fun <T : ViewModel> create(modelClass: Class<T>): T =
        ServerInfoViewModel(client, tokenStore) as T
}
