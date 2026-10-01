package com.admin.family.biometric

import androidx.biometric.BiometricManager
import androidx.biometric.BiometricPrompt
import androidx.core.content.ContextCompat
import androidx.fragment.app.FragmentActivity
import kotlin.coroutines.resume
import kotlinx.coroutines.suspendCancellableCoroutine

enum class BiometricAvailability {
    AVAILABLE,
    NO_HARDWARE,
    UNAVAILABLE,
    NOT_ENROLLED,
    UNKNOWN,
}

class BiometricError(val code: Int, message: String) : Exception(message)

/**
 * Thin wrapper around androidx.biometric.BiometricPrompt.
 *
 * Uses BIOMETRIC_WEAK (fingerprint / face) — no PIN fallback needed
 * because the user always has the access code as backup.
 */
class BiometricHelper(private val activity: FragmentActivity) {

    fun isAvailable(): BiometricAvailability {
        val manager = BiometricManager.from(activity)
        val can = manager.canAuthenticate(
            BiometricManager.Authenticators.BIOMETRIC_WEAK
        )
        return when (can) {
            BiometricManager.BIOMETRIC_SUCCESS -> BiometricAvailability.AVAILABLE
            BiometricManager.BIOMETRIC_ERROR_NO_HARDWARE -> BiometricAvailability.NO_HARDWARE
            BiometricManager.BIOMETRIC_ERROR_HW_UNAVAILABLE -> BiometricAvailability.UNAVAILABLE
            BiometricManager.BIOMETRIC_ERROR_NONE_ENROLLED -> BiometricAvailability.NOT_ENROLLED
            else -> BiometricAvailability.UNKNOWN
        }
    }

    /**
     * Shows the system biometric prompt and suspends until the user
     * succeeds, cancels, or errors.
     *
     * Returns Result.success(Unit) on success.
     * Returns Result.failure(BiometricError) on cancel/error.
     */
    suspend fun authenticate(
        title: String = "Unlock Family Guard",
        subtitle: String = "Use your biometric to continue",
        cancelLabel: String = "Use code instead",
    ): Result<Unit> = suspendCancellableCoroutine { cont ->
        val executor = ContextCompat.getMainExecutor(activity)

        val callback = object : BiometricPrompt.AuthenticationCallback() {
            override fun onAuthenticationSucceeded(
                result: BiometricPrompt.AuthenticationResult,
            ) {
                if (cont.isActive) cont.resume(Result.success(Unit))
            }

            override fun onAuthenticationError(code: Int, msg: CharSequence) {
                if (cont.isActive) {
                    cont.resume(Result.failure(BiometricError(code, msg.toString())))
                }
            }

            override fun onAuthenticationFailed() {
                // Individual attempt failed; system keeps the prompt open.
            }
        }

        val prompt = BiometricPrompt(activity, executor, callback)

        val info = BiometricPrompt.PromptInfo.Builder()
            .setTitle(title)
            .setSubtitle(subtitle)
            .setNegativeButtonText(cancelLabel)
            .setAllowedAuthenticators(BiometricManager.Authenticators.BIOMETRIC_WEAK)
            .setConfirmationRequired(false)
            .build()

        prompt.authenticate(info)
    }
}
