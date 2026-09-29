package com.admin.family.ui.settings

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.admin.family.data.api.ApiClient
import com.admin.family.data.prefs.AppPreferences
import com.admin.family.data.repository.SettingsRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

/**
 * Settings screen state machine.
 *
 * Flow:
 *  1. User edits URL input
 *  2. Save -> normalize + validate + persist + update ApiClient
 *  3. Test connection -> GET /health (real network call)
 *  4. UI reflects outcome (green/red + details)
 */
class SettingsViewModel(
    private val settingsRepo: SettingsRepository,
    private val apiClient: ApiClient,
    private val clock: () -> Long = System::currentTimeMillis,
) : ViewModel() {

    private val _state = MutableStateFlow(
        SettingsUiState(
            apiBaseUrlInput = settingsRepo.apiBaseUrl,
            savedApiBaseUrl = settingsRepo.apiBaseUrl,
            lastSuccessAtMillis = settingsRepo.lastTestSuccessAtMillis,
            lastFailureAtMillis = settingsRepo.lastTestFailureAtMillis,
        )
    )
    val state: StateFlow<SettingsUiState> = _state.asStateFlow()

    fun onUrlInputChanged(input: String) {
        _state.update { it.copy(apiBaseUrlInput = input, urlError = null) }
    }

    /**
     * Validate the current input. Returns true if valid.
     * On failure, sets `urlError` in state.
     */
    fun validateInput(): Boolean {
        val raw = _state.value.apiBaseUrlInput.trim()
        return try {
            AppPreferences.normalize(raw)
            _state.update { it.copy(urlError = null) }
            true
        } catch (e: IllegalArgumentException) {
            _state.update { it.copy(urlError = e.message ?: "Invalid URL") }
            false
        }
    }

    /**
     * Persist the current input as the new base URL and update ApiClient.
     * Assumes input already validated.
     */
    fun save() {
        if (!validateInput()) return
        val normalized = AppPreferences.normalize(_state.value.apiBaseUrlInput)
        settingsRepo.saveBaseUrl(normalized)
        apiClient.updateBaseUrl(normalized)
        _state.update {
            it.copy(
                apiBaseUrlInput = normalized,
                savedApiBaseUrl = normalized,
                urlError = null,
            )
        }
    }

    fun resetToDefaults() {
        settingsRepo.resetToDefaults()
        val defaultUrl = settingsRepo.apiBaseUrl
        apiClient.updateBaseUrl(defaultUrl)
        _state.update {
            it.copy(
                apiBaseUrlInput = defaultUrl,
                savedApiBaseUrl = defaultUrl,
                urlError = null,
                testResult = ConnectionTestResult.Idle,
            )
        }
    }

    /**
     * Real HTTP call to /health. Updates state with result.
     * Safe to call multiple times — previous call is cancelled only if
     * the caller triggers a new one (ViewModelScope handles scope).
     */
    fun testConnection() {
        if (!validateInput()) return
        _state.update { it.copy(testResult = ConnectionTestResult.Testing) }
        viewModelScope.launch {
            val now = clock()
            try {
                val health = apiClient.health()
                settingsRepo.recordTestSuccess(now)
                _state.update {
                    it.copy(
                        testResult = ConnectionTestResult.Success(health, now),
                        lastSuccessAtMillis = now,
                    )
                }
            } catch (t: Throwable) {
                settingsRepo.recordTestFailure(now)
                val msg = t.message?.takeIf { it.isNotBlank() } ?: "Connection failed"
                _state.update {
                    it.copy(
                        testResult = ConnectionTestResult.Failure(msg, now),
                        lastFailureAtMillis = now,
                    )
                }
            }
        }
    }
}

class SettingsViewModelFactory(
    private val settingsRepo: SettingsRepository,
    private val apiClient: ApiClient,
) : ViewModelProvider.Factory {
    @Suppress("UNCHECKED_CAST")
    override fun <T : ViewModel> create(modelClass: Class<T>): T =
        SettingsViewModel(settingsRepo, apiClient) as T
}
