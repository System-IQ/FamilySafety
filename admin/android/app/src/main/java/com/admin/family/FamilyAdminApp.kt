package com.admin.family

import android.app.Application
import com.admin.family.data.api.ApiClient
import com.admin.family.data.prefs.AppPreferences
import com.admin.family.data.repository.DefaultSettingsRepository
import com.admin.family.data.repository.DeviceRepository
import com.admin.family.data.repository.SettingsRepository

/**
 * Application entry point.
 *
 * Wires:
 * - AppPreferences (SharedPreferences)
 * - SettingsRepository (interface over prefs)
 * - ApiClient (uses base URL from prefs)
 * - DeviceRepository (uses ApiClient)
 *
 * All dependencies are exposed as immutable references for the
 * lifetime of the process. Base URL changes go through
 * `apiClient.updateBaseUrl()` — no need to recreate anything.
 */
class FamilyAdminApp : Application() {

    lateinit var preferences: AppPreferences
        private set

    lateinit var settingsRepository: SettingsRepository
        private set

    lateinit var apiClient: ApiClient
        private set

    lateinit var deviceRepository: DeviceRepository
        private set

    override fun onCreate() {
        super.onCreate()

        preferences = AppPreferences(this)
        settingsRepository = DefaultSettingsRepository(preferences)

        // Build client from whatever URL is currently saved.
        apiClient = ApiClient(preferences.apiBaseUrl)
        deviceRepository = DeviceRepository(apiClient)
    }
}
