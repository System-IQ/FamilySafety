package com.admin.family.ui.server

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.admin.family.data.tsnet.AuthKeyStore
import com.admin.family.data.tsnet.TsnetServerWrapper
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

class ServerControlViewModel(
    private val wrapper: TsnetServerWrapper,
    private val authKeyStore: AuthKeyStore,
) : ViewModel() {

    private val _state = MutableStateFlow(
        ServerControlUiState(
            authKeySaved = authKeyStore.authKey != null,
        )
    )
    val state: StateFlow<ServerControlUiState> = _state.asStateFlow()

    fun onAuthKeyChanged(input: String) {
        _state.update { it.copy(authKeyInput = input) }
    }

    fun onHostnameChanged(input: String) {
        _state.update { it.copy(hostname = input) }
    }

    fun saveAuthKey() {
        val key = _state.value.authKeyInput.trim()
        if (key.isEmpty()) return
        authKeyStore.authKey = key
        _state.update { it.copy(authKeySaved = true, authKeyInput = "") }
    }

    fun clearAuthKey() {
        authKeyStore.clear()
        _state.update { it.copy(authKeySaved = false, authKeyInput = "") }
    }

    fun startServer() {
        val key = authKeyStore.authKey ?: return

        _state.update { it.copy(state = ServerState.Starting) }

        viewModelScope.launch {
            val startResult = wrapper.start(
                key,
                _state.value.hostname,
            )

            if (startResult.isFailure) {
                _state.update {
                    it.copy(
                        state = ServerState.Failed(
                            wrapper.lastError ?: "server start failed"
                        )
                    )
                }
                return@launch
            }

            val proxyResult = wrapper.listenAndProxy(
                _state.value.proxyPort,
                _state.value.proxyTarget,
            )

            if (proxyResult.isFailure) {
                _state.update {
                    it.copy(
                        state = ServerState.Failed(
                            wrapper.lastError ?: "proxy start failed"
                        )
                    )
                }
                return@launch
            }

            val ip = wrapper.ip4()

            _state.update {
                it.copy(
                    state = ServerState.Running(ip)
                )
            }
        }
    }

    fun stopServer() {
        wrapper.stop()
        _state.update { it.copy(state = ServerState.Stopped) }
    }

    fun refreshStatus() {
        if (wrapper.isRunning()) {
            _state.update { it.copy(state = ServerState.Running(wrapper.ip4())) }
        } else {
            _state.update { it.copy(state = ServerState.Stopped) }
        }
    }
}

class ServerControlViewModelFactory(
    private val wrapper: TsnetServerWrapper,
    private val authKeyStore: AuthKeyStore,
) : ViewModelProvider.Factory {
    @Suppress("UNCHECKED_CAST")
    override fun <T : ViewModel> create(modelClass: Class<T>): T =
        ServerControlViewModel(wrapper, authKeyStore) as T
}
