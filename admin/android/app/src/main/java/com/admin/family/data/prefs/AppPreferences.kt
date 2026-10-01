package com.admin.family.data.prefs

import android.content.Context
import android.content.SharedPreferences

/**
 * Thin, typed wrapper around SharedPreferences.
 *
 * Stores only non-secret app state:
 *   - backend base URL
 *   - last email
 *   - last test timestamps
 *   - whether the embedded server should run 24/7 (serverEnabled)
 */
class AppPreferences(context: Context) {

    private val prefs: SharedPreferences =
        context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)

    var apiBaseUrl: String
        get() = prefs.getString(KEY_API_BASE_URL, DEFAULT_BASE_URL) ?: DEFAULT_BASE_URL
        set(value) {
            val normalized = normalize(value)
            prefs.edit().putString(KEY_API_BASE_URL, normalized).apply()
        }

    var lastEmail: String?
        get() = prefs.getString(KEY_LAST_EMAIL, null)
        set(value) {
            prefs.edit().putString(KEY_LAST_EMAIL, value).apply()
        }

    var lastTestSuccessAtMillis: Long
        get() = prefs.getLong(KEY_LAST_TEST_SUCCESS, 0L)
        set(value) {
            prefs.edit().putLong(KEY_LAST_TEST_SUCCESS, value).apply()
        }

    var lastTestFailureAtMillis: Long
        get() = prefs.getLong(KEY_LAST_TEST_FAILURE, 0L)
        set(value) {
            prefs.edit().putLong(KEY_LAST_TEST_FAILURE, value).apply()
        }

    /**
     * Whether the embedded backend should be running.
     * Written by ServerService on START/STOP.
     * Read on app launch and on boot to decide auto-start.
     */
    var serverEnabled: Boolean
        get() = prefs.getBoolean(KEY_SERVER_ENABLED, false)
        set(value) {
            prefs.edit().putBoolean(KEY_SERVER_ENABLED, value).apply()
        }

    fun resetToDefaults() {
        prefs.edit()
            .remove(KEY_API_BASE_URL)
            .remove(KEY_LAST_TEST_SUCCESS)
            .remove(KEY_LAST_TEST_FAILURE)
            .remove(KEY_SERVER_ENABLED)
            .apply()
    }

    companion object {
        const val PREFS_NAME = "family_admin_prefs"
        const val KEY_API_BASE_URL = "api_base_url"
        const val KEY_LAST_EMAIL = "last_email"
        const val KEY_LAST_TEST_SUCCESS = "last_test_success_ms"
        const val KEY_LAST_TEST_FAILURE = "last_test_failure_ms"
        const val KEY_SERVER_ENABLED = "server_enabled"

        const val DEFAULT_BASE_URL = "http://127.0.0.1:8000/"

        /**
         * Normalize a user-provided URL:
         * - trims whitespace
         * - ensures trailing slash
         * - refuses anything that is not http/https
         */
        fun normalize(raw: String): String {
            val trimmed = raw.trim()
            require(trimmed.isNotEmpty()) { "URL must not be empty" }
            val lower = trimmed.lowercase()
            require(lower.startsWith("http://") || lower.startsWith("https://")) {
                "URL must start with http:// or https://"
            }
            return if (trimmed.endsWith("/")) trimmed else "$trimmed/"
        }
    }
}
