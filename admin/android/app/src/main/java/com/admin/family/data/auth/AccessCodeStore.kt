package com.admin.family.data.auth

import android.content.Context

/**
 * Stores the single access code that unlocks the app + backend,
 * plus the user's preference to enable biometric unlock.
 */
class AccessCodeStore(context: Context) {
    private val prefs = context.getSharedPreferences("access_code", Context.MODE_PRIVATE)

    var code: String?
        get() = prefs.getString(KEY_CODE, null)
        set(v) { prefs.edit().putString(KEY_CODE, v?.trim()).apply() }

    var biometricEnabled: Boolean
        get() = prefs.getBoolean(KEY_BIO, false)
        set(v) { prefs.edit().putBoolean(KEY_BIO, v).apply() }

    fun isConfigured(): Boolean = !code.isNullOrBlank()

    fun clear() {
        prefs.edit().remove(KEY_CODE).remove(KEY_BIO).apply()
    }

    companion object {
        private const val KEY_CODE = "access_code"
        private const val KEY_BIO = "biometric_enabled"
        const val MIN_LENGTH = 12
    }
}
