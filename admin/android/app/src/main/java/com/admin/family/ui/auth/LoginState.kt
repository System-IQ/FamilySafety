package com.admin.family.ui.auth

sealed interface LoginPhase {
    data object Idle : LoginPhase
    data object Authenticating : LoginPhase
    data class Error(val message: String) : LoginPhase
    data object Success : LoginPhase
}

enum class AuthMode { LOGIN, REGISTER }

data class LoginUiState(
    val mode: AuthMode = AuthMode.LOGIN,
    val email: String = "",
    val password: String = "",
    val displayName: String = "",
    val passwordVisible: Boolean = false,
    val phase: LoginPhase = LoginPhase.Idle,
    val serverUrl: String = "",
) {
    val canSubmit: Boolean
        get() = email.contains("@") &&
                password.length >= 12 &&
                (mode == AuthMode.LOGIN || displayName.length >= 1) &&
                phase !is LoginPhase.Authenticating
}
