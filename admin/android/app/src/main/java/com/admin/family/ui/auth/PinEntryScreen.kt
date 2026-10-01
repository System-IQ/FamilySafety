package com.admin.family.ui.auth

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Fingerprint
import androidx.compose.material.icons.filled.Lock
import androidx.compose.material.icons.filled.LockOpen
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.platform.LocalFocusManager
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import com.admin.family.biometric.BiometricAvailability
import com.admin.family.data.auth.AccessCodeStore
import com.admin.family.ui.theme.Danger

/**
 * Unlock screen. Shown on every cold start after first-time PIN setup.
 *
 * Caller is responsible for:
 *   - verifying the PIN via AccessCodeStore.verifyPin()
 *   - navigating forward on success
 *   - passing an error message on failure (errorMessage arg)
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun PinEntryScreen(
    onUnlock: (pin: String) -> Unit,
    onForgotPin: () -> Unit,
    onBiometricRequest: (() -> Unit)? = null,
    biometricAvailability: BiometricAvailability = BiometricAvailability.UNKNOWN,
    errorMessage: String? = null,
    recoveryEmailHint: String? = null,
) {
    var pin by remember { mutableStateOf("") }
    val focus = LocalFocusManager.current

    // Clear pin when error changes so user can retry cleanly
    LaunchedEffect(errorMessage) {
        if (errorMessage != null) {
            pin = ""
        }
    }

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(
                Brush.verticalGradient(
                    listOf(
                        MaterialTheme.colorScheme.background,
                        MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.35f),
                    )
                )
            )
    ) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .verticalScroll(rememberScrollState())
                .padding(horizontal = 24.dp, vertical = 32.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            Spacer(Modifier.height(24.dp))

            Box(
                modifier = Modifier
                    .size(64.dp)
                    .background(MaterialTheme.colorScheme.primary, RoundedCornerShape(18.dp)),
                contentAlignment = Alignment.Center,
            ) {
                Text(
                    "FG",
                    style = MaterialTheme.typography.headlineSmall,
                    color = MaterialTheme.colorScheme.onPrimary,
                    fontWeight = FontWeight.Bold,
                )
            }
            Spacer(Modifier.height(14.dp))
            Text("Family Guard", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
            Text(
                "Enter your PIN to continue",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.alpha(0.75f),
            )

            Spacer(Modifier.height(28.dp))

            Card(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(16.dp),
                elevation = CardDefaults.cardElevation(defaultElevation = 1.dp),
            ) {
                Column(
                    modifier = Modifier.padding(20.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp),
                ) {
                    Text(
                        "Enter PIN",
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.Bold,
                    )
                    Text(
                        "6 digits. Stored on this device only.",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )

                    OutlinedTextField(
                        value = pin,
                        onValueChange = { pin = it.filter { c -> c.isDigit() }.take(AccessCodeStore.PIN_LENGTH) },
                        label = { Text("PIN") },
                        placeholder = { Text("••••••", textAlign = TextAlign.Center) },
                        leadingIcon = { Icon(Icons.Filled.Lock, contentDescription = null) },
                        visualTransformation = PasswordVisualTransformation(),
                        singleLine = true,
                        keyboardOptions = KeyboardOptions(
                            keyboardType = KeyboardType.NumberPassword,
                            imeAction = ImeAction.Done,
                        ),
                        modifier = Modifier.fillMaxWidth(),
                    )

                    if (errorMessage != null) {
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .background(Danger.copy(alpha = 0.12f), RoundedCornerShape(8.dp))
                                .padding(10.dp),
                            verticalAlignment = Alignment.CenterVertically,
                        ) {
                            Text(errorMessage, color = Danger, style = MaterialTheme.typography.bodySmall)
                        }
                    }

                    Spacer(Modifier.height(4.dp))

                    Button(
                        onClick = { focus.clearFocus(); onUnlock(pin) },
                        enabled = pin.length == AccessCodeStore.PIN_LENGTH,
                        shape = RoundedCornerShape(10.dp),
                        modifier = Modifier.fillMaxWidth().height(48.dp),
                    ) {
                        Icon(Icons.Filled.LockOpen, contentDescription = null)
                        Spacer(Modifier.width(8.dp))
                        Text("Unlock", fontWeight = FontWeight.SemiBold)
                    }

                    // Biometric button — only if available and a callback was supplied
                    if (onBiometricRequest != null &&
                        biometricAvailability == BiometricAvailability.AVAILABLE) {
                        OutlinedButton(
                            onClick = onBiometricRequest,
                            shape = RoundedCornerShape(10.dp),
                            modifier = Modifier.fillMaxWidth().height(48.dp),
                        ) {
                            Icon(Icons.Filled.Fingerprint, contentDescription = null)
                            Spacer(Modifier.width(8.dp))
                            Text("Unlock with biometric")
                        }
                    }

                    // Forgot PIN
                    TextButton(
                        onClick = onForgotPin,
                        modifier = Modifier.align(Alignment.End),
                    ) {
                        Text("Forgot PIN?")
                    }

                    if (!recoveryEmailHint.isNullOrBlank()) {
                        Text(
                            "Reset link will be sent to: $recoveryEmailHint",
                            style = MaterialTheme.typography.labelSmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                            modifier = Modifier.alpha(0.7f),
                        )
                    }
                }
            }

            Spacer(Modifier.height(20.dp))
            Text(
                "v${com.admin.family.BuildConfig.VERSION_NAME}  ·  Family Safety",
                style = MaterialTheme.typography.labelSmall,
                fontFamily = FontFamily.Monospace,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.alpha(0.5f),
            )
        }
    }
}
