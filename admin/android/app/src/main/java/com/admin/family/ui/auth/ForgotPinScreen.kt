package com.admin.family.ui.auth

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Key
import androidx.compose.material.icons.filled.Lock
import androidx.compose.material.icons.filled.Warning
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
import androidx.compose.ui.text.input.KeyboardCapitalization
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import com.admin.family.data.auth.AccessCodeStore
import com.admin.family.ui.theme.Danger
import com.admin.family.ui.theme.Success

/**
 * Forgot-PIN flow — OFFLINE via backup codes.
 *
 * Steps:
 *   1. ENTER_CODE  — user types one of their saved backup codes
 *   2. NEW_PIN     — user enters a new 6-digit PIN + confirm
 *   3. DONE        — success, tap to return
 *
 * Caller must provide:
 *   - verifyCode(input): Boolean — checks + burns the code
 *   - setNewPin(newPin): Boolean — saves the new PIN
 *   - remainingCodes: Int        — how many backup codes remain (for hint)
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ForgotPinScreen(
    onBack: () -> Unit,
    verifyCode: (String) -> Boolean,
    setNewPin: (String) -> Boolean,
    remainingCodes: Int,
) {
    var step by remember { mutableStateOf(Step.ENTER_CODE) }
    var codeInput by remember { mutableStateOf("") }
    var newPin by remember { mutableStateOf("") }
    var confirmPin by remember { mutableStateOf("") }
    var localError by remember { mutableStateOf<String?>(null) }
    var codesLeft by remember { mutableStateOf(remainingCodes) }

    val focus = LocalFocusManager.current

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
                .padding(horizontal = 24.dp, vertical = 24.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            // ═══ Top bar ═══
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                IconButton(onClick = onBack) {
                    Icon(Icons.Filled.ArrowBack, contentDescription = "Back")
                }
                Text(
                    "Recover access",
                    style = MaterialTheme.typography.titleLarge,
                    fontWeight = FontWeight.Bold,
                )
            }

            Spacer(Modifier.height(12.dp))

            // ═══ Step indicator ═══
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceEvenly,
            ) {
                StepDot(1, "Backup code", step.ordinal >= 0)
                StepDot(2, "New PIN", step.ordinal >= 1)
                StepDot(3, "Done", step.ordinal >= 2)
            }

            Spacer(Modifier.height(24.dp))

            // ═══ Content ═══
            Card(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(16.dp),
                elevation = CardDefaults.cardElevation(defaultElevation = 1.dp),
            ) {
                Column(
                    modifier = Modifier.padding(20.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp),
                ) {
                    when (step) {
                        Step.ENTER_CODE -> EnterCodeStep(
                            codeInput = codeInput,
                            onCodeChange = { codeInput = it.uppercase().take(9) },
                            localError = localError,
                            codesLeft = codesLeft,
                            onSubmit = {
                                focus.clearFocus()
                                localError = null
                                val normalized = codeInput.trim()
                                if (normalized.length < 8) {
                                    localError = "Enter the full 8-character code"
                                } else if (verifyCode(normalized)) {
                                    codesLeft -= 1
                                    step = Step.NEW_PIN
                                } else {
                                    localError = "Invalid or already used code"
                                }
                            },
                        )

                        Step.NEW_PIN -> NewPinStep(
                            newPin = newPin,
                            confirmPin = confirmPin,
                            onNewPinChange = { newPin = it.filter { c -> c.isDigit() }.take(6) },
                            onConfirmPinChange = { confirmPin = it.filter { c -> c.isDigit() }.take(6) },
                            localError = localError,
                            onSubmit = {
                                focus.clearFocus()
                                localError = null
                                if (newPin.length != AccessCodeStore.PIN_LENGTH) {
                                    localError = "PIN must be ${AccessCodeStore.PIN_LENGTH} digits"
                                } else if (newPin != confirmPin) {
                                    localError = "PINs do not match"
                                    confirmPin = ""
                                } else if (setNewPin(newPin)) {
                                    step = Step.DONE
                                } else {
                                    localError = "Failed to save PIN"
                                }
                            },
                        )

                        Step.DONE -> DoneStep(
                            codesLeft = codesLeft,
                            onBack = onBack,
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

// ───────────────────────────────────────────────────────────────
// Step composables
// ───────────────────────────────────────────────────────────────

@Composable
private fun EnterCodeStep(
    codeInput: String,
    onCodeChange: (String) -> Unit,
    localError: String?,
    codesLeft: Int,
    onSubmit: () -> Unit,
) {
    Text(
        "Enter a backup code",
        style = MaterialTheme.typography.titleMedium,
        fontWeight = FontWeight.Bold,
    )
    Text(
        "Type one of the codes you saved during setup. " +
                "Format: XXXX-XXXX (dashes optional).",
        style = MaterialTheme.typography.bodySmall,
        color = MaterialTheme.colorScheme.onSurfaceVariant,
    )

    Spacer(Modifier.height(4.dp))

    // Warning if 0 codes left
    if (codesLeft <= 0) {
        Card(
            modifier = Modifier.fillMaxWidth(),
            colors = CardDefaults.cardColors(
                containerColor = Danger.copy(alpha = 0.12f),
            ),
            shape = RoundedCornerShape(10.dp),
        ) {
            Row(
                modifier = Modifier.padding(12.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Icon(
                    Icons.Filled.Warning,
                    contentDescription = null,
                    tint = Danger,
                    modifier = Modifier.size(20.dp),
                )
                Spacer(Modifier.width(10.dp))
                Text(
                    "No backup codes remaining. You cannot recover this account.",
                    style = MaterialTheme.typography.bodySmall,
                    color = Danger,
                )
            }
        }
    }

    OutlinedTextField(
        value = codeInput,
        onValueChange = onCodeChange,
        label = { Text("Backup code") },
        placeholder = { Text("XXXX-XXXX") },
        leadingIcon = { Icon(Icons.Filled.Key, contentDescription = null) },
        singleLine = true,
        enabled = codesLeft > 0,
        keyboardOptions = KeyboardOptions(
            keyboardType = KeyboardType.Text,
            capitalization = KeyboardCapitalization.Characters,
            imeAction = ImeAction.Done,
        ),
        modifier = Modifier.fillMaxWidth(),
    )

    ErrorBanner(localError)

    Button(
        onClick = onSubmit,
        enabled = codeInput.length >= 8 && codesLeft > 0,
        shape = RoundedCornerShape(10.dp),
        modifier = Modifier.fillMaxWidth().height(48.dp),
    ) {
        Icon(Icons.Filled.CheckCircle, contentDescription = null)
        Spacer(Modifier.width(8.dp))
        Text("Verify code", fontWeight = FontWeight.SemiBold)
    }

    if (codesLeft > 0) {
        Text(
            "$codesLeft backup code(s) remaining after this one",
            style = MaterialTheme.typography.labelSmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            modifier = Modifier.alpha(0.7f),
        )
    }
}

@Composable
private fun NewPinStep(
    newPin: String,
    confirmPin: String,
    onNewPinChange: (String) -> Unit,
    onConfirmPinChange: (String) -> Unit,
    localError: String?,
    onSubmit: () -> Unit,
) {
    Text(
        "Set a new PIN",
        style = MaterialTheme.typography.titleMedium,
        fontWeight = FontWeight.Bold,
    )
    Text(
        "${AccessCodeStore.PIN_LENGTH} digits. Stored on this device.",
        style = MaterialTheme.typography.bodySmall,
        color = MaterialTheme.colorScheme.onSurfaceVariant,
    )

    OutlinedTextField(
        value = newPin,
        onValueChange = onNewPinChange,
        label = { Text("New PIN") },
        placeholder = { Text("••••••", textAlign = TextAlign.Center) },
        leadingIcon = { Icon(Icons.Filled.Lock, contentDescription = null) },
        visualTransformation = PasswordVisualTransformation(),
        singleLine = true,
        keyboardOptions = KeyboardOptions(
            keyboardType = KeyboardType.NumberPassword,
            imeAction = ImeAction.Next,
        ),
        modifier = Modifier.fillMaxWidth(),
    )

    OutlinedTextField(
        value = confirmPin,
        onValueChange = onConfirmPinChange,
        label = { Text("Confirm PIN") },
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

    ErrorBanner(localError)

    Button(
        onClick = onSubmit,
        enabled = newPin.length == AccessCodeStore.PIN_LENGTH &&
                confirmPin.length == AccessCodeStore.PIN_LENGTH,
        shape = RoundedCornerShape(10.dp),
        modifier = Modifier.fillMaxWidth().height(48.dp),
    ) {
        Icon(Icons.Filled.CheckCircle, contentDescription = null)
        Spacer(Modifier.width(8.dp))
        Text("Save PIN", fontWeight = FontWeight.SemiBold)
    }
}

@Composable
private fun DoneStep(
    codesLeft: Int,
    onBack: () -> Unit,
) {
    Row(verticalAlignment = Alignment.CenterVertically) {
        Icon(Icons.Filled.CheckCircle, contentDescription = null, tint = Success)
        Spacer(Modifier.width(8.dp))
        Text(
            "PIN updated",
            style = MaterialTheme.typography.titleMedium,
            fontWeight = FontWeight.Bold,
        )
    }
    Text(
        "Your new PIN is ready. You can unlock the app now.",
        style = MaterialTheme.typography.bodyMedium,
    )

    if (codesLeft in 1..2) {
        Spacer(Modifier.height(8.dp))
        Card(
            modifier = Modifier.fillMaxWidth(),
            colors = CardDefaults.cardColors(
                containerColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.6f),
            ),
            shape = RoundedCornerShape(10.dp),
        ) {
            Text(
                "You have only $codesLeft backup code(s) left. " +
                        "Consider generating new ones in Settings.",
                style = MaterialTheme.typography.bodySmall,
                modifier = Modifier.padding(12.dp),
            )
        }
    }

    Spacer(Modifier.height(8.dp))

    Button(
        onClick = onBack,
        shape = RoundedCornerShape(10.dp),
        modifier = Modifier.fillMaxWidth().height(48.dp),
    ) {
        Text("Back to unlock", fontWeight = FontWeight.SemiBold)
    }
}

@Composable
private fun ErrorBanner(error: String?) {
    if (error != null) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .background(Danger.copy(alpha = 0.12f), RoundedCornerShape(8.dp))
                .padding(10.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Text(error, color = Danger, style = MaterialTheme.typography.bodySmall)
        }
    }
}

@Composable
private fun StepDot(index: Int, label: String, active: Boolean) {
    Column(horizontalAlignment = Alignment.CenterHorizontally) {
        Box(
            modifier = Modifier
                .size(28.dp)
                .background(
                    color = if (active) MaterialTheme.colorScheme.primary
                    else MaterialTheme.colorScheme.surfaceVariant,
                    shape = RoundedCornerShape(50),
                ),
            contentAlignment = Alignment.Center,
        ) {
            Text(
                "$index",
                color = if (active) MaterialTheme.colorScheme.onPrimary
                else MaterialTheme.colorScheme.onSurfaceVariant,
                style = MaterialTheme.typography.labelMedium,
                fontWeight = FontWeight.Bold,
            )
        }
        Spacer(Modifier.height(4.dp))
        Text(
            label,
            style = MaterialTheme.typography.labelSmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            modifier = Modifier.alpha(if (active) 1f else 0.5f),
        )
    }
}

private enum class Step { ENTER_CODE, NEW_PIN, DONE }
