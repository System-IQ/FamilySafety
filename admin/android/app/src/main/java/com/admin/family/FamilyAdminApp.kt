package com.admin.family

import android.app.Application
import com.admin.family.data.api.ApiClient
import com.admin.family.data.api.ControlClient
import com.admin.family.data.auth.ControlTokenStore
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
    lateinit var controlClient: ControlClient
        private set
    lateinit var controlTokenStore: ControlTokenStore
        private set

    override fun onCreate() {
        super.onCreate()
        preferences = AppPreferences(this)
        settingsRepository = DefaultSettingsRepository(preferences)
        apiClient = ApiClient(preferences.apiBaseUrl)
        deviceRepository = DeviceRepository(apiClient)
        tokenStore = TokenStore(this)
        authRepository = AuthRepository(apiClient, tokenStore)

        // Control agent (Termux fs-control on 127.0.0.1:9999)
        controlTokenStore = ControlTokenStore(this)
        controlClient = ControlClient()
        controlClient.token = controlTokenStore.token

        // Restore session if token exists
        tokenStore.accessToken?.let { apiClient.setAuthToken(it) }
    }
}
