package com.admin.family.ui.server

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.admin.family.data.api.ApiClient
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch

/**
 * Server Dashboard — live poll /metrics every 3 seconds.
 *
 * Features:
 * - Auto-refresh with adaptive backoff on failure
 * - Keeps last known good metrics when a request fails
 * - Pauses polling when autoRefresh = false
 */
class ServerDashboardViewModel(
    private val apiClient: ApiClient,
    private val clock: () -> Long = System::currentTimeMillis,
) : ViewModel() {

    private val _ui = MutableStateFlow(
        ServerDashboardUiState(serverUrl = apiClient.baseUrl)
    )
    val ui: StateFlow<ServerDashboardUiState> = _ui.asStateFlow()

    private var pollJob: Job? = null

    init { startPolling() }

    fun refreshNow() {
        viewModelScope.launch { pollOnce() }
    }

    fun toggleAutoRefresh() {
        val enabled = !_ui.value.autoRefresh
        _ui.update { it.copy(autoRefresh = enabled) }
        if (enabled) startPolling() else stopPolling()
    }

    private fun startPolling() {
        pollJob?.cancel()
        pollJob = viewModelScope.launch {
            while (isActive) {
                pollOnce()
                val interval = _ui.value.refreshIntervalMs
                delay(interval)
            }
        }
    }

    private fun stopPolling() {
        pollJob?.cancel()
        pollJob = null
    }

    private suspend fun pollOnce() {
        val now = clock()
        try {
            val metrics = apiClient.systemMetrics()
            _ui.update {
                it.copy(
                    state = DashboardState.Ready(metrics, now, 0),
                    serverUrl = apiClient.baseUrl,
                )
            }
        } catch (t: Throwable) {
            val prev = _ui.value.state
            val fails = when (prev) {
                is DashboardState.Ready -> prev.consecutiveFails + 1
                is DashboardState.Failed -> prev.consecutiveFails + 1
                else -> 1
            }
            // 2 attempts grace (server may be restarting), then explicit Failed
            if (prev is DashboardState.Ready && fails < 2) {
                _ui.update {
                    it.copy(state = prev.copy(consecutiveFails = fails))
                }
            } else {
                val msg = when {
                    t is java.net.SocketTimeoutException -> "Server not responding (timeout)"
                    t is java.net.ConnectException -> "Server appears to be stopped"
                    t is java.net.UnknownHostException -> "Server unreachable"
                    t.message?.contains("HTTP 502") == true -> "Server gateway error"
                    else -> t.message ?: "Connection failed"
                }
                _ui.update {
                    it.copy(
                        state = DashboardState.Failed(
                            message = msg,
                            lastUpdateMillis = now,
                        )
                    )
                }
            }
        }
    }

    fun onScreenVisible() {
        if (_ui.value.autoRefresh) {
            startPolling()
        }
    }

    fun onScreenHidden() {
        stopPolling()
    }

    override fun onCleared() {
        super.onCleared()
        stopPolling()
    }
}

class ServerDashboardViewModelFactory(
    private val apiClient: ApiClient,
) : ViewModelProvider.Factory {
    @Suppress("UNCHECKED_CAST")
    override fun <T : ViewModel> create(modelClass: Class<T>): T =
        ServerDashboardViewModel(apiClient) as T
}
