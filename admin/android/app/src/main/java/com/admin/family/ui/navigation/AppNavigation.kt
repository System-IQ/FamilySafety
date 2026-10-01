package com.admin.family.ui.navigation

import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.platform.LocalContext
import androidx.fragment.app.FragmentActivity
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.NavHostController
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import com.admin.family.data.api.ApiClient
import com.admin.family.data.auth.AccessCodeStore
import com.admin.family.data.config.ConfigStore
import com.admin.family.data.prefs.AppPreferences
import com.admin.family.data.repository.DeviceRepository
import com.admin.family.data.repository.SettingsRepository
import com.admin.family.ui.config.ConfigurationsScreen
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

object Routes {
    const val CONTROL_ROOM     = "control_room"
    const val SETTINGS         = "settings"
    const val SERVER_DASHBOARD = "server_dashboard"
    const val SERVER_INFO      = "server_info"
    const val CONFIGURATIONS   = "configurations"
}

@Composable
fun AppNavigation(
    activity: FragmentActivity,
    deviceRepository: DeviceRepository,
    settingsRepository: SettingsRepository,
    apiClient: ApiClient,
    accessCodeStore: AccessCodeStore,
    preferences: AppPreferences,
    configStore: ConfigStore,
    onBootstrapBackend: (String) -> Unit,
) {
    val navController: NavHostController = rememberNavController()
    val scope = rememberCoroutineScope()

    NavHost(navController = navController, startDestination = Routes.CONTROL_ROOM) {

        // ────────────────────────────────────────────────────
        //  CONTROL ROOM (main screen)
        // ────────────────────────────────────────────────────
        composable(Routes.CONTROL_ROOM) {
            val vm: ControlRoomViewModel = viewModel(
                factory = ControlRoomViewModelFactory(deviceRepository),
            )
            ControlRoomScreen(
                vm = vm,
                onOpenSettings = { navController.navigate(Routes.SETTINGS) },
                onOpenServer = { navController.navigate(Routes.SERVER_DASHBOARD) },
                onOpenConfigurations = { navController.navigate(Routes.CONFIGURATIONS) },
                onLogout = {
                    // Reset: clear stored code, regenerate a fresh one,
                    // and re-bootstrap the embedded backend silently.
                    accessCodeStore.clear()
                    apiClient.setAuthToken(null)
                    val fresh = accessCodeStore.generateAndSaveCodeIfNeeded()
                    onBootstrapBackend(fresh)
                    navController.navigate(Routes.CONTROL_ROOM) {
                        popUpTo(0) { inclusive = true }
                    }
                },
            )
        }

        // ────────────────────────────────────────────────────
        //  SETTINGS
        // ────────────────────────────────────────────────────
        composable(Routes.SETTINGS) {
            val vm: SettingsViewModel = viewModel(
                factory = SettingsViewModelFactory(settingsRepository, apiClient),
            )
            SettingsScreen(viewModel = vm, onBack = { navController.popBackStack() })
        }

        // ────────────────────────────────────────────────────
        //  SERVER DASHBOARD
        // ────────────────────────────────────────────────────
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

        // ────────────────────────────────────────────────────
        //  SERVER INFO
        // ────────────────────────────────────────────────────
        composable(Routes.SERVER_INFO) {
            val app = LocalContext.current.applicationContext as com.admin.family.FamilyAdminApp
            val vm: ServerInfoViewModel = viewModel(
                factory = ServerInfoViewModelFactory(app),
            )
            ServerInfoScreen(vm = vm, onBack = { navController.popBackStack() })
        }

        // ────────────────────────────────────────────────────
        //  CONFIGURATIONS
        // ────────────────────────────────────────────────────
        composable(Routes.CONFIGURATIONS) {
            var configsList by remember { mutableStateOf(configStore.list()) }
            var activeId by remember { mutableStateOf(configStore.activeId()) }

            fun refresh() {
                configsList = configStore.list()
                activeId = configStore.activeId()
            }

            ConfigurationsScreen(
                configs = configsList,
                activeId = activeId,
                onCreate = { name, url ->
                    val cfg = configStore.create(name, url)
                    configStore.setActive(cfg.id)
                    apiClient.updateBaseUrl(cfg.backendUrl)
                    refresh()
                },
                onActivate = { id ->
                    configStore.setActive(id)
                    configStore.get(id)?.let { cfg ->
                        apiClient.updateBaseUrl(cfg.backendUrl)
                    }
                    refresh()
                },
                onDelete = { id ->
                    configStore.delete(id)
                    refresh()
                },
                onUpdate = { updated ->
                    configStore.save(updated)
                    if (updated.id == activeId) {
                        apiClient.updateBaseUrl(updated.backendUrl)
                    }
                    refresh()
                },
                onBack = { navController.popBackStack() },
            )
        }
    }
}
