package com.admin.family.ui.auth

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.admin.family.data.api.ApiClient
import com.admin.family.data.auth.TokenStore
import com.admin.family.data.prefs.AppPreferences
import com.admin.family.data.repository.AuthRepository
import com.admin.family.data.repository.SettingsRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

class LoginViewModel(
    private val apiClient: ApiClient,
    private val authRepo: AuthRepository,
    private val tokenStore: TokenStore,
    private val settingsRepo: SettingsRepository,
    private val preferences: AppPreferences,
) : ViewModel() {

    private val _ui = MutableStateFlow(
        LoginUiState(
            email = preferences.lastEmail ?: authRepo.userEmail() ?: "",
            serverUrl = apiClient.baseUrl,
        )
    )
    val ui: StateFlow<LoginUiState> = _ui.asStateFlow()

    fun onEmailChanged(v: String) = _ui.update {
        it.copy(email = v.trim(), phase = LoginPhase.Idle)
    }

    fun onPasswordChanged(v: String) = _ui.update {
        it.copy(password = v, phase = LoginPhase.Idle)
    }

    fun onDisplayNameChanged(v: String) = _ui.update {
        it.copy(displayName = v, phase = LoginPhase.Idle)
    }

    fun togglePasswordVisible() = _ui.update {
        it.copy(passwordVisible = !it.passwordVisible)
    }

    fun toggleMode() = _ui.update {
        it.copy(
            mode = if (it.mode == AuthMode.LOGIN) AuthMode.REGISTER else AuthMode.LOGIN,
            phase = LoginPhase.Idle,
        )
    }

    // ── Server URL editing ──

    fun startEditingServerUrl() = _ui.update {
        it.copy(editingServerUrl = true, serverUrlDraft = it.serverUrl, serverUrlError = null)
    }

    fun cancelEditingServerUrl() = _ui.update {
        it.copy(editingServerUrl = false, serverUrlDraft = "", serverUrlError = null)
    }

    fun onServerUrlDraftChanged(v: String) = _ui.update {
        it.copy(serverUrlDraft = v, serverUrlError = null)
    }

    fun saveServerUrl() {
        try {
            val normalized = AppPreferences.normalize(_ui.value.serverUrlDraft)
            settingsRepo.saveBaseUrl(normalized)
            apiClient.updateBaseUrl(normalized)
            _ui.update {
                it.copy(
                    serverUrl = normalized,
                    editingServerUrl = false,
                    serverUrlDraft = "",
                    serverUrlError = null,
                    phase = LoginPhase.Idle,
                )
            }
        } catch (e: IllegalArgumentException) {
            _ui.update { it.copy(serverUrlError = e.message ?: "Invalid URL") }
        }
    }

    fun resetServerUrl() {
        settingsRepo.resetToDefaults()
        val def = settingsRepo.apiBaseUrl
        apiClient.updateBaseUrl(def)
        _ui.update { it.copy(serverUrl = def, serverUrlDraft = def, serverUrlError = null) }
    }

    // ── Submit ──

    fun submit() {
        val s = _ui.value
        if (!s.canSubmit) return
        _ui.update { it.copy(phase = LoginPhase.Authenticating) }

        viewModelScope.launch {
            val result: Result<Unit> = if (s.mode == AuthMode.LOGIN) {
                authRepo.login(s.email, s.password)
            } else {
                try {
                    apiClient.register(s.email, s.password, s.displayName)
                    authRepo.login(s.email, s.password)
                } catch (t: Throwable) {
                    Result.failure(t)
                }
            }
            result.fold(
                onSuccess = {
                    apiClient.setAuthToken(tokenStore.accessToken)
                    preferences.lastEmail = s.email
                    _ui.update { it.copy(phase = LoginPhase.Success) }
                },
                onFailure = { t ->
                    _ui.update {
                        it.copy(
                            phase = LoginPhase.Error(t.message ?: "Authentication failed"),
                        )
                    }
                },
            )
        }
    }
}

class LoginViewModelFactory(
    private val apiClient: ApiClient,
    private val authRepo: AuthRepository,
    private val tokenStore: TokenStore,
    private val settingsRepo: SettingsRepository,
    private val preferences: AppPreferences,
) : ViewModelProvider.Factory {
    @Suppress("UNCHECKED_CAST")
    override fun <T : ViewModel> create(modelClass: Class<T>): T =
        LoginViewModel(apiClient, authRepo, tokenStore, settingsRepo, preferences) as T
}
