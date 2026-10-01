package com.admin.family

import android.app.Application
import android.util.Log
import com.admin.family.data.api.ApiClient
import com.admin.family.data.api.ControlClient
import com.admin.family.data.auth.ControlTokenStore
import com.admin.family.data.auth.TokenStore
import com.admin.family.data.prefs.AppPreferences
import com.admin.family.data.repository.AuthRepository
import com.admin.family.data.repository.DefaultSettingsRepository
import com.admin.family.data.repository.DeviceRepository
import com.admin.family.data.repository.SettingsRepository
import com.admin.family.python.PythonServer
import com.admin.family.tsnet.TsnetBridge
import com.admin.family.tsnet.TsnetProfileStore
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.launch

class FamilyAdminApp : Application() {

    private val appScope = CoroutineScope(SupervisorJob() + Dispatchers.IO)

    lateinit var preferences: AppPreferences
        private set
    lateinit var settingsRepository: SettingsRepository
        private set
    lateinit var apiClient: ApiClient
        private set
    lateinit var deviceRepository: DeviceRepository
        private set
    lateinit var tokenStore: TokenStore
        private set
    lateinit var authRepository: AuthRepository
        private set
    lateinit var controlClient: ControlClient
        private set
    lateinit var controlTokenStore: ControlTokenStore
        private set
    lateinit var tsnetBridge: TsnetBridge
        private set
    lateinit var tsnetProfiles: TsnetProfileStore
        private set

    override fun onCreate() {
        super.onCreate()
        Log.i(TAG, "onCreate")

        // ── 1. Boot embedded Python ──
        try {
            PythonServer.init(this)
            PythonServer.configure(this)
            Log.i(TAG, "Python configured")
        } catch (t: Throwable) {
            Log.e(TAG, "Python init failed", t)
        }

        // ── 2. DI container ──
        preferences = AppPreferences(this)
        settingsRepository = DefaultSettingsRepository(preferences)
        apiClient = ApiClient(preferences.apiBaseUrl)
        deviceRepository = DeviceRepository(apiClient)
        tokenStore = TokenStore(this)
        authRepository = AuthRepository(apiClient, tokenStore)

        controlTokenStore = ControlTokenStore(this)
        controlClient = ControlClient()
        controlClient.token = controlTokenStore.token

        tsnetProfiles = TsnetProfileStore(this)
        tsnetBridge = TsnetBridge(this)

        // Restore session
        tokenStore.accessToken?.let { apiClient.setAuthToken(it) }

        // ── 3. Start embedded FastAPI backend ──
        appScope.launch {
            try {
                val r = PythonServer.startBackend()
                Log.i(TAG, "startBackend -> $r")
                val ready = PythonServer.isBackendReady(timeoutSec = 20.0)
                Log.i(TAG, "backend ready: $ready")
                val status = PythonServer.status()
                Log.i(TAG, "status: $status")
            } catch (t: Throwable) {
                Log.e(TAG, "backend start failed", t)
            }
        }

        // ── 4. Note: tsnet profiles are NOT auto-started ──
        // User must press "Start" per profile in the UI.
        // This is intentional: Funnel + auth key still required.
        val saved = tsnetProfiles.list()
        Log.i(TAG, "tsnet profiles: ${saved.size} (${saved.joinToString { it.name }})")
    }

    companion object { private const val TAG = "FamilyAdminApp" }
}
