package com.admin.family.data.tsnet

import android.content.Context

/**
 * Secure-ish storage for the Tailscale auth key.
 * Currently plain SharedPreferences — will upgrade to EncryptedSharedPreferences later.
 */
class AuthKeyStore(context: Context) {
    private val prefs = context.getSharedPreferences("tsnet_auth", Context.MODE_PRIVATE)

    var authKey: String?
        get() = prefs.getString(KEY, null)
        set(value) {
            prefs.edit().putString(KEY, value).apply()
        }

    fun clear() {
        prefs.edit().remove(KEY).apply()
    }

    companion object {
        private const val KEY = "tailscale_auth_key"
    }
}
