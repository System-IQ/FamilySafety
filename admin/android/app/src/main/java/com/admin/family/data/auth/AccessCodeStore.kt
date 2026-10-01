package com.admin.family.data.auth

import android.content.Context
import android.util.Base64
import java.security.SecureRandom
import javax.crypto.SecretKeyFactory
import javax.crypto.spec.PBEKeySpec

/**
 * Stores the app's local authentication state:
 *   - PIN (6 digits)          — user-facing, unlocks the UI
 *   - Access code (32+ chars) — strong token sent to the backend as Bearer
 *   - Biometric preference    — optional quick unlock
 *   - Recovery email          — used by Forgot-PIN flow
 *
 * Backward compat: `code` getter/setter and `isConfigured()` still work
 * exactly as before. All existing callers continue to work.
 */
class AccessCodeStore(context: Context) {

    private val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)

    // ─── Access code (strong Bearer token) ───
    var code: String?
        get() = prefs.getString(KEY_CODE, null)
        set(v) { prefs.edit().putString(KEY_CODE, v?.trim()).apply() }

    // ─── PIN hash + salt (PBKDF2) ───
    private var pinHash: String?
        get() = prefs.getString(KEY_PIN_HASH, null)
        set(v) { prefs.edit().putString(KEY_PIN_HASH, v).apply() }

    private var pinSalt: String?
        get() = prefs.getString(KEY_PIN_SALT, null)
        set(v) { prefs.edit().putString(KEY_PIN_SALT, v).apply() }

    // ─── Biometric preference ───
    var biometricEnabled: Boolean
        get() = prefs.getBoolean(KEY_BIO, false)
        set(v) { prefs.edit().putBoolean(KEY_BIO, v).apply() }

    // ─── Recovery email ───
    var recoveryEmail: String?
        get() = prefs.getString(KEY_EMAIL, null)
        set(v) { prefs.edit().putString(KEY_EMAIL, v?.trim()).apply() }

    // ─── State queries ───
    fun isConfigured(): Boolean = !code.isNullOrBlank() && !pinHash.isNullOrBlank()
    fun hasPin(): Boolean = !pinHash.isNullOrBlank()
    fun hasRecoveryEmail(): Boolean = !recoveryEmail.isNullOrBlank()

    // ─── Operations ───
    fun setupPin(pin: String): Boolean {
        if (pin.length != PIN_LENGTH) return false
        if (!pin.all { it.isDigit() }) return false

        val salt = generateSalt()
        val hash = hashPin(pin, salt)
        val newCode = generateAccessCode()

        prefs.edit()
            .putString(KEY_PIN_SALT, salt)
            .putString(KEY_PIN_HASH, hash)
            .putString(KEY_CODE, newCode)
            .apply()
        return true
    }

    fun verifyPin(pin: String): Boolean {
        val storedHash = pinHash ?: return false
        val storedSalt = pinSalt ?: return false
        val testHash = hashPin(pin, storedSalt)
        return constantTimeEquals(storedHash, testHash)
    }

    fun resetWithNewPin(newPin: String): Boolean = setupPin(newPin)

    fun clear() {
        prefs.edit().clear().apply()
    }

    // ─── Crypto helpers ───
    private fun generateSalt(): String {
        val bytes = ByteArray(16)
        SecureRandom().nextBytes(bytes)
        return Base64.encodeToString(bytes, Base64.NO_WRAP)
    }

    private fun hashPin(pin: String, saltB64: String): String {
        val salt = Base64.decode(saltB64, Base64.NO_WRAP)
        val spec = PBEKeySpec(pin.toCharArray(), salt, ITERATIONS, 256)
        val factory = SecretKeyFactory.getInstance("PBKDF2WithHmacSHA256")
        val hash = factory.generateSecret(spec).encoded
        return Base64.encodeToString(hash, Base64.NO_WRAP)
    }

    private fun constantTimeEquals(a: String, b: String): Boolean {
        if (a.length != b.length) return false
        var r = 0
        for (i in a.indices) r = r or (a[i].code xor b[i].code)
        return r == 0
    }

    private fun generateAccessCode(): String {
        val bytes = ByteArray(24)
        SecureRandom().nextBytes(bytes)
        return Base64.encodeToString(
            bytes,
            Base64.NO_WRAP or Base64.NO_PADDING or Base64.URL_SAFE,
        )
    }

    companion object {
        private const val PREFS_NAME = "access_code"
        private const val KEY_CODE = "access_code"
        private const val KEY_PIN_HASH = "pin_hash"
        private const val KEY_PIN_SALT = "pin_salt"
        private const val KEY_BIO = "biometric_enabled"
        private const val KEY_EMAIL = "recovery_email"

        const val PIN_LENGTH = 6

        @Deprecated("Use PIN_LENGTH")
        const val MIN_LENGTH = 6

        private const val ITERATIONS = 100_000
    }
}
