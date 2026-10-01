package com.admin.family.data.prefs

import android.content.Context
import android.content.SharedPreferences

/**
 * Thin, typed wrapper around SharedPreferences.
 *
 * Only the essentials for now: API base URL + last known connection state.
 * No secrets are stored here (no tokens yet — will use EncryptedSharedPreferences
 * when auth lands in a future batch).
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

    fun resetToDefaults() {
        prefs.edit()
            .remove(KEY_API_BASE_URL)
            .remove(KEY_LAST_TEST_SUCCESS)
            .remove(KEY_LAST_TEST_FAILURE)
            .apply()
    }

    companion object {
        const val PREFS_NAME = "family_admin_prefs"
        const val KEY_API_BASE_URL = "api_base_url"
        const val KEY_LAST_EMAIL = "last_email"
        const val KEY_LAST_TEST_SUCCESS = "last_test_success_ms"
        const val KEY_LAST_TEST_FAILURE = "last_test_failure_ms"

        /**
         * Default points to the emulator loopback host (10.0.2.2 = host machine).
         * Users on a real device must change this in Settings.
         */
        const val DEFAULT_BASE_URL = "http://127.0.0.1:8000/"

        /**
         * Normalize a user-provided URL:
         * - trims whitespace
         * - ensures trailing slash
         * - lowercases scheme + host only (path kept as-is)
         * - refuses anything that is not http/https (throws)
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
