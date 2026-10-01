package com.admin.family.ui.auth

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.admin.family.data.api.ApiClient
import com.admin.family.data.auth.TokenStore
import com.admin.family.data.repository.AuthRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

class LoginViewModel(
    private val apiClient: ApiClient,
    private val authRepo: AuthRepository,
    private val tokenStore: TokenStore,
) : ViewModel() {

    private val _ui = MutableStateFlow(
        LoginUiState(
            email = authRepo.userEmail() ?: "",
            serverUrl = apiClient.baseUrl,
        )
    )
    val ui: StateFlow<LoginUiState> = _ui.asStateFlow()

    fun onEmailChanged(v: String) {
        _ui.update { it.copy(email = v.trim(), phase = LoginPhase.Idle) }
    }

    fun onPasswordChanged(v: String) {
        _ui.update { it.copy(password = v, phase = LoginPhase.Idle) }
    }

    fun onDisplayNameChanged(v: String) {
        _ui.update { it.copy(displayName = v, phase = LoginPhase.Idle) }
    }

    fun togglePasswordVisible() {
        _ui.update { it.copy(passwordVisible = !it.passwordVisible) }
    }

    fun toggleMode() {
        _ui.update {
            it.copy(
                mode = if (it.mode == AuthMode.LOGIN) AuthMode.REGISTER else AuthMode.LOGIN,
                phase = LoginPhase.Idle,
            )
        }
    }

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
                    // Push the freshly stored token into ApiClient
                    val tok = tokenStore.accessToken
                    apiClient.setAuthToken(tok)
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
) : ViewModelProvider.Factory {
    @Suppress("UNCHECKED_CAST")
    override fun <T : ViewModel> create(modelClass: Class<T>): T =
        LoginViewModel(apiClient, authRepo, tokenStore) as T
}
