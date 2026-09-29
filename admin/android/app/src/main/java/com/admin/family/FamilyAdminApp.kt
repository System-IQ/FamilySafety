package com.admin.family

import android.app.Application
import com.admin.family.data.api.ApiClient
import com.admin.family.data.repository.DeviceRepository

class FamilyAdminApp : Application() {

    lateinit var apiClient: ApiClient
        private set
    lateinit var deviceRepository: DeviceRepository
        private set

    override fun onCreate() {
        super.onCreate()
        apiClient = ApiClient(BuildConfig.API_BASE_URL)
        deviceRepository = DeviceRepository(apiClient)
    }
}
