package com.admin.family.ui.navigation

import androidx.compose.runtime.Composable
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.NavHostController
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import com.admin.family.data.api.ApiClient
import com.admin.family.data.auth.TokenStore
import com.admin.family.data.prefs.AppPreferences
import com.admin.family.data.repository.AuthRepository
import com.admin.family.data.repository.DeviceRepository
import com.admin.family.data.repository.SettingsRepository
import com.admin.family.ui.auth.LoginScreen
import com.admin.family.ui.auth.LoginViewModel
import com.admin.family.ui.auth.LoginViewModelFactory
import com.admin.family.ui.controlroom.ControlRoomScreen
import com.admin.family.ui.controlroom.ControlRoomViewModel
import com.admin.family.ui.controlroom.ControlRoomViewModelFactory
import com.admin.family.ui.server.ServerDashboardScreen
import com.admin.family.ui.server.ServerDashboardViewModel
import com.admin.family.ui.server.ServerDashboardViewModelFactory
import com.admin.family.ui.settings.SettingsScreen
import com.admin.family.ui.settings.SettingsViewModel
import com.admin.family.ui.settings.SettingsViewModelFactory

object Routes {
    const val LOGIN = "login"
    const val CONTROL_ROOM = "control_room"
    const val SETTINGS = "settings"
    const val SERVER_DASHBOARD = "server_dashboard"
}

@Composable
fun AppNavigation(
    deviceRepository: DeviceRepository,
    settingsRepository: SettingsRepository,
    apiClient: ApiClient,
    authRepository: AuthRepository,
    tokenStore: TokenStore,
    preferences: AppPreferences,
    navController: NavHostController = rememberNavController(),
) {
    // Start at LOGIN if no token, otherwise go straight to CONTROL_ROOM
    val startDestination = if (authRepository.isLoggedIn()) {
        Routes.CONTROL_ROOM
    } else {
        Routes.LOGIN
    }

    NavHost(
        navController = navController,
        startDestination = startDestination,
    ) {
        composable(Routes.LOGIN) {
            val vm: LoginViewModel = viewModel(
                factory = LoginViewModelFactory(apiClient, authRepository, tokenStore, settingsRepository, preferences),
            )
            LoginScreen(
                vm = vm,
                onSuccess = {
                    navController.navigate(Routes.CONTROL_ROOM) {
                        popUpTo(Routes.LOGIN) { inclusive = true }
                    }
                },
            )
        }

        composable(Routes.CONTROL_ROOM) {
            val vm: ControlRoomViewModel = viewModel(
                factory = ControlRoomViewModelFactory(deviceRepository),
            )
            ControlRoomScreen(
                vm = vm,
                onOpenSettings = { navController.navigate(Routes.SETTINGS) },
                onOpenServer = { navController.navigate(Routes.SERVER_DASHBOARD) },
                onLogout = {
                    authRepository.logout()
                    apiClient.setAuthToken(null)
                    navController.navigate(Routes.LOGIN) {
                        popUpTo(0) { inclusive = true }
                    }
                },
            )
        }

        composable(Routes.SETTINGS) {
            val vm: SettingsViewModel = viewModel(
                factory = SettingsViewModelFactory(settingsRepository, apiClient),
            )
            SettingsScreen(viewModel = vm, onBack = { navController.popBackStack() })
        }

        composable(Routes.SERVER_DASHBOARD) {
            val vm: ServerDashboardViewModel = viewModel(
                factory = ServerDashboardViewModelFactory(apiClient),
            )
            ServerDashboardScreen(
                vm = vm,
                onBack = { navController.popBackStack() },
            )
        }
    }
}
