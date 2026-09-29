package com.admin.family.ui.settings

import com.admin.family.data.api.dto.HealthDto

sealed interface ConnectionTestResult {
    object Idle : ConnectionTestResult
    object Testing : ConnectionTestResult
    data class Success(
        val health: HealthDto,
        val testedAtMillis: Long,
    ) : ConnectionTestResult
    data class Failure(
        val message: String,
        val testedAtMillis: Long,
    ) : ConnectionTestResult
}

data class SettingsUiState(
    val apiBaseUrlInput: String,
    val savedApiBaseUrl: String,
    val urlError: String? = null,
    val testResult: ConnectionTestResult = ConnectionTestResult.Idle,
    val lastSuccessAtMillis: Long = 0L,
    val lastFailureAtMillis: Long = 0L,
)
