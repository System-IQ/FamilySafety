package com.admin.family

import android.app.Application
import android.util.Log
import com.admin.family.data.api.ApiClient
import com.admin.family.data.auth.AccessCodeStore
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
    lateinit var tsnetBridge: TsnetBridge
        private set
    lateinit var tsnetProfiles: TsnetProfileStore
        private set
    lateinit var configStore: ConfigStore
        private set

    override fun onCreate() {
        super.onCreate()
        Log.i(TAG, "onCreate")

        // 1) Embedded Python runtime
        try {
            PythonServer.init(this)
            Log.i(TAG, "Python runtime started")
        } catch (t: Throwable) {
            Log.e(TAG, "Python init failed", t)
        }

        // 2) Dependency graph
        preferences = AppPreferences(this)
        settingsRepository = DefaultSettingsRepository(preferences)
        apiClient = ApiClient(preferences.apiBaseUrl)
        deviceRepository = DeviceRepository(apiClient)
        accessCodeStore = AccessCodeStore(this)
        tsnetProfiles = TsnetProfileStore(this)
        configStore = ConfigStore(this)
        tsnetBridge = TsnetBridge(this)

        // 3) Prepare the embedded backend environment (paths, access code,
        //    JWT secret) but DO NOT start uvicorn. Starting is controlled
        //    exclusively by Server Info (START) via ServerService.
        val savedCode = accessCodeStore.code
        val code = if (!savedCode.isNullOrBlank()) savedCode
                   else accessCodeStore.generateAndSaveCodeIfNeeded()
        prepareBackend(code)
        Log.i(TAG, "backend prepared, waiting for explicit START")
    }

    /**
     * Sets env vars / paths / access code. Does NOT start uvicorn.
     * Safe to call multiple times.
     */
    fun prepareBackend(code: String) {
        accessCodeStore.code = code
        apiClient.setAuthToken(code)
        try {
            PythonServer.configure(this, code)
        } catch (t: Throwable) {
            Log.e(TAG, "Python configure failed", t)
        }
    }

    /**
     * Starts uvicorn in a background thread. Called only from
     * ServerService when the user presses START.
     */
    fun startEmbeddedServer(): String {
        preferences.serverEnabled = true
        return try {
            val r = PythonServer.startBackendBlocking()
            Log.i(TAG, "startEmbeddedServer -> $r")
            r
        } catch (t: Throwable) {
            Log.e(TAG, "startEmbeddedServer failed", t)
            "error: ${t.message}"
        }
    }

    /**
     * Requests a graceful shutdown of uvicorn.
     * Called only from ServerService when the user presses STOP.
     */
    fun stopEmbeddedServer(): String {
        preferences.serverEnabled = false
        return try {
            val r = PythonServer.stopBackendBlocking()
            Log.i(TAG, "stopEmbeddedServer -> $r")
            r
        } catch (t: Throwable) {
            Log.e(TAG, "stopEmbeddedServer failed", t)
            "error: ${t.message}"
        }
    }

    /**
     * Blocking readiness probe used by ServerService to update the
     * notification body without spinning up a coroutine.
     */
    fun isBackendReadyBlocking(timeoutSec: Double = 2.0): Boolean {
        return try {
            PythonServer.isBackendReadyBlocking(timeoutSec)
        } catch (t: Throwable) {
            Log.e(TAG, "isBackendReadyBlocking failed", t)
            false
        }
    }

    /**
     * Backward-compat shim kept for AppNavigation.onBootstrapBackend.
     * Prepares the environment only; it does not start the server.
     */
    fun bootstrapBackend(code: String) = prepareBackend(code)

    companion object { private const val TAG = "FamilyAdminApp" }
}
