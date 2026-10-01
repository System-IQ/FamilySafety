package com.admin.family

import android.app.Application
import com.admin.family.data.api.ApiClient
import com.admin.family.data.prefs.AppPreferences
import com.admin.family.data.repository.DefaultSettingsRepository
import com.admin.family.data.repository.DeviceRepository
import com.admin.family.data.repository.SettingsRepository

/**
 * Application container.
 *
 * The Family Safety server runs in Termux (via start-server / stop-server).
 * This app is a CLIENT — it never hosts a network server itself.
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
        apiClient = ApiClient(preferences.apiBaseUrl)
        deviceRepository = DeviceRepository(apiClient)
    }
}
