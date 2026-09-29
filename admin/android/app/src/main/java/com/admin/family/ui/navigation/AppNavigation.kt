package com.admin.family.ui.navigation

import androidx.compose.runtime.Composable
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.NavHostController
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import com.admin.family.data.api.ApiClient
import com.admin.family.data.repository.DeviceRepository
import com.admin.family.data.repository.SettingsRepository
import com.admin.family.data.tsnet.AuthKeyStore
import com.admin.family.data.tsnet.TsnetServerWrapper
import com.admin.family.ui.controlroom.ControlRoomScreen
import com.admin.family.ui.controlroom.ControlRoomViewModel
import com.admin.family.ui.controlroom.ControlRoomViewModelFactory
import com.admin.family.ui.server.ServerControlScreen
import com.admin.family.ui.server.ServerControlViewModel
import com.admin.family.ui.server.ServerControlViewModelFactory
import com.admin.family.ui.settings.SettingsScreen
import com.admin.family.ui.settings.SettingsViewModel
import com.admin.family.ui.settings.SettingsViewModelFactory

object Routes {
    const val CONTROL_ROOM = "control_room"
    const val SETTINGS = "settings"
    const val SERVER = "server"
}

@Composable
fun AppNavigation(
    deviceRepository: DeviceRepository,
    settingsRepository: SettingsRepository,
    apiClient: ApiClient,
    tsnetWrapper: TsnetServerWrapper,
    authKeyStore: AuthKeyStore,
    navController: NavHostController = rememberNavController(),
) {
    NavHost(navController = navController, startDestination = Routes.CONTROL_ROOM) {
        composable(Routes.CONTROL_ROOM) {
            val vm: ControlRoomViewModel = viewModel(
                factory = ControlRoomViewModelFactory(deviceRepository),
            )
            ControlRoomScreen(
                vm = vm,
                onOpenSettings = { navController.navigate(Routes.SETTINGS) },
                onOpenServer = { navController.navigate(Routes.SERVER) },
            )
        }
        composable(Routes.SETTINGS) {
            val vm: SettingsViewModel = viewModel(
                factory = SettingsViewModelFactory(settingsRepository, apiClient),
            )
            SettingsScreen(viewModel = vm, onBack = { navController.popBackStack() })
        }
        composable(Routes.SERVER) {
            val vm: ServerControlViewModel = viewModel(
                factory = ServerControlViewModelFactory(tsnetWrapper, authKeyStore),
            )
            ServerControlScreen(vm = vm, onBack = { navController.popBackStack() })
        }
    }
}
