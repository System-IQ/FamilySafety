package com.admin.family.data.auth

import android.content.Context

/**
 * Stores the fs-control agent token (from ~/.fsserver/control-token).
 * Same approach as TokenStore but for the local control agent.
 */
class ControlTokenStore(context: Context) {
    private val prefs = context.getSharedPreferences("control_agent", Context.MODE_PRIVATE)

    var token: String?
        get() = prefs.getString(KEY_TOKEN, null)
        set(v) { prefs.edit().putString(KEY_TOKEN, v).apply() }

    fun isConfigured(): Boolean = !token.isNullOrBlank()

    fun clear() {
        prefs.edit().remove(KEY_TOKEN).apply()
    }

    companion object {
        private const val KEY_TOKEN = "control_token"
    }
}
