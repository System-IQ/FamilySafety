package com.admin.family.ui.server

import android.app.Application
import android.content.Context
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.admin.family.FamilyAdminApp
import com.admin.family.service.ServerService
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

/**
 * Server Info state — controls the embedded backend + Foreground Service.
 *
 * Everything runs in-process through ServerService;
 * no external agent, no token.
 */
data class ServerInfoUiState(
    val serverEnabled: Boolean = false,     // persisted preference
    val backendReady: Boolean = false,      // uvicorn reachable on 127.0.0.1:8000
    val busy: Boolean = false,              // operation in progress
    val uptimeSeconds: Long = 0L,
    val lastMessage: String? = null,
    val fatalError: String? = null,
)

class ServerInfoViewModel(app: Application) : AndroidViewModel(app) {

    private val adminApp: FamilyAdminApp get() = getApplication()

    private val _ui = MutableStateFlow(
        ServerInfoUiState(serverEnabled = adminApp.preferences.serverEnabled)
    )
    val ui: StateFlow<ServerInfoUiState> = _ui.asStateFlow()

    init {
        // Background poller: every 2s update backendReady + uptime
        viewModelScope.launch {
            while (true) {
                refresh()
                delay(2_000L)
            }
        }
    }

    fun refresh() {
        viewModelScope.launch {
            val enabled = adminApp.preferences.serverEnabled
            val ready = if (enabled) {
                withContext(Dispatchers.IO) { adminApp.isBackendReadyBlocking(0.6) }
            } else false
            _ui.update {
                it.copy(serverEnabled = enabled, backendReady = ready)
            }
        }
    }

    fun startServer(context: Context) {
        if (_ui.value.busy) return
        _ui.update { it.copy(busy = true, lastMessage = "Starting server…", fatalError = null) }
        ServerService.start(context)
        viewModelScope.launch {
            delay(3_000L)
            _ui.update {
                it.copy(busy = false, lastMessage = "Server start requested")
            }
        }
    }

    fun stopServer(context: Context) {
        if (_ui.value.busy) return
        _ui.update { it.copy(busy = true, lastMessage = "Stopping server…", fatalError = null) }
        ServerService.stop(context)
        viewModelScope.launch {
            delay(2_000L)
            _ui.update {
                it.copy(busy = false, lastMessage = "Server stop requested")
            }
        }
    }

    fun clearMessage() = _ui.update { it.copy(lastMessage = null) }
}

class ServerInfoViewModelFactory(
    private val app: Application,
) : ViewModelProvider.Factory {
    @Suppress("UNCHECKED_CAST")
    override fun <T : ViewModel> create(modelClass: Class<T>): T =
        ServerInfoViewModel(app) as T
}
