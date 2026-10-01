package com.admin.family.data.auth

import android.content.Context

class TokenStore(context: Context) {
    private val prefs = context.getSharedPreferences("auth_tokens", Context.MODE_PRIVATE)

    var accessToken: String?
        get() = prefs.getString(KEY_ACCESS, null)
        set(v) { prefs.edit().putString(KEY_ACCESS, v).apply() }

    var refreshToken: String?
        get() = prefs.getString(KEY_REFRESH, null)
        set(v) { prefs.edit().putString(KEY_REFRESH, v).apply() }

    var userEmail: String?
        get() = prefs.getString(KEY_EMAIL, null)
        set(v) { prefs.edit().putString(KEY_EMAIL, v).apply() }

    fun isLoggedIn(): Boolean = !accessToken.isNullOrBlank()

    fun clear() {
        prefs.edit().clear().apply()
    }

    companion object {
        private const val KEY_ACCESS = "access_token"
        private const val KEY_REFRESH = "refresh_token"
        private const val KEY_EMAIL = "user_email"
    }
}
