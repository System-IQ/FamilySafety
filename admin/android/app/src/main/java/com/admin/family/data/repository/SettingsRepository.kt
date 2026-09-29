package com.admin.family.data.repository

import com.admin.family.data.prefs.AppPreferences

/**
 * Settings repository — abstracts persistence from the UI/ViewModel layer.
 *
 * The interface lets us swap AppPreferences for DataStore or an
 * encrypted store later without touching ViewModels.
 */
interface SettingsRepository {
    val apiBaseUrl: String
    fun saveBaseUrl(url: String)
    fun resetToDefaults()

    val lastTestSuccessAtMillis: Long
    val lastTestFailureAtMillis: Long
    fun recordTestSuccess(atMillis: Long)
    fun recordTestFailure(atMillis: Long)
}

class DefaultSettingsRepository(
    private val prefs: AppPreferences,
) : SettingsRepository {

    override val apiBaseUrl: String
        get() = prefs.apiBaseUrl

    override fun saveBaseUrl(url: String) {
        prefs.apiBaseUrl = url
    }

    override fun resetToDefaults() {
        prefs.resetToDefaults()
    }

    override val lastTestSuccessAtMillis: Long
        get() = prefs.lastTestSuccessAtMillis

    override val lastTestFailureAtMillis: Long
        get() = prefs.lastTestFailureAtMillis

    override fun recordTestSuccess(atMillis: Long) {
        prefs.lastTestSuccessAtMillis = atMillis
    }

    override fun recordTestFailure(atMillis: Long) {
        prefs.lastTestFailureAtMillis = atMillis
    }
}
