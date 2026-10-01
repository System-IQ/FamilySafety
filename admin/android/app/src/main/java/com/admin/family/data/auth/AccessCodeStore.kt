package com.admin.family.data.auth

import android.content.Context
import android.util.Base64
import org.json.JSONArray
import org.json.JSONObject
import java.security.MessageDigest
import java.security.SecureRandom
import javax.crypto.SecretKeyFactory
import javax.crypto.spec.PBEKeySpec

/**
 * Stores the app's local authentication state:
 *   - PIN (6 digits)          — user-facing, unlocks the UI
 *   - Access code (32+ chars) — strong token sent to the backend as Bearer
 *   - Biometric preference    — optional quick unlock
 *   - Recovery email          — optional, informational only
 *   - Backup codes (10)       — offline PIN recovery
 *
 * Backup codes are generated once on first PIN setup, displayed to the
 * user, then hashed (SHA-256) before storage. Each code can be used
 * exactly once. No server, no email, no internet required.
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

    // ─── Recovery email (informational) ───
    var recoveryEmail: String?
        get() = prefs.getString(KEY_EMAIL, null)
        set(v) { prefs.edit().putString(KEY_EMAIL, v?.trim()).apply() }

    // ─── Backup codes (JSON array of {hash, used}) ───
    private var backupCodesJson: String?
        get() = prefs.getString(KEY_BACKUP_CODES, null)
        set(v) { prefs.edit().putString(KEY_BACKUP_CODES, v).apply() }

    // ─── State queries ───
    fun isConfigured(): Boolean = !code.isNullOrBlank() && !pinHash.isNullOrBlank()
    fun hasPin(): Boolean = !pinHash.isNullOrBlank()
    fun hasRecoveryEmail(): Boolean = !recoveryEmail.isNullOrBlank()

    /** How many unused backup codes remain. */
    fun backupCodesRemaining(): Int {
        val arr = parseBackupCodes() ?: return 0
        var count = 0
        for (i in 0 until arr.length()) {
            val obj = arr.optJSONObject(i) ?: continue
            if (!obj.optBoolean("used", false)) count++
        }
        return count
    }

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

    // ─── Backup codes ───

    /**
     * Generates [count] fresh backup codes, stores their SHA-256 hashes,
     * and returns the plain codes exactly once. The caller MUST display
     * them to the user immediately; they cannot be retrieved later.
     */
    fun generateAndStoreBackupCodes(count: Int = BACKUP_CODE_COUNT): List<String> {
        val plain = mutableListOf<String>()
        val arr = JSONArray()
        for (i in 0 until count) {
            val code = generateBackupCode()
            plain.add(code)
            val hash = sha256Hex(code)
            arr.put(JSONObject().apply {
                put("hash", hash)
                put("used", false)
                put("created_at", System.currentTimeMillis())
            })
        }
        backupCodesJson = arr.toString()
        return plain
    }

    /**
     * Verifies a user-entered backup code. If valid and unused:
     *   - marks the code as used (burns it)
     *   - returns true
     * Otherwise returns false.
     *
     * Input is normalized: uppercased, dashes and spaces stripped.
     */
    fun verifyAndBurnBackupCode(input: String): Boolean {
        val normalized = normalizeBackupCodeInput(input)
        if (normalized.length != BACKUP_CODE_LENGTH) return false

        val arr = parseBackupCodes() ?: return false
        val inputHash = sha256Hex(normalized)

        var burnIndex = -1
        for (i in 0 until arr.length()) {
            val obj = arr.optJSONObject(i) ?: continue
            if (obj.optBoolean("used", false)) continue
            val storedHash = obj.optString("hash", "")
            if (storedHash.isNotEmpty() && constantTimeEquals(storedHash, inputHash)) {
                burnIndex = i
                break
            }
        }
        if (burnIndex < 0) return false

        // Burn it
        val target = arr.getJSONObject(burnIndex)
        target.put("used", true)
        target.put("used_at", System.currentTimeMillis())
        backupCodesJson = arr.toString()
        return true
    }

    /** Remove all backup codes (e.g. after regenerating). */
    fun clearBackupCodes() {
        prefs.edit().remove(KEY_BACKUP_CODES).apply()
    }

    /** True if user has at least one backup code remaining. */
    fun hasBackupCodes(): Boolean = backupCodesRemaining() > 0

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

    /**
     * Backup code format: 8 chars from a confusion-free alphabet,
     * formatted as XXXX-XXXX (with a dash).
     * Alphabet: A-Z except I, O + 2-9 (no 0, 1, I, O, L confusion).
     */
    private fun generateBackupCode(): String {
        val sb = StringBuilder(BACKUP_CODE_LENGTH)
        val alphabet = BACKUP_ALPHABET
        for (i in 0 until BACKUP_CODE_LENGTH) {
            sb.append(alphabet[SecureRandom().nextInt(alphabet.length)])
        }
        // Format with dash: XXXX-XXXX
        return sb.substring(0, 4) + "-" + sb.substring(4, 8)
    }

    private fun normalizeBackupCodeInput(input: String): String {
        // Keep only alphabet chars, uppercase
        return input.uppercase().filter { it in BACKUP_ALPHABET }
    }

    private fun parseBackupCodes(): JSONArray? {
        val raw = backupCodesJson ?: return null
        return try {
            JSONArray(raw)
        } catch (_: Exception) {
            null
        }
    }

    private fun sha256Hex(s: String): String {
        val digest = MessageDigest.getInstance("SHA-256")
        val bytes = digest.digest(s.toByteArray(Charsets.UTF_8))
        val sb = StringBuilder(bytes.size * 2)
        for (b in bytes) sb.append("%02x".format(b))
        return sb.toString()
    }

    companion object {
        private const val PREFS_NAME = "access_code"
        private const val KEY_CODE = "access_code"
        private const val KEY_PIN_HASH = "pin_hash"
        private const val KEY_PIN_SALT = "pin_salt"
        private const val KEY_BIO = "biometric_enabled"
        private const val KEY_EMAIL = "recovery_email"
        private const val KEY_BACKUP_CODES = "backup_codes_v1"

        const val PIN_LENGTH = 6

        @Deprecated("Use PIN_LENGTH")
        const val MIN_LENGTH = 6

        /** Number of backup codes generated at setup. */
        const val BACKUP_CODE_COUNT = 10

        /** Raw length of a backup code without separator. */
        const val BACKUP_CODE_LENGTH = 8

        /** Confusion-free alphabet (no 0, 1, I, O, L). */
        private const val BACKUP_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"

        private const val ITERATIONS = 100_000
    }
}
