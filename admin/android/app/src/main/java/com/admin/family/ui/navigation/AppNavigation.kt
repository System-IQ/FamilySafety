package com.admin.family.ui.navigation

import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.fragment.app.FragmentActivity
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import androidx.lifecycle.compose.LocalLifecycleOwner
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
import com.admin.family.data.config.ConfigStore
import com.admin.family.data.prefs.AppPreferences
import com.admin.family.data.repository.DeviceRepository
import com.admin.family.data.repository.SettingsRepository
import com.admin.family.ui.auth.BackupCodesScreen
import com.admin.family.ui.auth.BiometricGateScreen
import com.admin.family.ui.auth.ForgotPinScreen
import com.admin.family.ui.auth.PinEntryScreen
import com.admin.family.ui.auth.PinSetupScreen
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
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

object Routes {
    const val PIN_SETUP       = "pin_setup"
    const val PIN_ENTRY       = "pin_entry"
    const val BACKUP_CODES    = "backup_codes"
    const val FORGOT_PIN      = "forgot_pin"
    const val BIOMETRIC_GATE  = "biometric_gate"
    const val CONTROL_ROOM    = "control_room"
    const val SETTINGS        = "settings"
    const val SERVER_DASHBOARD = "server_dashboard"
    const val SERVER_INFO     = "server_info"
    const val CONFIGURATIONS  = "configurations"
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
    configStore: ConfigStore,
    onBootstrapBackend: (String) -> Unit,
) {
    val navController: NavHostController = rememberNavController()
    val scope = rememberCoroutineScope()
    val biometric = remember { BiometricHelper(activity) }

    // Decide where to start:
    //  • No PIN yet → PIN_SETUP (first launch only)
    //  • PIN + session still valid → CONTROL_ROOM directly
    //  • PIN + biometric enabled → BIOMETRIC_GATE
    //  • Otherwise → PIN_ENTRY
    val startDestination = when {
        !accessCodeStore.isConfigured() -> Routes.PIN_SETUP
        accessCodeStore.isSessionValid() -> Routes.CONTROL_ROOM
        accessCodeStore.biometricEnabled -> Routes.BIOMETRIC_GATE
        else -> Routes.PIN_ENTRY
    }

    var biometricError by remember { mutableStateOf<String?>(null) }
    var pinEntryError by remember { mutableStateOf<String?>(null) }
    var generatedBackupCodes by remember { mutableStateOf<List<String>>(emptyList()) }

    fun isProtectedRoute(route: String?): Boolean = route == Routes.CONTROL_ROOM ||
            route == Routes.SETTINGS ||
            route == Routes.SERVER_DASHBOARD ||
            route == Routes.SERVER_INFO ||
            route == Routes.CONFIGURATIONS

    fun lockScreen() {
        pinEntryError = null
        val target = if (accessCodeStore.biometricEnabled) Routes.BIOMETRIC_GATE else Routes.PIN_ENTRY
        navController.navigate(target) {
            popUpTo(0) { inclusive = true }
        }
    }

    // ─── 30-minute idle timer while app is in foreground ───
    LaunchedEffect(Unit) {
        while (true) {
            delay(15_000L)
            val route = navController.currentDestination?.route
            if (isProtectedRoute(route) && !accessCodeStore.isSessionValid()) {
                lockScreen()
            }
        }
    }

    // ─── Re-lock when returning from background after timeout ───
    val lifecycleOwner = LocalLifecycleOwner.current
    DisposableEffect(lifecycleOwner) {
        val observer = LifecycleEventObserver { _, event ->
            if (event == Lifecycle.Event.ON_START) {
                val route = navController.currentDestination?.route
                if (isProtectedRoute(route) && !accessCodeStore.isSessionValid()) {
                    lockScreen()
                }
            }
        }
        lifecycleOwner.lifecycle.addObserver(observer)
        onDispose { lifecycleOwner.lifecycle.removeObserver(observer) }
    }

    NavHost(navController = navController, startDestination = startDestination) {

        // ─── 1. PIN SETUP (first-time only) ───
        composable(Routes.PIN_SETUP) {
            PinSetupScreen(
                isReset = false,
                onCancel = null,
                onPinReady = { pin ->
                    if (accessCodeStore.setupPin(pin)) {
                        accessCodeStore.markUnlocked()
                        val codes = accessCodeStore.generateAndStoreBackupCodes()
                        generatedBackupCodes = codes
                        val newCode = accessCodeStore.code
                        if (!newCode.isNullOrBlank()) {
                            onBootstrapBackend(newCode)
                        }
                        navController.navigate(Routes.BACKUP_CODES) {
                            popUpTo(Routes.PIN_SETUP) { inclusive = true }
                        }
                    }
                },
            )
        }

        // ─── 2. BACKUP CODES (one-time display) ───
        composable(Routes.BACKUP_CODES) {
            BackupCodesScreen(
                codes = generatedBackupCodes,
                onDone = {
                    accessCodeStore.markUnlocked()
                    navController.navigate(Routes.CONTROL_ROOM) {
                        popUpTo(0) { inclusive = true }
                    }
                },
            )
        }

        // ─── 3. PIN ENTRY ───
        composable(Routes.PIN_ENTRY) {
            PinEntryScreen(
                errorMessage = pinEntryError,
                biometricAvailability = biometric.isAvailable(),
                recoveryEmailHint = accessCodeStore.recoveryEmail,
                onUnlock = { pin ->
                    pinEntryError = null
                    if (accessCodeStore.verifyPin(pin)) {
                        accessCodeStore.markUnlocked()
                        val code = accessCodeStore.code
                        if (!code.isNullOrBlank()) {
                            onBootstrapBackend(code)
                        }
                        navController.navigate(Routes.CONTROL_ROOM) {
                            popUpTo(0) { inclusive = true }
                        }
                    } else {
                        pinEntryError = "Incorrect PIN"
                    }
                },
                onForgotPin = {
                    pinEntryError = null
                    navController.navigate(Routes.FORGOT_PIN)
                },
                onBiometricRequest = {
                    pinEntryError = null
                    scope.launch {
                        val r = biometric.authenticate()
                        r.fold(
                            onSuccess = {
                                val code = accessCodeStore.code
                                if (!code.isNullOrBlank()) {
                                    accessCodeStore.markUnlocked()
                                    onBootstrapBackend(code)
                                    navController.navigate(Routes.CONTROL_ROOM) {
                                        popUpTo(0) { inclusive = true }
                                    }
                                } else {
                                    pinEntryError = "No access code saved"
                                }
                            },
                            onFailure = { t ->
                                pinEntryError = t.message ?: "Authentication failed"
                            },
                        )
                    }
                },
            )
        }

        // ─── 4. FORGOT PIN (backup codes recovery) ───
        composable(Routes.FORGOT_PIN) {
            ForgotPinScreen(
                remainingCodes = accessCodeStore.backupCodesRemaining(),
                verifyCode = { input ->
                    accessCodeStore.verifyAndBurnBackupCode(input)
                },
                setNewPin = { newPin ->
                    accessCodeStore.resetWithNewPin(newPin)
                    accessCodeStore.markUnlocked()
                },
                onBack = {
                    navController.popBackStack()
                },
            )
        }

        // ─── 5. BIOMETRIC GATE ───
        composable(Routes.BIOMETRIC_GATE) {
            val availability = remember { biometric.isAvailable() }

            LaunchedEffect(Unit) {
                if (availability == BiometricAvailability.AVAILABLE) {
                    val r = biometric.authenticate()
                    r.fold(
                        onSuccess = {
                            val code = accessCodeStore.code
                            if (!code.isNullOrBlank()) {
                                accessCodeStore.markUnlocked()
                                onBootstrapBackend(code)
                                navController.navigate(Routes.CONTROL_ROOM) {
                                    popUpTo(0) { inclusive = true }
                                }
                            } else {
                                biometricError = "No access code saved"
                                navController.navigate(Routes.PIN_ENTRY) {
                                    popUpTo(0) { inclusive = true }
                                }
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
                    if (availability == BiometricAvailability.AVAILABLE) {
                        scope.launch {
                            val r = biometric.authenticate()
                            r.fold(
                                onSuccess = {
                                    val code = accessCodeStore.code
                                    if (!code.isNullOrBlank()) {
                                        accessCodeStore.markUnlocked()
                                        onBootstrapBackend(code)
                                        navController.navigate(Routes.CONTROL_ROOM) {
                                            popUpTo(0) { inclusive = true }
                                        }
                                    }
                                },
                                onFailure = { t -> biometricError = t.message ?: "Authentication failed" },
                            )
                        }
                    }
                },
                onUsePin = {
                    biometricError = null
                    navController.navigate(Routes.PIN_ENTRY) {
                        popUpTo(0) { inclusive = true }
                    }
                },
            )
        }

        // ─── 6. CONTROL ROOM ───
        composable(Routes.CONTROL_ROOM) {
            val vm: ControlRoomViewModel = viewModel(
                factory = ControlRoomViewModelFactory(
                    deviceRepository = deviceRepository,
                    controlClient = controlClient,
                    controlTokenStore = controlTokenStore,
                )
            )
            ControlRoomScreen(
                viewModel = vm,
                onOpenSettings = { navController.navigate(Routes.SETTINGS) },
                onOpenServerInfo = { navController.navigate(Routes.SERVER_INFO) },
                onOpenServerDashboard = { navController.navigate(Routes.SERVER_DASHBOARD) },
                onOpenConfigurations = { navController.navigate(Routes.CONFIGURATIONS) },
            )
        }

        // ─── 7. SETTINGS ───
        composable(Routes.SETTINGS) {
            val vm: SettingsViewModel = viewModel(
                factory = SettingsViewModelFactory(
                    settingsRepository = settingsRepository,
                    preferences = preferences,
                    accessCodeStore = accessCodeStore,
                )
            )
            SettingsScreen(
                viewModel = vm,
                onBack = { navController.popBackStack() },
            )
        }

        // ─── 8. SERVER DASHBOARD ───
        composable(Routes.SERVER_DASHBOARD) {
            val vm: ServerDashboardViewModel = viewModel(
                factory = ServerDashboardViewModelFactory(
                    deviceRepository = deviceRepository,
                    settingsRepository = settingsRepository,
                    apiClient = apiClient,
                )
            )
            ServerDashboardScreen(
                viewModel = vm,
                onBack = { navController.popBackStack() },
            )
        }

        // ─── 9. SERVER INFO ───
        composable(Routes.SERVER_INFO) {
            val vm: ServerInfoViewModel = viewModel(
                factory = ServerInfoViewModelFactory(
                    settingsRepository = settingsRepository,
                    apiClient = apiClient,
                )
            )
            ServerInfoScreen(
                viewModel = vm,
                onBack = { navController.popBackStack() },
            )
        }

        // ─── 10. CONFIGURATIONS ───
        composable(Routes.CONFIGURATIONS) {
            ConfigurationsScreen(
                configStore = configStore,
                onBack = { navController.popBackStack() },
            )
        }
    }
}
