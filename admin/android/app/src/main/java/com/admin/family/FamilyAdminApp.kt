package com.admin.family

import android.app.Application
import android.util.Log
import com.admin.family.data.api.ApiClient
import com.admin.family.data.api.ControlClient
import com.admin.family.data.auth.AccessCodeStore
import com.admin.family.data.auth.ControlTokenStore
import com.admin.family.data.config.ConfigStore
import com.admin.family.data.prefs.AppPreferences
import com.admin.family.data.repository.DefaultSettingsRepository
import com.admin.family.data.repository.DeviceRepository
import com.admin.family.data.repository.SettingsRepository
import com.admin.family.python.PythonServer
import com.admin.family.tsnet.TsnetBridge
import com.admin.family.tsnet.TsnetProfileStore

class FamilyAdminApp : Application() {

    lateinit var preferences: AppPreferences
        private set
    lateinit var settingsRepository: SettingsRepository
        private set
    lateinit var apiClient: ApiClient
        private set
    lateinit var deviceRepository: DeviceRepository
        private set
    lateinit var accessCodeStore: AccessCodeStore
        private set
    lateinit var controlClient: ControlClient
        private set
    lateinit var controlTokenStore: ControlTokenStore
        private set
    lateinit var tsnetBridge: TsnetBridge
        private set
    lateinit var tsnetProfiles: TsnetProfileStore
        private set
    lateinit var configStore: ConfigStore
        private set

    override fun onCreate() {
        super.onCreate()
        Log.i(TAG, "onCreate")

        // 1. Embedded Python
        try {
            PythonServer.init(this)
            Log.i(TAG, "Python runtime started")
        } catch (t: Throwable) {
            Log.e(TAG, "Python init failed", t)
        }

        // 2. DI
        preferences = AppPreferences(this)
        settingsRepository = DefaultSettingsRepository(preferences)
        apiClient = ApiClient(preferences.apiBaseUrl)
        deviceRepository = DeviceRepository(apiClient)
        accessCodeStore = AccessCodeStore(this)
        controlTokenStore = ControlTokenStore(this)
        controlClient = ControlClient()
        controlClient.token = controlTokenStore.token
        tsnetProfiles = TsnetProfileStore(this)
        configStore = ConfigStore(this)
        tsnetBridge = TsnetBridge(this)

        // 3. If code exists: configure backend in background
        val savedCode = accessCodeStore.code
        if (!savedCode.isNullOrBlank()) {
            bootstrapBackend(savedCode)
        } else {
            Log.i(TAG, "no access code — waiting for user input")
        }
    }

    /**
     * Configures embedded Python backend with the access code and
     * kicks off uvicorn in a background thread.
     *
     * Safe to call multiple times — Python's configure() is idempotent.
     */
    fun bootstrapBackend(code: String) {
        accessCodeStore.code = code
        apiClient.setAuthToken(code)
        try {
            PythonServer.configure(this, code)
        } catch (t: Throwable) {
            Log.e(TAG, "Python configure failed", t)
            return
        }
        Thread {
            try {
                val r = PythonServer.startBackendBlocking()
                Log.i(TAG, "startBackend -> $r")
            } catch (t: Throwable) {
                Log.e(TAG, "backend start failed", t)
            }
        }.start()
    }

    companion object { private const val TAG = "FamilyAdminApp" }
}
