package com.admin.family

import android.app.Application
import com.admin.family.data.api.ApiClient
import com.admin.family.data.auth.TokenStore
import com.admin.family.data.prefs.AppPreferences
import com.admin.family.data.repository.AuthRepository
import com.admin.family.data.repository.DefaultSettingsRepository
import com.admin.family.data.repository.DeviceRepository
import com.admin.family.data.repository.SettingsRepository

class FamilyAdminApp : Application() {
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

    override fun onCreate() {
        super.onCreate()
        preferences = AppPreferences(this)
        settingsRepository = DefaultSettingsRepository(preferences)
        apiClient = ApiClient(preferences.apiBaseUrl)
        deviceRepository = DeviceRepository(apiClient)
        tokenStore = TokenStore(this)
        authRepository = AuthRepository(apiClient, tokenStore)

        // Restore session if token exists
        tokenStore.accessToken?.let { apiClient.setAuthToken(it) }
    }
}
