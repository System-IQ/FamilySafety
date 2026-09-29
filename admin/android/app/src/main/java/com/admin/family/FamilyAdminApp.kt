package com.admin.family

import android.app.Application
import com.admin.family.data.api.ApiClient
import com.admin.family.data.prefs.AppPreferences
import com.admin.family.data.repository.DefaultSettingsRepository
import com.admin.family.data.repository.DeviceRepository
import com.admin.family.data.repository.SettingsRepository
import com.admin.family.data.tsnet.AuthKeyStore
import com.admin.family.data.tsnet.TsnetServerWrapper

class FamilyAdminApp : Application() {
    lateinit var preferences: AppPreferences
        private set
    lateinit var settingsRepository: SettingsRepository
        private set
    lateinit var apiClient: ApiClient
        private set
    lateinit var deviceRepository: DeviceRepository
        private set
    lateinit var authKeyStore: AuthKeyStore
        private set
    lateinit var tsnetWrapper: TsnetServerWrapper
        private set

    override fun onCreate() {
        super.onCreate()
        preferences = AppPreferences(this)
        settingsRepository = DefaultSettingsRepository(preferences)
        apiClient = ApiClient(preferences.apiBaseUrl)
        deviceRepository = DeviceRepository(apiClient)
        authKeyStore = AuthKeyStore(this)
        tsnetWrapper = TsnetServerWrapper(this)
    }
}
