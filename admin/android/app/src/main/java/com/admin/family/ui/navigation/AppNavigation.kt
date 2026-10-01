package com.admin.family.ui.navigation

import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.fragment.app.FragmentActivity
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.NavHostController
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import com.admin.family.biometric.BiometricAvailability
import com.admin.family.biometric.BiometricHelper
import com.admin.family.data.api.ApiClient
import com.admin.family.data.api.ControlClient
import com.admin.family.data.auth.AccessCodeStore
import com.admin.family.data.auth.ControlTokenStore
import com.admin.family.data.prefs.AppPreferences
import com.admin.family.data.repository.DeviceRepository
import com.admin.family.data.repository.SettingsRepository
import com.admin.family.ui.auth.AccessCodeScreen
import com.admin.family.ui.auth.BiometricGateScreen
import com.admin.family.ui.controlroom.ControlRoomScreen
import com.admin.family.ui.controlroom.ControlRoomViewModel
import com.admin.family.ui.controlroom.ControlRoomViewModelFactory
import com.admin.family.ui.server.ServerDashboardScreen
import com.admin.family.ui.server.ServerDashboardViewModel
import com.admin.family.ui.server.ServerDashboardViewModelFactory
import com.admin.family.ui.server.ServerInfoScreen
import com.admin.family.ui.server.ServerInfoViewModel
import com.admin.family.ui.server.ServerInfoViewModelFactory
import com.admin.family.ui.settings.SettingsScreen
import com.admin.family.ui.settings.SettingsViewModel
import com.admin.family.ui.settings.SettingsViewModelFactory
import kotlinx.coroutines.launch

object Routes {
    const val ACCESS_CODE = "access_code"
    const val BIOMETRIC_GATE = "biometric_gate"
    const val CONTROL_ROOM = "control_room"
    const val SETTINGS = "settings"
    const val SERVER_DASHBOARD = "server_dashboard"
    const val SERVER_INFO = "server_info"
}

@Composable
fun AppNavigation(
    activity: FragmentActivity,
    deviceRepository: DeviceRepository,
    settingsRepository: SettingsRepository,
    apiClient: ApiClient,
    accessCodeStore: AccessCodeStore,
    preferences: AppPreferences,
    controlClient: ControlClient,
    controlTokenStore: ControlTokenStore,
    onBootstrapBackend: (String) -> Unit,
) {
    val navController: NavHostController = rememberNavController()
    val scope = rememberCoroutineScope()
    val biometric = remember { BiometricHelper(activity) }

    val startDestination = when {
        !accessCodeStore.isConfigured() -> Routes.ACCESS_CODE
        accessCodeStore.biometricEnabled -> Routes.BIOMETRIC_GATE
        else -> Routes.CONTROL_ROOM
    }

    var biometricError by remember { mutableStateOf<String?>(null) }

    NavHost(navController = navController, startDestination = startDestination) {

        // ── 1. Access Code ──
        composable(Routes.ACCESS_CODE) {
            AccessCodeScreen(
                biometricAvailability = biometric.isAvailable(),
                initialCode = accessCodeStore.code ?: "",
                errorMessage = null,
                onUnlock = { code, enableBio ->
                    accessCodeStore.biometricEnabled = enableBio
                    onBootstrapBackend(code)
                    navController.navigate(Routes.CONTROL_ROOM) {
                        popUpTo(Routes.ACCESS_CODE) { inclusive = true }
                    }
                },
            )
        }

        // ── 2. Biometric Gate ──
        composable(Routes.BIOMETRIC_GATE) {
            val availability = remember { biometric.isAvailable() }

            // Trigger prompt on first composition
            LaunchedEffect(Unit) {
                if (availability == BiometricAvailability.AVAILABLE) {
                    val r = biometric.authenticate()
                    r.fold(
                        onSuccess = {
                            val code = accessCodeStore.code
                            if (!code.isNullOrBlank()) {
                                onBootstrapBackend(code)
                                navController.navigate(Routes.CONTROL_ROOM) {
                                    popUpTo(Routes.BIOMETRIC_GATE) { inclusive = true }
                                }
                            } else {
                                biometricError = "No access code saved"
                            }
                        },
                        onFailure = { t ->
                            biometricError = t.message ?: "Authentication failed"
                        },
                    )
                }
            }

            BiometricGateScreen(
                biometricAvailable = availability == BiometricAvailability.AVAILABLE,
                message = biometricError,
                onRetry = {
                    biometricError = null
                    scope.launch {
                        val r = biometric.authenticate()
                        r.fold(
                            onSuccess = {
                                val code = accessCodeStore.code
                                if (!code.isNullOrBlank()) {
                                    onBootstrapBackend(code)
                                    navController.navigate(Routes.CONTROL_ROOM) {
                                        popUpTo(Routes.BIOMETRIC_GATE) { inclusive = true }
                                    }
                                }
                            },
                            onFailure = { t ->
                                biometricError = t.message ?: "Authentication failed"
                            },
                        )
                    }
                },
                onFallbackToCode = {
                    navController.navigate(Routes.ACCESS_CODE) {
                        popUpTo(Routes.BIOMETRIC_GATE) { inclusive = true }
                    }
                },
            )
        }

        // ── 3. Control Room ──
        composable(Routes.CONTROL_ROOM) {
            val vm: ControlRoomViewModel = viewModel(
                factory = ControlRoomViewModelFactory(deviceRepository),
            )
            ControlRoomScreen(
                vm = vm,
                onOpenSettings = { navController.navigate(Routes.SETTINGS) },
                onOpenServer = { navController.navigate(Routes.SERVER_DASHBOARD) },
                onLogout = {
                    accessCodeStore.clear()
                    apiClient.setAuthToken(null)
                    navController.navigate(Routes.ACCESS_CODE) {
                        popUpTo(0) { inclusive = true }
                    }
                },
            )
        }

        // ── 4. Settings ──
        composable(Routes.SETTINGS) {
            val vm: SettingsViewModel = viewModel(
                factory = SettingsViewModelFactory(settingsRepository, apiClient),
            )
            SettingsScreen(viewModel = vm, onBack = { navController.popBackStack() })
        }

        // ── 5. Server Dashboard ──
        composable(Routes.SERVER_DASHBOARD) {
            val vm: ServerDashboardViewModel = viewModel(
                factory = ServerDashboardViewModelFactory(apiClient),
            )
            ServerDashboardScreen(
                vm = vm,
                onBack = { navController.popBackStack() },
                onOpenServerInfo = { navController.navigate(Routes.SERVER_INFO) },
            )
        }

        // ── 6. Server Info ──
        composable(Routes.SERVER_INFO) {
            val vm: ServerInfoViewModel = viewModel(
                factory = ServerInfoViewModelFactory(controlClient, controlTokenStore),
            )
            ServerInfoScreen(vm = vm, onBack = { navController.popBackStack() })
        }
    }
}
