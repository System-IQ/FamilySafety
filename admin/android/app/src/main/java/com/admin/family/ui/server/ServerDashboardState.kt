package com.admin.family.ui.server

import com.admin.family.data.api.dto.SystemMetrics

sealed interface DashboardState {
    data object Loading : DashboardState
    data class Ready(
        val metrics: SystemMetrics,
        val lastUpdateMillis: Long,
        val consecutiveFails: Int = 0,
    ) : DashboardState
    data class Failed(
        val message: String,
        val lastUpdateMillis: Long = 0L,
        val consecutiveFails: Int = 0,
    ) : DashboardState
}

data class ServerDashboardUiState(
    val state: DashboardState = DashboardState.Loading,
    val serverUrl: String = "",
    val autoRefresh: Boolean = true,
    val refreshIntervalMs: Long = 3000L,
)
